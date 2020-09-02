"""Simple package for your tail recursion needs."""

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, Tuple


@dataclass(init=False)
class tail_recursive:
    """A decorator that gives your functions the ability to be tail recursive.

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

    func: Callable[..., Any]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]

    def __init__(self, func: Callable[..., Any]):
        """Assigns the ``func`` attribute to the decorated function."""
        self.func = func  # type: ignore

    def __call__(self, *args, **kwargs) -> Any:
        @wraps(self.func)
        def wrapper(*args, **kwargs) -> Any:
            # If ``return_value`` is an instance of ``tail_recursive`` then
            # ``return_value`` will be reassigned to the return value of the
            # function stored as ``func`` called with the arguments set in the
            # call to tail_recursion.
            return_value: tail_recursive = self.tail_call(*args, **kwargs)
            while isinstance(
                (return_value := return_value.func(
                    *return_value.args,
                    **return_value.kwargs
                )),
                type(self)
            ):
                pass
            # Once ``return_value`` is no longer an instance of ``tail_recursive``, it
            # is returned.
            return return_value
        return wrapper(*args, **kwargs)

    def tail_call(self, *args, **kwargs) -> 'tail_recursive':
        """Passes arguments to a tail recursive function so that it may lazily called.

        This method should be called as the single return value of a function. This
        enables the function to be called once the after its caller function has been
        garbage collected.

        Example::

            def f():
                return tail_recursive_function.tail_call(...)
        """
        self.args = args
        self.kwargs = kwargs
        return self
