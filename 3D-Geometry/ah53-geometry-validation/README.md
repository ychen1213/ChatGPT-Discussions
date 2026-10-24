# AH53 三维几何验证：先理解，再看模型

本项目回答：**不规则条纹应该怎样存进电脑，才能准确查看、测量、转换和修改？** 已完成参数化曲面（P）、三角表面（T）和体素（V）的九组独立比较、四条局部转换路线、一条全域转换，以及局部编辑与离线 3D 查看器。

独立实现并验证 A 的九组几何表示和 B 的四条转换路线，另含一次全域组合与局部编辑。输入是 AH53 名义版图上的合成工艺形貌，非实测三维重建。坐标为 X 横向 / Y 高度 / Z 长度，单位 nm。

## 新人从这里开始

- **[新增：只从体素重建 P/T 的检查与测试](AH53_从体素重建P与T_检查与测试.md)**。隔离原轮廓，完成 5/10 nm 输入的 8 条主路线和 4 类挑战。5 nm 下 P95：T 2.260 nm，三档 P 为 2.306/2.214/2.031 nm；P 文件约 3.8 MB、T 约 73.6 MB。P 精度优势有限，当前 P 拒绝孔洞/合并，T 保留。
- [新模型的独立离线 3D 预览](AH53_体素重建_3D查看.html)：下载 HTML 后可双击，库和局部数据已内嵌；完整 P/T 的 PLY 地址见新报告。预览不等于完整评分几何。
- **[P 和 T 怎样生成：从截面、扫掠和位移场讲到实际文件](AH53_P与T生成原理_从截面到三维.md)**。新增 4 张原理图，逐项对应 `x_L(Y,Z)=x_L,0(Y)+u_L(Y,Z)`，并用同一批点演示两种连接规则。
- [离线互动教学页](docs/PT生成原理_动手演示.html)：下载后用浏览器打开，可拖动 Z，比较观测位置与中间位置的 P/T。教学数据不是 AH53 实验结果。

- **[完整新手教程：目的、做了什么、原理、逐图讲解和文件用途](AH53_三种几何表示验证_详细说明.md)**。GitHub 可直接阅读，不要求先懂样条、网格或 Python。
- [五分钟操作入口](先看这里.md)。本机双击 `启动3D查看器.bat` 打开交互查看器。
- [完整技术报告与数值表](AH53_三种几何表示验证_技术验证报告.md)。需要核对指标或全部结果时阅读。
- [实际小样说明](samples/README.md) · [约 1 MB 小样压缩包](samples/AH53_实际模型小样.zip)。包含实际样条系数、闭合三角表面和 5 nm 标签裁片。

下载整个目录后，可双击 `AH53_三种几何表示验证_详细说明.html` 离线阅读；`文件用途索引.html` 可按文件名或用途搜索。保留 `docs/figures` 与 `results/20261024_v2/figures`，图片用相对路径连接。

## 生成的 3D 文件在哪？

本次执行电脑上的完整地址：

```text
D:\工作\ChatGPT-Discussions\3D-Geometry\ah53-geometry-validation\results\20261024_v2\models\
```

| 模型 | 核心数据（相对上述 models 目录） |
|---|---|
| 局部细档 P | `local_P_fine/splines.npz` |
| 局部细档 T | `local_T_direct_fine/vertices.npy` 和 `faces.npy` |
| 局部 5 nm V | `local_V_direct_fine/labels.npy` |
| 全域 P / T / V | `full_P_fine` / `full_T_direct_fine` / `full_V_direct_10nm` |

每份模型需要配套 `metadata.json` 等文件，移动时保留整个子目录。它们是数值模型，当前未导出 STL、OBJ 或 STEP。截图在 `figures`，不能代替 3D 数据。

新增体素重建结果位于 `results/20261024_voxel_reconstruction/`。其中 `models/local_5nm__P_sigma05/P/coefficients.npz` 是新 P，`models/local_5nm__T_MC/T/vertices.npy` 与 `faces.npy` 是新 T；`exports/P_5nm_sigma05_display_20nm_40nm.ply` 为 P 显示网格，`exports/T_5nm_MC_exact.ply` 为完整 T 原样导出。PLY 坐标单位为 nm，完整文件留本机；GitHub 提供内嵌局部预览与可复现源码。

**GitHub 上传范围：** 源代码、配置、报告、结果表、图片、离线查看器和小样。多 GB 的完整模型、显示缓存和本机 `.venv` 保留本地，由 `.gitignore` 排除。刚下载仓库时没有完整 `models`，请按下方命令重建，或从原电脑复制对应结果目录。

## 在另一台电脑重建

在本目录打开 PowerShell，安装 Python 后执行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe run_validation.py --config configs/default.json --output results/new_run
.\.venv\Scripts\python.exe scripts/audit_saved_results.py --output results/new_run
.\.venv\Scripts\python.exe scripts/build_report.py --run new_run
.\.venv\Scripts\python.exe serve_viewer.py --results results/new_run
```

开发检查：`.\.venv\Scripts\python.exe -m pytest tests`。查看器 Three.js 依赖已打包在 `viewer/vendor`，安装 Python 依赖后可离线运行。运行使用现有项目环境；源码仓库不包含 `.venv` 和大体素标签，结果需在本地生成。

原体素文件存在后，可执行 `.\.venv\Scripts\python.exe run_voxel_reconstruction_validation.py --output results/my_voxel_test` 重现新增实验。输入来源默认是 `20261024_v2`；首次运行其他源批次时先修改 `configs/voxel_reconstruction.json` 的 `source_run`，再用新输出目录。该入口依次净化输入、隔离重建和评分，禁止混用不同参数/输入/代码的缓存。详见 [预注册方案](docs/体素重建验证_预注册方案.md)。

首次安装需要网络。完整体素和转换模型需要数 GB 磁盘空间，程序检查内存预算。配置变化请使用新结果目录。只看小样可运行 `.\.venv\Scripts\python.exe samples/inspect_samples.py`，无需重建大模型。

`build_report.py` 生成技术报告。新手教程是本次归档运行的固定教学文档；`scripts/build_beginner_guide.py` 从 `docs` 的文稿重新组装它，不会自动替换成新运行的数据。`scripts/build_file_index.py` 刷新本机文件索引。

## 如何理解结果

局部细档 P / T / 5 nm V 的截面 P95 约为 0.015 / 0.434 / 2.367 nm。平滑合成参考与 P 的分区样条相匹配，这些数字不是制造精度。对于本轮平滑、固定拓扑且需编辑的对象，可保留原始观测并以 P 为可编辑源；T 也可以作为独立源，按用途生成派生表示。适用限制见教程及技术报告。

上述是第一轮“已提供有序轮廓点”的结果。新增体素重建实验重新寻找轮廓和对应关系，没有复现如此大的 P 精度优势；两轮输入信息、P 参数化和评价高度范围不同，不能直接把数值相减。T 的输入格中心 IoU 为 1，也不意味着恢复了体素分辨率以下的全部原始细节。

主指标为双向、弧长加权 **XY 截面距离**，不冒充全域三维 Hausdorff 误差。直接参考体素分支比稀疏观测拥有更多信息，不能把 A 当作同样实测输入下的重建排名。
