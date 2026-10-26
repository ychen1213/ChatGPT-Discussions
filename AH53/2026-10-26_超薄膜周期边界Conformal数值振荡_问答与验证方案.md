# AH53 7.9 nm薄膜：周期边界、Conformal Mesh 与衍射振幅伪振荡

> 对话归档 1/2 · 2026-10-26 · 原问题与上一轮分析的结构化记录；本轮补充的完整公式、理论图和独立LSF详见 [局部介电扰动的傅里叶推导与完整测试](2026-10-26_AH53局部介电扰动傅里叶推导与测试代码_完整问答.md)。

## 用户提问（原文）

> 实际上是绝对变化相同 另一个ai的分析是在存在超薄膜时周期性边界条件和conformal mesh在边缘处理出现问题 边缘出现介电常数不连续的点 你看看呢

## 核心结论

**对方提出的机制确有官方依据，应优先验证，但“绝对振荡相近”不是边界接缝故障的唯一指纹。** 一个网格宽的异常介电常数区域或边缘位置误差会有较宽的空间傅里叶谱，从而可能向许多低阶衍射通道贡献大小接近的附加复散射。其电磁散射幅值还与局部场、偏振及级次有关。

官方出处：

- [Is the boundary condition region important for simulations with Bloch/periodic boundary conditions?](https://optics.ansys.com/hc/en-us/articles/4412965790611-Is-the-boundary-condition-region-important-for-simulations-with-Bloch-periodic-boundary-conditions)：周期/Bloch边界处理区厚一个网格单元，要求材料在两侧周期对应位置匹配，建议在边界外延续至少一个周期的结构。
- [Optical Metrology – S-Matrix Methodology](https://optics.ansys.com/hc/en-us/articles/360042238733-Optical-Metrology-S-Matrix-Methodology)：弱散射仿真要避免人为破坏周期性；建议在样品平面使用完整周期范围的统一网格，避免只在局部缺陷附近添加不同横向网格；延伸物体到周期边界处理区。
- [Selecting the best mesh refinement option](https://optics.ansys.com/hc/en-us/articles/360034382614-Selecting-the-best-mesh-refinement-option-in-the-FDTD-simulation-object)：Conformal Variant 0默认可处理多数非金属双材料界面；一个网格单元出现三种以上材料时，该单元退回Staircase。

## 1. 为什么小小的边界异常会散射到多个级次？

对于AH53母周期 $P=16\,\mu\mathrm m$，$G=2\pi/P$。把局部误差简化为宽$a$、中心$x_b$、强度$\delta\epsilon_0$的矩形区域：

$$
\delta\epsilon(x)=\delta\epsilon_0\mathbf1_{[x_b-a/2,x_b+a/2]}(x).
$$

其横向傅里叶系数为：

$$
\boxed{\widehat{\delta\epsilon}_m=
\frac{\delta\epsilon_0 a}{P}
\,\mathrm{sinc}\!\left(\frac{\pi ma}{P}\right)
e^{-imGx_b}},
\quad \mathrm{sinc}(u)=\frac{\sin u}{u}.
$$

当 $a=25\,\mathrm{nm}$ 时：

| 级次 $|m|$ | $|\mathrm{sinc}(\pi ma/P)|$ |
|---:|---:|
| 0 | 1 |
| 1 | 0.999996 |
| 5 | 0.999900 |
| 8 | 0.999743 |
| 16 | 0.998972 |
| 24 | 0.997688 |

因此几何频谱在低阶非常接近平坦。这只说明**几何傅里叶谱**；严格电磁散射还要乘局部入射场、伴随出射场及材料响应因子，不能等同于所有 $r_m$ 的误差严格相等。

![局部异常的理论傅里叶频谱](figures/2026-10-26_AH53_local_defect_sinc_spectrum.svg)

## 2. 为什么会在位移扫描中表现为周期振荡？

正常位移相位：

$$
r_m^\mathrm{ideal}(d)=A_m e^{i\phi_m-imGd}.
$$

如果数值模型额外产生**固定不变**的伪散射场 $B_me^{i\psi_m}$，则：

$$
r_m^\mathrm{num}(d)=A_me^{i(\phi_m-mGd)}+B_me^{i\psi_m}.
$$

$$
\boxed{|r_m^\mathrm{num}(d)|^2=A_m^2+B_m^2+2A_mB_m\cos(\phi_m-mGd-\psi_m).}
$$

当 $B_m\ll A_m$ 时：

$$
|r_m^\mathrm{num}(d)|\simeq A_m+B_m\cos(\phi_m-mGd-\psi_m).
$$

所以振幅的绝对变化有可能由 $B_m$ 决定，近似与原有 $A_m$ 大小无关。但固定伪缺陷干涉的理论位移周期为 $T_m=P/|m|$：第1阶16 μm、第5阶3.2 μm、第8阶2 μm。**如果实际振荡周期接近25 nm，就不能只归因于一个强度和位置都不变的接缝缺陷，还需要随几何-网格相对位置变化的误差机制。**

![固定缺陷和位移Mark相干干涉](figures/2026-10-26_AH53_stationary_defect_interference.svg)

## 3. 7.9 nm薄膜为什么与Conformal问题相关？

当Y网格为30 nm、薄膜厚7.9 nm，$t/\Delta y=0.263$，该膜层不能依赖普通Staircase被可靠解析。若一个单元同时遇到Si、7.9 nm薄膜与其他层，其多材料组合可能触发Conformal→Staircase回退。Mark沿X位移时，侧壁与层间交会处的网格填充状态会变化，进而产生随位移变化的附加散射。

必须区分：

- **真实介电常数不连续**：Si/膜层边界本来就是不连续的，这是物理现象；
- **错误或额外的介电常数不连续**：由于周期边界未延伸、重叠对象材料优先级错误、薄膜在离散单元内消失等造成的数值异常；
- **局部薄膜解析不足**：可带来固定系统误差，不一定单独造成X位移振荡；需与边缘/网格位置变化结合分析。

## 4. 三种机制的诊断区分

| 机制 | 可能的表现 | 关键反证/验证 |
|---|---|---|
| 周期边界材料未延续 | 延伸膜层或平移计算窗口后明显改变 | 对比边界两侧的实际材料和复系数 |
| 薄膜多材料单元回退 | 细化Y网格/换Conformal后改善 | 查看index/mesh与网格收敛 |
| 侧壁与X网格锁定 | 位移振荡尺度随dx改变 | 固定周期范围统一X网格，比较dx=10/5/2.5nm |
| 归一化/监视器处理 | 多级次同步变化，但总功率异常 | 分画Rtotal、G_m和复数级次输出 |

### 诊断特征：窄接缝缺陷的相位

如果局部错误恰好发生在$x_b=P/2$，其**几何傅里叶项**带有：

$$
e^{-imGx_b}=e^{-i m\pi}=(-1)^m.
$$

偶数与奇数级次的几何附加散射项可出现180°交替。但真实电磁场耦合与数据相位参考会修饰此模式，它不是必须满足的判据，也不是单靠振幅模值曲线就能判断的现象。

## 5. 上一轮建议的主要验证测试

1. **Index/mesh inspection**：在7.9 nm薄膜处查看实际Yee网格、边界两侧的材料分布，使用Nearest Mesh Cell与Conformal监视；注意Index Preview不完整反映共形系数。
2. **周期边界材料外延**：把确实横向均匀的所有平坦膜和衬底延伸过FDTD边界，必要时为真正跨边界的周期图案复制相邻周期；不改16 μm求解周期。
3. **计算窗口平移**：将FDTD和匹配的Plane Wave/Monitor窗口整体沿X移动1–2 μm，但不移动实际光栅；需确保新窗口对应相同周期性实体。
4. **复数残差**：
   $$D_m(d)=r_m^\mathrm{FDTD}(d)-r_m^\mathrm{FDTD}(0)e^{-imGd}.$$
   比较各级次 $|D_m|$ 与相位，而不只看 $\Delta|r_m|$。
5. **网格对照**：横向整周期统一Mesh Override，Y方向只在7.9 nm薄膜邻近区域进行2 nm量级加密；比较Conformal 0/1及Staircase时保证网格相同。
6. **薄膜去除对照**：只在工程副本移除7.9 nm薄膜，比较有无薄膜时的**平移对称性误差**，不要要求两种不同物理模型的原始反射系数一致。

### 已上传的实际LSF代码

- [01_extend_periodic_layers.lsf](scripts/2026-10-26_01_extend_periodic_layers.lsf)
- [02_uniform_x_and_thinfilm_y_mesh.lsf](scripts/2026-10-26_02_uniform_x_and_thinfilm_y_mesh.lsf)
- [03_index_and_mesh_inspection.lsf](scripts/2026-10-26_03_index_and_mesh_inspection.lsf)
- [04_shift_sweep_complex_orders.lsf](scripts/2026-10-26_04_shift_sweep_complex_orders.lsf)
- [05_shift_periodic_window.lsf](scripts/2026-10-26_05_shift_periodic_window.lsf)
- [06_remove_thinfilm_control.lsf](scripts/2026-10-26_06_remove_thinfilm_control.lsf)
- [07_mesh_refinement_comparison.lsf](scripts/2026-10-26_07_mesh_refinement_comparison.lsf)

**脚本适用限制**：以 Lumerical 2023 R2.1 公共LSF接口优先编写，尚无本机真实AH53工程与软件许可运行验证。执行前必须将对象名称映射到实际项目，并在副本运行。图示为理论模型，不是FDTD实测。完整推导和运行顺序见下一份问答文档。

## 最终判断

“边界条件 + 7.9 nm超薄膜 + Conformal Mesh多材料回退”是一条有官方依据的**待验证假设**。但仅凭多个衍射级次振幅的绝对变化相近，还不能证明错误发生在周期接缝；同样宽频的局部侧壁离散误差也可能造成类似结果。最有鉴别力的实验是：**延伸所有跨边界材料、改变窗口位置、统一横向网格并比对复数残差与实际Index**。