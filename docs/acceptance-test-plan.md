# RheoLab v0.1 验收标准与测试计划

本轮范围：依次实现并验证 `data.py`、`models.py`、`fitting.py`。
每个模块测试通过并说明核心代码后，才进入下一个模块。
UI、Plotly 绘图、GitHub 工作流和发布不在本轮实现范围。
MIT 尚未最终确认，不创建 LICENSE 或填写许可证元数据。

## 1. 数据模块

接口：`read_csv(source) -> tuple[NDArray, NDArray]`，支持路径和文本/二进制文件对象；
`validate_measurements(shear_rate, viscosity)` 为 CSV 和拟合入口提供共同校验。

- CSV 使用 UTF-8（允许 BOM），逗号分隔；必须有且仅有一个名为
  `shear_rate` 和 `viscosity` 的必需列。列顺序不限，额外列不参与计算。
- 两列转换为一维 float64 数组；长度一致，非空，数值有限且严格大于零。
- 至少 5 个不同剪切速率，按原始 float64 值判断，不自动合并近似值。
- 允许重复测量和无序输入，保留每一行及其顺序，不平均、不排序、不删除。
- 不过滤异常值，不填补空值；CSV 中的空数据行也不得静默跳过。
- 拒绝空文件、缺列、重复表头、行列数不一致、非数值、NaN、Inf、
  非正值、少于 5 个不同剪切速率，以及数组形状或长度不正确。
- 数值字符串允许显式转为浮点数；布尔值、复数不是有效的数值数组输入。
- 非法数据抛出 ValueError，说明字段、原因；数值问题尽量报告数据行序号
  （从 1 开始，不含表头；不是文件的物理行号）。读取失败说明文件原因。
- 单位固定为 s⁻¹ 与 Pa·s，不自动推断或转换。

测试：合法路径、文本与二进制文件、BOM、反序列名、额外列、重复测量、
无序数据保留；上述非法输入逐项参数化测试。5 行但仅 4 个不同速率必须拒绝。

## 2. 模型模块

接口：`power_law(shear_rate, k, n) -> NDArray`。

- 使用 η = K γ̇^(n−1)，输入为非空一维正有限剪切速率数组。
- K 为有限正标量，n 为有限实标量；不擅自施加 n > 0 或 n < 1 约束。
- 预测不需要 5 个不同速率：这是拟合的数据要求，不是模型求值要求。
- 返回与输入同形状的 float64 黏度数组，不修改调用者的数据。
- 不生成绘图网格或外推曲线；后续绘图模块负责限制展示范围。
- 计算溢出、下溢为零或产生非有限结果时明确报错。

测试：用手工预期值检查剪切变稀、n=1、剪切增稠和有限负 n；检查单点、
无序与重复输入；参数、形状和数值异常；检查溢出和下溢失败路径。

## 3. 拟合模块

接口：`fit_power_law(shear_rate, viscosity) -> FitResult`。

令 x = ln(γ̇)，y = ln(η)，用 scipy.stats.linregress 计算普通最小二乘直线
y = a + b x；恢复 K = exp(a)，n = b + 1。每行等权，重复测量也逐行参与。
不使用原始黏度空间最小二乘，不对参数截断，不做重变换偏差修正。

结果包含 `k`、`n`、`r_squared_log`、`rmse`、`mape_percent`、`predicted_viscosity`
和 `residuals`。预测值和残差与原始输入行顺序一致。

- 残差 rᵢ = ηᵢ − η̂ᵢ。
- R²_log = 1 − Σ(ln ηᵢ − (a + b ln γ̇ᵢ))² / Σ(ln ηᵢ − mean(ln η))²。
- 常黏度数据的分母为零，R²_log 返回 None，含义为未定义。
- RMSE = sqrt(mean(rᵢ²))，单位 Pa·s。
- MAPE = 100 × mean(abs(rᵢ) / ηᵢ)，输出单位为百分数。
- K 的单位为 Pa·sⁿ；所有其他应有数值的输出都必须有限，预测黏度严格为正。
- 输入校验与 CSV 一致；回归、参数恢复、预测或指标数值失败不得作为成功返回。
- 拟合不改变输入数组，不生成超出原始范围的绘图数据。

测试计划：

1. 无噪声合成数据：K=2.5，n 分别取 0.6、1.0、1.4；非零指标与参数
   使用 rtol=1e-10，接近零的 RMSE/MAPE 使用 atol=1e-10。
2. 含噪声合成数据：固定随机种子 20261015，80 个对数间隔速率，
   η=Kγ̇^(n−1)exp(ε)，ε~N(0,0.03²)；K 相对误差 <5%，n 绝对误差 <0.02。
3. 独立数值基准：使用预先构造的对数残差和手算的参数/指标预期值，
   不仅使用生产模型生成并再次验证同一公式。
4. 重复测量：与保留所有行的参考 OLS 结果比较，确保未先取平均。
5. 数据顺序：乱序后参数和指标不变，预测与残差跟随原始行对应。
6. 原始空间指标：手工参考值检查 RMSE 与百分数 MAPE；通过独立
   log-space OLS 参考值确认使用自然对数后的最小二乘目标。
7. 异常输入：空、非数值、形状/长度错误、缺失、无穷、非正值和
   不同速率不足；拟合入口必须直接拒绝，不能仅依赖 CSV 入口。
8. 数值失败：可控地模拟回归失败和无效返回，另以极端数据验证
   参数恢复/预测失败；不依赖某组数据偶然触发失败。

合成数据测试只验证实现，不代表独立实验验证。

## 4. 分阶段验证

1. 数据模块：运行 test_data.py、Ruff 检查及格式检查，解释校验与 CSV 流程。
2. 模型模块：运行 test_models.py 及已有测试、Ruff，解释数组运算与参数校验。
3. 拟合模块：运行全部测试、Ruff，解释自然对数回归、dataclass 与误差空间。

使用 uv 管理依赖；本轮仅添加 NumPy、Pandas、SciPy、pytest 和 Ruff。
不提前添加尚未使用的 Streamlit、Plotly 或构建发布流程。
每次交付记录实际执行的检查，不把未执行的检查记为通过。

## 5. 本轮执行结果（2026-10-15）

| 阶段 | 测试结果 | Ruff 检查与格式检查 |
| --- | --- | --- |
| data.py | 48 项通过 | 通过 |
| models.py | 新增 34 项，累计 82 项通过 | 通过 |
| fitting.py | 新增 40 项，累计 122 项通过 | 通过 |
| 最终包安装验证 | 移除测试路径注入，通过实际可编辑安装再次运行 122 项测试 | 通过 |

实际环境为 Windows、Python 3.12.14；尚未验证其他 Python 版本或操作系统。
uv 安装于临时工具环境，未修改系统 PATH；项目依赖在本项目 `.venv` 内，
精确版本已记录到 `uv.lock`。已确认项目许可证字段为空，未创建 LICENSE。

如果本机 uv 已加入 PATH，在项目根目录执行：

```powershell
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

工具和解释器的安装路径由本机环境决定，使用者按上述标准命令创建环境即可。
项目声明 Python >=3.11，但本轮仅在上述 3.12 环境验证。
Plotly 图形（包括数据范围限制和残差图）、Streamlit UI、许可证确认和发布
仍属于后续任务；本轮不能视为整个 v0.1 已完成。

核心接口的调用顺序：

```python
from rheolab.data import read_csv
from rheolab.fitting import fit_power_law

shear_rate, viscosity = read_csv("measurements.csv")
result = fit_power_law(shear_rate, viscosity)
print(result.k, result.n)
print(result.r_squared_log, result.rmse, result.mape_percent)
```

实际文件需符合上文数据规范；这里的文件名只是调用示例。

实现依据：SciPy 的 [linregress 官方文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html)
说明其进行线性普通最小二乘回归；包安装配置采用
[setuptools 官方说明](https://setuptools.pypa.io/en/latest/userguide/quickstart.html)。

## 6. 绘图模块与合成示例（2026-10-15）

`plotting.create_fit_figure(rates, viscosity, result, *, title=...)` 返回一个
Plotly Figure：上图为双对数黏度散点与幂律曲线，下图为原始空间残差，
残差纵轴线性并显示零参考线。图中明确区分对数 R² 与原始空间误差。
模块不重新拟合，不保存文件，不自动打开页面。

验收标准：

- 测量散点和残差保留全部输入行、重复测量和行号对应。
- 曲线按递增速率绘制，采样点全部在观测最小/最大剪切速率之间。
- 曲线使用已有 K、n，仅调用模型求值，不执行回归。
- 拒绝形状错误、非有限、非正预测，及与给定数据/参数不对应的结果。
- 标明 s⁻¹ 与 Pa·s，残差定义为实测值减预测值，常黏度 R² 显示未定义。
- 对数轴只标十倍主刻度，避免次级刻度省略数量级造成误读。
- HTML 内嵌 Plotly，可离线打开并交互；实际浏览检查标题、坐标和残差图。

新增 `test_plotting.py`：19 项测试通过；累计 141 项测试通过，Ruff
检查及格式检查通过。示例 CSV 经现有读取/拟合入口回读后绘图。

示例位于 `examples/`：40 个不同速率、每个重复两次，共 80 行；固定随机
种子 20261015，已知 K=12、n=0.62，乘性对数噪声标准差为 0.06。
拟合结果：K=11.882092、n=0.620373、R²_log=0.997138、
RMSE=0.596650 Pa·s、MAPE=4.460219%。数据、页面和说明明确标注为合成数据。

交付 CSV、可离线打开的 HTML、通过图形工具栏导出的 PNG，以及可复现的
`plot_demo.py`；生成脚本只覆盖两个同名 CSV/HTML 产物，不改动核心计算模块。
本阶段完成绘图模块，Streamlit 页面、许可证与发布仍待后续处理。

图形实现参考 [Plotly 子图说明](https://plotly.com/python/subplots/) 和
[离线 HTML 导出说明](https://plotly.com/python/interactive-html-export/)。

## 7. 最小 Streamlit 页面（2026-10-15）

新增根目录 `app.py`，仅组织输入、页面状态及现有模块调用：

1. 选择上传 CSV 或现有合成示例；页面标明必需列、单位和输入约束。
2. 使用已有 `read_csv` 校验并预览两列数据，保留全部测量与行顺序。
3. 点击按钮后调用 `fit_power_law`，展示 K、n、对数 R²、原始空间 RMSE
   和百分数 MAPE，并用 `create_fit_figure` 显示黏度图及残差图。
4. 常黏度 R² 显示未定义；非法输入、拟合失败或绘图失败不展示成功结果。

验收标准：合法 CSV 完成全部流程；更换、移除文件及切换来源后旧指标和
图形消失；同名但不同内容的文件也必须清除旧结果；新数据需重新点击拟合。
实现使用来源、文件名和内容 SHA-256 构成输入标识，变化时清除 session_state
中的旧拟合结果。无输入与非法输入不能保留旧结果。页面不实现数值算法。

新增 `tests/test_app.py` 的 13 项界面测试，使用 Streamlit AppTest 的原生文件
上传接口，覆盖正常上传、合成示例、同名/异名替换、文件移除、来源切换、
缺列、不同速率不足、非正黏度、空文件，以及可控的拟合/绘图失败。
累计 **154 项测试通过**，Ruff 检查与格式检查通过。

浏览器实际验证：

- 上传 `examples/synthetic_power_law.csv`，确认预览为 80 行、40 个不同速率。
- 点击拟合，确认 K=11.8821、n=0.620373、R²_log=0.997138、
  RMSE=0.59665 Pa·s、MAPE=4.46%，交互图与残差图显示正常。
- 替换为临时目录下同名但第 2 个数据行黏度为零的 CSV，确认清除旧指标和
  图形，错误明确包含 `viscosity data row 2`。
- 移除该文件，确认恢复等待上传状态；切换合成示例并拟合后可恢复成功结果。
- 页面结果截图保存为 `streamlit-preview.jpg`，非法输入截图保存为
  `streamlit-invalid-input.jpg`。无效 CSV 仅用于临时目录测试，不进入示例数据。

新增 README 启动与使用说明，添加 Streamlit 依赖并更新 uv.lock。
当前实际验证环境为 Windows / Python 3.12 / Streamlit 1.66；尚未验证其他
平台或 Python 版本。已有 data/models/fitting/plotting 模块未修改。
未添加部署、GitHub 自动检查或许可证文件；这些仍是后续任务。

参考：[文件上传](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader)、
[Plotly 图形组件](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)、
[AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)。

## 8. GitHub Actions 配置（2026-10-15）

新增 `.github/workflows/ci.yml`，并在 README 中补充触发方式和查看结果的方法。
工作流在 push、pull_request 和 workflow_dispatch 时运行单个检查任务：

- Ubuntu 24.04、Python 3.12、uv 0.13.1；任务最长运行 10 分钟。
- checkout v7.0.1 与 setup-uv v9.0.0 固定到已核对的提交 SHA。
- 仅授予 contents: read，checkout 不保留凭据。
- 使用 setup-uv 缓存 uv 下载内容，缓存依据为 uv.lock。
- 依次执行 `uv sync --locked --dev`、`uv run --locked pytest -q`、
  `uv run --locked ruff check .` 和 `uv run --locked ruff format --check .`。
- 任一安装或检查步骤失败时任务失败，不更新锁文件或自动格式化代码。

本地验收结果：

1. 核对官方仓库版本标签与 workflow 中的两个 Action 提交 SHA 一致。
2. 使用官方 actionlint 1.7.12 验证工作流，无错误；工具仅存于临时目录，
   下载包 SHA-256 与官方发布元数据一致，未添加项目依赖。
3. `uv sync --locked --dev` 通过；原有 uv.lock 未修改。
4. 154 项 pytest 测试通过，Ruff 和格式检查通过。

以上执行环境仍是本地 Windows / Python 3.12，不代表 Ubuntu 云端已经通过。
当前目录尚未初始化 Git，也没有 GitHub 远程地址；未推送或实际触发云端运行。
后续将项目提交并推送到 GitHub，在 Actions → CI 查看首次运行结果，才能完成
云端验收。此阶段仅修改工作流与相关说明，未修改业务代码、依赖声明或测试。

实现依据：[uv 官方 GitHub Actions 指南](https://docs.astral.sh/uv/guides/integration/github/)
及 [GitHub 工作流语法](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)。

## 9. Windows 双击启动（2026-10-15）

新增根目录 `启动RheoLab.cmd` 和 `scripts/start_rheolab.ps1`，并补充 README。
当前电脑的桌面已建立 `RheoLab.lnk`，指向项目内的 CMD 启动入口。
快捷方式只存在本机桌面，不放入 Git 仓库。

- 启动器使用项目目录定位文件，不依赖启动时的工作目录或 Codex 临时 uv 路径。
- 优先使用现有 `.venv`；环境不完整时尝试 PATH 或用户 `.local/bin` 中的 uv，
  执行 `uv sync --locked --python 3.12`。没有 uv 时明确提示安装入口。
- 使用项目路径生成的命名互斥锁，重复启动只打开已运行实例，不重复启动服务。
- 默认尝试 8501，按顺序避让至 8510，不停止或复用不明来源的端口服务。
- Streamlit 使用 headless 模式避开首次运行的邮箱询问；独立的后台任务等待
  本地健康检查通过后打开浏览器。服务仍在用户的启动窗口内运行。
- 启动失败保留提示；按 Ctrl+C 可停止服务。脚本以 UTF-8 BOM 保存，兼容
  Windows PowerShell 5.1 的中文提示；无需修改系统执行策略或 PATH。

实际验证：从项目外目录执行 CMD 入口成功；8501 已占用时使用 8502，健康
检查返回 200，并确认默认浏览器自动打开 RheoLab 页面。重复启动前后的 Python
进程集合相同（Windows 虚拟环境包含入口与实际解释器两个进程），未新增实例。
在含中文和空格的临时目录验证缺少环境/uv 时的明确错误。验证 Ctrl+C 停止后
启动器所属服务无残留，原有 8501 服务仍正常。桌面快捷方式的目标文件有效。

现有 154 项测试、Ruff 和格式检查通过；PowerShell 语法检查通过。
环境缺失时自动联网恢复依赖的分支尚未做完整安装验证；本轮验证了已安装环境
的启动和环境缺失时的提示。仍不是独立 EXE，首次准备环境可能需要联网。

实现依据：[Streamlit 启动说明](https://docs.streamlit.io/develop/api-reference/cli/run)
和 [uv 锁文件与环境同步](https://docs.astral.sh/uv/concepts/projects/sync/)。
