# 合成数据绘图示例

`synthetic_power_law.csv` 是程序生成的合成数据，**不是实验数据**。
`synthetic_power_law.html` 是对应的交互图，可直接用浏览器打开，无需联网。
HTML 内嵌 Plotly，因此文件大小会明显大于 CSV。
另附 `synthetic_power_law.png` 静态预览，供直接查看整张图。
PNG 通过 HTML 工具栏的下载按钮导出；示例脚本只重新生成 CSV 和 HTML。

## 数据来源

- 模型：η = K γ̇^(n−1)。
- 已知参数：K = 12 Pa·sⁿ，n = 0.62，表现为剪切变稀。
- 剪切速率：0.1–1000 s⁻¹，40 个对数等间距速率，每个速率重复两次，共 80 行。
- 噪声：η_observed = η_model × exp(ε)，ε ~ N(0, 0.06²)。
  0.06 是对数噪声标准差，不表示每个数据点固定偏差 6%。
- 随机种子：20261015；成对打乱行顺序，不剔除或平均任何数据。
- CSV 只包含 `shear_rate`（s⁻¹）和 `viscosity`（Pa·s）。

## 图形含义

上图显示原始散点和幂律拟合曲线，两个坐标轴均为对数刻度。
拟合曲线只覆盖 CSV 中的最小至最大剪切速率，不外推。
下图显示原始黏度空间的残差，定义为实测值减预测值；正值表示实测黏度
高于预测值，负值表示低于预测值。残差纵轴是线性的，虚线代表零残差。
悬停可查看数据行编号与数值，可缩放、拖动和点击图例。
点击工具栏的相机按钮，可导出 1650 × 1230 像素的 PNG 图形。

重复测量可能在图中接近或重叠，但每一行均保留并等权参与拟合。
页面中的 R² 在自然对数空间计算，RMSE 和百分数 MAPE 在原始空间计算。
示例只演示绘图和计算流程，不作为独立实验验证。

## 重新生成

在项目根目录、安装 uv 后执行：

```powershell
uv sync --locked
uv run --locked python examples/plot_demo.py
```

本次临时 uv 工具也可以使用：

```powershell
& "$env:TEMP\rheolab-tool-env\Scripts\uv.exe" run --locked python examples/plot_demo.py
```

重新运行会覆盖该目录下的两个 `synthetic_power_law` 输出文件。

## 调用绘图模块

```python
from rheolab.data import read_csv
from rheolab.fitting import fit_power_law
from rheolab.plotting import create_fit_figure

rates, viscosity = read_csv("examples/synthetic_power_law.csv")
result = fit_power_law(rates, viscosity)
figure = create_fit_figure(rates, viscosity, result)
figure.write_html("preview.html", include_plotlyjs=True)
```

`create_fit_figure()` 不重新拟合，也不保存文件；调用者决定展示或导出方式。
