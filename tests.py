import concurrent.futures
import sys
import time

import pytest

from tail_recursive import tail_recursive, NestedCallMode


def non_recursive_factorial(n):
    result = 1
    for coefficient in range(2, n + 1):
        result *= coefficient
    return result


def test__repr__():

    def func():
        pass

    decorated_func = tail_recursive(func)

    # Without tail calls.
    assert repr(decorated_func) == f"tail_recursive(func={repr(func)})"

    # With tail calls.
    # Without arguments.
    assert repr(
        decorated_func.tail_call()
    ) == f"tail_recursive(func={repr(func)}).tail_call()"

    # With arguments.
    assert repr(decorated_func.tail_call(
        "first_arg", 2, [],
        first_kwarg="1", second_kwarg=2, third_kwarg={},
    )) == f"tail_recursive(func=" + repr(func) + ").tail_call('first_arg', 2, [], first_kwarg='1', second_kwarg=2, third_kwarg={})"


def test_nested_tail_call_mode_raises_exception_for_unknown_mode():

    with pytest.raises(ValueError) as excinfo:
        @tail_recursive(nested_call_mode="not_a_mode")
        def _():
            pass

    assert "'not_a_mode' is not a valid NestedCallMode" in str(excinfo.value)


def test_nested_tail_call_mode_converts_string_to_mode():

    @tail_recursive(nested_call_mode="resolve_nested_calls")
    def _():
        pass

    @tail_recursive(nested_call_mode="do_not_resolve_nested_calls")
    def _():
        pass


def test_factorial_fails_when_max_recursion_depth_is_reached():
    for nested_call_mode in (NestedCallMode.RESOLVE_NESTED_CALLS, NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS):

        @tail_recursive(nested_call_mode=nested_call_mode)
        def factorial(n, accumulator=1):
            if n == 1:
                return accumulator
            return factorial(n - 1, n * accumulator)

        assert factorial(1) == non_recursive_factorial(1) == 1
        assert factorial(3) == non_recursive_factorial(3) == 6
        assert factorial(4) == non_recursive_factorial(4) == 24
        assert factorial(6) == non_recursive_factorial(6) == 720

        n = sys.getrecursionlimit() + 1
        with pytest.raises(RecursionError) as excinfo:
            factorial(n)
        assert "maximum recursion depth" in str(excinfo.value)


def test_factorial_succeeds_with_tail_recursion():
    for nested_call_mode in (NestedCallMode.RESOLVE_NESTED_CALLS, NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS):

        @tail_recursive(nested_call_mode=nested_call_mode)
        def factorial(n, accumulator=1):
            if n == 1:
                return accumulator
            return factorial.tail_call(n - 1, n * accumulator)

        assert factorial(1) == non_recursive_factorial(1) == 1
        assert factorial(3) == non_recursive_factorial(3) == 6
        assert factorial(4) == non_recursive_factorial(4) == 24
        assert factorial(6) == non_recursive_factorial(6) == 720

        n = sys.getrecursionlimit() + 100
        assert factorial(n) == non_recursive_factorial(n)


def test_multithreaded_factorial_succeeds_with_tail_recursion():
    """Test for thread safety."""
    for nested_call_mode in (NestedCallMode.RESOLVE_NESTED_CALLS, NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS):

        @tail_recursive(nested_call_mode=nested_call_mode)
        def factorial(n, accumulator=1):
            time.sleep(0.001)
            if n == 1:
                return accumulator
            return factorial.tail_call(n - 1, n * accumulator)

        # If there is shared data accross multiple threads then the following
        # may invoke a race condition.
        n1 = 100
        n2 = 6
        ns = (n2, n1)
        n_expected_result_map = {n: non_recursive_factorial(n) for n in ns}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Runs factorial concurrently on different threads for each n of ns.
            n_factorial_future_map = {
                n: executor.submit(factorial, n) for n in ns}
            concurrent.futures.wait(n_factorial_future_map.values())
            assert n_factorial_future_map[n1].result(
            ) == n_expected_result_map[n1]
            assert n_factorial_future_map[n2].result(
            ) == n_expected_result_map[n2]


def test_multi_function_factorial_fails_with_nested_tail_call_resolution_disabled():

    @tail_recursive
    def mul(a, b):
        return a * b

    @tail_recursive(nested_call_mode=NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS)
    def factorial(n):
        if n == 1:
            return n
        return mul.tail_call(n, factorial.tail_call(n - 1))

    with pytest.raises(Exception):
        assert factorial(3) == non_recursive_factorial(3) == 6


def test_multi_function_factorial_succeeds_with_nested_tail_call_resolution_enabled():

    @tail_recursive
    def mul(a, b):
        return a * b

    @tail_recursive(nested_call_mode=NestedCallMode.RESOLVE_NESTED_CALLS)
    def factorial(n):
        if n == 1:
            return n
        return mul.tail_call(n, factorial.tail_call(n - 1))

    assert factorial(1) == non_recursive_factorial(1) == 1
    assert factorial(3) == non_recursive_factorial(3) == 6
    assert factorial(4) == non_recursive_factorial(4) == 24
    assert factorial(6) == non_recursive_factorial(6) == 720

    n = sys.getrecursionlimit() + 100
    assert factorial(n) == non_recursive_factorial(n)


def test_factorial_succeeds_with_lru_cache_and_tail_recursion():
    import functools

    for nested_call_mode in (NestedCallMode.RESOLVE_NESTED_CALLS, NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS):
        @tail_recursive(nested_call_mode=nested_call_mode)
        @functools.lru_cache
        def factorial(n, accumulator=1):
            if n == 1:
                return accumulator
            return factorial.tail_call(n - 1, n * accumulator)

        assert factorial(1) == non_recursive_factorial(1) == 1
        assert factorial(3) == non_recursive_factorial(3) == 6
        assert factorial(4) == non_recursive_factorial(4) == 24
        assert factorial(6) == non_recursive_factorial(6) == 720

        n = sys.getrecursionlimit() + 100
        assert factorial(n) == non_recursive_factorial(n)


def non_recursive_fibonacci(n):
    current_fib = 0
    next_fib = 1
    for _ in range(n):
        last_fib = current_fib
        current_fib = next_fib
        next_fib = last_fib + current_fib
    return current_fib


def test_fibonacci_fails_when_max_recursion_depth_is_reached():
    for nested_call_mode in (NestedCallMode.RESOLVE_NESTED_CALLS, NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS):

        @tail_recursive(nested_call_mode=nested_call_mode)
        def fibonacci(n, a=0, b=1):
            if n == 0:
                return a
            elif n == 1:
                return b
            return fibonacci(n - 1, b, a + b)

        assert fibonacci(0) == non_recursive_fibonacci(0) == 0
        assert fibonacci(1) == non_recursive_fibonacci(1) == 1
        assert fibonacci(4) == non_recursive_fibonacci(4) == 3
        assert fibonacci(7) == non_recursive_fibonacci(7) == 13

        n = sys.getrecursionlimit() + 1
        with pytest.raises(RecursionError) as excinfo:
            fibonacci(n)
        assert "maximum recursion depth" in str(excinfo.value)


def test_fibonacci_succeeds_with_tail_recursion():
    for nested_call_mode in (NestedCallMode.RESOLVE_NESTED_CALLS, NestedCallMode.DO_NOT_RESOLVE_NESTED_CALLS):

        @tail_recursive(nested_call_mode=nested_call_mode)
        def fibonacci(n, a=0, b=1):
            if n == 0:
                return a
            elif n == 1:
                return b
            return fibonacci.tail_call(n - 1, b, a + b)

        assert fibonacci(0) == non_recursive_fibonacci(0) == 0
        assert fibonacci(1) == non_recursive_fibonacci(1) == 1
        assert fibonacci(4) == non_recursive_fibonacci(4) == 3
        assert fibonacci(7) == non_recursive_fibonacci(7) == 13

        n = sys.getrecursionlimit() + 100
        assert fibonacci(n) == non_recursive_fibonacci(n)


def test_multi_function_fibonacci_fails_with_nested_tail_call_resolution_disabled():
    import functools

    @tail_recursive
    def add(a, b):
        return a + b

    @tail_recursive(nested_call_mode="do_not_resolve_nested_calls")
    @functools.lru_cache
    def fibonacci(n):
        if n <= 1:
            return n
        return add.tail_call(fibonacci.tail_call(n - 1), fibonacci.tail_call(n - 2))

    with pytest.raises(Exception):
        fibonacci(4)


def test_multi_function_fibonacci_succeeds_with_nested_tail_call_resolution_enabled():
    import functools

    @tail_recursive
    def add(a, b):
        return a + b

    @tail_recursive(nested_call_mode="resolve_nested_calls")
    # Requires ``lru_cache`` because this version of fibonacci is highly inefficient.
    @functools.lru_cache
    def fibonacci(n):
        if n <= 1:
            return n
        return add.tail_call(fibonacci.tail_call(n - 1), fibonacci.tail_call(n - 2))

    assert fibonacci(0) == non_recursive_fibonacci(0) == 0
    assert fibonacci(1) == non_recursive_fibonacci(1) == 1
    assert fibonacci(4) == non_recursive_fibonacci(4) == 3
    assert fibonacci(7) == non_recursive_fibonacci(7) == 13

    n = sys.getrecursionlimit() + 1
    assert fibonacci(n) == non_recursive_fibonacci(n)


def test_tail_call_as_part_for_datastructure_is_not_evaluated():

    @tail_recursive
    def add(a, b):
        return a + b

    @tail_recursive
    def getitem(obj, index):
        return obj[index]

    @tail_recursive
    def square_and_triangular_numbers(n):
        square = n**2
        if n == 1:
            triangular_number = n
        else:
            triangular_number = add.tail_call(
                n,
                getitem.tail_call(
                    square_and_triangular_numbers.tail_call(n - 1),
                    1
                )
            )
        return square, triangular_number

    assert square_and_triangular_numbers(3) != (9, 6)


def test_tail_call_as_part_for_datastructure_with_factory_succeeds():

    @tail_recursive
    def tuple_factory(*args):
        return tuple(args)

    @tail_recursive
    def add(a, b):
        return a + b

    @tail_recursive
    def getitem(obj, index):
        return obj[index]

    @tail_recursive
    def square_and_triangular_numbers(n):
        square = n**2
        if n == 1:
            triangular_number = n
        else:
            triangular_number = add.tail_call(
                n,
                getitem.tail_call(
                    square_and_triangular_numbers.tail_call(n - 1),
                    1
                )
            )
        return tuple_factory.tail_call(square, triangular_number)

    assert square_and_triangular_numbers(3) == (9, 6)
