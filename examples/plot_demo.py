"""Generate reproducible synthetic measurements and an offline plot preview.

Run from the project root: uv run examples/plot_demo.py
Running again replaces only the two generated synthetic_power_law files.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from rheolab.data import read_csv
from rheolab.fitting import fit_power_law
from rheolab.models import power_law
from rheolab.plotting import create_fit_figure


def main() -> None:
    """Write 80 synthetic observations and plot the fit to that CSV."""
    output_dir = Path(__file__).resolve().parent
    rng = np.random.default_rng(20261015)
    k_true, n_true = 12.0, 0.62
    rates = np.repeat(np.geomspace(0.1, 1000.0, 40), 2)
    observed = power_law(rates, k_true, n_true) * np.exp(
        rng.normal(loc=0.0, scale=0.06, size=rates.size)
    )
    # Shuffle paired rows together to demonstrate order-independent plotting.
    order = rng.permutation(rates.size)
    csv_path = output_dir / "synthetic_power_law.csv"
    pd.DataFrame({"shear_rate": rates[order], "viscosity": observed[order]}).to_csv(
        csv_path, index=False
    )

    # Read the saved CSV back, so the preview corresponds to the delivered file.
    rates, observed = read_csv(csv_path)
    result = fit_power_law(rates, observed)
    figure = create_fit_figure(
        rates,
        observed,
        result,
        title="RheoLab · 合成数据示例（非实验数据）",
    )
    html_path = output_dir / "synthetic_power_law.html"
    figure.write_html(
        html_path,
        include_plotlyjs=True,
        full_html=True,
        config={
            "responsive": True,
            "displaylogo": False,
            "toImageButtonOptions": {
                "format": "png",
                "filename": "synthetic_power_law",
                "width": 1100,
                "height": 820,
                "scale": 1.5,
            },
        },
    )
    print(f"Synthetic data: {csv_path}")
    print(f"Offline preview: {html_path}")
    print(f"Known parameters: K={k_true}, n={n_true}")
    print(f"Fitted parameters: K={result.k:.6f}, n={result.n:.6f}")
    print(f"R2_log={result.r_squared_log:.6f}")
    print(f"RMSE={result.rmse:.6f} Pa.s; MAPE={result.mape_percent:.6f}%")


if __name__ == "__main__":
    main()
