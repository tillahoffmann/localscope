from localscope import localscope, LocalscopeException
import uuid
import pytest

allowed_global = uuid.uuid4()
forbidden_global = uuid.uuid4()
integer_global = 17


def test_vanilla_function():
    @localscope
    def add(a, b):
        return a + b

    assert add(1, 2) == 3


def test_missing_global():
    def func():
        return never_declared  # noqa: F821

    with pytest.raises(LocalscopeException, match="`never_declared` is not in globals"):
        localscope(func)

    # IMPORTANT! This function can be executed, but localscope complains because the
    # global variable is not defined at the time when the function is analysed. This
    # could be improved, but, most likely, one shouldn't write functions that rely on
    # future globals in the first place.
    """
    never_declared = 123
    assert func() == 123
    """


def test_forbidden_global():
    with pytest.raises(LocalscopeException, match="`forbidden_global` is not a perm"):

        @localscope
        def return_forbidden_global():
            return forbidden_global


def test_builtin():
    @localscope
    def transpose(a, b):
        return list(zip(a, b))

    assert transpose([1, 2], [3, 4]) == [(1, 3), (2, 4)]


def test_allowed():
    @localscope(allowed=["allowed_global"])
    def return_allowed_global():
        return allowed_global

    assert return_allowed_global() == allowed_global


def test_closure():
    def wrapper():
        forbidden_closure = uuid.uuid4()

        @localscope
        def return_forbidden_closure():
            return forbidden_closure

        return return_forbidden_closure()

    with pytest.raises(LocalscopeException, match="`forbidden_closure` is not a perm"):
        wrapper()


def test_allow_any_closure():
    forbidden_closure = uuid.uuid4()

    def wrapper():
        @localscope(allow_closure=True)
        def return_forbidden_closure():
            return forbidden_closure

        return return_forbidden_closure()

    assert wrapper() == forbidden_closure


def test_allow_custom_predicate():
    decorator = localscope(predicate=lambda x: isinstance(x, int))
    with pytest.raises(LocalscopeException, match="`forbidden_global` is not a perm"):

        @decorator
        def return_forbidden_global():
            return forbidden_global

    @decorator
    def return_integer_global():
        return integer_global

    assert return_integer_global() == integer_global


def test_comprehension():
    with pytest.raises(LocalscopeException, match="`integer_global` is not a perm"):

        @localscope
        def evaluate_mse(xs, ys):  # missing argument integer_global
            return sum(((x - y) / integer_global) ** 2 for x, y in zip(xs, ys))


def test_recursive():
    with pytest.raises(LocalscopeException, match="`forbidden_global` is not a perm"):

        @localscope
        def wrapper():
            def return_forbidden_global():
                return forbidden_global

            return return_forbidden_global()


def test_recursive_without_call():
    # We even raise an exception if we don't call a function. That's necessary because
    # we can't trace all possible execution paths without actually running the function.
    with pytest.raises(LocalscopeException, match="`forbidden_global` is not a perm"):

        @localscope
        def wrapper():
            def return_forbidden_global():
                return forbidden_global


def test_recursive_local_closure():
    @localscope
    def wrapper():
        a = "hello world"

        def child():
            return a


def test_mfc():
    import sys

    x = lambda: 0  # noqa: E731

    class MyClass:
        pass

    # Check we can access modules, functions, and classes
    @localscope.mfc
    def doit():
        sys.version
        x()
        MyClass()

    x = 1

    with pytest.raises(LocalscopeException, match="`x` is not a permitted"):

        @localscope.mfc
        def breakit():
            x + 1


def test_comprehension_with_argument():
    @localscope
    def f(n):
        return [n for i in range(n)]

    assert f(2) == [2, 2]


def test_comprehension_with_closure():
    @localscope
    def f():
        n = 3
        return [n for i in range(n)]

    assert f() == [3, 3, 3]


def test_argument():
    @localscope
    def add(a):
        return a + 1

    assert add(3) == 4


def test_argument_with_closure():
    @localscope
    def add(a):
        return a + 1
        lambda: a

    assert add(3) == 4


def test_local_deref():
    @localscope
    def identity(x):
        return x
        lambda: x

    assert identity(42) == 42
