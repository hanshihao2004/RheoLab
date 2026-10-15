import math
from io import StringIO
from types import SimpleNamespace

import numpy as np
import pytest

from rheolab.data import read_csv
from rheolab.fitting import FitResult, fit_power_law


@pytest.mark.parametrize("n", [0.6, 1.0, 1.4, -0.5])
def test_noiseless_synthetic_data(n):
    rates = np.geomspace(0.1, 1000, 40)
    observed = 2.5 * rates ** (n - 1)
    result = fit_power_law(rates, observed)
    assert isinstance(result, FitResult)
    assert result.k == pytest.approx(2.5, rel=1e-10)
    assert result.n == pytest.approx(n, rel=1e-10)
    assert result.rmse == pytest.approx(0, abs=1e-10)
    assert result.mape_percent == pytest.approx(0, abs=1e-10)
    if n == 1:
        assert result.r_squared_log is None
    else:
        assert result.r_squared_log == pytest.approx(1, rel=1e-10)
    np.testing.assert_allclose(result.predicted_viscosity, observed, rtol=1e-10)
    np.testing.assert_allclose(result.residuals, 0, atol=1e-10)


def test_seeded_multiplicative_noise():
    rng = np.random.default_rng(20261015)
    rates = np.geomspace(0.1, 1000, 80)
    observed = 2.5 * rates ** (-0.4) * np.exp(rng.normal(0, 0.03, rates.size))
    result = fit_power_law(rates, observed)
    assert result.k == pytest.approx(2.5, rel=0.05)
    assert result.n == pytest.approx(0.6, abs=0.02)
    assert 0.99 < result.r_squared_log <= 1
    assert result.rmse > 0
    assert 0 < result.mape_percent < 5


def test_independent_hand_calculated_parameters_and_metrics():
    # x = [0,1,2,3,4]; log-errors = ln(2)*[1,-1,0,-1,1].
    # Both sum(error) and sum(x*error) are zero, so OLS recovers ln(2), -0.5.
    rates = np.exp(np.arange(5.0))
    observed = np.array([4, math.exp(-0.5), 2 / math.e, math.exp(-1.5), 4 / math.e**2])
    result = fit_power_law(rates, observed)
    expected_predictions = [
        2,
        2 * math.exp(-0.5),
        2 / math.e,
        2 * math.exp(-1.5),
        2 / math.e**2,
    ]
    expected_residuals = [2, -math.exp(-0.5), 0, -math.exp(-1.5), 2 / math.e**2]
    assert result.k == pytest.approx(2, rel=1e-12)
    assert result.n == pytest.approx(0.5, rel=1e-12)
    assert result.r_squared_log == pytest.approx(2.5 / (2.5 + 4 * math.log(2) ** 2))
    expected_rmse = math.sqrt((4 + math.exp(-1) + math.exp(-3) + 4 * math.exp(-4)) / 5)
    assert result.rmse == pytest.approx(expected_rmse)
    assert result.mape_percent == pytest.approx(60)
    np.testing.assert_allclose(result.predicted_viscosity, expected_predictions)
    np.testing.assert_allclose(result.residuals, expected_residuals, atol=1e-14)


def test_repeated_measurements_are_individually_weighted():
    rates = np.array([1, 2, 4, 8, 16, 1, 1, 1], dtype=float)
    observed = np.array([10, 8, 4, 3, 1, 20, 30, 40], dtype=float)
    design = np.column_stack([np.ones(rates.size), np.log(rates)])
    intercept, slope = np.linalg.lstsq(design, np.log(observed), rcond=None)[0]
    result = fit_power_law(rates, observed)
    assert result.k == pytest.approx(math.exp(intercept))
    assert result.n == pytest.approx(slope + 1)
    assert result.residuals.shape == (8,)


def test_reordering_preserves_parameters_and_row_alignment():
    rates = np.array([1, 2, 4, 8, 16, 1], dtype=float)
    observed = np.array([10, 7, 6, 3, 2, 12], dtype=float)
    before_rates, before_observed = rates.copy(), observed.copy()
    result = fit_power_law(rates, observed)
    permutation = [4, 0, 5, 3, 1, 2]
    shuffled = fit_power_law(rates[permutation], observed[permutation])
    for field in ("k", "n", "r_squared_log", "rmse", "mape_percent"):
        assert getattr(shuffled, field) == pytest.approx(getattr(result, field))
    np.testing.assert_allclose(
        shuffled.predicted_viscosity, result.predicted_viscosity[permutation]
    )
    np.testing.assert_allclose(shuffled.residuals, result.residuals[permutation])
    np.testing.assert_array_equal(rates, before_rates)
    np.testing.assert_array_equal(observed, before_observed)


@pytest.mark.parametrize("viscosity", [1.0, 2.5, 7.0, 0.1])
def test_constant_viscosity_has_undefined_log_r_squared(viscosity):
    result = fit_power_law([1, 2, 3, 4, 5], [viscosity] * 5)
    assert result.k == pytest.approx(viscosity)
    assert result.n == pytest.approx(1)
    assert result.r_squared_log is None
    assert result.rmse == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize(
    ("rates", "observed", "message"),
    [
        ([], [], "non-empty"),
        (1, [1] * 5, "one-dimensional"),
        ([[1, 2, 3, 4, 5]], [1] * 5, "one-dimensional"),
        ([1, 2, 3, 4, 5], [[1, 2, 3, 4, 5]], "one-dimensional"),
        ([1, 2, 3, 4, 5], [1, 2], "same length"),
        ([1, 2, 3, 4, 4], [1] * 5, "5 distinct"),
        ([1] * 5, [1] * 5, "5 distinct"),
        ([1, 2, 0, 4, 5], [1] * 5, "shear_rate"),
        ([1, 2, -1, 4, 5], [1] * 5, "shear_rate"),
        ([1, 2, np.nan, 4, 5], [1] * 5, "shear_rate"),
        ([1, 2, np.inf, 4, 5], [1] * 5, "shear_rate"),
        ([1, 2, 3, 4, 5], [1, 2, 0, 4, 5], "viscosity"),
        ([1, 2, 3, 4, 5], [1, 2, -1, 4, 5], "viscosity"),
        ([1, 2, 3, 4, 5], [1, 2, np.nan, 4, 5], "viscosity"),
        ([1, 2, 3, 4, 5], [1, 2, np.inf, 4, 5], "viscosity"),
        (["bad"] * 5, [1] * 5, "shear_rate"),
        ([1, 2, 3, 4, 5], ["bad"] * 5, "viscosity"),
        ([True] * 5, [1] * 5, "bool or complex"),
        ([1 + 1j] * 5, [1] * 5, "bool or complex"),
    ],
)
def test_invalid_fit_inputs(rates, observed, message):
    with pytest.raises(ValueError, match=message):
        fit_power_law(rates, observed)


def test_regression_failure_is_explicit(monkeypatch):
    def fail(*args):
        raise RuntimeError("controlled regression failure")

    monkeypatch.setattr("rheolab.fitting.linregress", fail)
    with pytest.raises(ValueError, match="fit failed.*controlled regression failure"):
        fit_power_law([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])


@pytest.mark.parametrize(
    ("slope", "intercept"),
    [(np.nan, 0), (0, np.inf), (0, 1000), (0, -1000), (1e308, 0)],
)
def test_invalid_regression_results(monkeypatch, slope, intercept):
    monkeypatch.setattr(
        "rheolab.fitting.linregress",
        lambda *args: SimpleNamespace(slope=slope, intercept=intercept),
    )
    with pytest.raises(ValueError, match="fit failed"):
        fit_power_law([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])


def test_real_data_can_produce_unrepresentable_k():
    rates = np.geomspace(1e100, 1e101, 5)
    observed = 1e300 * (rates / 1e100) ** -2
    with pytest.raises(ValueError, match="fit failed"):
        fit_power_law(rates, observed)


def test_large_residuals_have_finite_rmse_without_squaring_overflow():
    result = fit_power_law([1, 2, 3, 4, 5], np.array([10, 7, 9, 2, 3]) * 1e200)
    assert math.isfinite(result.rmse)
    assert result.rmse > 1e199


def test_csv_to_fit_integration():
    rates, observed = read_csv(
        StringIO("shear_rate,viscosity\n1,12\n4,6\n9,4\n16,3\n36,2\n")
    )
    result = fit_power_law(rates, observed)
    assert result.k == pytest.approx(12)
    assert result.n == pytest.approx(0.5)
    np.testing.assert_allclose(result.predicted_viscosity, observed)
