import sys
import pytest

from . import TailCall, tail_recursive


def test_factorial_fails_without_tail_recursion():

    def factorial(n, accumulator=1):
        if n == 1:
            return accumulator
        return factorial(n - 1, n * accumulator)

    n = sys.getrecursionlimit() + 1
    with pytest.raises(RecursionError) as excinfo:
        factorial(n)
    assert "maximum recursion depth" in str(excinfo.value)


def test_factorial_succeeds_with_tail_recursion():

    @tail_recursive
    def factorial(n, accumulator=1):
        if n == 1:
            return accumulator
        return TailCall(factorial, n - 1, n * accumulator)

    n = sys.getrecursionlimit() + 1
    expected_result = 1
    for i in range(2, n + 1):
        expected_result *= i
    assert factorial(n) - expected_result == 0
