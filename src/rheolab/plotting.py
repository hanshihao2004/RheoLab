"""Plot measured viscosity, an existing power-law fit and its residuals."""

import numpy as np
import plotly.graph_objects as go
from numpy.typing import ArrayLike
from plotly.subplots import make_subplots

from rheolab.data import validate_measurements
from rheolab.fitting import FitResult
from rheolab.models import power_law


def create_fit_figure(
    shear_rate: ArrayLike,
    viscosity: ArrayLike,
    result: FitResult,
    *,
    title: str = "RheoLab · 幂律模型拟合",
) -> go.Figure:
    """Build two panels without refitting, saving files or opening a browser.

    Top: log-log viscosity and fitted curve within the observed rate range.
    Bottom: observed minus predicted viscosity, on a linear vertical axis.
    Measurements and residuals retain their input order, including repeats.
    """
    rates, observed = validate_measurements(shear_rate, viscosity)
    predicted = np.asarray(result.predicted_viscosity, dtype=np.float64)
    residuals = np.asarray(result.residuals, dtype=np.float64)
    if predicted.shape != rates.shape or residuals.shape != rates.shape:
        raise ValueError("FitResult arrays must match the measurement shape.")
    if not np.all(np.isfinite(predicted) & (predicted > 0)) or not np.all(
        np.isfinite(residuals)
    ):
        raise ValueError(
            "FitResult predictions and residuals must be valid and finite."
        )
    expected = power_law(rates, result.k, result.n)
    if not np.allclose(predicted, expected, rtol=1e-10, atol=0) or not np.allclose(
        residuals, observed - predicted, rtol=1e-10, atol=0
    ):
        raise ValueError("FitResult does not match the supplied measurements or model.")

    curve_rates = np.geomspace(rates.min(), rates.max(), 200)
    curve_viscosity = power_law(curve_rates, result.k, result.n)
    rows = np.arange(1, rates.size + 1)
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.14,
        subplot_titles=("黏度与拟合曲线", "残差 · 实测值 − 预测值"),
    )
    figure.add_trace(
        go.Scatter(
            x=rates,
            y=observed,
            mode="markers",
            name="测量数据",
            customdata=rows,
            marker={"color": "#2563eb", "size": 8, "opacity": 0.8},
            hovertemplate=(
                "数据行 %{customdata}<br>剪切速率 %{x:.5g} s⁻¹"
                "<br>黏度 %{y:.5g} Pa·s<extra>测量数据</extra>"
            ),
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=curve_rates,
            y=curve_viscosity,
            mode="lines",
            name="幂律拟合",
            line={"color": "#0f766e", "width": 3},
            hovertemplate=(
                "剪切速率 %{x:.5g} s⁻¹<br>拟合黏度 %{y:.5g} Pa·s<extra>幂律拟合</extra>"
            ),
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=rates,
            y=residuals,
            mode="markers",
            name="残差",
            customdata=rows,
            showlegend=False,
            marker={"color": "#2563eb", "size": 7, "opacity": 0.8},
            hovertemplate=(
                "数据行 %{customdata}<br>剪切速率 %{x:.5g} s⁻¹"
                "<br>残差 %{y:.5g} Pa·s<extra>实测值 − 预测值</extra>"
            ),
        ),
        row=2,
        col=1,
    )
    figure.add_hline(y=0, line_color="#64748b", line_dash="dash", row=2, col=1)
    figure.update_xaxes(type="log", dtick=1, gridcolor="#e2e8f0", showticklabels=True)
    figure.update_xaxes(title_text="剪切速率 (s⁻¹)", row=2, col=1)
    figure.update_yaxes(type="log", dtick=1, title_text="黏度 (Pa·s)", row=1, col=1)
    figure.update_yaxes(type="linear", title_text="残差 (Pa·s)", row=2, col=1)
    r_squared = (
        "未定义（常黏度）"
        if result.r_squared_log is None
        else f"{result.r_squared_log:.4f}"
    )
    figure.update_layout(
        template="plotly_white",
        height=820,
        margin={"l": 85, "r": 40, "t": 155, "b": 75},
        title={
            "text": (
                f"{title}<br><sup>K = {result.k:.5g} Pa·sⁿ · n = {result.n:.5g}"
                f" · R²（ln 空间）= {r_squared}<br>"
                f"RMSE = {result.rmse:.4g} Pa·s · MAPE = {result.mape_percent:.3g}%"
                " · 自然对数空间 OLS</sup>"
            ),
            "x": 0.04,
            "y": 0.98,
        },
        font={"family": "Segoe UI, Microsoft YaHei, sans-serif", "size": 14},
        legend={"orientation": "h", "y": 1.09, "x": 1, "xanchor": "right"},
        hovermode="closest",
    )
    return figure
