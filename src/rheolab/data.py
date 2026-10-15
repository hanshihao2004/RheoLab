"""Read CSV measurements without dropping or changing observations."""

import csv
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import BinaryIO, TextIO

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _as_positive_vector(values: ArrayLike, name: str) -> NDArray[np.float64]:
    """Convert one measurement column, rejecting invalid observations."""
    try:
        raw = np.asarray(values)
        if raw.ndim != 1 or raw.size == 0:
            raise ValueError(f"{name} must be a non-empty one-dimensional array.")
        if np.iscomplexobj(raw) or raw.dtype.kind == "b":
            raise ValueError(f"{name} must contain real numbers, not bool or complex.")
        result = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid {name}: {exc}") from exc

    invalid = ~np.isfinite(result) | (result <= 0)
    if invalid.any():
        row = int(np.flatnonzero(invalid)[0]) + 1
        raise ValueError(f"{name} data row {row} must be finite and greater than zero.")
    return result


def validate_measurements(
    shear_rate: ArrayLike, viscosity: ArrayLike
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Validate paired data; preserve row order and repeated measurements."""
    rates = _as_positive_vector(shear_rate, "shear_rate")
    viscosities = _as_positive_vector(viscosity, "viscosity")
    if rates.size != viscosities.size:
        raise ValueError("shear_rate and viscosity must have the same length.")
    if np.unique(rates).size < 5:
        raise ValueError("At least 5 distinct shear_rate values are required.")
    return rates, viscosities


def read_csv(
    source: str | PathLike[str] | TextIO | BinaryIO,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Read UTF-8 CSV from a path or an open stream at its current position.

    Units are s^-1 and Pa.s. Extra columns are ignored, but malformed rows and
    invalid required values are errors. The caller's stream is not closed.
    """
    # Pandas is only needed for CSV conversion, not for numerical validation.
    import pandas as pd

    try:
        if isinstance(source, (str, PathLike)):
            text = Path(source).read_text(encoding="utf-8-sig")
        else:
            text = source.read()
        if isinstance(text, bytes):
            text = text.decode("utf-8-sig")
        if not isinstance(text, str):
            raise ValueError("CSV source must provide text or UTF-8 bytes.")
        reader = csv.reader(StringIO(text.removeprefix("\ufeff")), strict=True)
        header = next(reader, None)
        if not header:
            raise ValueError("CSV is empty or has no header.")
        if len(set(header)) != len(header):
            raise ValueError("CSV contains duplicate column names.")
        for column in ("shear_rate", "viscosity"):
            if column not in header:
                raise ValueError(f"CSV is missing required column: {column}.")
        rows = []
        for row_number, row in enumerate(reader, start=1):
            if len(row) != len(header):
                raise ValueError(
                    f"CSV data row {row_number} has {len(row)} fields; "
                    f"expected {len(header)}. Blank rows are not skipped."
                )
            rows.append(row)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"Cannot read CSV: {exc}") from exc

    frame = pd.DataFrame(rows, columns=header)
    # Conversion failures become NaN and are immediately rejected, never dropped.
    rates = pd.to_numeric(frame["shear_rate"], errors="coerce").to_numpy(
        dtype=np.float64
    )
    viscosities = pd.to_numeric(frame["viscosity"], errors="coerce").to_numpy(
        dtype=np.float64
    )
    return validate_measurements(rates, viscosities)
