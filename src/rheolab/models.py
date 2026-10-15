"""Numerical evaluation of the Ostwald-de Waele viscosity model."""

import numpy as np
from numpy.typing import ArrayLike, NDArray

from rheolab.data import _as_positive_vector


def _finite_scalar(value: float, name: str) -> float:
    """Reject arrays and non-real/non-finite model parameters."""
    raw = np.asarray(value)
    if raw.ndim != 0 or np.iscomplexobj(raw) or raw.dtype.kind == "b":
        raise ValueError(f"{name} must be a finite real scalar.")
    try:
        number = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real scalar.") from exc
    if not np.isfinite(number):
        raise ValueError(f"{name} must be a finite real scalar.")
    return number


def power_law(shear_rate: ArrayLike, k: float, n: float) -> NDArray[np.float64]:
    """Return eta = K * shear_rate**(n - 1) in Pa.s.

    shear_rate is in s^-1; K is in Pa.s^n. K must be positive and n finite.
    This function evaluates supplied points; it does not generate a fit curve.
    """
    rates = _as_positive_vector(shear_rate, "shear_rate")
    k = _finite_scalar(k, "k")
    n = _finite_scalar(n, "n")
    if k <= 0:
        raise ValueError("k must be greater than zero.")
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            predicted = np.exp(np.log(k) + (n - 1.0) * np.log(rates))
    except FloatingPointError as exc:
        raise ValueError("Power-law prediction exceeds the numerical range.") from exc
    if not np.all(np.isfinite(predicted) & (predicted > 0)):
        raise ValueError("Power-law prediction must be finite and greater than zero.")
    return predicted
