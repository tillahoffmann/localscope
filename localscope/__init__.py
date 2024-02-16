import builtins
import dis
import functools as ft
import inspect
import logging
import types
from typing import Any, Callable, Dict, Optional, Set, Union


LOGGER = logging.getLogger(__name__)


def localscope(
    func: Optional[Union[types.FunctionType, types.CodeType]] = None,
    *,
    predicate: Optional[Callable] = None,
    allowed: Optional[Set[str]] = None,
    allow_closure: bool = False,
    _globals: Optional[Dict[str, Any]] = None,
):
    """
    Restrict the scope of a callable to local variables to avoid unintentional
    information ingress.

    Args:
        func : Callable whose scope to restrict.
        predicate : Predicate to determine whether a global variable is allowed in the
            scope. Defaults to allow any module.
        allowed: Names of globals that are allowed to enter the scope.
        _globals : Globals associated with the root callable which are passed to
            dependent code blocks for analysis.

    Attributes:
        mfc: Decorator allowing *m*\\ odules, *f*\\ unctions, and *c*\\ lasses to enter
            the local scope.

    Examples:

        Basic example demonstrating the functionality of localscope.

        >>> a = 'hello world'
        >>> @localscope
        ... def print_a():
        ...     print(a)
        Traceback (most recent call last):
        ...
        ValueError: `a` is not a permitted global

        The scope of a function can be extended by providing a list of allowed
        exceptions.

        >>> a = 'hello world'
        >>> @localscope(allowed=['a'])
        ... def print_a():
        ...     print(a)
        >>> print_a()
        hello world

        The predicate keyword argument can be used to control which `values` are allowed
        to enter the scope (by default, only modules may be used in functions).

        >>> a = 'hello world'
        >>> allow_strings = localscope(predicate=lambda x: isinstance(x, str))
        >>> @allow_strings
        ... def print_a():
        ...     print(a)
        >>> print_a()
        hello world

        Localscope is strict by default, but :code:`localscope.mfc` can be used to allow
        modules, functions, and classes to enter the function scope: a common use case
        in notebooks.

        >>> class MyClass:
        ...     pass
        >>> @localscope.mfc
        ... def create_instance():
        ...     return MyClass()
        >>> create_instance()
        <MyClass object at 0x...>

    Notes:

        The localscope decorator analysis the decorated function (and any dependent code
        blocks) at the time of declaration because static analysis has a minimal impact
        on performance and it is easier to implement.
    """
    # Set defaults
    predicate = predicate or inspect.ismodule
    allowed = set(allowed) if allowed else set()
    if func is None:
        return ft.partial(
            localscope,
            allow_closure=allow_closure,
            predicate=predicate,
            allowed=allowed,
        )

    if isinstance(func, types.FunctionType):
        code = func.__code__
        _globals = {**func.__globals__, **inspect.getclosurevars(func).nonlocals}
    else:
        code = func
        _globals = _globals or {}

    # Add function arguments to the list of allowed exceptions
    allowed.update(code.co_varnames[: code.co_argcount])

    opnames = {"LOAD_GLOBAL"}
    if not allow_closure:
        opnames.add("LOAD_DEREF")

    LOGGER.info("analysing instructions for %s...", func)
    for instruction in dis.get_instructions(code):
        LOGGER.info(instruction)
        name = instruction.argval
        if instruction.opname in opnames:
            # Explicitly allowed
            if name in allowed or hasattr(builtins, name):
                continue
            # Complain if the variable is not available
            if name not in _globals:
                raise NameError(f"`{name}` is not in globals")
            # Get the value of the variable and check it against the predicate
            value = _globals[name]
            if not predicate(value):
                raise ValueError(f"`{name}` is not a permitted global")
        elif instruction.opname == "STORE_DEREF":
            allowed.add(name)
    # Deal with code objects recursively after adding the current arguments to the
    # allowed exceptions
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            localscope(
                const,
                _globals=_globals,
                allow_closure=True,
                predicate=predicate,
                allowed=allowed,
            )

    return func


def _allow_mfc(x):
    return inspect.ismodule(x) or inspect.isfunction(x) or inspect.isclass(x)


localscope.mfc = localscope(predicate=_allow_mfc)  # type: ignore[attr-defined]
