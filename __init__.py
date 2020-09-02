from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List


@dataclass(init=False)
class TailCallable:
    func: Callable
    args: List[Any]
    kwargs: Dict[str, Any]

    def __init__(self, func: Callable):
        self.func = func

    def __call__(self, *args, **kwargs):
        @wraps(self.func)
        def wrapper(*args, **kwargs):
            current_tail_return_value: TailCallable = self.tail_call(
                *args, **kwargs)
            while True:
                new_return_value: Any = current_tail_return_value.func(
                    *current_tail_return_value.args,
                    **current_tail_return_value.kwargs
                )
                if isinstance(new_return_value, type(self)):
                    current_tail_return_value = new_return_value
                    continue
                return new_return_value
        return wrapper(*args, **kwargs)

    def tail_call(self, *args, **kwargs) -> TailCallable:
        self.args = args
        self.kwargs = kwargs
        return self


def tail_recursive(func):
    return TailCallable(func)
