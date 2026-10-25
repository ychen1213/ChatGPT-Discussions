# 非周期复杂三维有限 Mark 的开源 FDTD 与 Lumerical 对比调研

讨论与资料核查日期：2026 年 10 月 26 日。

用户问题：

> 调研一下在非周期、复杂形状、三维有限结构的要求下 各个开源软件的优劣 还有他们和lumericalFDTD在这方面仿真在功能和适用性上的的差距

以下保留本轮答复原文措辞、来源链接和适用条件；公式使用 GitHub 支持的数学排版。软件功能与版本状态以资料核查日期为准。

**调研后的建议是：Meep 作为成熟的光学仿真基准；gprMax 4 和 openEMS 作为原生 Windows 的重点候选；FDTDX 保留为光子学开发和优化候选。flaport/fdtd 适合保留现有轻量用途，不建议继续把它扩展成完整的三维仿真平台。**

对于你的需求，决定选型的主要因素是：**复杂界面能否准确离散、吸收材料能否正确建模、衬底上的照明和散射能否正确分离，以及能否在可接受的内存和时间内得到可靠的复数场。**

下面按“Mark 在横向有限，下面可以有延展的多层衬底”评估。这比空气中孤立颗粒更接近我们的应用。资料核查截至 **2026 年 10 月 26 日**，包括官方文档和部分已发布源码；本轮尚未进行相同 Mark 的跨软件实测。

| 软件 | 对非周期、复杂三维 Mark 的优势 | 相对 Lumerical FDTD 的主要差距 | 对我们的定位 |
|---|---|---|---|
| **Meep** | 成熟的三维光学求解；色散、各向异性、子像素平滑、复场、背景场相减、近远场和 MPI | 常规网格分辨率统一，多尺度结构可能耗费大量内存；色散界面的平滑有限制；原生 Windows 不受官方支持 | **成熟光学后端和基准首选**，适合现有 Linux/WSL 环境。[官方文档](https://meep.readthedocs.io/en/latest/) |
| **gprMax 4.0.1** | STL/STEP 体素导入，Drude/Lorentz 材料，TFSF，复数近远场和分层背景远场；已有 Windows CPU 安装包及 CUDA 路线 | 专业聚焦照明、光学材料与成像流程需要补充；分层远场有适用限制；新版本几何转换仍有待发布修复 | **原生 Windows 的重点试验候选**，尤其值得测试 GPU 路线。[功能](https://docs.gprmax.com/en/latest/features.html)、[正式发布](https://github.com/gprMax/gprMax/releases/tag/v.4.0.1) |
| **openEMS 0.37.0** | 原生 Windows；STL/多面体；非均匀网格；多极色散材料；复场和远场输出 | 标准 TFSF 对衬底模型限制明显；聚焦光束、光学材料拟合、弱散射与成像分析需要开发 | **Windows CPU 的重点候选**，薄膜网格值得测试，但光学适配工作量不能低估。[几何](https://docs.openems.de/en/stable/concepts/primitives.html)、[色散材料](https://docs.openems.de/en/latest/concepts/dispersive.html) |
| **FDTDX 0.6.3** | 面向三维光子学；GDS/多边形、色散、非均匀网格、亚像素处理、复场和角谱投影；支持自动微分 | 部分材料、网格和平滑功能不能任意组合；完整 CAD、高 NA 照明和验证体系仍需建设；Windows GPU 受 JAX 限制 | **有发展潜力的第二梯队**，未来做参数优化更有吸引力。[API](https://fdtdx.readthedocs.io/en/latest/07_api.html) |
| **Angora** | 专门支持分层空间、聚焦光束、Drude/Lorentz、光学成像和分层近远场，物理方向很贴近 Mark | 官方仅提供 GNU/Linux；公开发行工具链较旧，现代构建和集成需要重新验证 | **值得参考其照明与分层散射实现**，暂不作为 Windows 主线。[官方项目](https://backmanlab.github.io/AngoraFDTD/) |
| **GSvit** | 面向纳米光学、粗糙表面散射；有 Windows、CUDA、色散和近远场功能 | 公开安装包较旧，现代 Windows/CUDA 兼容性、维护状态和复杂光学工作流需要核验 | **专项备用候选**，暂不优先投入。[项目](https://sourceforge.net/projects/gsvit/)、[发行文件](https://sourceforge.net/projects/gsvit/files/) |
| **flaport/fdtd** | Python 简单易改，支持三维材料数组、PML、基础源和探测器，可选 PyTorch | 完整色散、专业光源、近远场、网格和分析链缺口大；扩展到通用平台需要承担大量数值验证 | **保留轻量算例和现有功能**。[官方文档](https://fdtd.readthedocs.io/en/stable/) |

需要特别更新的是 **gprMax**：当前 4.x 的能力已经明显超出早期雷达软件的功能范围，不能因名字而排除。另一方面，openEMS 对晶圆衬底的照明限制，使它的光学适配成本比仅看“Windows＋STL＋三维”时更高。

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
| **gprMax 分层远场** | 有限内部层可以有损、色散，但两个开放的观察半空间要求无损。因此吸收型半无限衬底仍需另行处理。[发布版实现](https://github.com/gprMax/gprMax/blob/v.4.0.1/gprMax/ntff/layered.py) |
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
