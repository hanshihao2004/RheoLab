import numpy as np
import pytest

from rheolab.models import power_law


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0.5, [12, 6, 4]),
        (1.0, [12, 12, 12]),
        (1.5, [12, 24, 36]),
        (-1.0, [12, 0.75, 4 / 27]),
    ],
)
def test_hand_calculated_predictions(n, expected):
    predicted = power_law([1, 4, 9], k=12, n=n)
    np.testing.assert_allclose(predicted, expected, rtol=1e-12)
    assert predicted.dtype == np.float64


def test_single_point_and_repeated_unsorted_points():
    np.testing.assert_allclose(power_law([4], 12, 0.5), [6])
    rates = np.array([9.0, 1.0, 4.0, 4.0])
    before = rates.copy()
    np.testing.assert_allclose(power_law(rates, 12, 0.5), [4, 12, 6, 6])
    np.testing.assert_array_equal(rates, before)


@pytest.mark.parametrize(
    "rates", [[], 1, [[1, 2]], [0], [-1], [np.nan], [np.inf], ["bad"], [True]]
)
def test_invalid_shear_rate(rates):
    with pytest.raises(ValueError, match="shear_rate"):
        power_law(rates, 1, 0.5)


@pytest.mark.parametrize(
    "k", [0, -1, np.nan, np.inf, -np.inf, [1], True, 1 + 1j, "bad"]
)
def test_invalid_k(k):
    with pytest.raises(ValueError, match="k"):
        power_law([1, 2], k, 0.5)


@pytest.mark.parametrize("n", [np.nan, np.inf, -np.inf, [1], True, 1 + 1j, "bad"])
def test_invalid_n(n):
    with pytest.raises(ValueError, match="n"):
        power_law([1, 2], 1, n)


def test_log_evaluation_avoids_intermediate_power_overflow():
    # Directly evaluating (1e200)**2 would overflow before multiplying by K.
    np.testing.assert_allclose(power_law([1e200], 1e-300, 3), [1e100], rtol=1e-12)


@pytest.mark.parametrize(
    ("rates", "k", "n"),
    [([1e300], 1e100, 2), ([1e300], 1e-100, 0), ([1e300], 1, 1e308)],
)
def test_prediction_outside_float_range(rates, k, n):
    with pytest.raises(ValueError, match="prediction"):
        power_law(rates, k, n)
