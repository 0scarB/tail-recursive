"""Simple package for your tail recursion needs.

Use the ``tail_recursive`` decorator to define tail_recursive functions.

Example::

    import sys
    from tail_recursive import tail_recursive

    @tail_recursive
    def factorial(n):
        if n == 1:
            return n
        # Overloading of dunder methods such as __mul__ and __rmul__ are
        # supported by default.
        return n * factorial.tail_call(n - 1)


    # Calls to tail recursive functions will not exceed the maximum recursion
    # depth, because functions are called sequentially.
    factorial(sys.getrecursionlimit() + 1)
"""

import abc
from dataclasses import dataclass
import enum
import functools
import itertools
from typing import Any, Callable, Dict, List, Optional, Type, Union

# Dunder methods from https://docs.python.org/3/reference/datamodel.html.
_NUMERIC_DUNDER_METH_BASE_NAMES: List[str] = [
    "add",
    "sub",
    "mul",
    "matmul",
    "truediv",
    "floordiv",
    "mod",
    "divmod",
    "pow",
    "lshift",
    "rshift",
    "and",
    "xor",
    "or",
]

_NUMERIC_RIGHT_DUNDER_METH_NAMES: List[str] = [
    f"r{name}" for name in _NUMERIC_DUNDER_METH_BASE_NAMES
]
_NUMERIC_RIGHT_DUNDER_METH_NAMES_SET_WITH_UNDERSCORES = {
    f"__{meth_name}__" for meth_name in _NUMERIC_RIGHT_DUNDER_METH_NAMES
}

_NUMERIC_DUNDER_METH_NAMES: List[str] = \
    _NUMERIC_DUNDER_METH_BASE_NAMES \
    + _NUMERIC_RIGHT_DUNDER_METH_NAMES \
    + [f"i{name}" for name in _NUMERIC_DUNDER_METH_BASE_NAMES] \
    + [
        "neg",
        "pos",
        "abs",
        "invert",
        "complex",
        "int",
        "float",
        "index",
        "round",
        "trunc",
        "floor",
        "ciel"
    ]

_DUNDER_METH_NAMES: List[str] = \
    [
        # Cannot be overridden because they will break functionality:
        # "new",
        # "init",
        # "del",
        # "getattribute",
        # "setattr",
        # "get",
        # "set",
        # "delete",
        # "set_name",
        # "init_subclass",
        # "prepare",
        #
        # getattr and delattr have custom overrides (see below).
        "repr",
        "str",
        "bytes",
        "format",
        "lt",
        "le",
        "eq",
        "ne",
        "gt",
        "ge",
        "hash",
        "bool",
        "dir",
        "instancecheck",
        "subclasscheck",
        "class_getitem",
        "call",
        "len",
        "length_hint",
        "getitem",
        "setitem",
        "delitem",
        "missing",
        "iter",
        "reversed",
        "contains",
        "enter",
        "exit",
        "await",
        "aiter",
        "anext",
        "aenter",
        "aexit",
    ] \
    + _NUMERIC_DUNDER_METH_NAMES


@dataclass
class _FuncStore:
    _func: Callable[..., Any]

    @property
    def _func_repr(self) -> str:
        return repr(self._func)


@dataclass
class _ArgsAndKwargsStore:
    _args: List[Any]
    _kwargs: Dict[str, Any]

    @property
    def _args_and_kwargs_string(self) -> str:
        return ', '.join(itertools.chain(
            (repr(arg) for arg in self._args),
            (f"{name}={repr(val)}" for name, val in self._kwargs.items())
        ))


@dataclass(init=False)
class _IndexedArgsAndKwargsAccess:
    length: int
    _accessing_object: _ArgsAndKwargsStore
    _last_arg_index: int
    _kwargs_index_key_map: Dict[int, str]

    def __init__(self, _accessing_object: _ArgsAndKwargsStore):
        self._accessing_object = _accessing_object
        self._last_arg_index = len(self._accessing_object._args) - 1
        self.length = (
                self._last_arg_index
                + len(self._accessing_object._kwargs) + 1
        )
        self._kwargs_index_key_map = {
            index: key for index, key in zip(
                range(self._last_arg_index + 1, self.length),
                self._accessing_object._kwargs.keys()
            )
        }

    def get(self, index: int) -> Any:
        if index > self._last_arg_index:
            return self._accessing_object._kwargs[self._kwargs_index_key_map[index]]
        return self._accessing_object._args[index]

    def set(self, index: int, val: Any) -> None:
        if index > self._last_arg_index:
            self._accessing_object._kwargs[self._kwargs_index_key_map[index]] = val
        else:
            self._accessing_object._args[index] = val


# Mypy doesn't currently allow abstract dataclasses (see https://github.com/python/mypy/issues/5374).
@dataclass  # type: ignore
class TailCall(abc.ABC, _FuncStore, _ArgsAndKwargsStore):
    """Stores information necessary to lazily execute a function in the future."""

    def _to_string(self) -> str:
        return f"{tail_recursive(self._func)}.tail_call({self._args_and_kwargs_string})"

    @abc.abstractmethod
    def _resolve(self):
        """Lazily and sequentially evaluates recursive tail calls while maintaining same size of callstack."""
        ...


class TailCallBase(TailCall):

    def _resolve(self):
        resolution_value = self._func(*self._args, **self._kwargs)
        while isinstance(resolution_value, TailCall):
            resolution_value = self._func(
                *resolution_value._args,
                **resolution_value._kwargs
            )
        return resolution_value


@dataclass(init=False)
class _TailCallStackItem:
    tail_call: TailCall
    indexed_args_and_kwargs: _IndexedArgsAndKwargsAccess
    resolving_arg_or_kwarg_with_index: Optional[int]

    def __init__(self, tail_call: TailCall):
        self.tail_call = tail_call
        self.indexed_args_and_kwargs = _IndexedArgsAndKwargsAccess(tail_call)
        self.resolving_arg_or_kwarg_with_index = None


@dataclass(init=False)
class _TailCallStack:
    stack: List[_TailCallStackItem]
    length: int

    def __init__(self, initial_item: TailCall):
        self.stack = [_TailCallStackItem(initial_item)]
        self.length = 1

    @property
    def last_item(self):
        return self.stack[-1]

    def push(self, item: TailCall):
        self.stack.append(_TailCallStackItem(item))
        self.length += 1

    def pop_item_resolution(self):
        tail_call_with_fully_resolved_args_and_kwargs = self.stack.pop().tail_call
        self.length -= 1
        return tail_call_with_fully_resolved_args_and_kwargs._func(
            *tail_call_with_fully_resolved_args_and_kwargs._args,
            **tail_call_with_fully_resolved_args_and_kwargs._kwargs
        )

    def set_arg_or_kwarg_of_last_item_to_resolution(self, resolution: Any):
        self.last_item.indexed_args_and_kwargs.set(
            self.last_item.resolving_arg_or_kwarg_with_index,
            resolution
        )


@dataclass
class TailCallWithNestedCallResolution(TailCall):

    def _resolve(self):
        tail_call_stack = _TailCallStack(initial_item=self)
        while True:
            if tail_call_stack.last_item.resolving_arg_or_kwarg_with_index is None:
                start_arg_index = 0
            else:
                start_arg_index = tail_call_stack.last_item.resolving_arg_or_kwarg_with_index + 1
            for arg_index in range(start_arg_index, tail_call_stack.last_item.indexed_args_and_kwargs.length):
                arg = tail_call_stack.last_item.indexed_args_and_kwargs.get(
                    arg_index
                )
                if isinstance(arg, TailCall):
                    tail_call_stack.last_item.resolving_arg_or_kwarg_with_index = arg_index
                    tail_call_stack.push(arg)
                    break
            # Else block is evaluated if loop is not broken out of.
            else:
                resolution = tail_call_stack.pop_item_resolution()
                if isinstance(resolution, TailCall):
                    tail_call_stack.push(resolution)
                elif tail_call_stack.length > 0:
                    tail_call_stack.set_arg_or_kwarg_of_last_item_to_resolution(
                        resolution
                    )
                else:
                    return resolution


class TailCallWithDunderOverloads(TailCallBase):

    @staticmethod
    def _tail_call_dunder_meth_factory(dunder_meth_name: str):

        # If <self>.__r<operation>__(other) does not exist, try <other>.__<operation>__(self)
        if dunder_meth_name in _NUMERIC_RIGHT_DUNDER_METH_NAMES_SET_WITH_UNDERSCORES:
            def func(self, other, *args, **kwargs) -> Any:
                try:
                    return getattr(self, dunder_meth_name)(other, *args, **kwargs)
                except AttributeError:
                    return getattr(other, f"__{dunder_meth_name[3:]}")(self, *args, **kwargs)
        else:
            # Ignore differing parameter signatures
            def func(self, *args, **kwargs) -> Any:  # type: ignore[misc]
                return getattr(self, dunder_meth_name)(*args, **kwargs)

        def dunder_meth(self, *args, **kwargs):
            tail_call_class = type(self)
            return tail_call_class(
                _func=func,
                _args=[self] + list(args),
                _kwargs=kwargs
            )

        return dunder_meth

    def __new__(cls, *args, **kwargs):
        for dunder_meth_name_without_underscores in _DUNDER_METH_NAMES:
            dunder_meth_name = f"__{dunder_meth_name_without_underscores}__"

            setattr(cls, dunder_meth_name, cls._tail_call_dunder_meth_factory(
                dunder_meth_name
            ))
        return super().__new__(cls)

    def __init__(self, _func: Callable[..., Any], _args: List[Any], _kwargs: Dict[str, Any]):
        # ``setattr`` stops mypy complaining.
        # Seems to be related to this issue https://github.com/python/mypy/issues/2427.
        setattr(self, "_func", _func)
        self._args = _args
        self._kwargs = _kwargs

    def __getattr__(self, name):
        return type(self)(
            _func=lambda self, name: getattr(self, name),
            _args=[self, name], _kwargs={}
        )

    def __delattr__(self, name):
        return type(self)(
            _func=lambda self, name: delattr(self, name),
            _args=[self, name], _kwargs={}
        )


class TailCallWithNestedCallResolutionAndDunderOverloads(TailCallWithNestedCallResolution, TailCallWithDunderOverloads):
    pass


@enum.unique
class FeatureSet(enum.IntFlag):
    """Different ways of resolving nested tail calls."""

    BASE = 0
    NESTED_CALLS = 1
    OVERLOADING = 2
    FULL = NESTED_CALLS | OVERLOADING


FEATURE_SET_TAILCALL_SUBCLASS_MAP: Dict[FeatureSet, Type[TailCall]] = {
    FeatureSet.BASE: TailCallBase,
    FeatureSet.NESTED_CALLS: TailCallWithNestedCallResolution,
    FeatureSet.OVERLOADING: TailCallWithDunderOverloads,
    FeatureSet.NESTED_CALLS | FeatureSet.OVERLOADING: TailCallWithNestedCallResolutionAndDunderOverloads,
    FeatureSet.FULL: TailCallWithNestedCallResolutionAndDunderOverloads,
}


@dataclass(init=False)
class TailCallable(_FuncStore):
    feature_set: FeatureSet

    def __init__(self, _func: Callable[..., Any], *, feature_set: Union[FeatureSet, str] = FeatureSet.FULL):
        functools.update_wrapper(self, _func)
        # ``setattr`` stops mypy complaining.
        # Seems to be related to this issue https://github.com/python/mypy/issues/2427.
        setattr(self, "_func", _func)
        if isinstance(feature_set, FeatureSet):
            self.feature_set = feature_set
        else:
            try:
                self.feature_set = getattr(FeatureSet, feature_set.upper())
            except AttributeError as err:
                raise ValueError(f"'{feature_set}' is not a valid FeatureSet") from err

    def __repr__(self) -> str:
        return f"{tail_recursive.__qualname__}(func={self._func_repr})"

    def __call__(self, *args, **kwargs) -> Any:
        return self.tail_call(*args, **kwargs)._resolve()

    def tail_call(self, *args, **kwargs) -> TailCall:
        """Passes arguments to a tail recursive function so that it may lazily called.

        This method should be called as the single return value of a function. This
        enables the function to be called once the after its caller function has been
        garbage collected.

        Example::

            def f():
                return tail_recursive_function.tail_call(...)
        """
        return FEATURE_SET_TAILCALL_SUBCLASS_MAP[self.feature_set](_func=self._func, _args=list(args), _kwargs=kwargs)


def tail_recursive(
        _func: Optional[Callable[..., Any]] = None,
        *,
        feature_set: Union[FeatureSet, str] = FeatureSet.FULL
):
    """A decorator that gives your functions the ability to be tail recursive.

    Args:
        feature_set: Defines the feature set available when working with tail calls.
            If the feature set is set to ``"full"`` or ``FeatureSet.FULL`` then
            nested tail calls (i.e. ``<function>.tail_call([..., ]<function>.tail_call(...)[, ...])``)
            and dunder overrides (e.g. ``<function>.tail_call(...).<attribute> + <function>.tail_call(...)[<index>]``)
            are supported.
            If the feature set is set to ``"base"`` or ``FeatureSet.FULL`` then the aforementioned
            is not supported.

    Example::

        import sys
        from tail_recursive import tail_recursive

        @tail_recursive
        def factorial(n):
            if n == 1:
                return n
            # Overloading of dunder methods such as __mul__ and __rmul__ are
            # supported by default.
            return n * factorial.tail_call(n - 1)


        # Calls to tail recursive functions will not exceed the maximum recursion
        # depth, because functions are called sequentially.
        factorial(sys.getrecursionlimit() + 1)

    Methods:
        tail_call(*args, **kwargs)
    """

    def decorator(func):
        return TailCallable(func, feature_set=feature_set)

    if _func is None:
        return decorator
    else:
        return decorator(_func)
