# 非周期复杂三维有限 Mark 的开源 FDTD 与 Lumerical 对比调研

讨论与资料核查日期：2026 年 10 月 26 日。

用户问题：

> 调研一下在非周期、复杂形状、三维有限结构的要求下 各个开源软件的优劣 还有他们和lumericalFDTD在这方面仿真在功能和适用性上的的差距

本报告已按后续要求改为所有软件共用的功能矩阵，并增加需要开发功能的难度等级、版本限制与来源。软件功能与版本状态以资料核查日期为准；开发难度为本项目的工程估计。

**调研后的建议是：Meep 作为成熟的光学仿真基准；gprMax 4 和 openEMS 作为原生 Windows 的重点候选；FDTDX 保留为光子学开发和优化候选。flaport/fdtd 适合保留现有轻量用途，不建议继续把它扩展成完整的三维仿真平台。**

对于你的需求，决定选型的主要因素是：**复杂界面能否准确离散、吸收材料能否正确建模、衬底上的照明和散射能否正确分离，以及能否在可接受的内存和时间内得到可靠的复数场。**

下面按“Mark 在横向有限，下面可以有延展的多层衬底”评估。这比空气中孤立颗粒更接近我们的应用。资料核查截至 **2026 年 10 月 26 日**，包括官方文档和部分已发布源码；本轮尚未进行相同 Mark 的跨软件实测。

## 统一功能矩阵与开发难度

本矩阵将原“对非周期、复杂三维 Mark 的优势”拆成 **40 个统一功能项**。每一行对照所有软件；Lumerical 作为商业参照，SCUFF-EM 作为频域边界元参照。表格较宽，可在 GitHub 横向滚动。

### 符号与难度如何阅读

| 标记 | 含义 |
|---|---|
| ✓ | 在本列证据范围内已有接口、工具或官方示例。仍需配置、收敛与项目验收；不代表与 Lumerical 精度相同。 |
| △ D0 | 有条件支持；在注明的材料、平台、角度等范围内可先配置和验证，无需先开发新算法。 |
| △ D1–D3 | 有部分实现或可用基础模块，达到本行所指工作流仍需适配；难度见下表和对应说明。 |
| ✗ D1–D4 | 核查范围内无现成实现，后面的等级是新增该功能的工程难度。表示功能缺口，不表示物理上不能实现。 |
| ？ | 证据不足或版本关系未查清；不能据此判定没有功能，也不强行估计开发难度。 |
| △ 文 | 有作者论文中的实现证据，但尚未对应到所列发行安装包；先核查版本，当前不估新增功能的难度。 |
| — | 本方法不需要该步骤，不能当作功能缺失，例如边界元不需要 FDTD 的 TFSF 盒。 |
| ✗ 厂商 | 涉及闭源求解器核心，用户不能在其源码上自行补齐；须由厂商实现或更换后端。 |

| 等级 | 开发难度 | 典型工作与验收 |
|---|---|---|
| D0 | 无新增功能开发 | 安装依赖、配置参数、验证版本与功能组合、运行收敛算例。D0 不意味着无需时间或算力。 |
| D1 | 低 | Python/命令行封装、格式或单位转换、已有复场的参考相减与孔径积分；核对坐标、相位和归一化。 |
| D2 | 中 | 几何导入与材料映射、专业光斑、材料拟合、统一角谱/成像、多模块接口；需要独立解析或数值对照。 |
| D3 | 高 | 新色散/张量更新、TFSF、分层 Green 函数、网格耦合、GPU/MPI 或系统移植；需要稳定性与收敛验证。 |
| D4 | 很高 | 多个核心模块同时重构，或达到通用商业平台的功能组合、性能、交互及验证覆盖。 |

**难度是工程判断，不是软件作者的承诺或工期。** 估计对象是“实现所列能力并验证可用”，不是只写出接口。同一功能若已有可复用模块，难度可以降低；要求跨材料、宽带、多 GPU 和计量级弱信号时，难度会提高。一个 △ 后的等级只针对其说明中的适配路线，不能理解成消除全部理论和实现限制的成本。✓ 未附等级通常对应 D0；接入 MarkSim 的统一任务和数据接口另需 D1–D2。

### 软件与版本范围

| 列名 | 本次比较范围 |
|---|---|
| Lumerical | Ansys 官方当前 FDTD 文档，以 CPU 功能为基准；GPU 的差异单独说明，不把全部 CPU 功能算到 GPU 上。 |
| Meep | 官方 Meep 1.35.0；不把第三方 GPU 扩展算成官方功能。 |
| gprMax | 4.0.1；关键能力交叉核对发布包，未发布几何修复另列。 |
| openEMS | 0.37.0；CSXCAD 接口需配套；Unreleased GPU 不算已发布支持。 |
| FDTDX | 0.6.3 发布包与官方 API；JAX 的平台限制单独计入。 |
| Angora | 官方主页标示 0.22.5，并参照作者实验室公开仓库和手册；未将每个源码文件回溯到发行压缩包。 |
| GSvit | 1.9.4 公开发行及作者 2021 年论文。论文没有给出对应软件 tag，因此增强项用 △ 文，不保证旧安装包具备。 |
| flaport | flaport/fdtd 0.3.5 基础库；不等同于当前 MarkSimFDTD 已封装的功能。 |
| SCUFF | SCUFF-EM 官方文档/源码主线；频域表面积分/边界元方法，按同一物理需求解释对应关系。 |

### A 三维几何与结构输入

| 功能 | Lumerical | Meep | gprMax | openEMS | FDTDX | Angora | GSvit | flaport | SCUFF |
|---|---|---|---|---|---|---|---|---|---|
| A1 非周期有限三维全矢量开放域 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| A2 任意三维体素/材料函数输入 | ✓ | ✓ | ✓ | △ D1–D2 | ✓ | △ D1 | △ 文 | ✓ | ✗ D3–D4 |
| A3 多材料部件与延展层状背景 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | △ 文 | ✓ | ✓ |
| A4 STL 三角几何导入 | ✓ | ✓ | △ D0 | ✓ | ✗ D1–D2 | ✗ D1–D2 | ？ | ✗ D1–D2 | ✗ D1–D2 |
| A5 GDS 读取并挤出三维 | ✓ | ✓ | ✗ D1–D2 | ✗ D1–D2 | ✓ | ✗ D1–D2 | ？ | ✗ D1–D2 | ✗ D2 |
| A6 程序化斜侧壁/曲面几何构造 | ✓ | ✓ | △ D0 | ✓ | ✓ | △ D1–D2 | △ 文 | △ D1–D2 | △ D1–D2 |
| A7 随机粗糙度或随机材料生成 | ✓ | △ D1–D2 | ✓ | △ D1–D2 | △ D1 | △ D1 | △ 文 | △ D1 | △ D1–D2 |

A2 指输入空间材料分布，不表示自动完成 CAD 修复、薄层保真和材料界面精度。A3 只说明可以建模层状背景，**不代表分层 TFSF、跨层远场、有损 PML 或全部材料组合已同时验证**。

- Meep 的 STL 要求合适的封闭三角边界；多材料部件应分开。GDS 使用官方 gdstk 到 Prism 路线。
- openEMS 引擎有 HDF5 离散材料；Python 概念页和 API 页存在差异，需核对实际 CSXCAD 版本，所以 A2 保留适配等级。
- gprMax 4.0.1 已有 STL 转换器，但后续未发布修复涉及体素尺寸、位置和薄层，A4 的 D0 是几何核验；需要回移修复时另需 D1–D2。A6 已有球、任意轴圆柱/圆锥和三角棱柱，复杂 Mark 的统一原语拼装仍需 D1。
- FDTDX 的 STL API 是导出。导入应通过外部体素化和材料映射，不能直接打勾。A6 则已有 GDS 层的 sidewall_angle/reference_plane 与球、圆柱等曲面原语，不需要先开发斜壁功能；见 [GDSLayerSpec](https://fdtdx.readthedocs.io/en/stable/api/fdtdx.GDSLayerSpec.html)。
- SCUFF 采用分段均匀材料的表面网格，可以表达复杂有限形状；A2 的叉针对任意体素/连续变化材料函数这类通用输入与求解，增加它涉及积分方程表示的改变。其原生网格格式是 msh/mphtxt，STL/GDS 转换属于外部适配。

几何依据：[Lumerical 结构与导入](https://optics.ansys.com/hc/en-us/articles/360033154434-FDTD-product-reference-manual)、[Lumerical 粗糙度](https://optics.ansys.com/hc/en-us/articles/360034382374-Tips-for-adding-surface-roughness-to-structures)、[Meep 1.35 几何](https://raw.githubusercontent.com/NanoComp/meep/v1.35.0/python/geom.py)、[Meep GDS](https://meep.readthedocs.io/en/latest/Python_Tutorials/GDS_Import/)、[openEMS 几何](https://docs.openems.de/en/v0.37.0/concepts/primitives.html)、[离散材料](https://docs.openems.de/en/latest/concepts/disc_material.html)、[gprMax 建模](https://docs.gprmax.com/en/latest/input_hash_cmds.html)、[gprMax 未发布修复](https://docs.gprmax.com/en/latest/release_notes.html)、[FDTDX API](https://fdtdx.readthedocs.io/en/stable/07_api.html)、[SCUFF 几何](https://homerreid.github.io/scuff-em-documentation/reference/Geometries/)。

### B 网格与界面离散

| 功能 | Lumerical | Meep | gprMax | openEMS | FDTDX | Angora | GSvit | flaport | SCUFF |
|---|---|---|---|---|---|---|---|---|---|
| B1 沿坐标轴变步长的非均匀计算网格 | ✓ | ✗ D3–D4 | ✗ D3 | ✓ | ✓ | ✗ D3 | ？ | ✗ D3 | — |
| B2 按波长/材料/几何自动组织光学网格 | ✓ | ✗ D2¹ | ✗ D2¹ | △ D2 | ✗ D2 | ✗ D2¹ | ？ | ✗ D2¹ | ✗ D2 |
| B3 任意局部嵌套三维子网格 | ✗ 厂商 | ✗ D3–D4 | △ D0 | ✗ D3–D4 | ✗ D3 | ✗ D3 | △ 文 | ✗ D3 | — |
| B4 介质界面平均/亚像素处理 | ✓ | ✓ | △ D0 | △ D0 | △ D0 | △ D0 | △ 文 | ✗ D3 | — |
| B5 色散界面的平均/共形处理 | △ D0 | △ D0 | △ D0 | ？ | ？ | ？ | ？ | ✗ D3 | — |

¹ B2 的 D2 只是在已有网格能力上选择步长和组织收敛，例如自动选择统一分辨率。要达到 B1 的非均匀核心或 B3 的嵌套耦合，仍需另计 D3–D4，不能用 D2 代表复制 Lumerical 自动网格系统。

**B4/B5 中的“有处理”不代表使用同一种算法或达到相同误差。**

- Lumerical 非均匀网格和 mesh override 不等于任意嵌套 subgrid；默认 conformal 不处理金属，开启金属处理仍须检查伪共振。
- Meep 的 MaterialGrid 是材料输入和插值机制，不是非均匀计算网格；B5 的现有平滑只处理瞬时部分，使用它为 D0，补齐色散响应的界面处理属于 D3–D4。
- gprMax 主网格每轴步长固定；HSG 子网格支持 CPU/CUDA、细化时要求双精度，不能与分布式 MPI 任意组合。其界面处理是电边算术平均，色散平均保留混合极点，不应等同于通用 conformal。
- openEMS 的 quarter-cell 平均与 SmoothMeshLines 有用，但分别不同于完整张量界面处理和光学自动网格。圆柱 multigrid 也不同于任意局部三维子网格。
- FDTDX 已有非均匀网格与亚像素处理，但对象须提供真实填充分数；只有二值 mask 不会自动获得几何精度提升。未确认完整色散界面处理，因此 B5 保留 ？。
- Angora 的平面材料层有界面插值，B4 为 △；通用曲面子像素处理仍需 D3。
- SCUFF 不使用 Yee 网格机制；它可以局部细化三角表面网格，仍需做曲面和积分精度收敛。B2 的光学自动网格规则仍有意义，需在外部表面网格工具中适配，估为 D2。

网格依据：[Lumerical 网格](https://optics.ansys.com/hc/en-us/articles/360034382634-Understanding-the-non-uniform-mesh-in-FDTD)、[Lumerical 共形处理](https://optics.ansys.com/hc/en-us/articles/360034382614-Selecting-the-best-mesh-refinement-option-in-the-FDTD-simulation-object)、[Meep 平滑](https://meep.readthedocs.io/en/latest/Subpixel_Smoothing/)、[gprMax 子网格与精度](https://docs.gprmax.com/en/latest/accelerators.html)、[openEMS 网格](https://docs.openems.de/en/v0.37.0/concepts/mesh.html)、[圆柱 subgridding](https://docs.openems.de/en/v0.37.0/concepts/cylindrical_fdtd.html)、[FDTDX 非均匀网格](https://fdtdx.readthedocs.io/en/stable/api/fdtdx.RectilinearGrid.html)、[FDTDX 初始化与组合限制](https://github.com/ymahlau/fdtdx/blob/59ec558484d709d511cd70e3a8a45c05e662cfda/src/fdtdx/fdtd/initialization.py)。

### C 材料

| 功能 | Lumerical | Meep | gprMax | openEMS | FDTDX | Angora | GSvit | flaport | SCUFF |
|---|---|---|---|---|---|---|---|---|---|
| C1 电导损耗/复介电响应 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| C2 Drude/Lorentz 电色散 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | △ 文 | ✗ D3 | ✓ |
| C3 实验 n,k 到可用模型的自动拟合工具 | ✓ | ✓ | △ D2 | △ D2 | ✗ D2 | ✗ D2 | ？ | ✗ D3² | — |
| C4 对角各向异性 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ D3 | ？ | ✓ | ✗ D3–D4 |
| C5 非对角张量/旋转主轴 | △ D0 | △ D0 | ✗ D3 | ✗ D3 | △ D0 | ✗ D3 | ？ | △ D2–D3 | ✗ D3–D4 |

² flaport 的宽带材料拟合首先依赖 D3 色散求解实现，随后还需 D2 拟合与验证。不能只拟合一条曲线就认为基础库已经支持该材料。

- Meep 有官方 Lorentz 拟合脚本，所以 C3 打勾；它与 Lumerical 的交互材料浏览和自动检查体验仍不同。
- gprMax 有 DebyeFit，但面向光学金属的稳健 Drude/Lorentz 拟合仍需适配；openEMS 有色散模型与部分辅助工具，不能视为完整的实验 n,k 自动拟合系统。openEMS 对角各向异性本身已有接口，但官方说明其与色散同时使用尚未测试。
- C5 的 △ 各有范围：Lumerical 的一般张量转换要求满足其可对角化条件；Meep 常用实对称张量等受支持形式；FDTDX 的非对角色散极点不能与非均匀网格直接组合。
- flaport 的 AnisotropicObject 内部有张量操作，但公开初始化主要构造对角项；不能把类名当作完整旋转张量支持。
- SCUFF 按频率直接输入复介电常数或插值材料表，C3 不需要时域极点拟合；n,k 到 ε 的转换为 D1。它不支持一般各向异性和连续空间变化材料，不能将另一个项目 BUFF-EM 的能力算入。

材料依据：[Lumerical n,k 拟合](https://optics.ansys.com/hc/en-us/articles/360034915093-Creating-new-sampled-data-materials-in-FDTD)、[Lumerical 张量](https://optics.ansys.com/hc/en-us/articles/360034394694-Creating-anisotropic-optical-materials-in-FDTD-and-MODE)、[Meep 材料](https://meep.readthedocs.io/en/latest/Materials/)、[Meep 发布版拟合脚本](https://github.com/NanoComp/meep/blob/v1.35.0/python/examples/eps_fit_lorentzian.py)、[gprMax 材料与平均](https://docs.gprmax.com/en/latest/input_hash_cmds.html)、[DebyeFit](https://docs.gprmax.com/en/latest/inc_DebyeFit.html)、[openEMS 色散](https://docs.openems.de/en/v0.37.0/concepts/dispersive.html)、[openEMS 材料限制](https://docs.openems.de/en/v0.37.0/concepts/properties.html)、[FDTDX Material](https://fdtdx.readthedocs.io/en/stable/api/fdtdx.Material.html)、[SCUFF 材料](https://homerreid.github.io/scuff-em-documentation/reference/Materials/)、[SCUFF 与 BUFF 的适用性区别](https://homerreid.github.io/buff-em-documentation/reference/BUFFvsSCUFF/)。

### D 光源与衬底照明

| 功能 | Lumerical | Meep | gprMax | openEMS | FDTDX | Angora | GSvit | flaport | SCUFF |
|---|---|---|---|---|---|---|---|---|---|
| D1 宽带时间脉冲 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| D2 普通平面波照明层状样品 | ✓ | ✓ | △ D0 | △ D2 | ✓ | ✓ | △ 文 | △ D2 | △ D1–D2 |
| D3 三维空间 Gaussian 光束 | ✓ | ✓ | ✗ D2 | △ D1–D2 | ✓ | ✓ | △ 文（聚焦源） | △ D2 | ✓ |
| D4 高 NA 全矢量物镜聚焦 | ✓ | △ D2–D3 | ✗ D2–D3 | ✗ D2–D3 | ✗ D2 | ✓ | ？ | ✗ D2–D3 | △ D2–D3 |
| D5 均匀背景封闭 TFSF 盒 | ✓ | ✗ D2–D3 | ✓ | △ D0 | △ D0 | ✓ | ✓ | ✗ D2–D3 | — |
| D6 分层背景 TFSF 正入射 | ✓ | ✗ D3 | ✓ | ✗ D3 | ✗ D2–D3 | △ D0 | △ 文 | ✗ D3 | — |
| D7 分层背景 TFSF 斜入射 | △ D0 | ✗ D3–D4 | ✗ D3 | ✗ D3–D4 | ✗ D3 | △ D0 | ？ | ✗ D3–D4 | — |

**D2 与 D5–D7 必须分开看。** 没有现成 TFSF 盒，仍可用入射源、直接求解层状样品和参考运行得到散射。Meep 的常用工作流就是这种路线，无需为了模拟 Mark 而先实现整个 TFSF 模块。

- Lumerical 分层 TFSF 要求源盒侧边看见相同层状背景；注入坐标轴垂直膜层，光的传播角可以非零。斜入射角随频率变化及网格条件仍需处理。GPU 不支持此 TFSF 功能。
- gprMax 分层 TFSF 的轴向形式限正入射；有 Gaussian 时间脉冲不能算三维空间光斑。
- openEMS 现成 TFSF 只适用于空气/真空源盒边界；普通层状照明应另做激励和归一化。
- FDTDX TFSF 源面要求局部各向同性；GaussianPlaneSource 有空间包络，但不等同于高 NA 物镜 pupil 的完整矢量场。
- Angora 有聚焦光束和分层 TFSF，但任意损耗/色散/角度组合仍需核实，D6/D7 的 △ 不能读成无限制支持。
- GSvit 作者论文有平面波分解聚焦源；D3 记录这项部分证据，精确 Gaussian 参数和高 NA pupil 工作流仍需核验。
- SCUFF 直接在积分方程中使用入射场和分层 Green 函数，TFSF 盒不适用；D2 的层状照明组合仍需验证。其现成 Gaussian 也不能直接等同任意物镜 pupil。

光源依据：[Lumerical 光束](https://optics.ansys.com/hc/en-us/articles/360034382854-Plane-wave-and-beam-source-Simulation-object)、[物镜 pupil](https://optics.ansys.com/hc/en-us/articles/360034902053-Defining-a-beam-using-a-pupil-function)、[Lumerical TFSF](https://optics.ansys.com/hc/en-us/articles/360034382934-Tips-and-best-practices-when-using-the-FDTD-TFSF-source)、[Meep 发布版源接口](https://raw.githubusercontent.com/NanoComp/meep/v1.35.0/python/source.py)、[gprMax 激励](https://docs.gprmax.com/en/latest/features.html)、[openEMS 激励限制](https://docs.openems.de/en/v0.37.0/concepts/excitations.html)、[FDTDX Gaussian](https://fdtdx.readthedocs.io/en/stable/api/fdtdx.GaussianPlaneSource.html)、[FDTDX TFSF](https://fdtdx.readthedocs.io/en/stable/api/fdtdx.TFSFPlaneSourceRegion.html)、[SCUFF 入射场](https://homerreid.github.io/scuff-em-documentation/reference/IncidentFields/)。

### E 复场、远场与测量信号

| 功能 | Lumerical | Meep | gprMax | openEMS | FDTDX | Angora | GSvit | flaport | SCUFF |
|---|---|---|---|---|---|---|---|---|---|
| E1 频域复 E/H 获取与相位保存 | ✓ | ✓ | ✓ | ✓ | ✓ | △ D1 | ？ | △ D1–D2 | ✓ |
| E2 两次参考运行的复场相减流程 | △ D1 | ✓ | △ D1 | △ D1–D2 | △ D1 | △ D1 | ？ | △ D1–D2 | △ D1 |
| E3 均匀介质近远场并保留复数幅相 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ？ | ✗ D2–D3 | ✓ |
| E4 跨分层界面的 Green 函数远场 | ✗ D3 | ✗ D3 | △ D0 | ✗ D3 | ✗ D2–D3 | △ D0 | ？ | ✗ D3 | △ D2 |
| E5 吸收半无限衬底的分层 Green 函数反射远场 | ✗ D3 | ✗ D3 | ✗ D3 | ✗ D3 | ✗ D3 | ？ | ？ | ✗ D3 | △ D2 |
| E6 指定 NA 内的角度/偏振/功率分析 | ✓ | △ D1–D2 | △ D1–D2 | △ D1–D2 | △ D1–D2 | ✓ | ？ | ✗ D2–D3 | △ D1–D2 |
| E7 相干物镜成像与复场传播 | ✓ | ✗ D2–D3 | ✗ D2 | ✗ D2–D3 | ✗ D2 | ✓ | ？ | ✗ D2–D3 | ✗ D2 |
| E8 波导本征模式源与模式投影 | ✓ | △ D0 | ✓ | △ D2 | ✓ | ？ | ？ | ✗ D3 | ？ |

**E4/E5 的叉只针对“跨层 Green 函数远场模块”，不能解释为无法模拟吸收衬底上的 Mark。** 若只收集空气侧反射，可在上方均匀空气区采复场，再做角谱、背景相减和 NA 分析，通常是 D1–D2；有限监测面、源分离和相位归一化必须验证。没有必要为了这条反射观测路线先开发 E5。

- E1 中在线 DFT 与时域记录后 FFT 都能提供复场，但内存与工作流不同。Angora 的现成 phasor 主要在远场模块；flaport 只有基础记录和 FFT 辅助，仍需组织完整 E/H 与相位校准。
- E2 专指参考/样品双运行的流程，普通数组相减不算现成专用接口。Lumerical/Angora 的 TFSF 及 SCUFF 的直接散射场输出是另一条已有路线，E2 的 △ 不否定它们能直接输出散射场。
- gprMax 4.0.1 分层远场要求开放观察半空间无损，而且分层背景各层的 Re(ε)、Re(μ) 为正。金属有限散射体可建模，不代表负 ε 的无限背景层可以使用同一分层投影。
- Lumerical、Meep、openEMS 和 FDTDX 的通用投影均有均匀介质条件。Lumerical 的改变远场折射率/Fresnel 后处理也不能当作完整跨层多重散射 Green 函数。
- GSvit 确认有时域近远场，但未确认保相位的复数输出和本行完整工作流，E3 保留 ？。
- Angora 有光学成像与总场/散射场/背景场输出；其分层频域和时域变换的适用范围不同，不能混用。
- SCUFF 有全波分层 Green 函数和复材料输入；复杂 Mark、吸收底层、指定反射角谱的组合仍需适配和验收，E5 保留 △。
- E7 不包含任意像差、部分相干和整台光学仪器的全部功能。扩展为完整成像系统需另计 D2–D3。E8 中 Meep 的 MPB 模式求解有材料适用范围；openEMS 的解析/自定义波导端口不等于通用光学截面本征模求解器。

场与分析依据：[Lumerical 远场条件](https://optics.ansys.com/hc/en-us/articles/360034914713-Far-field-projections-in-FDTD-overview)、[Lumerical 复远场](https://optics.ansys.com/hc/en-us/articles/360034410114-farfieldvector3d-Script-command)、[简化显微成像](https://optics.ansys.com/hc/en-us/articles/360042260213-Simplified-microscopic-imaging)、[Meep 背景相减](https://meep.readthedocs.io/en/latest/Python_Tutorials/Basics/)、[Meep 近远场](https://meep.readthedocs.io/en/latest/Python_Tutorials/Near_to_Far_Field_Spectra/)、[Meep 模式源](https://meep.readthedocs.io/en/latest/Python_Tutorials/Eigenmode_Source/)、[gprMax 发布版分层变换](https://github.com/gprMax/gprMax/blob/v.4.0.1/gprMax/ntff/layered.py)、[openEMS NF2FF](https://docs.openems.de/en/v0.37.0/concepts/nf2ff.html)、[openEMS 端口](https://docs.openems.de/en/v0.37.0/python/openEMS/ports.html)、[FDTDX 投影](https://fdtdx.readthedocs.io/en/stable/api/fdtdx.FieldProjectionAngleDetector.html)、[SCUFF 散射输出](https://homerreid.github.io/scuff-em-documentation/applications/scuff-scatter/scuff-scatter/)、[SCUFF 全波分层 Green 函数](https://homerreid.github.io/scuff-em-documentation/tex/FullWaveSubstrate.pdf)。

### F 平台、并行与工程接口

| 功能 | Lumerical | Meep | gprMax | openEMS | FDTDX | Angora | GSvit | flaport | SCUFF |
|---|---|---|---|---|---|---|---|---|---|
| F1 原生 Windows CPU 路线 | ✓ | ✗ D3 | ✓ | ✓ | △ D0 | ✗ D3 | △ D0 | ✓ | ？ |
| F2 原生 Windows NVIDIA GPU 路线 | △ D0 | ✗ D3–D4 | △ D0 | ✗ D3–D4 | ✗ D3 | ✗ D3–D4 | △ D0 | △ D0 | ？ |
| F3 Linux GPU 路线 | △ D0 | ✗ D3–D4 | ✓ | ✗ D3–D4 | ✓ | ✗ D3–D4 | △ D0 | ✓ | ？ |
| F4 单个模型的 MPI 域分解 | ✓ | ✓ | △ D0 | ✗ D3 | ✗ D3 | ✓ | ？ | ✗ D3 | ？ |
| F5 公开可用的 float64 E/H 场求解 | ？ | ✓ | ✓ | ✗ D2–D3 | ✓ | ✓ | △ 文 | ✓ | ✓ |
| F6 Python API | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ D1–D2 | ？ | ✓ | ✓ |
| F7 集成几何/材料/光源/结果 GUI | ✓ | ✗ D2–D3 | ✗ D2–D3 | △ D2 | ✗ D2–D3 | ✗ D2–D3 | △ 文 | ✗ D2–D3 | ✗ D2–D3 |
| F8 伴随梯度/自动微分优化 | △ D0 | △ D0 | ✗ D3–D4 | ✗ D3–D4 | △ D0 | ✗ D3–D4 | ？ | ✗ D3–D4 | ？ |

- F1/F2 的“原生”不包含 WSL。Meep 的 Windows 移植涉及依赖、构建与 Python/DLL；FDTDX 的 Windows GPU 缺口来自 JAX，不能只改 FDTD 参数解决。
- gprMax Windows CPU wheel 已发布；CUDA 仍需 Toolkit、PyCUDA、MSVC 等环境。FDTDX Windows CPU 依赖路线存在，但项目完整流程尚未实测。GSvit 只有历史发行和平台声明，现代环境从 D0 验证开始；失败后的修复工作量尚不能承诺。
- openEMS 0.37.0 移除了 MPI；GPU 仍在 Unreleased。试验未发布 GPU 核心与从零编写的成本不同，但都不能给当前发行版打勾。
- F4 只指 MPI。FDTDX 已有 JAX sharding 多设备机制；没有 MPI 不等于没有任何多设备能力。gprMax 的 MPI CPU 域分解与 GPU 独立任务并行也不能混称单模型多 GPU。
- F5 比较 E/H 场精度，不代表全部材料、系数和输出都同一精度。Angora E/H 为 double、材料参数仍有 float；SCUFF 使用频域复双精度。Lumerical 官方说明采用混合精度，未确认可选的全场 float64 模式，故保留 ？。openEMS 更改 typedef 后仍需验证 SIMD、扩展和输出，不能视作已经支持。
- F6 中 Angora 可用 D1 子进程封装，真正 Python 绑定更接近 D2。F7 的 D2–D3 是本项目所需 GUI；复制商业平台全部交互和验证生态属于 D4。
- F8 的 ✓/△ 与 PyTorch 后端不同：有张量库不自动获得正确伴随梯度。Lumerical LumOpt、Meep adjoint 和 FDTDX 可微路线均须对实际材料、目标函数及几何参数校验梯度。

平台依据：[Lumerical GPU 限制](https://optics.ansys.com/hc/en-us/articles/17518942465811-Getting-started-with-running-FDTD-on-GPU)、[Lumerical MPI](https://optics.ansys.com/hc/en-us/articles/360026321353-Distributed-computing)、[Lumerical 精度说明](https://optics.ansys.com/hc/en-us/articles/360034915833-Convergence-testing-process-for-FDTD-simulations)、[Lumerical Python API](https://optics.ansys.com/hc/en-us/articles/39744901602707-Installation-and-Getting-Started-Python-API)、[LumOpt](https://optics.ansys.com/hc/en-us/articles/360049853854-Photonic-Inverse-Design-Overview-Python-API)、[Meep 安装](https://meep.readthedocs.io/en/latest/Installation/)、[Meep 构建精度](https://meep.readthedocs.io/en/latest/Build_From_Source/)、[Meep 伴随](https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/)、[gprMax 4.0.1](https://github.com/gprMax/gprMax/releases/tag/v.4.0.1)、[gprMax 加速与精度](https://docs.gprmax.com/en/latest/accelerators.html)、[openEMS 发布记录](https://docs.openems.de/en/latest/changelog/openEMS.html)、[openEMS 场类型](https://raw.githubusercontent.com/thliebig/openEMS/v0.37.0/tools/constants.h)、[JAX 平台支持](https://docs.jax.dev/en/latest/installation.html)、[SCUFF 安装](https://homerreid.github.io/scuff-em-documentation/reference/Installing/)。

### 其他软件列的证据与版本限制

| 软件 | 核查依据与表中限制 |
|---|---|
| Angora | [作者实验室主页](https://backmanlab.github.io/AngoraFDTD/)、[配置字段](https://raw.githubusercontent.com/BackmanLab/AngoraFDTD/master/cfg/config_all.cfg)、[仓库手册](https://raw.githubusercontent.com/BackmanLab/AngoraFDTD/master/doc/angora.texi)、[场与材料类型](https://raw.githubusercontent.com/BackmanLab/AngoraFDTD/master/src/globals.h)。支持聚焦、分层与成像；体素文件输入有单参数/量化等限制，材料限各向同性。 |
| GSvit | [项目功能](https://sourceforge.net/projects/gsvit/)、[发行文件](https://sourceforge.net/projects/gsvit/files/)、[作者 2021 年论文](https://dspace.vut.cz/server/api/core/bitstreams/87b3846f-8cf3-4fd4-90a5-7205104f6475/content)。论文第 2–3 页描述 VTK/四面体、分层 TSF、聚焦、局部子网格、有效介质、PLRC/ADE 与 CPU 双精度等；未给出软件 tag，增强项全部保留“△ 文”。 |
| flaport | [0.3.5 发布包](https://pypi.org/project/fdtd/0.3.5/)、[官方文档](https://fdtd.readthedocs.io/en/stable/)。本次交叉检查 wheel 中的 sources、objects、detectors、fourier、grid；文档页面自标旧版本，未据其标题推断发布版。库支持三维，不表示 MarkSimFDTD 当前二维周期适配器已支持本矩阵全部能力。 |
| SCUFF | [几何与分层介质](https://homerreid.github.io/scuff-em-documentation/reference/Geometries/)、[材料适用性](https://homerreid.github.io/buff-em-documentation/reference/BUFFvsSCUFF/)。Windows 安装节缺少可核验步骤，MPI 编译器说明也不足以证明单模型 MPI 求解，故保留 ？。 |

本次另发现 [第三方 meep-gpu 1.0.0](https://pypi.org/project/meep-gpu/1.0.0/)。它是依赖现有 Meep 建模与后处理的独立 beta 扩展，不是新增的完整独立求解平台；作者只报告有限硬件和算例，且 GPU 路线以单精度为基准。它值得单独试验，但不能据此把官方 Meep 的 Windows/GPU 单元格改成 ✓。

### 对 MarkSim 的开发优先级

| 路线 | 应先补齐的功能 | 难度判断 | 何时才值得做更重的开发 |
|---|---|---|---|
| Meep | 几何/任务接口、参考场、反射角谱、NA 与成像 | D1–D2；严格高 NA 光源可到 D2–D3 | 原生 Windows 是不可放宽条件且其他候选未通过时，再评估 D3 移植。 |
| gprMax | 光学 n,k 拟合、有限光斑、几何核验、统一复场/成像 | 主要 D1–D2；Windows CUDA 先 D0 验证 | 确实需要分层斜入射 TFSF 或跨层金属/吸收外部介质投影时，再投入 D3。 |
| openEMS | 层状样品激励、有限光斑、材料拟合、反射复场提取 | 主要 D2，不能只做文件格式转换 | 只有项目证据表明必须，才投入 D3 级 GPU、完整张量或新边界模块。 |
| FDTDX | STL/多材料输入、材料拟合、角谱/NA/成像 | 主要 D1–D2 | 原生 Windows GPU 属 D3 后端问题；可优先选择其他运行路线。 |
| Angora | 任务与几何封装、现代依赖验证 | 接口 D1–D2；Windows 移植 D3 | 其聚焦/分层/成像优势足够覆盖迁移成本时。 |
| GSvit | 先确认论文功能对应版本，再验证现代 Windows/CUDA | 先 D0 核查；版本未知项暂不估新功能开发 | 形成可重建、可复现的版本基线以后。 |
| flaport | 色散、专业源、界面算法、近远场、三维分析链 | 单项 D2–D3，整条路线趋向 D4 | 只有明确选择自研求解器平台，而非尽快完成 Mark 仿真时。 |
| SCUFF | 表面网格/材料接口、分层照明组合、复角谱与 NA | 主要 D1–D2；各向异性可能 D3–D4 | 少数频率、分段均匀材料的实际模型显示资源或精度优势时。 |
| Lumerical | Python 调度、统一输入/结果和测量后处理 | 项目适配 D1–D2 | 核心缺口须走厂商路线或外部后处理，不能按开源内核估算。 |

这些难度不能相加成总工期，也不能按对勾数量给软件排总分。对当前任务，优先验证 **A1–A6 的几何保真、C1–C3 的材料、D2–D4 的实际照明、E1–E3/E6–E7 的复场与测量信号，以及 F1–F3 的部署和规模能力**。分层 TFSF 与分层 Green 函数是可选实现路线，不是每个 Mark 工作流都必须开发。

## 适用性分析与验证路线

**gprMax 4.x** 已具备多种可用于光学仿真的能力，值得进入实际 Mark 验证。另一方面，openEMS 对晶圆衬底的照明限制，使它的光学适配成本比仅看“Windows＋STL＋三维”时更高。

**和 Lumerical 的差距，可以分成下面几类。**

**第一，复杂形状的主要难点是界面精度和计算成本。**

斜侧壁、圆角、薄膜、小缺口都可以被离散，但这些细节可能决定 Mark 的弱散射和相位。Lumerical 提供自动非均匀网格、局部网格设置和 conformal 界面处理，能够减少用户自行组织网格的工作。不过，默认 conformal 不处理金属/PEC 界面，金属 conformal 也需要检查伪共振和收敛。[官方网格说明](https://optics.ansys.com/hc/en-us/articles/360034382614-Selecting-the-best-mesh-refinement-option-in-the-FDTD-simulation-object)

Meep 的介质子像素平滑较成熟，但它对色散材料只平滑瞬时介电响应，不能把损耗和色散界面的误差一并消除。对于金属、吸收衬底和斜侧壁，这可能增加网格需求。[Meep 平滑限制](https://meep.readthedocs.io/en/latest/Subpixel_Smoothing/)

还有两个具体发现：

- **Meep 1.35.0 已有 `Mesh.from_file`**，可通过三角网格导入 STL 等复杂几何；多材料部件需要分别处理。因此复杂 CAD 入口本身已不是它的主要短板。[发布版几何源码](https://raw.githubusercontent.com/NanoComp/meep/v1.35.0/python/geom.py)
- **gprMax 最新未发布修复涉及 STL 体素化尺寸和位置误差。** 试验时必须核对转换后的体积、位置和薄层厚度，并固定版本。[发布说明](https://docs.gprmax.com/en/latest/release_notes.html)

对于均匀三维网格，三个方向的网格间距同时减半，网格数约增加到 **8 倍**，同一物理时间需要的时间步约增加到 **2 倍**。这也是复杂有限 Mark 特别依赖网格效率的原因。

**第二，真实光学材料和实际照明，是商业软件较明显的优势。**

Lumerical 可以导入实验 $n,k$ 数据并拟合时域材料模型；光源包含 Gaussian、全矢量薄透镜光束和 pupil 定义，适合把物镜 NA、偏振和有限光斑纳入模型。[材料拟合](https://optics.ansys.com/hc/en-us/articles/360034915093-Creating-new-sampled-data-materials-in-FDTD)、[光束源](https://optics.ansys.com/hc/en-us/articles/360034382854-Plane-wave-and-beam-source-Simulation-object)

开源软件中的 Drude/Lorentz 支持，为真实光学材料提供了基础，但仍需完成实验数据拟合、带宽误差和稳定性验证。对于光源也要区分：

- 时间上的 Gaussian 脉冲；
- 空间上的 Gaussian 光斑；
- 包含纵向场分量的高 NA 聚焦光束。

三者对应不同功能。gprMax 当前公开接口没有完整的高 NA 聚焦光束工作流；FDTDX 的 Gaussian 剖面源也不能直接视为 Lumerical 全矢量聚焦源的等价实现。[gprMax 激励](https://docs.gprmax.com/en/latest/features.html)、[FDTDX Gaussian 源](https://fdtdx.readthedocs.io/en/latest/api/fdtdx.GaussianPlaneSource.html)

**第三，衬底上的有限 Mark，是最应优先验证的场景。**

这里有几项直接影响适用性的限制：

| 软件/功能 | 对我们有什么影响 |
|---|---|
| **Lumerical CPU TFSF** | 支持多层和吸收背景，但源盒侧边必须看到一致的层状背景，Mark 要满足源盒位置要求。[官方说明](https://optics.ansys.com/hc/en-us/articles/360034382934-Tips-and-best-practices-when-using-the-FDTD-TFSF-source) |
| **openEMS 标准 TFSF** | 源盒边界要求处于空气/真空，不能穿过材料。横向延伸的晶圆衬底需要另行设计激励和参考场相减流程。[官方限制](https://docs.openems.de/en/stable/concepts/excitations.html) |
| **gprMax 分层远场** | 有限内部层允许一定范围的损耗、色散，但背景各层要求 Re(ε)、Re(μ) 为正，两个开放的观察半空间还要求无损。负 ε 的金属背景层、吸收型半无限衬底不能直接套用该投影。[发布版实现](https://github.com/gprMax/gprMax/blob/v.4.0.1/gprMax/ntff/layered.py) |
| **Lumerical 标准近远场投影** | 同样要求监测面位于单一均匀介质，不能任意跨空气和衬底界面；有限监测面的截断也会产生误差。[官方要求](https://optics.ansys.com/hc/en-us/articles/360034914713-Far-field-projections-in-FDTD-overview) |

对于我们主要关心的反射信号，可以考虑在 **Mark 上方的均匀空气区采集复数场，再进行角谱和物镜 NA 分析**。这条路线仍需验证监测面尺寸、位置以及入射场分离。

非周期有限 Mark 的输出也应从现有的离散衍射级次，扩展到 **连续角分布、复数偏振场和收集孔径内的信号**。若测量依赖 Mark 散射与平坦衬底反射的相干干涉，就需要保留两者的相位关系：

$$
I\propto\left|E_{\mathrm{背景}}+E_{\mathrm{Mark散射}}\right|^2
$$

只比较总反射率或散射强度，可能无法判断最终 Mark 测量信号是否正确。Lumerical 已有复数远场和显微成像示例，开源后端通常需要我们统一建立这层分析。[复数远场](https://optics.ansys.com/hc/en-us/articles/360034410114-farfieldvector3d-Script-command)、[成像示例](https://optics.ansys.com/hc/en-us/articles/360042260213-Simplified-microscopic-imaging)

**第四，Windows 和 GPU 要按已发布功能分别看。**

- **Meep：**官方仍不支持原生 Windows，推荐 WSL；成熟并行路线是 CPU MPI。[安装说明](https://meep.readthedocs.io/en/latest/Installation/)、[并行说明](https://meep.readthedocs.io/en/latest/Parallel_Meep/)
- **openEMS 0.37.0：**已有 Windows CPU 发行包；GPU 工作列在未发布部分，该版本还移除了 MPI。[版本记录](https://docs.openems.de/en/latest/changelog/openEMS.html)
- **gprMax 4.0.1：**Windows CPU wheel 已发布；Windows CUDA 还需要 CUDA Toolkit、PyCUDA 和相应编译环境。公司电脑能否部署这套环境需要实际核查。[加速器要求](https://docs.gprmax.com/en/latest/accelerators.html)
- **FDTDX：**JAX 有 Windows CPU 支持，但官方不支持原生 Windows NVIDIA GPU。这个限制会直接影响它作为我们大规模三维后端的价值。[JAX 平台支持](https://docs.jax.dev/en/latest/installation.html)
- **Lumerical：**有 Windows GPU 路线，但当前 GPU 不支持 TFSF、BFAST 等部分 CPU 功能，也必须按实际模型组合选运行方式。[GPU 支持范围](https://optics.ansys.com/hc/en-us/articles/17518942465811-Getting-started-with-running-FDTD-on-GPU)

此外，如果以后主要计算**少数波长、各区域内部均匀的复杂结构**，可以把 **SCUFF-EM 边界元**作为专项候选。它以表面网格表示物体，并支持隐式分层衬底，有机会减少空气区域的体网格成本；但需要每频率求解线性系统，也尚未验证我们的具体 Mark 组合。[几何与衬底支持](https://homerreid.github.io/scuff-em-documentation/reference/Geometries/)

**对 MarkSimFDTD，我建议按以下路线选择。**

1. **保留 Meep 和 Lumerical 作为交叉基准。** Lumerical 参考算例也要经过网格、时间和边界收敛，不能直接把默认结果当真值。
2. **第一轮并行验证 gprMax 与 openEMS。** 前者重点看 Windows GPU、色散和复场；后者重点看 Windows 部署、薄膜网格以及衬底照明。
3. **FDTDX 做第二轮候选。** 如果后续需要自动优化，或能接受 Linux GPU，它的优先级可以提高。
4. **暂缓全面移植 Meep，也暂缓给 flaport 大规模补功能。** 先确定现成后端缺的究竟是哪几项，再决定做局部扩展还是移植。

验收至少应覆盖这几类模型：

| 验证模型 | 主要判断什么 |
|---|---|
| 球散射、平坦薄膜 | 与解析解比较，检查材料、归一化和基本场精度 |
| 有限非对称 L 形/十字 Mark | 检查三维端部效应、交叉偏振和连续角谱 |
| 多层或吸收衬底上的斜侧壁 Mark | 检查真正影响选型的材料、源、PML 和场提取组合 |
| 带圆角、薄层或金属细节的 Mark | 检查界面误差与网格成本 |
| 实际尺寸、实际光斑的 Mark | 检查复场误差、NA 内信号、内存和运行时间 |

**最终应选择“能以可接受资源让实际 Mark 的幅度、相位和测量信号收敛”的后端。现有证据支持上述候选排序，还不足以承诺某个开源软件能全面替代 Lumerical，或给出固定的精度差距百分比。**
