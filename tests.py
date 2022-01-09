from contextlib import contextmanager
import concurrent.futures
import sys
import time

import pytest

from tail_recursive import tail_recursive, FeatureSet


def non_recursive_factorial(n):
    result = 1
    for coefficient in range(2, n + 1):
        result *= coefficient
    return result


def test__repr__():

    def func():
        pass

    decorated_func = tail_recursive(func)

    assert repr(decorated_func) == f"tail_recursive(func={repr(func)})"


def test_to_string():

    def func():
        pass

    decorated_func = tail_recursive(func)

    # Without arguments.
    assert (
        decorated_func.tail_call()._to_string()
        == f"tail_recursive(func={repr(func)}).tail_call()"
    )

    # With arguments.
    assert decorated_func.tail_call(
        "first_arg", 2, [],
        first_kwarg="1", second_kwarg=2, third_kwarg={},
    )._to_string() == f"tail_recursive(func=" + repr(func) + ").tail_call('first_arg', 2, [], first_kwarg='1', second_kwarg=2, third_kwarg={})"


def test_nested_tail_call_mode_raises_exception_for_unknown_feature_set():

    with pytest.raises(ValueError) as excinfo:
        @tail_recursive(feature_set="not_a_feature_set")
        def _():
            pass

    assert "'not_a_feature_set' is not a valid FeatureSet" in str(
        excinfo.value)


def test_nested_tail_call_mode_converts_string_to_feature_set():

    @tail_recursive(feature_set="full")
    def _():
        pass

    @tail_recursive(feature_set="base")
    def _():
        pass


def test_factorial_fails_when_max_recursion_depth_is_reached():
    for feature_set in (FeatureSet.FULL, FeatureSet.BASE):

        @tail_recursive(feature_set=feature_set)
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
    for feature_set in (FeatureSet.FULL, FeatureSet.BASE):

        @tail_recursive(feature_set=feature_set)
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
    for feature_set in (FeatureSet.FULL, FeatureSet.BASE):

        @tail_recursive(feature_set=feature_set)
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

    @tail_recursive(feature_set=FeatureSet.BASE)
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

    @tail_recursive(feature_set=FeatureSet.FULL)
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


def test_factorial_succeeds_with_operator_overloading_of_tail_calls():

    @tail_recursive
    def factorial(n):
        if n == 1:
            return n
        return n * factorial.tail_call(n - 1)

    assert factorial(1) == non_recursive_factorial(1) == 1
    assert factorial(3) == non_recursive_factorial(3) == 6
    assert factorial(4) == non_recursive_factorial(4) == 24
    assert factorial(6) == non_recursive_factorial(6) == 720

    n = sys.getrecursionlimit() + 100
    assert factorial(n) == non_recursive_factorial(n)


def test_factorial_succeeds_with_lru_cache_and_tail_recursion():
    import functools

    for feature_set in (FeatureSet.FULL, FeatureSet.BASE):
        @tail_recursive(feature_set=feature_set)
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
    for feature_set in (FeatureSet.FULL, FeatureSet.BASE):

        @tail_recursive(feature_set=feature_set)
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
    for feature_set in (FeatureSet.FULL, FeatureSet.BASE):

        @tail_recursive(feature_set=feature_set)
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

    @tail_recursive(feature_set="base")
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

    @tail_recursive(feature_set="full")
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


def test_fibonacci_succeeds_with_operator_overloading_of_tail_calls():
    import functools

    @tail_recursive(feature_set="full")
    # Requires ``lru_cache`` because this version of fibonacci is highly inefficient.
    @functools.lru_cache
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci.tail_call(n - 1) + fibonacci.tail_call(n - 2)

    assert fibonacci(0) == non_recursive_fibonacci(0) == 0
    assert fibonacci(1) == non_recursive_fibonacci(1) == 1
    assert fibonacci(4) == non_recursive_fibonacci(4) == 3
    assert fibonacci(7) == non_recursive_fibonacci(7) == 13

    n = sys.getrecursionlimit() + 1
    assert fibonacci(n) == non_recursive_fibonacci(n)


def test_tail_call_as_part_for_datastructure_fails():

    @tail_recursive
    def square_and_triangular_numbers(n):
        square = n**2
        if n == 1:
            triangular_number = n
        else:
            triangular_number = n + \
                square_and_triangular_numbers.tail_call(
                    n - 1
                )[1]
        return square, triangular_number

    try:
        assert square_and_triangular_numbers(3) != (9, 6)
    except:
        pass


def test_tail_call_as_part_for_datastructure_with_factory_succeeds():

    @tail_recursive
    def tuple_factory(*args):
        return tuple(args)

    @tail_recursive
    def square_and_triangular_numbers(n):
        square = n**2
        if n == 1:
            triangular_number = n
        else:
            triangular_number = n + square_and_triangular_numbers.tail_call(
                n - 1
            )[1]
        return tuple_factory.tail_call(square, triangular_number)

    assert square_and_triangular_numbers(3) == (9, 6)


def test_tail_call_with_dataclass_succeeds():
    from dataclasses import dataclass

    @tail_recursive
    @dataclass
    class SquareAndTriangularNumber:
        square: int
        triangular: int = 1

    @tail_recursive(feature_set="full")
    def square_and_triangular_numbers(n):
        square_and_triangular_number = SquareAndTriangularNumber.tail_call(
            square=n**2,
            triangular=1 if n == 1
            else n + square_and_triangular_numbers.tail_call(n - 1).triangular
        )
        return square_and_triangular_number

    assert square_and_triangular_numbers(3).square == 9
    assert square_and_triangular_numbers(3).triangular == 6


def test_class_property():
    import functools

    class MathStuff:

        def __init__(self, n):
            self.n = n

        @tail_recursive(feature_set="full")
        # Requires ``lru_cache`` because this version of fibonacci is highly inefficient.
        @functools.lru_cache
        def fibonacci(self, n):
            if n <= 1:
                return n
            return self.fibonacci.tail_call(self, n - 1) + self.fibonacci.tail_call(self, n - 2)

        @property
        @tail_recursive
        def fib_of_n(self):
            return self.fibonacci.tail_call(self, self.n)

    assert MathStuff(0).fib_of_n == non_recursive_fibonacci(0) == 0
    assert MathStuff(1).fib_of_n == non_recursive_fibonacci(1) == 1
    assert MathStuff(4).fib_of_n == non_recursive_fibonacci(4) == 3
    assert MathStuff(7).fib_of_n == non_recursive_fibonacci(7) == 13

    n = sys.getrecursionlimit() + 1
    assert MathStuff(n).fib_of_n == non_recursive_fibonacci(n)


def test_lst_concatenation_succeeds_for_arbitrary_operator_order():
    # Test that this works using python's standard recursion
    def non_tail_recursive_func1(is_base_case=False):
        if is_base_case:
            return [1]
        return non_tail_recursive_func1(True) + [2]

    @tail_recursive
    def func1(is_base_case=False):
        if is_base_case:
            return [1]
        return func1.tail_call(True) + [2]

    # Test that this works using python's standard recursion
    def non_tail_recursive_func2(is_base_case=False):
        if is_base_case:
            return [2]
        return [1] + non_tail_recursive_func2(True)

    @tail_recursive
    def func2(is_base_case=False):
        if is_base_case:
            return [2]
        return [1] + func2.tail_call(True)

    for func, description in (
            (non_tail_recursive_func1, "Standard python `<recursive function returning list>(...) + <list>`"),
            (func1, "Tail recursive `<recursive function returning list>.tail_call(...) + <list>`"),
            (non_tail_recursive_func2, "Standard python `<list> + <recursive function returning list>(...)`"),
            (func2, "Tail recursive `<list> + <recursive function returning list>.tail_call(...)`")
    ):
        try:
            assert func() == [1, 2], f"{description} is incorrect"
        except Exception as err:
            return pytest.fail(f"{description} failed with error {err}")


def test_reverse_succeeds_with_operator_overloading():
    def non_tail_recursive_reverse(lst):
        """Standard python recursive reverse function"""
        if len(lst) <= 1:
            return lst

        start, *middle, end = lst
        return [end] + non_tail_recursive_reverse(middle) + [start]

    @tail_recursive
    def reverse(lst):
        """Tail recursive reverse function"""
        if len(lst) <= 1:
            return lst

        start, *middle, end = lst
        return [end] + reverse.tail_call(middle) + [start]

    with set_max_recursion_depth(100):
        for n, expect_non_tail_recursive_fails_with_err in (
                (10, None),
                (1000, RecursionError),
        ):
            lst = list(range(n))
            expected_result = list(reversed(lst))

            try:
                print(expect_non_tail_recursive_fails_with_err)
                assert non_tail_recursive_reverse(lst) == expected_result, \
                    f"{non_tail_recursive_reverse.__doc__} is incorrect"

                if expect_non_tail_recursive_fails_with_err is not None:
                    pytest.fail(
                        f"{non_tail_recursive_reverse.__doc__} was expected to fail "
                        f"with error '{expect_non_tail_recursive_fails_with_err.__qualname__}'"
                    )
            except Exception as err:
                if not isinstance(err, expect_non_tail_recursive_fails_with_err):
                    pytest.fail(f"{non_tail_recursive_reverse.__doc__} unexpectedly failed with error {err}")

            try:
                assert reverse(lst) == expected_result, f"{reverse.__doc__} is incorrect"
            except Exception as err:
                pytest.fail(f"{reverse.__doc__} failed with error {err}")


@contextmanager
def set_max_recursion_depth(depth):
    original_depth = sys.getrecursionlimit()
    sys.setrecursionlimit(depth)
    yield
    sys.setrecursionlimit(original_depth)