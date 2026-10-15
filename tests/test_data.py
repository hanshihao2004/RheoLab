from io import BytesIO, StringIO

import numpy as np
import pytest

from rheolab.data import read_csv, validate_measurements

VALID_CSV = "shear_rate,viscosity\n1,10\n2,8\n3,6\n4,5\n5,4\n"


@pytest.mark.parametrize(
    "source",
    [StringIO(VALID_CSV), BytesIO(VALID_CSV.encode()), StringIO("\ufeff" + VALID_CSV)],
)
def test_read_stream(source):
    rates, viscosities = read_csv(source)
    np.testing.assert_array_equal(rates, [1, 2, 3, 4, 5])
    np.testing.assert_array_equal(viscosities, [10, 8, 6, 5, 4])
    assert rates.dtype == viscosities.dtype == np.float64
    assert not source.closed


def test_read_path_with_bom(tmp_path):
    path = tmp_path / "measurements.csv"
    path.write_text(VALID_CSV, encoding="utf-8-sig")
    np.testing.assert_array_equal(read_csv(path)[0], [1, 2, 3, 4, 5])
    np.testing.assert_array_equal(read_csv(str(path))[1], [10, 8, 6, 5, 4])


def test_preserves_repeats_order_and_ignores_extra_columns():
    text = (
        "viscosity,note,shear_rate\n"
        '4,"test, extra",5\n10,x,1\n8,x,2\n6,x,3\n5,x,4\n9,x,1\n'
    )
    rates, viscosities = read_csv(StringIO(text))
    np.testing.assert_array_equal(rates, [5, 1, 2, 3, 4, 1])
    np.testing.assert_array_equal(viscosities, [4, 10, 8, 6, 5, 9])


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "empty"),
        ("shear_rate,viscosity\n", "non-empty"),
        ("rate,viscosity\n1,2\n", "shear_rate"),
        ("shear_rate,eta\n1,2\n", "viscosity"),
        ("shear_rate,viscosity,viscosity\n1,2,3\n", "duplicate"),
        (VALID_CSV + "6,3,extra\n", "row 6"),
        (VALID_CSV + "6\n", "row 6"),
        (VALID_CSV + "\n", "row 6"),
        (VALID_CSV + '6,"unclosed\n', "Cannot read CSV"),
        ("shear_rate;viscosity\n1;2", "missing"),
        (VALID_CSV.replace("5,4", "1,4"), "5 distinct"),
    ],
)
def test_invalid_csv_structure(text, message):
    with pytest.raises(ValueError, match=message):
        read_csv(StringIO(text))


@pytest.mark.parametrize("bad", ["", "bad", "NaN", "inf", "-inf", "0", "-1"])
@pytest.mark.parametrize("column", ["shear_rate", "viscosity"])
def test_invalid_csv_values_report_column_and_row(bad, column):
    text = VALID_CSV.replace(
        "3,6", f"{bad},6" if column == "shear_rate" else f"3,{bad}"
    )
    with pytest.raises(ValueError, match=column + " data row 3"):
        read_csv(StringIO(text))


def test_missing_file(tmp_path):
    with pytest.raises(ValueError, match="Cannot read CSV"):
        read_csv(tmp_path / "missing.csv")


def test_invalid_encoding():
    with pytest.raises(ValueError, match="Cannot read CSV"):
        read_csv(BytesIO(b"\xff\xfe"))


@pytest.mark.parametrize(
    ("rates", "viscosities", "message"),
    [
        ([], [], "non-empty"),
        (1, [1, 2, 3, 4, 5], "one-dimensional"),
        ([[1, 2, 3, 4, 5]], [1] * 5, "one-dimensional"),
        ([1, 2, 3, 4, 5], [[1, 2, 3, 4, 5]], "one-dimensional"),
        ([1, 2, 3, 4, 5], [1, 2], "same length"),
        ([1, 2, 3, 4, 4], [1] * 5, "5 distinct"),
        ([1, 1, 1, 1, 1], [1] * 5, "5 distinct"),
        ([1, 2, np.nan, 4, 5], [1] * 5, "shear_rate"),
        ([1, 2, 3, 4, 5], [1, 2, np.inf, 4, 5], "viscosity"),
        ([0, 2, 3, 4, 5], [1] * 5, "greater than zero"),
        ([1, 2, 3, 4, 5], [-1] * 5, "greater than zero"),
        (["bad"] * 5, [1] * 5, "shear_rate"),
        ([True] * 5, [1] * 5, "bool or complex"),
        ([1 + 1j] * 5, [1] * 5, "bool or complex"),
    ],
)
def test_invalid_arrays(rates, viscosities, message):
    with pytest.raises(ValueError, match=message):
        validate_measurements(rates, viscosities)


def test_validation_does_not_modify_input():
    rates = np.array([5.0, 1.0, 2.0, 3.0, 4.0, 1.0])
    viscosities = np.arange(1.0, 7.0)
    original_rates, original_viscosities = rates.copy(), viscosities.copy()
    validated_rates, validated_viscosities = validate_measurements(rates, viscosities)
    np.testing.assert_array_equal(validated_rates, original_rates)
    np.testing.assert_array_equal(validated_viscosities, original_viscosities)
    np.testing.assert_array_equal(rates, original_rates)
    np.testing.assert_array_equal(viscosities, original_viscosities)


def test_numeric_strings_are_converted():
    rates, viscosities = validate_measurements(["1", "2", "3", "4", "5"], ["2"] * 5)
    np.testing.assert_array_equal(rates, [1, 2, 3, 4, 5])
    np.testing.assert_array_equal(viscosities, [2] * 5)
