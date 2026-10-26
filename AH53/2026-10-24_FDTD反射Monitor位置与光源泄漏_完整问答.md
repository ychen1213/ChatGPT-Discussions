# AH53 FDTD 反射监视器、光源反向注入误差与参考仿真：官方依据、物理推导和验证流程

> **专题更新：2026-10-26**。原始 2026-10-24 问答完整保留于文末附录。本次重新核查了 Ansys Optics 官方文档，并就“空仿真 vs 将材料改为 Air”、光源上下两个监视器、复数级次提取与相位参考作补充。
>
> **适用模型**：AH53 单层 Alignment Mark；母周期 P=16 μm，入射 λ=643 nm；正入射平面波沿 −Y 传播；2D XY（Z 方向均匀）；光栅上方可存在平坦覆盖膜与衬底层。使用 FDTD 的 Periodic-X / PML-Y。公式除另注外采用时间因子 exp(−iωt)。本文区分“Ansys 官方明确说明”与“依据 Maxwell 方程推导 / 研究建议”。**文中示例脚本未在本次会话的 Lumerical 2023 R2.1 或 2025 R2 上实际运行。**
>
> **版权提示**：每篇官方文档仅摘录极短英文原句，附中文解释及原文链接；并非复制官方全文。建议点击链接阅读完整上下文及下载示例工程。

## 0. 先说最终结论

1. 对于向 −Y 单向注入的普通 Plane Wave，**R_back 置于光源上方（即光源传播方向的背后）**，理想情况下仅有向 +Y 的反射波，常规反射测量无需参考场扣除。但数值的向后注入误差、PML回波等可能污染该结果。**不是每个案例都必须扣除参考场**。
2. **R_front 位于光源与 AH53 之间**，它避开光源背侧的一部分注入误差，但那里有向 −Y 的入射场与向 +Y 的反射场。总电场不能直接当反射电场；净功率、复场分离是不同操作。
3. **均匀空气参考（Air-only）**用于检测不应存在的反向背景场，并校准注入平面波；**背景膜层/衬底参考（background-only）**用于研究相对背景的差分散射。后者的真实镜面反射不能称为“光源泄漏”。
4. “删除物体”与“把所有物体材料改为 Air”**在最终实际 ε、μ 分布、源所处介质及离散网格等条件都等效时**可以成为相同的空气参考；但只把Si光栅设为Air、覆盖膜和衬底保留，**绝不是 Air-only**。
5. 用复场做相干校正：E_corrected=E_sample−E_reference；不能直接用 |E_sample|²−|E_reference|² 代替 |E_sample−E_reference|²。另一方面，在已定义的净功率通量法中，两个案例的净功率之差可以用于估计反射功率，**这与复场相减不是同一件事**。
6. 对 AH53 的 r_ss^(m), r_pp^(m)，**源泄漏诊断、复场的入射归一化、功率系数归一化、相位参考面统一**是四个不同任务。即使漏场可以忽略，也不能省略后三者。

## 1. AH53的三个平面与符号

采用沿 Y 从上至下的空间顺序：

~~~text
              +Y ↑
      y_max : PML
      R_back：反射监视器（光源上方）
      Plane Wave source：方向 −Y
      R_front：反射监视器（光源下方）
      均匀上方介质：如 Air
      平坦覆盖膜
      非理想或规则的 AH53 Si 光栅
      衬底 / 下方连续材料
      y_min : PML
              −Y ↓
~~~

这里“above/below source”是**空间上下**；“behind/in front of the source”是**相对于光的注入方向**。在本例二者对应关系如上。不能把“R放在结构上方”与“R放在光源上方”当成同一回事。

令源向 −Y 入射，场可展开为：

$$
\mathbf E(x,y)=\mathbf E_{\mathrm{inc}}^{(-)}(x,y)+
\mathbf E_{\mathrm{refl}}^{(+)}(x,y).
$$

在源以下、结构以上的均匀介质区域，两个方向一般共存；在源以上，**理想单向注入**时没有继续向上走的入射波，因此只剩反射场。前提是 source 注入方式、监视器坐标及边界条件没有制造额外的向上场。

## 2. Ansys 官方究竟说了什么？逐条核对

### 2.1 《Tips for accurately measuring reflection in an FDTD simulation》

**原文**：[Tips for accurately measuring reflection in an FDTD simulation](https://optics.ansys.com/hc/en-us/articles/360034915753-Tips-for-accurately-measuring-reflection-in-an-FDTD-simulation)

官方短句摘录：**“the monitor is placed behind the source”**。

官方明确列出三种反射测量方法，主要是：

- **Monitor behind the source**：最直接、最常见。理想源情况下，注入与反射共存于源的前方，源的后方只应记录反射。这是我们原先将 R 放在 source 上方的依据。
- **Source injection errors**：源的离散注入可向本不应出现的方向产生数值散射。官方表示多数情况下很小；斜入射、mode source、broadband source 情况更值得注意。因此不能机械认定所有 behind-source monitor 的数据都准确。
- **Monitor in front of the source**：官方指出，当注入误差较大时，换成源前方的 monitor、依据净功率守恒估计反射率可能更准确。其示例通过与理论对比验证改善。
- **Reference normalization**：官方还指出源的注入功率归一化也可能受注入误差影响；此时可进行**没有反射结构**的参考运行，用源前方监视器测得的实际向前功率来重新归一化。
- **Line monitor interference**：还可利用入射/反射波的干涉驻波拟合反射率，但官方不作为一般推荐；只有单模、采样充分等限制，且不能直接获得我们需要的各阶复Jones系数。

**关键区分**：官方“监视器前移 + 1减净透射”主要针对**总反射功率**，**没有声称这一步自动得到了所有阶的复振幅和相位**。

### 2.2 《Optical Defect Metrology (S-Matrix)》

**原文**：[Optical Defect Metrology (S-Matrix)](https://optics.ansys.com/hc/en-us/articles/360041768554-Optical-Defect-Metrology-S-Matrix)

官方短句摘录：**“ideally below the source to minimize the effect of source injection errors”**。

在 **Important model settings → Monitor** 和 **Appendix → S parameter extraction** 中，官方明确把接收反射级次的监视器放在**结构上方、光源下方**，原因是希望降低源注入误差。这里特别提出：监视器处于 source 与 structure 之间时，要注意设置衍射投影的**传播方向**。

该案例通过 **gratingpolar** 分解 s/p 对应的角向复场，再进行：

1. 根据反射功率与源功率的关系补全**绝对幅值归一化**；
2. 对出射远场和入射平面波执行**相位参考点校正**，案例使用全局 (0,0,0)。

因此，不能把 gratingpolar 返回的矩阵直接视为已经按我们指定参考面归一化的 r_ss、r_pp。

**需要进一步说明的数学限制**：**方向参数指定的是投影半球/传播方向**，而在同一均匀平面上，仅有一个复电场 E(x) 的傅里叶系数，通常不能唯一拆分方向相反但横向波矢相同的两束波。对于混合场，严格的模态分离需要结合 E/H、两平面数据或可信的入射复场参考。官方范例的具体脚本、参考方向和相位校正应整体复现后再作精度判断，不宜只复制 gratingpolar() 一行。

### 2.3 《transmission》与《sourcepower》

**原文**：

- [transmission - Script command](https://optics.ansys.com/hc/en-us/articles/360034405354-transmission-Script-command)
- [sourcepower - Script command](https://optics.ansys.com/hc/en-us/articles/360034925313-sourcepower-Script-command)

transmission 官方短句摘录：**“Negative values mean the power is flowing in the negative direction.”**

官方定义 transmission() 返回穿过监视器表面的**净Poynting通量/源功率**，不是“向上反射波复振幅”的专用函数。对 2D XY 且沿 −Y 入射的水平 y-normal monitor，监视器正法向一般沿 +Y；因此向下入射贡献为负，向上反射贡献为正。

sourcepower() 计算源注入的功率谱，**不是复入射场的相位与振幅本身**。光学功率归一化与Jones复幅度归一化不能互相替代。

### 2.4 《grating》、《gratingpolar》、《gratingvector》

**原文**：

- [grating](https://optics.ansys.com/hc/en-us/articles/360034927213-grating-Script-command)
- [gratingpolar](https://optics.ansys.com/hc/en-us/articles/360034407034-gratingpolar-Script-command)
- [gratingvector](https://optics.ansys.com/hc/en-us/articles/360034407054-gratingvector-Script-command)
- [Grating projections in FDTD overview](https://optics.ansys.com/hc/en-us/articles/360034394354-Grating-projections-in-FDTD-overview)

**grating** 的输出是各个传播级次占所选方向功率的比例，所有级次之和归一化为1；要得到相对于注入源的功率比例，需要结合相应 monitor 的功率归一化量。

**gratingpolar / gratingvector** 输出的是具有相位信息、但按所有级次归一化的矢量分解结果，投影参考与直接在指定几何平面上测量的电场不同。官方文档还给出 direction=+1 或 −1 的可选参数，应该根据本例向上 +Y 的反射方向显式选择，不宜让默认“最大功率流”在混合场中决定方向。

此处原文档需要明确加强：**不能用 gratingvector 的某个复数分量，未经功率/参考面处理，就命名为电场定义下的 r_ss^(m) 或 r_pp^(m)。**

### 2.5 《TFSF tips》不能与普通Plane Wave混淆

**原文**：[Tips and best practices when using the FDTD TFSF source](https://optics.ansys.com/hc/en-us/articles/360034382934-Tips-and-best-practices-when-using-the-FDTD-TFSF-source)

官方对 TFSF 描述了在源盒边界进行**已知入射场扣除**的机制，盒外是 scattered-field 区域。但是：

- 这是一种**特定的TFSF光源实现**，不是“普通Plane Wave源背侧天然等于完美散射场区”的证明。
- 官方对于周期光栅一般推荐普通Plane Wave；周期光栅搭配TFSF时，参考角落穿过不同的材料会改变哪些背景场被扣除。不能随意把TFSF思路移植到本例。

结论：AH53的常规周期光栅先用Plane Wave加监视器/参考运行即可；不要为解决微弱泄漏就不经验证改成TFSF。

## 3. 为什么数值上会出现“向上泄漏”？

在连续Maxwell理论中，均匀介质内的一束理想单向平面波只向 −Y 传播。FDTD则在有限网格、有限时间步长及源注入平面上施加离散激励。离散传播算子与注入的理想连续场之间存在不完全匹配，可能激发一个很小的反向场。

在 R_back 监视器处可写成：

$$
\mathbf E_{\rm back}^{\rm meas}
=
\mathbf E_{\rm refl}
+
\mathbf E_{\rm inj,error}
+
\mathbf E_{\rm other,error}.
$$

第三项可能包含上/下PML反射、边界不匹配、源和监视器位置相关的数值杂散，不能把空参考测到的全部向上场都无条件归因于source injection error。

例如真实某级次反射场振幅为0.10，而误差场振幅0.01且同相：

$$
|E_{\rm true}|^2=0.0100,\qquad
|E_{\rm measured}|^2=|0.10+0.01|^2=0.0121.
$$

相对功率误差为21%，即从1.00%变为1.21%（**绝对增加0.21个百分点**）。这说明误差场功率虽小，仍能通过相干干涉影响弱衍射级次。官方反射测量文章给出了对应的数字例子；以上的绝对/相对误差表述按数值重新核算。

一般地，若某阶真实复幅度为 a，误差为 b，定义 η=|b|/|a|，则有保守上界：

$$
\frac{\big||a+b|^2-|a|^2\big|}{|a|^2}\le 2\eta+\eta^2.
$$

当 η<1，单纯复数扰动引起的最大相位偏差不超过 arcsin(η)。例如 η=0.01 时，理论上功率相对偏差不超过约2.01%、相位偏差不超过约0.573°。**这些是由幅度比推得的误差界限，而不是Lumerical自动保证的精度**。

尤其对于 AH53 的 r^(±1)、r^(±5)：不能仅凭空参考总反射功率 <10^−4 就认为所有弱级次的相位可靠，必须比较每个关心通道的复误差幅度。

## 4. 两个监视器各自测到了什么？

### 4.1 R_back：源上方

理想情形：

$$
\mathbf E_{\rm back}=\mathbf E_{\rm refl}.
$$

数值情形：

$$
\mathbf E_{\rm back}=\mathbf E_{\rm refl}+\boldsymbol\epsilon_{\rm back}.
$$

优势：反射场占主导，可用 transmission(R_back) 做总功率诊断，用 grating 函数分析传播级次（确认所选向上方向和监视器介质）。限制：小的背景误差可能影响弱通道与相位。监视器需置于源与上方PML之间的均匀介质区，与source/PML均留出合理距离，检查位置收敛。

### 4.2 R_front：源下方、结构上方

$$
\mathbf E_{\rm front}=\mathbf E_{\rm inc}^{(-)}+\mathbf E_{\rm refl}^{(+)}.
$$

对应时间平均Poynting通量：

$$
P_{\rm net}=P_{\rm refl}^{(+)}-P_{\rm inc}^{(-)}
$$

（此式采用监视器法向 +Y，且要求完整周期面、均匀介质、正确模态通量处理。）

若归一化入射功率恰好是1，且结构以上没有其他损耗，则：

$$
T_{\rm front}=R-1,\qquad R=1+T_{\rm front}.
$$

若把监视器功率定义成向下为正，则是 $T_{\downarrow}=1-R$，进而 $R=1-T_{\downarrow}$。**这就是官方“1−transmission”写法与本例 transmission() 可能为负值之间的符号差异。**

只用 abs(transmission(R_front)) 会近似得到 1−R，**不是R**。如果吸收发生在R_front下方的Mark内部，R_front处的净通量依旧是入射减反射，因此上式不要求样品无吸收；但必须校准入射功率、避免测量面内其他源/损耗、保证监视器跨越完整横向区域。

使用真正的空气参考测量该处的负向注入通量 $T_{\rm front,air}$，可以用

$$
R_{\rm flux}\approx T_{\rm front,sample}-T_{\rm front,air}
$$

估计归一化总反射功率（法向 +Y、源和数值设置不变、两次注入一致时）。**这里减的是净通量基线，用于功率诊断；这并不恢复任何衍射级次的复反射相位。**

### 4.3 更严格的前后向分离：需要E和H

在结构上方、source下方、均匀且各向同性的介质平面，针对X周期可先做傅里叶分解：

$$
\widehat F_m(y)=\frac1P\int_0^P F(x,y)\exp(-imGx)\,dx,
\quad G=2\pi/P.
$$

$$
k_{y,m}=\sqrt{(nk_0)^2-(mG)^2},\qquad k_0=2\pi/\lambda.
$$

以下考虑可传播级次（$k_{y,m}>0$），反射向 +Y。若入射/反射介质无磁响应，定义 $Y_{s,m}=k_{y,m}/(\omega\mu)$：

**s偏振（E_z, H_x）**：

$$
E^{(+)}_{z,m}=
\frac12\left(\widehat E_{z,m}+
\frac{\widehat H_{x,m}}{Y_{s,m}}\right),\qquad
E^{(-)}_{z,m}=
\frac12\left(\widehat E_{z,m}-
\frac{\widehat H_{x,m}}{Y_{s,m}}\right).
$$

其中 (+) 为向 +Y 反射，(−) 为向 −Y 入射。这个表达式可由频域 Maxwell 关系 $H_x=(k_y/\omega\mu)E_z$ 推出。

**p偏振（E_x, H_z）**：令 $Y_{p,m}=\omega\epsilon/k_{y,m}$，则

$$
E^{(+)}_{x,m}=
\frac12\left(\widehat E_{x,m}-
\frac{\widehat H_{z,m}}{Y_{p,m}}\right),\qquad
E^{(-)}_{x,m}=
\frac12\left(\widehat E_{x,m}+
\frac{\widehat H_{z,m}}{Y_{p,m}}\right).
$$

这些是**切向电场幅值**；换成p偏振的完整Jones基矢幅值时，仍需考虑出射角的投影和符号定义。对倏逝级次、吸收介质、3D锥形入射等，导纳与模式规范需要相应扩展。

**重要：**上述 E/H 分解是根据麦克斯韦方程的理论方案，并非 Ansys 官方上述 S-Matrix 示例完整给出的逐行实现。FDTD 的 E/H 分量处于交错Yee位置；使用它们时应先保证相同参考面、插值/相位约定、时谐约定，否则会引入额外误差。

对于正入射的单一理想平面波，前向入射只有母周期 **m=0**。因此在均匀区：

- m≠0 的反射侧级次可以更方便地通过横向傅里叶分解诊断，因为理想入射本来没有这些级次；
- **m=0 是特殊情况**，存在入射与镜面反射的混合，更需要参考复场或E/H方向分离；
- 即使 m≠0 未受到入射 m=0 直接污染，也要检查数值网格破坏周期性、反向注入与散射级次之间的耦合。

## 5. “空仿真”到底是什么？设置材料为Air能替代吗？

**先确定要得到哪一种参考**：空气参考（消除纯注入/边界背景）、基底参考（差分Mark散射）、还是入射幅值参考（归一化）。这三者可能需要不同模型。

### 5.1 参考A：均匀介质 Air-only（优先用于本问题）

物理条件：在有效FDTD域里，**不应有任何能够反射或衍射的实际物体/界面**。如果上方光源位于空气（n=1），则整个物理域为Air、PML处的背景材料一致。

以下两种构造在**物理材料分布完全一致**时等效：

- **A1：禁用/删除Mark、平坦膜、衬底等所有几何对象**，保留FDTD、source、monitor和需要的固定网格；
- **A2：保留这些几何对象，但将它们及所有会影响介电常数的层都改成真实的 n=1,k=0 Air**，并确保不存在其他未改动材料或重叠优先级导致的介质分区。

电磁意义上只要两者最终 $n(x,y)=1$ 且源、边界与求解网格等效，理想解相同。**但是数值上不应先断言两个文件得到逐位相同的泄漏场**，因为CAD实体、材料优先级、自动网格与共形边界可能产生离散差异。为检验基线稳定性，最好同时做A1与A2，并比较 index、mesh、source、monitor结果。

**推荐执行方式**：以现有AH53工程复制出的A1为标准“空结构”。保留source、monitor、FDTD区域、边界与独立指定的均匀mesh override；确保不存在所有Si、氧化物、基底等。其余数值设置不变。

注意：如果源实际埋在 $n\ne1$ 的均匀介质，物理上正确的空参考应采用源所在**相同均匀介质**，而不是机械地把整个域都变为Air，否则源注入条件变了。

### 5.2 参考B：background-only（保留平坦膜与衬底）

从物理上保留完整背景层叠、只去掉有周期图案的AH53：

$$
\epsilon_{\rm sample}(x,y)=\epsilon_{\rm background}(y)+\Delta\epsilon_{\rm mark}(x,y),
\qquad
\epsilon_{\rm ref,B}(x,y)=\epsilon_{\rm background}(y).
$$

这里的背景介质自身存在薄膜/衬底界面，通常有真实镜面反射：

$$
E_{\rm back,B}\approx E_{\rm Fresnel/film}+E_{\rm numerical}.
$$

**这不是测量“源泄漏”的纯净参考。** 如果相减：

$$
E_{\rm sample}-E_{\rm background},
$$

得到的是**相对于背景的差分散射**。它适合缺陷检测、差分反射问题；但如果目标是完整 AH53 的 $r_{ss}^{(0)}$，把背景的零阶反射直接扣除就是改变了被定义的物理量。

### 5.3 “只将Si Mark材料设为Air”的特殊陷阱

对于 AH53 的填充膜/平坦覆盖层，光栅沟槽内部材料、覆盖膜顶部界面和衬底几何是相互关联的。**只把Si ridge设为Air** 可能仍保留氧化物膜与Si衬底的真实反射，甚至由于对象重叠/材料优先级，改变原本想保留的部分膜层。它既不等于A，也未必等于正确的B。

在做参考前必须先决定：背景参考是“平坦膜覆盖连续Si衬底”还是“平坦膜覆盖整个参考Air区域”等具体层叠。用index monitor确认最终介电常数分布，不能只凭CAD对象材料名判断。

| 参考构造 | 保留Mark图案？ | 保留真实膜/衬底？ | 在R_back中应有的物理反射 | 主要用途 |
|---|---|---|---|---|
| A1 删除全部散射结构 | 否 | 否 | 理想零 | 检查背向背景；入射参考 |
| A2 所有结构真正设为同一均匀介质 | 否 | 否 | 理想零 | 与A1互证 |
| B 只移除Mark，保留物理层叠 | 否 | 是 | 真实零阶反射 | 背景差分、膜层基线 |
| C 仅把ridge设Air | 不一定 | 通常是 | 真实反射，且材料分布需核对 | **不能自动当空参考** |
| S 完整AH53 | 是 | 是 | 真实各阶反射+数值背景 | 最终物理结果 |

## 6. 哪些场可以相减？如何判断参考场是否可信？

**对于R_back：**

$$
E^S_{\rm back}=E^S_{\rm refl}+\epsilon^S_{\rm back},
\quad
E^A_{\rm back}=0+\epsilon^A_{\rm back}.
$$

如果两次注入误差具有足够好的可重复性，才可以近似用：

$$
E^{S,\rm corrected}_{\rm refl}\approx
E^S_{\rm back}-E^A_{\rm back}.
$$

**对于R_front：**

$$
E^S_{\rm front}=E^S_{\rm inc}+E^S_{\rm refl},\quad
E^A_{\rm front}\approx E^A_{\rm inc}.
$$

当两次入射场一致、来源和网格配准时：

$$
E^S_{\rm front}-E^A_{\rm front}
\approx E^S_{\rm refl}.
$$

这正是为什么 **front monitor 的“减空气参考”通常是在减掉强入射波，而back monitor的“减空气参考”通常是在修正小的背向误差场**；两者虽然形式一样，目的不同。

需要匹配：频率/波长、源方向/极化/相位、源面和monitor坐标、X周期16 μm、横向采样、FDTD PML、材料背景、mesh与监视器的CW归一化和apodization。若存在E/H插值差异，应先配准到相同物理平面。

**减复场，不是减强度**：

$$
|E_S-E_A|^2=
|E_S|^2+|E_A|^2-2\mathrm{Re}(E_SE_A^*).
$$

如果源/网格变化使 $\epsilon^S_{\rm back}$ 与 $\epsilon^A_{\rm back}$ 不相等，空参考相减并不一定改善真实结果；有时会反而引入相位误差。特别是去掉结构以后自动网格变了，参考场无法被视为严格可重复的加性背景。

**两个实用对照**：

1. 同样的样品，比较R_back直接测量与R_front+Air复场扣除；二者经相位/幅值参考校正后应该收敛一致。
2. 分别做空参考A1和A2，检查它们的背向复场差值是否远小于真实AH53所关心阶次；如果差值本身很大，先修复网格/源/PML再考虑扣除。

## 7. 对于16 μm母周期，尤其要单独检查m=0和±1、±5

在理想均匀Air-only参考里，由于输入平面波正入射且横向均匀：

$$
\widehat E_{m\ne0}^{\rm air}=0
$$

（不计数值杂散）。因此参考中的**主要污染通道通常是m=0**，不是每个$m$都会有独立的“泄漏级次”。

重要后果：

- 观察 Air-only 的总R_back泄漏功率，可以快速检查光源/PML/网格是否干净。
- 对 m≠0，空参考几乎为零**不代表含结构时该阶的数值误差也为零**。后者还会受到边界阶梯化、材料离散、反射波与源耦合等影响。
- 对 m=0，必须认真处理入射复场、空场泄漏及可能的膜层真实镜面反射，三者定义不同。
- 对±1、±5的低功率弱通道，最好观察复场差、网格收敛、PML收敛及相位随Mark平移的理论斜率，而不是只看总功率。

建议输出两个诊断量：

$$
L_{\rm back}^{\rm air}=|\mathrm{transmission}(R_{\rm back,air})|,
$$

$$
\eta_m=\frac{|a_{m,\rm sample}-a_{m,\rm corrected}|}{|a_{m,\rm sample}|}
$$

其中第二式只有当相关复级次幅值足够大、分母不接近零时才有意义；将源注入/网格误差与参考误差混合时，它只能作为**校正前后差异**，不是已知的真实误差上界。

建议同时输出相位差：

$$
\delta\phi_m=
\arg\left(a_{m,\rm corrected}a_{m,\rm sample}^{*}\right).
$$

## 8. 可执行的对照实验与Lumerical脚本框架

### 8.1 设置四个文件而非只看一条曲线

- **A1_air_empty.fsp**：关闭所有引起介电差异的结构；源处介质为Air；保留FDTD/source/monitor/固定网格。
- **A2_all_air_objects.fsp**：保留几何但所有相应介质确实为n=1,k=0；验证是否等效A1。
- **B_background_stack.fsp**：保留实际平坦膜/衬底，只去掉周期图案；用于背景反射，不作为源泄漏场。
- **S_AH53.fsp**：完整实际AH53。

每个文件保留两个水平频域场监视器（2D中为线monitor），分别名为 R_back 和 R_front，并在必要时增加记录E/H、index与mesh的检查监视器。光源与monitor都使用相同的643 nm采样，所有坐标固定不随样品移动。

### 8.2 能直接在Analysis模式运行的功率诊断框架

下述代码假定这两个对象已创建并完成仿真，且二者都是法向+Y的 **y-normal** 监视器。**这里只输出净通量，不能当成Jones矩阵脚本。**

~~~lsf
# In Analysis mode, after each completed simulation
f = getdata("R_back","f");
fi = find(c/f*1e9,643);

Tb = transmission("R_back");
Tf = transmission("R_front");

?"lambda (nm) = " + num2str(c/f(fi)*1e9);
?"R_back net T (normal +Y) = " + num2str(Tb(fi));
?"R_front net T (normal +Y) = " + num2str(Tf(fi));

# A1-Air should give Tb ~= 0 and Tf ~= -1
# For sample S, R_back reflected net power ~= Tb
# At R_front, if injection power normalized to 1:
# R_total ~= 1 + Tf(fi)
# Prefer comparing to air-calibrated baseline:
# R_total ~= Tf_sample - Tf_air
# Save Tb, Tf, source/monitor positions per run.
~~~

注意：对于R_back的 air reference，**不要直接把 abs(transmission) 当作每阶误差的复振幅**；它是总净功率量。对于R_front，**不要使用原来常见的 abs(transmission("R")) 作为反射率**，该位置主要测得向下净功率。

对R_back的单独衍射分解（确认处于均匀空气、方向+Y）可另外检查：

~~~lsf
N = gratingn("R_back",fi);
G = grating("R_back",fi,1,+1);
V = gratingvector("R_back",fi,1,+1);
R_back_total = transmission("R_back");

# Only when R_back contains predominantly true upward reflected flux:
R_by_order = G * R_back_total(fi);

?N;
?R_by_order;
# V is normalized grating vector data, NOT raw r_ss/r_pp.
~~~

这段脚本主要用于现有AH53代码的自检。对Air-only，R_back_total接近零，此时归一化的G/V即使形式上有结果，也可能被极小数值噪声支配，**不应解释其相位**。

### 8.3 推荐运行与验收顺序

| 步骤 | 需要比较的量 | 正常预期 / 异常判断 |
|---|---|---|
| 1. A1 空空气 | R_back净通量；R_front净通量 | 约0；约−1（+Y法向） |
| 2. A2 全Air对象 | A2与A1复场及mesh/index | 在数值精度范围内接近 |
| 3. B仅背景膜层 | R_back镜面反射，是否只有m=0 | 零阶可能不小，不能当泄漏 |
| 4. S完整Mark | R_back各阶强度、相位 | 反映结构衍射，受源误差影响 |
| 5. S与A1复场差 | m=0、±1、±5及功率 | 比较是否需要实际扣除 |
| 6. R_back与R_front法复系数 | 同一参考面上逐阶比对 | 理论上应收敛趋同 |
| 7. 移动R_back/R_front位置 | 相位传播校正后复系数 | 应尽量不变 |
| 8. 网格/PML收敛 | 弱级次复系数变化 | 趋于稳定，而非由网格支配 |

对于真实AH53，建议先做两种入射偏振分别测试，并保存所有频域 E/H 数据、每个 case 的源/监视器坐标与仿真设置，而不仅是 transmission() 的标量结果。

## 9. 真正想提取r_ss/r_pp，还必须解决三件事

### 9.1 入射复振幅分母

定义：

$$
r_{\alpha\beta}^{(m)}=
\frac{b_{\alpha,m}^{(+)}(y_{\rm ref})}
{a_{\beta,0}^{(-)}(y_{\rm ref})},
\qquad \alpha,\beta\in\{s,p\}.
$$

分子是第m阶**真实向上反射**的归一化模式复幅度，分母是同一参考面上的**实际向下入射**模式复幅度。sourcepower() 仅提供功率信息，没有复数相位，不能独自完成这个除法。

### 9.2 参考面传播相位

若反射模式从参考面 $y_{\rm ref}$ 到监视器 $y_m$ 按 $\exp[i k_{y,m}(y_m-y_{\rm ref})]$ 传播，则：

$$
b_{\alpha,m}^{(+)}(y_{\rm ref})
=
b_{\alpha,m}^{(+)}(y_m)
\exp[-i k_{y,m}(y_m-y_{\rm ref})].
$$

入射波沿 −Y 传播，参考传播因子方向相反。若不同参数扫描中monitor或结构高度随意变化，未统一这一相位基准，可能把参考面变化误认为真实Mark散射相位。

**官方S-Matrix案例专门给出这一相位校正，而不是直接以gratingpolar的原始复数作为最终S参数。**

### 9.3 场归一化 ≠ 功率归一化

若入射、出射介质相同、均为无磁均匀介质，采用完整极化电场幅度定义时：

$$
R_m=\frac{\cos\theta_m}{\cos\theta_{\rm in}}|r_m|^2.
$$

对于不同出入射介质，还要加入相应波阻抗/导纳和折射率因子。对于来自 gratingvector() 的归一化复场，其模平方先表示**相对级次功率**，应按官方 grating/S-Matrix 约定处理，不能再次无条件套用cosθ因子。

对你的2D XY模型（条纹沿Z），正入射s偏振主要由E_z表示，p偏振由X/Y截面内的E表示；完整Jones提取要统一s/p基的符号，不能把不同出射角的Ex直接等同于完整p偏振场幅度。

## 10. 对旧文档需要保留和更正的地方

**旧结论保留**：光源上方Monitor理想情况下可直接测反射；source injection errors真实存在；不必规定所有case都必须空参考扣除；应对复场而非光功率进行相干扣除；背景膜层不是纯空气参考。

**新增约束 / 澄清**：

- 旧文档若将“源下方设置投影方向”理解为“直接从混合电场严格剥离上下两个模式”，应补充E/H或参考复场方案，并尤其检查m=0。
- 旧文档中写“R_leak=abs(transmission(R))”只适用于R位于source背侧并确认为反向背景诊断；不适用于源前混合场。
- “空仿真”必须具体写明 **全空气 / 源所在均匀介质**；“只把Si改为Air”并不充分。
- 若比较两次复场，需匹配物理网格、监视器坐标、频率、归一化和source配置；不能只因为文件名带ref就直接相减。
- 正确的样品完整反射与相对背景散射不是同一个量，尤其在m=0中区别非常大。
- 官方示例的 source-back/front 优劣是条件性的；本次没有在你的实际AH53工程中实测哪一位置更准确。

## 11. 官方来源索引（优先查阅顺序）

1. **核心**：[Tips for accurately measuring reflection in an FDTD simulation](https://optics.ansys.com/hc/en-us/articles/360034915753-Tips-for-accurately-measuring-reflection-in-an-FDTD-simulation) —— 光源上下两侧的Monitor、背向注入误差、参考功率归一化与驻波方法。
2. **核心**：[Optical Defect Metrology (S-Matrix)](https://optics.ansys.com/hc/en-us/articles/360041768554-Optical-Defect-Metrology-S-Matrix) —— 反射场Monitor推荐位置、分级次s/p、振幅及相位校正；附有可下载仿真文件/脚本。
3. [transmission - Script command](https://optics.ansys.com/hc/en-us/articles/360034405354-transmission-Script-command) —— 净Poynting通量、方向符号和源功率归一化。
4. [sourcepower - Script command](https://optics.ansys.com/hc/en-us/articles/360034925313-sourcepower-Script-command) —— 注入源功率定义与特殊配置警告。
5. [gratingpolar - Script command](https://optics.ansys.com/hc/en-us/articles/360034407034-gratingpolar-Script-command) —— 相对s/p级次复场、归一化、direction参数。
6. [gratingvector - Script command](https://optics.ansys.com/hc/en-us/articles/360034407054-gratingvector-Script-command) —— 相对笛卡尔复场及归一化。
7. [grating - Script command](https://optics.ansys.com/hc/en-us/articles/360034927213-grating-Script-command) —— 级次功率比例而非原始电场反射系数。
8. [Grating projections in FDTD overview](https://optics.ansys.com/hc/en-us/articles/360034394354-Grating-projections-in-FDTD-overview) —— 级次方向、功率与相位的作用范围。
9. [Tips and best practices when using the FDTD TFSF source](https://optics.ansys.com/hc/en-us/articles/360034382934-Tips-and-best-practices-when-using-the-FDTD-TFSF-source) —— TFSF的入射场扣除与周期结构注意事项；**不可和普通Plane Wave等同**。
10. [Refractive index monitor - Simulation object](https://optics.ansys.com/hc/en-us/articles/360034383134-Refractive-index-monitor-Simulation-object) —— 检查Air-only与background-only最终的实际介电常数/离散网格。
11. [Plasmonics simulation methodology](https://optics.ansys.com/hc/en-us/articles/360041688154-Plasmonics-simulation-methodology) —— 周期模型宜使用Plane Wave，周期边界会复制有限横向光源。

---

## 附录：2026-10-24 原始完整问答（历史记录，不替代上方更新版）

以下为既有记录的原文存档。遇到定义不清、符号或适用条件与本次核查冲突之处，请以上方2026-10-26专题更新为准。

# FDTD 反射监视器位置、光源泄漏与参考仿真

## 用户提问

**其次，要分清入射场和反射场。** 按上图将 R monitor 放在向下入射的单向平面波光源上方，通常可以直接记录向上传播的反射场。如果将监视器放在光源和光栅之间，记录的是入射场与反射场的叠加，需要利用参考仿真分离入射分量。

关于之前你说的这部分的内容 我看有ai说即使把monitor放在光源上方也需要利用参考仿真分离入射分量 是这样吗 他说入射光会有泄露 你再搜一搜 看看实际上是怎么样的

## ChatGPT 回答

我查了 Ansys Lumerical 的官方技术文档。结论是：

**另一位 AI 提醒的“入射光泄漏”现象确实存在，但“即使把 R monitor 放在光源上方，也必须做参考仿真减去入射场”这个说法过于绝对。**

官方的结论实际上是：

1. **理想情况下**，R monitor 放在向下入射光源的上方，只记录返回的反射场，不需要减去入射场。
2. **实际 FDTD 中**，光源注入可能产生少量向后的非物理散射（source injection error），从而污染反射场。
3. 大多数正常设置下，这个误差很小，可以直接测量；但如果要提取精确的复反射矩阵，尤其是弱衍射级次的相位，就值得使用参考仿真检查和校正。

Ansys 官方文章 [Tips for accurately measuring reflection in an FDTD simulation](https://optics.ansys.com/hc/en-us/articles/360034915753-Tips-for-accurately-measuring-reflection-in-an-FDTD-simulation) 明确指出：把监视器放在光源注入平面后方，是最简单、最常用的反射测量方法；通常只有反射场到达该位置。但它也明确承认，光源注入误差可能向后产生额外电磁场，在某些情况下不可忽略。

## 一、先分清两个不同的“入射场”

以你的 AH53 模型为例，光沿 −Y 传播：

在光源下方、光栅上方的 R₂ 位置，电场通常为：

\[
E_{\mathrm{R2}}=E_{\mathrm{incident}}+E_{\mathrm{reflected}}.
\]

而在光源上方的 R 位置，理想情况下：

\[
\boxed{E_{\mathrm R}=E_{\mathrm{reflected}}}
\]

但数值计算中可能变成：

\[
\boxed{E_{\mathrm R}^{\mathrm{measured}}=E_{\mathrm{reflected}}+E_{\mathrm{leak}}}
\]

这里的 \(E_{\mathrm{leak}}\) 不是正常入射光穿过光源平面后又返回，而是光源注入时可能产生的**数值误差场**，也可能包含其他非物理反射贡献。

官方关于有限平面波源的说明还给了一个很直观的例子：正常周期边界、正确延伸的平面波源，在无结构情况下，光源后方记录到的场应为零；有散射结构时，后方才出现反射场。

## 二、为什么数值上的“泄漏”会影响反射测量？

Ansys 的官方文档专门讨论了 **Source Injection Errors（光源注入误差）**。

FDTD 在离散网格上注入电磁场，理想的单向平面波注入无法保证在所有条件下数值误差严格为零。因此，光源平面可能产生少量反向散射。

官方指出，这种误差更容易在以下条件下变得明显：斜入射、宽带光源以及模式光源。

它为什么有时影响很大？因为电场是相干叠加的：

\[
E_{\mathrm{measured}}=E_{\mathrm{reflected}}+E_{\mathrm{leak}}.
\]

测量到的功率为：

\[
|E_{\mathrm{measured}}|^2=|E_{\mathrm{reflected}}|^2+|E_{\mathrm{leak}}|^2+2\operatorname{Re}(E_{\mathrm{reflected}}E_{\mathrm{leak}}^*).
\]

最后一项是干涉项。即使泄漏功率很小，也可能显著改变最终结果。

例如，真实反射振幅为0.10、泄漏振幅为0.01且两者同相：

\[
R_{\mathrm{true}}=0.10^2=0.0100,\qquad
R_{\mathrm{measured}}=(0.10+0.01)^2=0.0121.
\]

真实反射率为1%，测得却是1.21%，**相对误差达到21%**。这正是Ansys官方文档提供的示例。

所以另一位AI提出的担忧是有物理和数值依据的。

## 三、Ansys 的 S-Matrix 官方案例，反而推荐把监视器放在光源下方

这是我检索中发现的一个特别重要的信息。

在官方 [Optical Defect Metrology (S-Matrix)](https://optics.ansys.com/hc/en-us/articles/360041768554-Optical-Defect-Metrology-S-Matrix) 示例中，Ansys明确建议：

> 为减小光源注入误差，反射监视器最好位于结构上方、光源下方。

即放在 **Source与Mark之间**，再通过指定功率传播方向等方式提取向上传播的反射光，而不是简单把混合场直接当成反射场。

这看起来与你之前的理解相反，但并不矛盾。

| 监视器位置 | 优势 | 需要注意 |
|---|---|---|
| 光源上方 | 理想情况下只包含反射场，处理简单 | 可能受到光源注入误差污染 |
| 光源下方、光栅上方 | 可以避开部分源注入误差 | 含入射与反射场，必须正确分离传播方向 |

所以两种方法都有官方依据。**如果追求精确的复S矩阵，不能只根据监视器的位置就断定哪种更准确。**

需要额外说明，官方的“1减去透射”方法主要用于反射功率分析，它不能直接恢复每阶复振幅的相位。你的 SMASH 项目仍然需要复场分解和统一参考面。

## 四、对你的 AH53，怎么判断究竟要不要做参考仿真？

我建议做一次非常简单的对照实验。

### 实验 A：空结构参考仿真

保留原来AH53模型的光源、监视器、FDTD区域、网格、边界条件和波长643 nm。

将结构替换为均匀空气区域（不保留会产生真实反射的衬底或膜层），运行一次。

记录光源上方 R monitor 的数据：

\`\`\`javascript
R_leak = abs(transmission("R"));
?R_leak;
\`\`\`

如果是理想的单向光源，这个位置应当没有反射功率，即：

\[
R_{\mathrm{leak}}=0.
\]

实际得到一个很小的非零值，则说明存在数值背景场。这可以来自光源注入误差，也可能涉及计算边界的非物理反射。

不过，**仅检查总泄漏功率还不够**。你真正关心的是各个衍射级次，尤其是弱级次；一个总功率很小的误差，仍可能相对于某个弱级次很大。

### 实验 B：恢复 AH53，并比较原始和校正后的复场

在完全相同的监视器位置和频率下，保存参考仿真的复场：

\[
E_{\mathrm R}^{\mathrm{ref}}(x).
\]

再恢复真实AH53，得到：

\[
E_{\mathrm R}^{\mathrm{sample}}(x).
\]

如果参考场主要代表可以重复的注入误差，则可尝试：

\[
\boxed{
E_{\mathrm R}^{\mathrm{corrected}}(x)
=
E_{\mathrm R}^{\mathrm{sample}}(x)
-
E_{\mathrm R}^{\mathrm{ref}}(x)
}
\]

然后对校正后的复场进行衍射级次分解。

这里有三个要求：

**必须减复电场，不是减功率。** 不能通过 \(R_{\mathrm{sample}}-R_{\mathrm{ref}}\) 消除相干干涉项。

**参考仿真应尽可能保留一致的数值设置。** 特别是光源、计算网格、监视器采样坐标、频率和时间傅里叶处理。若两次监视器的网格不同，不能直接逐元素相减，应先配准或重新采样。

**参考场校正不是万能的。** 例如真实Mark反射光被上方PML再次反射所造成的误差，可能只存在于样品仿真中，空结构参考无法消除。必须通过PML、网格和监视器位置收敛性测试检查。

另外，如果参考模型保留裸衬底，那么减去的是裸衬底的相干反射贡献；你得到的将是**相对于裸衬底的差分散射场**，而不是完整Mark的总反射场。你的 Jones 矩阵需要包含完整Mark反射时，不能不加区分地减去裸衬底响应。

## 五、对于你的复Jones矩阵，我建议的最终方案

你需要的不只是 \(R_m\)，而是：

\[
\mathbf r^{(m)}=
\begin{pmatrix}
r_{ss}^{(m)}&r_{sp}^{(m)}\\
r_{ps}^{(m)}&r_{pp}^{(m)}
\end{pmatrix}.
\]

我建议未来的 FDTD 自动化程序采用下面的方式。

| 环节 | 处理方法 |
|---|---|
| 入射光参考 | 单独参考仿真，提取真实入射复振幅 |
| 光源上方 R monitor | 记录主要反射数据 |
| 空结构反向泄漏 | 单独记录，判断是否需要复场校正 |
| 光源与结构之间的监视器 | 用于交叉验证，必要时做前后向模式分解 |
| 各阶复场 | 提取s/p分量，得到复反射系数 |
| 相位参考 | 统一到指定Mark参考面 |
| 数值验证 | 检查复系数、功率和相位的收敛性 |

如果测试发现空结构的反向泄漏相对于所有关注级次都足够小，完全可以直接使用光源上方监视器的数据。**没有必要为了形式上的严格，每一个case都做一次多余的减法。**

但入射场的复数归一化和相位参考校正，仍是另一件事：它们并不会因为反向泄漏很小就自动完成。Ansys的S-Matrix官方流程也将源功率归一化和入射、出射相位校正列为独立步骤。

---

**最终结论：我之前说“R放在光源上方，可以直接得到反射场”，作为常规FDTD布置是正确的，但没有充分强调数值光源注入误差。另一位AI说“可能发生泄漏”也是正确的；它若进一步断言“所有这种布置都必须用参考仿真减去入射场”，则不符合Ansys官方给出的条件性结论。**

针对你目前的643 nm、正入射、二维周期性AH53模型，正常单向平面波注入的反向误差通常应当较小，但必须通过空结构测试确认。

**我建议你优先做一次空结构反向泄漏测试，特别记录0、±1、±5阶的背景复场。** 它不仅能验证监视器位置，还能成为以后整个 Meep/Lumerical 复Jones矩阵提取模块的固定数值验收项目。