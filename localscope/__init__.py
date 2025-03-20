import builtins
import dis
import functools as ft
import inspect
import logging
import sys
import textwrap
import types
from typing import Any, Callable, Dict, Iterable, Optional, Set, Union


LOGGER = logging.getLogger(__name__)
PY_LT_3_13 = sys.version_info < (3, 13)


def localscope(
    func: Optional[Union[types.FunctionType, types.CodeType]] = None,
    *,
    predicate: Optional[Callable] = None,
    allowed: Optional[Union[Iterable[str], str]] = None,
    allow_closure: bool = False,
):
    """
    Restrict the scope of a callable to local variables to avoid unintentional
    information ingress.

    Args:
        func : Callable whose scope to restrict.
        predicate : Predicate to determine whether a global variable is allowed in the
            scope. Defaults to allow any module.
        allowed: Names of globals that are allowed to enter the scope.
        allow_closure: Allow access to non-local variables from the enclosing scope.

    Attributes:
        mfc: Decorator allowing *m*\\ odules, *f*\\ unctions, and *c*\\ lasses to enter
            the local scope.

    Examples:

        Basic example demonstrating the functionality of localscope.

        >>> from localscope import localscope
        >>>
        >>> a = 'hello world'
        >>>
        >>> @localscope
        ... def print_a():
        ...     print(a)
        Traceback (most recent call last):
        ...
        localscope.LocalscopeException: `a` is not a permitted global (file "...",
            line 1, in print_a)

        The scope of a function can be extended by providing an iterable of allowed
        variable names or a string of space-separated allowed variable names.

        >>> a = 'hello world'
        >>>
        >>> @localscope(allowed=['a'])
        ... def print_a():
        ...     print(a)
        >>>
        >>> print_a()
        hello world

        The predicate keyword argument can be used to control which `values` are allowed
        to enter the scope (by default, only modules may be used in functions).

        >>> a = 'hello world'
        >>>
        >>> @localscope(predicate=lambda x: isinstance(x, str))
        ... def print_a():
        ...     print(a)
        >>>
        >>> print_a()
        hello world

        Localscope is strict by default, but :code:`localscope.mfc` can be used to allow
        modules, functions, and classes to enter the function scope: a common use case
        in notebooks.

        >>> class MyClass:
        ...     pass
        >>>
        >>> @localscope.mfc
        ... def create_instance():
        ...     return MyClass()
        >>>
        >>> create_instance()
        <MyClass object at 0x...>

    Notes:

        The localscope decorator analyses the decorated function at the time of
        declaration because static analysis has a minimal impact on performance and it
        is easier to implement.

        This also ensures localscope does not affect how your code runs in any way.

        >>> def my_func():
        ...     pass
        >>>
        >>> my_func is localscope(my_func)
        True
    """
    # Set defaults and construct partial if the callable has not yet been provided for
    # parameterized decorators, e.g., @localscope(allowed={"foo", "bar"}). This is a
    # thin wrapper around the actual implementation `_localscope`. The wrapper
    # reconstructs an informative traceback.
    if isinstance(allowed, str):
        allowed = allowed.split()
    allowed = set(allowed) if allowed else set()
    predicate = predicate or inspect.ismodule
    if not func:
        return ft.partial(
            localscope,
            allow_closure=allow_closure,
            allowed=allowed,
            predicate=predicate,
        )

    return _localscope(
        func,
        allow_closure=allow_closure,
        allowed=allowed,
        predicate=predicate,
        _globals={},
    )


class LocalscopeException(RuntimeError):
    """
    Raised when a callable tries to access a non-local variable.
    """

    def __init__(
        self,
        message: str,
        code: types.CodeType,
        instruction: dis.Instruction,
        lineno: Optional[int] = None,
    ) -> None:
        source = None
        # TODO: Conditional coverage.
        if PY_LT_3_13:  # pragma: no cover
            lineno = (
                instruction.starts_line  # type: ignore[attr-defined]
                if lineno is None
                else lineno
            )
        else:  # pragma: no cover
            lineno = (
                instruction.line_number  # type: ignore[attr-defined]
                if lineno is None
                else lineno
            )

        if lineno is not None:
            # Add the source code if we can find it.
            try:
                # Get the source, dedent, re-indent, and add a marker where the
                # error occurred.
                lines, start = inspect.getsourcelines(code)
                lines = textwrap.dedent("".join(lines)).split("\n")
                text = "\n".join(
                    f"{no:3}: {line}" for no, line in enumerate(lines, start=start)
                )
                lines = textwrap.indent(text, "    ").split("\n")
                offset = lineno - start
                lines[offset] = "--> " + lines[offset][4:]

                # Don't show all lines of the source.
                lines = lines[max(0, offset - 2) : offset + 3]
                source = "\n".join(lines)
            except OSError:  # pragma: no cover
                pass
        message = (
            f'{message} (file "{code.co_filename}", line {lineno}, in {code.co_name})'
        )
        if source:
            message = f"{message}\n{source}"
        super().__init__(message)


def _localscope(
    func: Union[types.FunctionType, types.CodeType],
    *,
    predicate: Callable,
    allowed: Set[str],
    allow_closure: bool,
    _globals: Dict[str, Any],
):
    """
    Args:
        ...: Same as for the wrapper :func:`localscope`.
        _globals : Globals associated with the root callable which are passed to
            dependent code blocks for analysis.
    """

    # Extract global variables from a function
    # (https://docs.python.org/3/library/types.html#types.FunctionType) or keep the
    # explicitly provided globals for code objects
    # (https://docs.python.org/3/library/types.html#types.CodeType).
    if isinstance(func, types.FunctionType):
        code = func.__code__
        _globals = {**func.__globals__, **_safely_get_closure_vars(func).nonlocals}
    else:
        code = func

    # Add function arguments to the list of allowed exceptions. We only take
    # `code.co_argcount + code.co_kwonlyargcount` variables because `code.co_varnames`
    # contains all local variables.
    has_varargs = 1 if code.co_flags & inspect.CO_VARARGS else 0
    allowed.update(
        code.co_varnames[: code.co_argcount + code.co_kwonlyargcount + has_varargs]
    )

    # Construct set of forbidden operations. The first accesses global variables. The
    # second accesses variables from the outer scope.
    forbidden_opnames = {"LOAD_GLOBAL"}
    if not allow_closure:
        forbidden_opnames.add("LOAD_DEREF")

    LOGGER.info("analysing instructions for %s...", func)
    lineno: Any = None
    for instruction in dis.get_instructions(code):
        LOGGER.info(instruction)
        # TODO: Conditional coverage.
        if PY_LT_3_13:  # pragma: no cover
            if instruction.starts_line is not None:  # type: ignore[attr-defined]
                lineno = instruction.starts_line  # type: ignore[attr-defined]
        else:  # pragma: no cover
            if instruction.line_number is not None:  # type: ignore[attr-defined]
                lineno = instruction.line_number  # type: ignore[attr-defined]
        name = instruction.argval
        if instruction.opname in forbidden_opnames:
            # Variable explicitly allowed by name or in `builtins`.
            if name in allowed or hasattr(builtins, name):
                continue
            # Complain if the variable is not available.
            if name not in _globals:
                raise LocalscopeException(
                    f"`{name}` is not in globals", code, instruction, lineno
                )
            # Check if variable is allowed by value.
            value = _globals[name]
            if not predicate(value):
                raise LocalscopeException(
                    f"`{name}` is not a permitted global", code, instruction, lineno
                )
        elif instruction.opname == "STORE_DEREF":
            # Store a new allowed variable which has been created in the scope of the
            # function.
            allowed.add(name)

    # Deal with code objects recursively after adding the current arguments to the
    # allowed exceptions
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            _localscope(
                const,
                _globals=_globals,
                allow_closure=True,
                predicate=predicate,
                allowed=allowed,
            )

    return func


@ft.wraps(inspect.getclosurevars)
def _safely_get_closure_vars(func):  # pragma: no cover
    # This function has the same functionality as `inspect.getclosurevars`` but silently
    # discards empty cells. We need this implementation because the use of `super`
    # implicitly creates a closure for which cells are not available at the time of
    # declaration of the function.

    if inspect.ismethod(func):
        func = func.__func__

    if not inspect.isfunction(func):
        raise TypeError("{!r} is not a Python function".format(func))

    code = func.__code__
    # Nonlocal references are named in co_freevars and resolved
    # by looking them up in __closure__ by positional index
    if func.__closure__ is None:
        nonlocal_vars = {}
    else:
        # nonlocal_vars = {
        #     var: cell.cell_contents
        #     for var, cell in zip(code.co_freevars, func.__closure__)
        # }
        nonlocal_vars = {}
        for var, cell in zip(code.co_freevars, func.__closure__):
            try:
                nonlocal_vars[var] = cell.cell_contents
            except ValueError as ex:
                if not (var == "__class__" and str(ex) == "Cell is empty"):
                    raise ValueError(
                        f"Error when accessing cell contents for `{var}`: {ex}."
                    )

    # Global and builtin references are named in co_names and resolved
    # by looking them up in __globals__ or __builtins__
    global_ns = func.__globals__
    builtin_ns = global_ns.get("__builtins__", builtins.__dict__)
    if inspect.ismodule(builtin_ns):
        builtin_ns = builtin_ns.__dict__
    global_vars = {}
    builtin_vars = {}
    unbound_names = set()
    for name in code.co_names:
        if name in ("None", "True", "False"):
            # Because these used to be builtins instead of keywords, they
            # may still show up as name references. We ignore them.
            continue
        try:
            global_vars[name] = global_ns[name]
        except KeyError:
            try:
                builtin_vars[name] = builtin_ns[name]
            except KeyError:
                unbound_names.add(name)

    return inspect.ClosureVars(nonlocal_vars, global_vars, builtin_vars, unbound_names)


def _allow_mfc(x):
    return inspect.ismodule(x) or inspect.isfunction(x) or inspect.isclass(x)


localscope.mfc = localscope(predicate=_allow_mfc)  # type: ignore[attr-defined]
