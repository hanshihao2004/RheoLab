# RheoLab

面向化工科研人员的流变数据分析工具。当前版本支持 CSV 读取、
Ostwald–de Waele 幂律模型拟合，以及交互式黏度图和残差图。

## 本地启动

Windows 上可直接双击根目录的 **启动RheoLab.cmd**。启动器会检查运行环境，
启动本地服务并自动打开默认浏览器；运行窗口需保持开启，按 Ctrl+C 或关闭
该运行窗口可停止服务。已运行时再次双击会打开现有实例。

默认尝试 8501 端口，被占用时依次尝试至 8510，不会停止其他占用端口的程序。
实际地址以运行窗口显示的地址为准。

现有 `.venv` 环境完整时不需要另外安装 uv。首次使用或环境缺失时，启动器
会尝试调用已安装的 uv，按锁文件自动准备 Python 3.12 和依赖；该过程可能
需要联网。如未安装 uv，会显示[安装说明](https://docs.astral.sh/uv/getting-started/installation/)。
此启动器需要项目文件与运行环境，尚不是独立的 EXE 安装包。

开发时也可以使用命令行：

需要 Python 3.11 或更高版本及 uv；当前在 Windows / Python 3.12 上验证。

```powershell
uv sync --locked
uv run --locked streamlit run app.py --server.address 127.0.0.1
```

打开终端显示的本地地址，默认是 `http://127.0.0.1:8501`。
如系统无法识别 `uv`，请按上述安装说明安装，并重新打开终端。

上传 CSV 或选择“合成示例（非实验数据）”，检查预览后点击“拟合 Power-law”。
更换、移除文件或切换数据来源会清除旧结果，需要再次点击拟合。

## 输入规范

CSV 为 UTF-8（允许 BOM），英文逗号分隔，必须包含：

| 列名 | 含义 | 单位 |
| --- | --- | --- |
| shear_rate | 剪切速率 | s⁻¹ |
| viscosity | 黏度 | Pa·s |

两列数值必须有限且大于零，至少包含 5 个不同剪切速率。
重复测量逐行等权参与拟合，不自动平均、清洗或剔除异常值。
额外列不参与分析，非法数据会明确报错。
可使用 `examples/synthetic_power_law.csv` 试用，数据来源和生成方法见
[示例说明](examples/README.md)。

## 计算方法

η = Kγ̇^(n−1)，以 ln(γ̇) 和 ln(η) 进行普通最小二乘回归。
K = exp(截距)，n = 斜率 + 1。

- K 的单位为 Pa·sⁿ，n 为无量纲流动行为指数。
- R² 在自然对数空间计算；常黏度数据的 R² 显示“未定义”。
- RMSE 在原始黏度空间计算，单位 Pa·s。
- MAPE 在原始黏度空间计算，以百分数展示。
- 残差为实测黏度减预测黏度，纵轴使用线性坐标。
- 拟合曲线仅覆盖输入剪切速率范围，不外推。

拟合指标描述输入数据上的表现，不代表独立实验验证。

## 代码结构与检查

`app.py` 只负责页面流程和状态；`src/rheolab/` 中的 `data.py`、`models.py`、
`fitting.py` 和 `plotting.py` 分别负责数据、模型、拟合和绘图。

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

## GitHub 自动检查

工作流位于 [ci.yml](.github/workflows/ci.yml)。推送提交、提交 PR 或在
GitHub Actions 页面手动触发时，依次执行：

1. 使用 Ubuntu 24.04、Python 3.12 和 uv 0.13.1 准备环境。
2. 执行 `uv sync --locked --dev`，按 `uv.lock` 安装项目与开发依赖。
3. 运行 pytest、Ruff 检查和格式检查；任何一步失败，该任务即失败。

`--locked` 会在依赖声明与锁文件不一致时报错，不会在检查中自动更新锁文件。
格式检查仅报告问题，不自动修改代码。配置采用
[uv 官方 GitHub Actions 集成](https://docs.astral.sh/uv/guides/integration/github/)，
Action 固定到已核对的提交，uv 下载缓存按锁文件更新。

将项目提交并推送到 GitHub 后，在仓库的 **Actions → CI** 查看运行结果。
本地通过仅代表本地验证成功，Ubuntu 云端是否通过以实际运行结果为准。

验收与测试记录见 [验收计划](docs/acceptance-test-plan.md)。
本项目尚未创建 LICENSE，许可证待维护者最终确认。
