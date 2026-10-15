# RheoLab

面向化工科研人员的流变数据分析工具。读取剪切速率与黏度 CSV 数据，
拟合 Ostwald–de Waele 幂律模型，输出参数、误差指标和交互式图形。

当前版本：[0.1.0rc1（预览版）](https://github.com/hanshihao2004/RheoLab/releases/tag/v0.1.0rc1)。

## 启动与使用

### Windows 双击启动

1. 下载并解压项目，首次使用先安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)。
2. 双击项目根目录的 **启动RheoLab.cmd**，等待浏览器自动打开。
3. 上传 CSV，或选择“合成示例（非实验数据）”，检查预览后点击“拟合 Power-law”。
4. 查看拟合参数、误差指标、黏度曲线和残差图。

首次启动可能需要联网下载 Python 3.12 和依赖；已有完整运行环境时可直接启动。
运行窗口需保持开启，按 Ctrl+C 或关闭窗口可停止服务。再次双击会打开已有实例。
更换数据后需要重新点击拟合。当前提供源码启动方式，尚无独立 EXE 安装包。

### 命令行启动

安装 uv 后，在项目根目录执行：

```powershell
uv sync --locked --python 3.12
uv run --locked streamlit run app.py --server.address 127.0.0.1
```

打开终端显示的本地地址，通常为 `http://127.0.0.1:8501`。
Windows 启动器遇到端口占用时会在 8501–8510 中选择可用端口。

## 数据要求

CSV 使用 UTF-8 编码（允许 BOM）、英文逗号分隔，必须包含以下两列：

| 列名 | 含义 | 单位 |
| --- | --- | --- |
| `shear_rate` | 剪切速率 | s⁻¹ |
| `viscosity` | 黏度 | Pa·s |

数值必须有限且大于零，至少包含 **5 个不同剪切速率**。
允许重复测量，每行等权参与拟合；不自动平均、清洗或剔除异常值。
额外列不参与分析，非法数据会显示错误信息。

可直接试用[示例 CSV](examples/synthetic_power_law.csv)，生成方法见[示例说明](examples/README.md)。

## 计算与限制

- 模型为 η = Kγ̇^(n−1)，对 ln(γ̇) 和 ln(η) 进行普通最小二乘拟合。
- 输出 K（Pa·sⁿ）、n（无量纲）、对数空间 R²、原始空间 RMSE（Pa·s）和 MAPE（%）。
- 残差为实测黏度减预测黏度；拟合曲线仅覆盖输入数据范围，不外推。
- 常黏度数据的 R² 未定义。拟合指标描述输入数据上的表现，不代表独立实验验证。

当前在 Windows / Python 3.12 验证交互与启动流程，Ubuntu / Python 3.12 运行自动测试。
测试方法与记录见[验收文档](docs/acceptance-test-plan.md)，问题反馈请提交 [Issue](https://github.com/hanshihao2004/RheoLab/issues)。

## 许可证

本项目采用 [MIT License](LICENSE)，版权归属 © 2026 hanshihao2004。
第三方依赖及示例 HTML 内嵌的 Plotly 脚本保留各自许可证。
