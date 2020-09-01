from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List


_UNWRAPPED_FUNC_ATTR_NAME = "_unwrapped_tail_recursive_func"


@dataclass(init=False)
class TailCall:
    func: Callable
    args: List[Any]
    kwargs: Dict[str, Any]

    def __init__(self, func: Callable, *args, **kwargs):
        self.func = getattr(func, _UNWRAPPED_FUNC_ATTR_NAME, func)
        self.args = args
        self.kwargs = kwargs


def tail_recursive(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        current_tail_return_value: TailCall = TailCall(
            func, *args, **kwargs)
        while True:
            new_return_value: Any = current_tail_return_value.func(
                *current_tail_return_value.args,
                **current_tail_return_value.kwargs
            )
            if isinstance(new_return_value, TailCall):
                current_tail_return_value = new_return_value
                continue
            return new_return_value
    setattr(wrapper, _UNWRAPPED_FUNC_ATTR_NAME, func)
    return wrapper
