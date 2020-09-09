"""Simple package for your tail recursion needs.

Use the ``tail_recursive`` decorator to define tail_recursive functions.

Example::

    import sys
    from tail_recursive import tail_recursive


    @tail_recursive
    def mul(a, b):
        return a * b

    @tail_recursive
    def factorial(n):
        if n == 1:
            return n
        # Nested tail calls are supported by default.
        return mul.tail_call(n, factorial.tail_call(n - 1))

    
    # Calls to tail recursive functions will not exceed the maximum recursion
    # depth, because functions are called sequentially.
    factorial(sys.getrecursionlimit() + 1)
"""

import abc
from dataclasses import dataclass
import enum
import functools
import itertools
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Union


@dataclass
class _FuncStore:
    func: Callable[..., Any]

    @property
    def _func_repr(self) -> str:
        return repr(self.func)


@dataclass
class _ArgsAndKwargsStore:
    args: List[Any]
    kwargs: Dict[str, Any]

    @property
    def _args_and_kwargs_string(self) -> str:
        return ', '.join(itertools.chain(
            (repr(arg) for arg in self.args),
            (f"{name}={repr(val)}" for name, val in self.kwargs.items())
        ))


@dataclass(init=False)
class _IndexedArgsAndKwargsAccess:
    length: int
    _accessing_object: _ArgsAndKwargsStore
    _last_arg_index: int
    _kwargs_index_key_map: Dict[int, str]

    def __init__(self, _accessing_object: _ArgsAndKwargsStore):
        self._accessing_object = _accessing_object
        self._last_arg_index = len(self._accessing_object.args) - 1
        self.length = (
            self._last_arg_index
            + len(self._accessing_object.kwargs) + 1
        )
        self._kwargs_index_key_map = {
            index: key for index, key in zip(
                range(self._last_arg_index + 1, self.length),
                self._accessing_object.kwargs.keys()
            )
        }

    def get(self, index: int) -> Any:
        if index > self._last_arg_index:
            return self._accessing_object.kwargs[self._kwargs_index_key_map[index]]
        return self._accessing_object.args[index]

    def set(self, index: int, val: Any) -> None:
        if index > self._last_arg_index:
            self._accessing_object.kwargs[self._kwargs_index_key_map[index]] = val
        else:
            self._accessing_object.args[index] = val


# Mypy doesn't currently allow abstract dataclasses (see https://github.com/python/mypy/issues/5374).
@dataclass  # type: ignore
class TailCall(abc.ABC, _FuncStore, _ArgsAndKwargsStore):
    """Stores information necessary to lazily execute a function in the future."""

    def __repr__(self) -> str:
        return f"{tail_recursive(self.func)}.tail_call({self._args_and_kwargs_string})"

    @ abc.abstractmethod
    def resolve(self):
        """Lazily and sequentially evaluates recursive tail calls while maintaining same size of callstack."""
        ...


class TailCallWithoutNestedCallResolution(TailCall):

    def resolve(self):
        resolution_value = self.func(*self.args, **self.kwargs)
        while isinstance(resolution_value, TailCall):
            resolution_value = self.func(
                *resolution_value.args,
                **resolution_value.kwargs
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
        return tail_call_with_fully_resolved_args_and_kwargs.func(
            *tail_call_with_fully_resolved_args_and_kwargs.args,
            **tail_call_with_fully_resolved_args_and_kwargs.kwargs
        )

    def set_arg_or_kwarg_of_last_item_to_resolution(self, resolution: Any):
        self.last_item.indexed_args_and_kwargs.set(
            self.last_item.resolving_arg_or_kwarg_with_index,
            resolution
        )


class TailCallWithNestedCallResolution(TailCall):

    def __init__(self, func: Callable[..., Any], args: List[Any], kwargs: Dict[str, Any]):
        # ``setattr`` stops mypy complaining.
        # Seems to be related to this issue https://github.com/python/mypy/issues/2427.
        setattr(self, "func", func)
        self.args = args
        self.kwargs = kwargs

    def resolve(self):
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


@enum.unique
class NestedCallMode(enum.Enum):
    """Different ways of resolving nested tail calls."""

    DO_NOT_RESOLVE_NESTED_CALLS: str = "do_not_resolve_nested_calls"
    RESOLVE_NESTED_CALLS: str = "resolve_nested_calls"


NESTED_CALL_MODE_TAILCALL_SUBCLASS_MAP: Dict[NestedCallMode, Type[TailCall]] = {
    NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS: TailCallWithoutNestedCallResolution,
    NestedCallMode.RESOLVE_NESTED_CALLS: TailCallWithNestedCallResolution,
}


@dataclass(init=False)
class TailCallable(_FuncStore):

    nested_call_mode: NestedCallMode

    def __init__(self, func: Callable[..., Any], *, nested_call_mode: Union[NestedCallMode, str] = NestedCallMode.RESOLVE_NESTED_CALLS):
        functools.update_wrapper(self, func)
        # ``setattr`` stops mypy complaining.
        # Seems to be related to this issue https://github.com/python/mypy/issues/2427.
        setattr(self, "func", func)
        if isinstance(nested_call_mode, NestedCallMode):
            self.nested_call_mode = nested_call_mode
        else:
            self.nested_call_mode = NestedCallMode(nested_call_mode)

    def __repr__(self) -> str:
        return f"{tail_recursive.__qualname__}(func={self._func_repr})"

    def __call__(self, *args, **kwargs) -> Any:
        return self.tail_call(*args, **kwargs).resolve()

    def tail_call(self, *args, **kwargs) -> TailCall:
        """Passes arguments to a tail recursive function so that it may lazily called.

        This method should be called as the single return value of a function. This
        enables the function to be called once the after its caller function has been
        garbage collected.

        Example::

            def f():
                return tail_recursive_function.tail_call(...)
        """
        return NESTED_CALL_MODE_TAILCALL_SUBCLASS_MAP[self.nested_call_mode](func=self.func, args=list(args), kwargs=kwargs)


def tail_recursive(_func=None, *, nested_call_mode=NestedCallMode.RESOLVE_NESTED_CALLS):
    """A decorator that gives your functions the ability to be tail recursive.

    Args:
        nested_call_mode: Defines the way in which nested calls are resolved.

    Example::

        # Pick a larger value if n is below your system's recursion limit.
        x = 5000

        def factorial_without_tail_recursion(n, accumulator=1):
            if n == 1:
                return accumulator
            return factorial_without_tail_recursion(n - 1, n * accumulator)

        try:
            # This will exceed the maximum recursion depth.
            factorial_without_tail_recursion(x)
        except RecursionError:
            pass

        @tail_recursive
        def factorial(n, accumulator=1):
            if n == 1:
                return accumulator
            return factorial.tail_call(n - 1, n * accumulator)

        # Implementation with tail recursion succeeds because the function is
        # called sequentially under the hood.
        factorial(x)

    Methods:
        tail_call(*args, **kwargs)
    """
    def decorator(func):
        return TailCallable(func, nested_call_mode=nested_call_mode)

    if _func is None:
        return decorator
    else:
        return decorator(_func)
