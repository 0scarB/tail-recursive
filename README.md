![tests](https://github.com/0scarB/tail-recursive/workflows/Tests/badge.svg)

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

## Nested Calls

In the previous example the whole concept of an accumulator my not fit your mental model
that well (it doesn't for me at least).
Luckily calls to `tail_call` support nested calls (i.e. another `tail_call` passed as an
argument).
Taking this functionality into consideration we can refactor the previous example.

```python
...

@tail_recursive
def mul(a, b):
    return a * b

@tail_recursive
def factorial(n):
    if n == 1:
        return n
    return mul.tail_call(n, factorial.tail_call(n - 1))

...
```

This, however, comes a performance cost and can be disabled as follows.

```python
@tail_recursive(nested_call_mode="do_not_resolve_nested_calls")
def factorial(n, accumulator=1):
    if n == 1:
        return accumulator
    return factorial.tail_call(n - 1, n * accumulator)
```

or

```python
from tail_recursive import tail_recursive, NestedCallMode

...

@tail_recursive(nested_call_mode=NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS)
def factorial(n, accumulator=1):
    ...
```

Similarly, use `nested_call_mode="resolve_nested_calls"` or `nested_call_mode=NestedCallMode.RESOLVE_NESTED_CALLS`
to explicitly enable this feature.

## Current Limitations

### Return Values

Currently tail calls that are returned as an item in a tuple or other
data structure are not evaluated.

The following will not evaluate the tail call.

```python
from tail_recursive import tail_recursive

@tail_recursive
def func(...):
    ...
    return return_val1, func.tail_call(...)
```

A workaround is to use factory functions.

```python
from tail_recursive import tail_recursive

@tail_recursive
def tuple_factory(*args):
    return tuple(args)

@tail_recursive
def func(...):
    ...
    return tuple_factory.tail_call(
        return_val1,
        func.tail_call(...)
    )
```

## Other Packages

Check out [tco](https://github.com/baruchel/tco) for an alternative api with extra functionality.
