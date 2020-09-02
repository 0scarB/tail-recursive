Use the `tail_recursive` decorator to simply define tail recursive functions.

If you are encountering **maximum recursion depth errors** or **out-of-memory crashes** tail recursion can be a helpful strategy.

### Example

```python
import tail_recursive from tail_recursive


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
    # It is important that you return the return value of the `tail_call`
    # method for tail recursion to take effect!
    return factorial.tail_call(n - 1, n * accumulator)


# Implementation with tail recursion succeeds because the function is
# called sequentially under the hood.
factorial(x)
```

The `tail_call` method returns an object which stores a function (e.g. `factorial`) and
its arguments. The function is then lazily evaluated once the object has been returned
from the caller function (in this case also `factorial`). This means that the
resources in the caller function's scope are free to be garbage collected and that its
frame is popped from the call stack before we push the returned function on.

## Other Packages

Check out [tco](https://github.com/baruchel/tco) for an alternative api with extra functionality.
