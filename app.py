"""Minimal Streamlit interface. Run with: uv run streamlit run app.py."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from rheolab.data import read_csv
from rheolab.fitting import fit_power_law
from rheolab.plotting import create_fit_figure

EXAMPLE_PATH = Path(__file__).resolve().parent / "examples" / "synthetic_power_law.csv"
UPLOAD_SOURCE = "上传 CSV"
DEMO_SOURCE = "合成示例（非实验数据）"


def main() -> None:
    """Connect existing data, fitting and plotting modules to a small UI."""
    st.set_page_config(page_title="RheoLab", page_icon="🧪", layout="wide")
    st.title("RheoLab")
    st.caption("流变数据分析 · Ostwald–de Waele 幂律模型")
    st.markdown("黏度模型 **η = Kγ̇ⁿ⁻¹**，使用自然对数变换后的普通最小二乘拟合。")

    st.subheader("1. 选择数据")
    st.caption(
        "UTF-8 CSV，必须包含 shear_rate（s⁻¹）和 viscosity（Pa·s）。"
        "数值须有限且大于零，至少 5 个不同剪切速率；保留重复测量，不自动清洗。"
    )
    source = st.radio(
        "数据来源", [UPLOAD_SOURCE, DEMO_SOURCE], horizontal=True, key="data_source"
    )
    content, filename = None, None
    if source == UPLOAD_SOURCE:
        uploaded = st.file_uploader("选择 CSV 文件", type=["csv"], key="csv_file")
        if uploaded is not None:
            content, filename = uploaded.getvalue(), uploaded.name
    else:
        try:
            content, filename = EXAMPLE_PATH.read_bytes(), EXAMPLE_PATH.name
        except OSError as exc:
            st.error(f"无法加载合成示例：{exc}")
        st.info("合成数据：80 行、40 个不同速率，设定 K=12、n=0.62，含少量乘性噪声。")

    # Content identity also catches replacement files that share the same name.
    input_id = (
        (source, filename, sha256(content).hexdigest()) if content is not None else None
    )
    if st.session_state.get("input_id") != input_id:
        st.session_state["input_id"] = input_id
        st.session_state.pop("fit_result", None)

    if content is None:
        st.info("请上传 CSV，或选择合成示例开始。")
        return
    try:
        rates, viscosity = read_csv(BytesIO(content))
    except ValueError as exc:
        st.session_state.pop("fit_result", None)
        st.error(f"数据校验失败：{exc}")
        return

    st.subheader("2. 数据预览")
    st.caption(
        f"当前文件：{filename} · {rates.size} 行 · "
        f"{np.unique(rates).size} 个不同剪切速率。"
        "仅展示用于分析的两列，保持原始行顺序。"
    )
    st.dataframe(
        pd.DataFrame({"shear_rate": rates, "viscosity": viscosity}),
        width="stretch",
        height=250,
        hide_index=True,
    )
    if st.button("拟合 Power-law", type="primary", key="fit"):
        st.session_state.pop("fit_result", None)
        try:
            st.session_state["fit_result"] = fit_power_law(rates, viscosity)
        except ValueError as exc:
            st.error(f"拟合失败：{exc}")
            return

    result = st.session_state.get("fit_result")
    if result is None:
        st.info("数据校验通过。点击“拟合 Power-law”查看结果。")
        return
    try:
        figure = create_fit_figure(
            rates,
            viscosity,
            result,
            title=(
                "RheoLab · 合成数据拟合（非实验数据）"
                if source == DEMO_SOURCE
                else "RheoLab · 幂律模型拟合"
            ),
        )
    except ValueError as exc:
        st.session_state.pop("fit_result", None)
        st.error(f"结果绘图失败：{exc}")
        return

    st.subheader("3. 拟合结果")
    parameters = st.columns(2)
    parameters[0].metric("K (Pa·sⁿ)", f"{result.k:.6g}")
    parameters[1].metric("n", f"{result.n:.6g}")
    metrics = st.columns(3)
    metrics[0].metric(
        "R²（对数空间）",
        "未定义" if result.r_squared_log is None else f"{result.r_squared_log:.6f}",
        help="自然对数黏度的决定系数；常黏度数据的该指标未定义。",
    )
    metrics[1].metric("RMSE (Pa·s)", f"{result.rmse:.6g}")
    metrics[2].metric("MAPE", f"{result.mape_percent:.4g}%")
    st.caption(
        "R² 在自然对数空间计算；RMSE 和 MAPE 在原始黏度空间计算。"
        "残差 = 实测值 − 预测值；曲线仅覆盖原始剪切速率范围。"
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displaylogo": False},
        key="fit_chart",
    )


if __name__ == "__main__":
    main()
