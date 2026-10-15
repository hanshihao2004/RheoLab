"""Ordinary least squares in natural-log space for viscosity data."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import linregress

from rheolab.data import validate_measurements
from rheolab.models import power_law


@dataclass(frozen=True)
class FitResult:
    """Fit parameters and metrics; arrays follow the input measurement order.

    k: Pa.s^n; n and r_squared_log: dimensionless; rmse: Pa.s;
    mape_percent: percent; predicted_viscosity and residuals: Pa.s.
    r_squared_log is None for constant measured viscosity.
    """

    k: float
    n: float
    r_squared_log: float | None
    rmse: float
    mape_percent: float
    predicted_viscosity: NDArray[np.float64]
    residuals: NDArray[np.float64]


def fit_power_law(shear_rate: ArrayLike, viscosity: ArrayLike) -> FitResult:
    """Fit ln(eta) = intercept + slope * ln(shear_rate), each row equally.

    K = exp(intercept), n = slope + 1. Residuals are observed minus predicted.
    No averaging, filtering, parameter clipping or retransformation correction
    is applied. R-squared is in log space; RMSE and MAPE are in original space.
    """
    rates, observed = validate_measurements(shear_rate, viscosity)
    log_rates, log_observed = np.log(rates), np.log(observed)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            regression = linregress(log_rates, log_observed)
            slope, intercept = regression.slope, regression.intercept
            if not np.all(np.isfinite([slope, intercept])):
                raise ValueError("Regression returned non-finite coefficients.")
            k, n = float(np.exp(intercept)), float(slope + 1.0)
            predicted = power_law(rates, k, n)
            residuals = observed - predicted

            # Scaling avoids overflow in residuals**2 when RMSE is representable.
            residual_scale = float(np.max(np.abs(residuals)))
            rmse = (
                float(
                    residual_scale * np.sqrt(np.mean((residuals / residual_scale) ** 2))
                )
                if residual_scale > 0
                else 0.0
            )
            mape_percent = float(100.0 * np.mean(np.abs(residuals) / observed))

            centered_log = log_observed - np.mean(log_observed)
            log_scale = float(np.max(np.abs(centered_log)))
            # Equality is checked before centering: the mean can round slightly.
            if np.all(log_observed == log_observed[0]):
                r_squared_log = None
            else:
                log_residuals = log_observed - (intercept + slope * log_rates)
                r_squared_log = float(
                    1.0
                    - np.sum((log_residuals / log_scale) ** 2)
                    / np.sum((centered_log / log_scale) ** 2)
                )
            metrics = [rmse, mape_percent]
            if r_squared_log is not None:
                metrics.append(r_squared_log)
            if not np.all(np.isfinite(metrics)):
                raise ValueError("Fit metrics must be finite.")
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        raise ValueError(f"Power-law fit failed: {exc}") from exc

    return FitResult(k, n, r_squared_log, rmse, mape_percent, predicted, residuals)
