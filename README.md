![tests](https://github.com/0scarB/tail-recursive/workflows/Tests/badge.svg)

## Installation

`pip install tail-recursive`

## Basic Usage

Use the `tail_recursive` decorator to simply define tail recursive functions.

If you are encountering **maximum recursion depth errors** or **out-of-memory crashes** tail recursion can be a helpful strategy.

### Example

```python
from tail_recursive import tail_recursive


# Pick a larger value if n is below your system's recursion limit.
x = 5000


def factorial_without_tail_recursion(n):
    if n <= 1:
        return n
    return n * factorial_without_tail_recursion(n - 1)


try:
    # This will exceed the maximum recursion depth.
    factorial_without_tail_recursion(x)
except RecursionError:
    pass


@tail_recursive
def factorial(n):
    if n <= 1:
        return n
    # It is important that you return the return value of the `tail_call`
    # method for tail recursion to take effect!
    # Note tail calls work with dunder methods, such as __mul__ and __rmul__,
    # by default.
    return n * factorial.tail_call(n - 1)


# Implementation with tail recursion succeeds because the function is
# called sequentially under the hood.
factorial(x)
```

### How it works

When a function (in this case `factorial`) is decorated by `@tail_recursive`, it returns
an object implementing the `tail_call` method. This object also overrides the `__call__`
method, meaning that it can be called just like the original function (e.g. `factorial(x)`).

Decorated functions test whether they return a call to `tail_call(...)`. If this is the case
then the return value is pushed on a call stack implemented as a list. `tail_call` returns
an object storing the function it was called on (e.g. `factorial`) and the (keyword)
arguments (e.g. `n - 1`) it was called with. If the arguments contain a nested call to `tail_call` then this
call is also pushed onto the call stack. On the other hand if `tail_call` is passed no nested
`tail_call`s then the function that it stores is called with the stored (keyword) arguments. The
return value of this lazy call then (a) replaces the argument it was passed as or (b)
returns another `tail_call` which is pushed to the stack or (c) is the final return value of
the call to the decorated function (e.g. `factorial(x)`).

But how can `factorial.tail_call(n - 1)` be multiplied by `n`? Well, the object returned by
`tail_call` overrides most dunder methods, such as `__mul__` and `__rmul__`, pushing the
equivalent of `tail_recursive(int.__rmul__).tail_call(n, factorial.tail_call(n - 1)` to the
call stack.

The call stack for `factorial(3)` would looks something like this.

1. Because `factorial(3)` is called, `<lazy_call_obj>(func=factorial, args=(3,), kwargs={})`
   is **pushed** on the stack.

```python
[
    <lazy_call_obj>(func=factorial, args=(3,), kwargs={}),
]
```

2. Because `<lazy_call_obj>(func=factorial, args=(3,), kwargs={})` contains no nested arguments,
   it is **popped** off the stack. It is then lazily evaluated, returning another `<lazy_call_obj>`, which is **pushed** to the stack.

```python
[
    <lazy_call_obj>(func=int.__rmul__, args(<lazy_call_obj>(func=factorial, args=(2,), kwargs={}), 3), kwargs={}),
]
```

3. The lazy call to `__rmul__` has a nested call as an argument. Consequentially, this
   argument is **pushed** on the call stack.

```python
[
    <lazy_call_obj>(func=int.__rmul__, args=(<lazy_call_obj>(func=factorial, args=(2,), kwargs={}), 3), kwargs={}),
    <lazy_call_obj>(func=factorial, args=(2,), kwargs={}),
]
```

4. As in step _2_ the lazy call to `factorial(2)` is **pop** off the stack and its return
   value is **pushed** on.

```python
[
    <lazy_call_obj>(func=int.__rmul__, args=(<lazy_call_obj>(func=factorial, args=(2,), kwargs={}), 3), kwargs={}),
    <lazy_call_obj>(func=int.__rmul__, args=(<lazy_call_obj>(func=factorial, args=(1,), kwargs={}), 2), kwargs={}),
]
```

5. Similarly to step _3_, because the lazy call to `__rmul__` has a nested call as an
   argument, this argument is **pushed** on the stack.

```python
[
    <lazy_call_obj>(func=int.__rmul__, args=(<lazy_call_obj>(func=factorial, args=(2,), kwargs={}), 3), kwargs={}),
    <lazy_call_obj>(func=int.__rmul__, args=(<lazy_call_obj>(func=factorial, args=(1,), kwargs={}), 2), kwargs={}),
    <lazy_call_obj>(func=factorial, args=(1,), kwargs={}),
]
```

6. `<lazy_call_obj>(func=int.__rmul__, args=(1,), kwargs={})` has no nested lazy calls
   as arguments, so it is **popped** off the stack and its return value replaces
   the argument of `__rmul__` that it was originally passed as.

```python
[
    <lazy_call_obj>(func=int.__rmul__, args=(<lazy_call_obj>(func=factorial, args=(2,), kwargs={}), 3), kwargs={}),
    <lazy_call_obj>(func=int.__rmul__, args=(1, 2), kwargs={}),
]
```

7. The same process as in _6_ is repeated, where
   `<lazy_call_obj>(func=int.__rmul__, args=(2, 1), kwargs={})` is **popped** off the
   stack and its return value replaces the second argument of the lazy call to
   `int.__rmul__(3, ...)`.

```python
[
    <lazy_call_obj>(func=int.__rmul__, args=(2, 3), kwargs={}),
]
```

8. Finally, because the lazy call to `__rmul__` no longer has any nested calls as
   arguments, it can be **popped** off the stack. Furthermore, it was not passed
   as an argument of a previous call on the stack and, for that reason, is returned
   from our decorated function (i.e. `factorial(3) = int.__rmul__(2, 3) = 6`).

```python
[]
```

## Features

### Nested Tail Calls

(only works for `feature_set="full"|FeatureSet.FULL`)

As mentioned above nested tail calls are sequentially evaluated by creating a call stack.

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

Nested calls, however, comes a performance cost and can be disabled as follows.

```python
@tail_recursive(feature_set="base")
def factorial(n, accumulator=1):
    if n == 1:
        return accumulator
    return factorial.tail_call(n - 1, n * accumulator)
```

or

```python
from tail_recursive import tail_recursive, FeatureSet

...

@tail_recursive(nested_call_mode=FeatureSet.BASE)
def factorial(n, accumulator=1):
    ...
```

Similarly, use `feature_set="full"` or `feature_set=FeatureSet.FULL`
to explicitly enable this feature.

### Dunder Method Overrides

(only works for `feature_set="full"|FeatureSet.FULL`)

`n * factorial.tail_call(n - 1)` shows that numeric operations
can be done on tail calls and so long as the result of the expression
is returned by the function. These expression will ultimately
evaluate to the same value that they would have if `tail_call` had been omitted.
This is also true for comparison and bitwise
operations, attribute and index access (i.e. `<func>.tail_call(...)[...]`)
and much more functionality provided by dunder methods.

That being said, attribute assignment (i.e. `<func>.tail_call(...).<attr> = val`)
and the functionality provided by the following dunder methods are not currently
supported with `tail_call`.

- `__del__`
- `__getattribute__`
- `__setattr__`
- `__get__`
- `__set__`
- `__delete__`
- `__set_name__`
- `__init_subclass__`
- `__prepare__`

Note that also `__init__` and `__new__` cannot be called directly on a tail call
(e.g. `<func>.tail_call(...).__init__(...)`) and are instead implicitly lazily evaluated
with the arguments passed to `tail_call` while popping off/unwinding the tail call stack.

Futhermore, dunder methods added after 3.8 and in standard library or third-party packages/modules may also not be supported.

Another important note is that dunder attributes will currently not be lazily evaluated.
e.g.

- `__doc__`
- `__name__`
- `__qualname__`
- `__module__`
- `__defaults__`
- `__defaults__`
- `__code__`
- `__globals__`
- `__dict__`
- `__closure__`
- `__annotations__`
- `__kwdefaults__`

Finally, since `__repr__` and `__str__` are overridden use
`<func>.tail_call(...)._to_string()` to pretty print tail calls.

## Usage with other Decorators

Especially in recursive algorithms it can significantly increase performance
to use memoization. In this use case it is best to place the decorator enabling
memoization after `@tail_recursive`. e.g.

```python
import functools

@tail_recursive(feature_set="full")
@functools.lru_cache
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci.tail_call(n - 1) + fibonacci.tail_call(n - 2)
```

For properties place the `@property` decorator before `@tail_recursive`.

## Current Limitations

### Return Values

Currently tail calls that are returned as item/member in a tuple or other
data structures are not evaluated.

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

Or pass the container object's type directly to `tail_recursive`.

```python
from tail_recursive import tail_recursive

@tail_recursive
def func(...):
    ...
    return tail_recursive(tuple).tail_call((
        return_val1,
        func.tail_call(...)
    ))
```

### Method Decorators

Currently, when calling `tail_call` on a decorated method, you need to explicitly pass
self (the current objects instance) as the first argument. e.g.

```python
class MathStuff:

    @tail_recursive(feature_set="full")
    def fibonacci(self, n):
        if n <= 1:
            return n
        return self.fibonacci.tail_call(self, n - 1) + self.fibonacci.tail_call(self, n - 2)
                                        ^^^^                                    ^^^^
```

## Other Packages

Check out [tco](https://github.com/baruchel/tco) for an alternative api with extra functionality.
