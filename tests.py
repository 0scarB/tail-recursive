import sys
import pytest

from tail_recursive import tail_recursive


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


def test_factorial_fails_when_max_recursion_depth_is_reached():

    @tail_recursive
    def factorial(n, accumulator=1):
        if n == 1:
            return accumulator
        return factorial(n - 1, n * accumulator)

    assert factorial(1) == 1
    assert factorial(3) == 6
    assert factorial(4) == 24
    assert factorial(6) == 720

    n = sys.getrecursionlimit() + 1
    with pytest.raises(RecursionError) as excinfo:
        factorial(n)
    assert "maximum recursion depth" in str(excinfo.value)


def test_factorial_succeeds_with_tail_recursion():

    @tail_recursive
    def factorial(n, accumulator=1):
        if n == 1:
            return accumulator
        return factorial.tail_call(n - 1, n * accumulator)

    assert factorial(1) == 1
    assert factorial(3) == 6
    assert factorial(4) == 24
    assert factorial(6) == 720

    n = sys.getrecursionlimit() + 100
    expected_result = 1
    for i in range(2, n + 1):
        expected_result *= i
    assert factorial(n) == expected_result


def test_fibonacci_fails_when_max_recursion_depth_is_reached():

    @tail_recursive
    def fibonacci(n, a=0, b=1):
        if n == 0:
            return a
        elif n == 1:
            return b
        return fibonacci(n - 1, b, a + b)

    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(4) == 3
    assert fibonacci(7) == 13

    n = sys.getrecursionlimit() + 1
    with pytest.raises(RecursionError) as excinfo:
        fibonacci(n)
    assert "maximum recursion depth" in str(excinfo.value)


def test_fibonacci_succeeds_with_tail_recursion():

    @tail_recursive
    def fibonacci(n, a=0, b=1):
        if n == 0:
            return a
        elif n == 1:
            return b
        return fibonacci.tail_call(n - 1, b, a + b)

    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(4) == 3
    assert fibonacci(7) == 13

    n = sys.getrecursionlimit() + 100
    last = 0
    expected_result = 1
    for _ in range(n - 1):
        new_last = expected_result
        expected_result = last + expected_result
        last = new_last
    assert fibonacci(n) == expected_result
