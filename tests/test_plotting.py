from dataclasses import replace

import numpy as np
import pytest

from rheolab.fitting import fit_power_law
from rheolab.plotting import create_fit_figure


@pytest.fixture
def measurements():
    rates = np.array([16, 1, 4, 2, 8, 1], dtype=float)
    observed = np.array([2, 12, 5, 8, 3, 10], dtype=float)
    return rates, observed, fit_power_law(rates, observed)


def test_measurements_and_residuals_keep_all_rows_and_alignment(measurements):
    rates, observed, result = measurements
    figure = create_fit_figure(rates, observed, result)
    points, _, residuals = figure.data
    np.testing.assert_array_equal(points.x, rates)
    np.testing.assert_array_equal(points.y, observed)
    np.testing.assert_array_equal(residuals.x, rates)
    np.testing.assert_allclose(residuals.y, observed - result.predicted_viscosity)
    np.testing.assert_array_equal(points.customdata, np.arange(1, 7))
    assert min(residuals.y) < 0 < max(residuals.y)


def test_curve_is_ordered_and_never_extrapolates(measurements):
    rates, observed, result = measurements
    figure = create_fit_figure(rates, observed, result)
    curve = figure.data[1]
    assert curve.mode == "lines"
    assert min(curve.x) == rates.min()
    assert max(curve.x) == rates.max()
    assert np.all(np.diff(curve.x) > 0)
    # Independent direct formula checks the curve uses the fitted parameters.
    np.testing.assert_allclose(
        curve.y, result.k * np.asarray(curve.x) ** (result.n - 1)
    )


def test_axes_and_zero_reference(measurements):
    figure = create_fit_figure(*measurements)
    assert figure.layout.xaxis.type == figure.layout.xaxis2.type == "log"
    assert figure.layout.yaxis.type == "log"
    assert figure.layout.yaxis2.type == "linear"
    zero = figure.layout.shapes[0]
    assert zero.y0 == zero.y1 == 0
    assert zero.yref == "y2"
    assert "Pa·s" in figure.layout.yaxis.title.text
    assert "s⁻¹" in figure.layout.xaxis2.title.text


def test_plotting_does_not_refit_or_mutate_inputs(measurements, monkeypatch):
    rates, observed, result = measurements
    before = [array.copy() for array in (rates, observed, result.residuals)]

    def forbidden(*args, **kwargs):
        pytest.fail("Plotting must not refit measurements.")

    monkeypatch.setattr("rheolab.fitting.linregress", forbidden)
    create_fit_figure(rates, observed, result)
    for actual, expected in zip(
        (rates, observed, result.residuals), before, strict=True
    ):
        np.testing.assert_array_equal(actual, expected)


def test_constant_viscosity_displays_undefined_r_squared():
    rates, observed = np.arange(1, 6), np.full(5, 2.5)
    figure = create_fit_figure(rates, observed, fit_power_law(rates, observed))
    assert "未定义" in figure.layout.title.text
    assert "nan" not in figure.layout.title.text.lower()


@pytest.mark.parametrize(
    "changes",
    [
        {"predicted_viscosity": np.ones(5)},
        {"residuals": np.ones((6, 1))},
        {"predicted_viscosity": np.full(6, np.nan)},
        {"predicted_viscosity": np.zeros(6)},
        {"residuals": np.full(6, np.inf)},
        {"residuals": np.ones(6)},
        {"k": 100},
    ],
)
def test_mismatched_or_invalid_result_is_rejected(measurements, changes):
    rates, observed, result = measurements
    with pytest.raises(ValueError, match="FitResult"):
        create_fit_figure(rates, observed, replace(result, **changes))


def test_reordered_data_without_reordered_result_is_rejected(measurements):
    rates, observed, result = measurements
    with pytest.raises(ValueError, match="does not match"):
        create_fit_figure(rates[::-1], observed[::-1], result)


@pytest.mark.parametrize(
    ("rates", "observed", "message"),
    [
        ([], [], "non-empty"),
        ([1, 2, 3, 4, 5], [1, 2], "same length"),
        ([1, 2, 3, 4, 4], [1] * 5, "5 distinct"),
        ([1, 2, 3, 4, 5], [1, 2, np.nan, 4, 5], "viscosity"),
        ([0, 2, 3, 4, 5], [1] * 5, "shear_rate"),
    ],
)
def test_invalid_measurements(measurements, rates, observed, message):
    with pytest.raises(ValueError, match=message):
        create_fit_figure(rates, observed, measurements[2])


def test_standalone_html_can_be_saved_offline(measurements, tmp_path):
    figure = create_fit_figure(*measurements, title="Synthetic data preview")
    path = tmp_path / "preview.html"
    figure.write_html(path, include_plotlyjs=True, full_html=True)
    html = path.read_text(encoding="utf-8")
    assert "Synthetic data preview" in html
    assert "Plotly.newPlot" in html
    assert '<script src="https://cdn.plot.ly' not in html
