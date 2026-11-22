# 随机 Mark 边缘参数化与电磁仿真：文献调研全文（文本备份）

> 2026-11-23 · 22页 PDF 的可检索文本转存。排版、图形和公式位置可能与原 PDF 不同，31 个独立公式的原生 LaTeX 源码见 `roughness_equations_LaTeX.tex`。此文件不是 LaTeX 排版 PDF 的替代品，也不包含插图。



---

### PDF 第 1 页


RESEARCH & IMPLEMENTATION · 2026-11-22




随机 Mark 边缘
参数化与电磁仿真
面向 Alignment / Overlay 的文献调研与实施方案




   推荐主线
   中心与宽度分解 → PSD 约束的随机边缘 → 相关的三维侧壁 → 少量严格计算 → 按最终 KPI 决定保留尺
   度。


你的“各种边缘弯曲叠加”思路是可行的。需要补充的是统计约束、相关性、三维几何和输出误差判据。


  关键问题                   本次结论

  如何参数化任意边               单值、无拓扑变化的边缘可以用 Fourier / B 样条等表示；随机总体用 PSD、分布和互相关
  缘？                     生成，实测单个 Mark 还必须保留相位。


  FDTD / RCWA 如何         沿条纹的变化通常要求严格 3D 求解。先对齐相同随机超胞，再用少量有限 Mark / 有限光
  计算？                    斑验证。


  细小变化能否忽略？              可以，但必须以复场、干涉信号和位置 KPI 的误差验收；小于波长、NA 外或小于网格都不
                         是独立证明。


  怎样控制成本？                低维统计参数扫描，频带灵敏度筛选，经过严格算例验证的微扰核或等效界面。



项目背景：既有复 Jones 矩阵 → 光路 / 扫描曲线 → KPI 链路。
示例采用 AH53 的既有 643 nm、NA=0.6、38 μm 光斑设定；光斑直径定义仍待标定。
本报告是文献与方法方案；插图为合成几何，未运行新的 FDTD / RCWA 粗糙度求解。




MARK ROUGHNESS | Research & implementation                              01 / 22


---

### PDF 第 2 页


01 · RECOMMENDATION



方案的边界与决策逻辑
本课题关注的输出是对准 / 叠加测量信号及其偏差。对形貌的简化应服务于这些输出，而不以“几何看起来足
够像”作为终点。以下方案是结合文献提出的工程设计，具体数值起点均不构成精度保证。

先区分两个任务

  任务                    需要保存的对象                    适合的方法

  重现某一块实测               边缘实际坐标、相位、缺口位置、层间配准及       拟合实测轮廓；PSD 用于检查和压缩，而
  Mark                  测量不确定性                     不替代轮廓


  研究一种工艺的随              统计模型及 seed；每条边缘 / 每层的相关结   随机生成多个实现，分别计算完整曲线和
  机总体                   构                          KPI，再统计



分三种方式处理短尺度
 • 直接省略：保留低频不变，删高频以后，目标 KPI 的成对误差低于预算。

 • 等效处理：短尺度仍改变主阶振幅 / 相位，但可由校准后的等效界面或二阶响应重现。

 • 显式保留：强局部场、尖角、窄缝、共振、拓扑变化，或简化后误差超限。

本报告使用的证据层级
Mack 的工作直接支持随机轮廓和 PSD 处理；Bergner、Kato、Heusinger 与 Fernández Herrero 的工作
直接涉及粗糙光栅散射。部分研究使用 EUV / X 射线或二值标量光学，能说明机制，但其数值阈值不能迁移到
643 nm 的 AH53。[1–8]


   不把“文献中某个样本可近似”写成“本项目已通过验证”。最终结论应绑定材料、波长、偏振、几何、
   光斑、NA、求解器精度与 KPI 定义。


保留 X=跨条纹、Y=厚度 / 入射、Z=沿条纹的约定；为避免此前“y 方向不均匀”的命名歧义，正文统一使用
(u,v,w)=(X,Z,Y)。




MARK ROUGHNESS | Research & implementation                           02 / 22


---

### PDF 第 3 页


02 · LITERATURE



最值得精读的研究
  文献                          直接回答什么                  迁移到本课题的限制

  Mack, 2013 [1]              如何按指定统计量生成随机边缘；有限长      需要检查实际生成谱，不能只相信输入
                              度和采样会导致方差偏差             的 σ、ξ


  Bergner et al., 2010 [3]    随机粗糙边缘的双周期 RCWA；各向异性    633 nm / Si 很相关，但几何不同；
                              等效界面                    σ≪ξ≪λ 是其受限条件


  Kato et al., 2012 [4]       正弦边缘的出平面散射及 3D FEM 验证   解析部分包含标量 / Fraunhofer 近似


  Heusinger et al., 2018      小扰动时以 PSD × 理想光栅响应预测二   不是任意强扰动的精确叠加法
  [5]                         维漫散射


  Fernández Herrero et        随机 LER/LWR、线间相关和高度共同影   EUV 样品说明建模要素，不提供本项
  al., 2022 [6]               响散射                     目通用截止


  van Kessel et al., 2020     顶视 SEM 边缘与三维侧壁粗糙度的差异    顶视轮廓不能唯一决定高度方向的形貌
  [9]



这些研究对“波形叠加”给出的完整回答
几何轮廓可以用基函数叠加；Kato 的正弦案例很适合作为起步校验。但 2022 年的随机光栅研究明确指出，随
机样品的漫散射不能普遍由不同幅值的周期二值光栅结果相加来解释，必须考虑线间相关与结构高度。[4,6]

应把“生成总几何后严格求解”与“经过验证的一阶响应叠加”做成两个明确路径。前者保留完整耦合，后者
用于高效扫描。

值得保留的近似，但不作为默认真值
仅依赖 RMS 的 Debye–Waller 衰减、独立二维截面平均、简单等效介质都有文献使用。随机分布、相关长
度、偏振、几何或共振改变以后，需要重新验证；不能仅将各阶强度统一乘一个经验因子。[3,7,8]




MARK ROUGHNESS | Research & implementation                                     03 / 22


---

### PDF 第 4 页


03 · GEOMETRY



沿用中心 / 宽度分解，避免重复计数
令 j 表示第 j 条线，v 为沿条纹坐标，w 为高度。任意仍保持单值侧壁的线形可写成：

                                                                    𝑑𝑗 (𝑣, 𝑤)
                                        𝑢𝐿,𝑗 (𝑣, 𝑤) = 𝑐𝑗 (𝑣, 𝑤) −
                                                                        2

                                                                    𝑑𝑗 (𝑣, 𝑤)
                                        𝑢𝑅,𝑗 (𝑣, 𝑤) = 𝑐𝑗 (𝑣, 𝑤) +
                                                                        2

c 是局部中心，d 是局部线宽。将设计形状、系统性形变和随机残差拆开：

                                     (0)
                             𝑐𝑗 = 𝑐𝑗 (𝑤) + 𝑐𝑗,det (𝑣, 𝑤) + 𝑐𝑗,rnd (𝑣, 𝑤)

                                     (0)
                            𝑑𝑗 = 𝑑𝑗 (𝑤) + 𝑑𝑗,det (𝑣, 𝑤) + 𝑑𝑗,rnd (𝑣, 𝑤)

  部分            建议包含                                        如何避免重复

  基准截面          CD、侧壁角、footing、圆角、层厚                        明确 CD 在顶部 / 中部 / 底部；平均形状只出现一次


  确定性变化         整条线弯曲、倾斜、慢漂移、周期调制                           与随机模型联合拟合或设定互不重叠频带


  随机残差          LER / LWR、邻线差异、高度与层间波动                      保留独立统计量；不再在 CD / pitch 中重复加入




   分别给每条线中心加随机量时，相邻中心之差已经产生 pitch 波动；再无约束叠加独立 pitch 参数，会重
   复或改变统计结构。


非规则轮廓可用基准边界的法向位移 h(s)；一般三维侧壁用 h(s,t)。这种表示仍要求不自交、不改变拓扑。桥
接、断线、孤岛、悬垂要用独立缺陷族或封闭网格 / level set 表示。

不能逐条“拉直”实测边缘后丢弃低频信息；去除的平移、旋转、斜率和弯曲必须单独记录，因为它们可能正
是 AL 敏感部分。[11]




MARK ROUGHNESS | Research & implementation                                                 04 / 22


---

### PDF 第 5 页


04 · CORRELATION



只有一个 RMS，无法定义随机 Mark
设两条边缘残差为 hL、hR。它们的中心和宽度变化是：

                                              ℎ𝐿 + ℎ𝑅
                                      ℎ𝑐 =            ,       ℎ 𝑑 = ℎ 𝑅 − ℎ𝐿
                                                 2

若左右单边 RMS 均为 σ、零滞后相关系数为 ρ，由协方差直接得到：

                                              𝜎2
                                      𝜎𝑐2 =      (1 + 𝜌),     𝜎𝑑2 = 2𝜎2 (1 − 𝜌)
                                              2


  左右关系            中心 RMS       宽度 RMS          几何含义

  ρ=+1，同向         σ            0               整条线摆动，宽度不变


  ρ=0，不相关         σ/√2         √2 σ            位置与宽度都变化


  ρ=−1，反向         0            2σ              中心不变，宽度起伏



这些是几何恒等关系，不是光学近似。LER 在不同文献中可能指单边 1σ 或 3σ；配置必须明确。不要同时把
σc、σd 与 ρ 当作互相独立的自由参数。

需要逐步补齐的相关性

  相关方向          会改变什么                                       第一版建议

  左右边缘          位置摆动与线宽起伏的比例                                纯中心、纯宽度与混合对照


  相邻条纹          共同弯曲或独立变动；峰与散射背景                            全共同 / 独立两个端点


  沿高度           同一轮廓挤出或不同高度各自变化                             完全相关挤出基准，再加有限相关


  不同材料层         上下边缘相互跟随或错位                                 保留相关与相对偏移



一般应使用频率相关互谱，而非单个 ρ。互谱矩阵必须是 Hermitian 半正定；任意填写两两相关系数不一定
构成有效随机场。不同样本的实际相位仍需 seed / 系数保存。[6]




MARK ROUGHNESS | Research & implementation                                        05 / 22


---

### PDF 第 6 页


05 · RANDOM FIELD



PSD 把“各种弯曲”变成可控参数
用 q 表示角空间频率，单位 rad/μm；沿边缘周期 Λ=2π/|q|。采用双边 PSD 定义：

                                                                            ∞
                                 𝐶(𝜏 ) = 𝔼[ℎ(𝑣)ℎ(𝑣 + 𝜏 )] ,      𝑆(𝑞) = ∫        𝐶(𝜏 )𝑒−𝑖𝑞𝜏 d𝜏
                                                                            −∞


                                                                   ∞
                                                                1
                                             𝜎2 = 𝐶(0) =          ∫ 𝑆(𝑞) d𝑞
                                                               2𝜋 −∞

一种有直接文献依据的模型是伸缩指数协方差；ξ 在此为 ACF 降到 1/e 的距离，H 控制短尺度变化。[2]

                                                                  2𝐻
                                  𝐶(𝜏 ) = 𝜎2 exp[− (|𝜏 |/𝜉)            ],    0<𝐻≤1

                                                1                        2𝜎2 𝜉
                                        𝐻=        ∶           𝑆(𝑞) =
                                                2                      1 + (𝑞𝜉)2

                                                                  √                       2
                                𝐻=1∶                  𝑆(𝑞) =           𝜋 𝜎2 𝜉 𝑒−(𝑞𝜉) /4

也可使用 S(q)=A/[1+(qξ)²]H+1/2 的自仿射谱，但它一般不是上式协方差的精确 Fourier 变换，ξ 定义也不同。
第一版选一个模型族并固定定义。

建议扫描统计参数，而非几千个独立系数

  类别            参数

  尺度与幅度         中心 / 宽度 RMS、ξ、H、物理短波截止、计算带宽


  联合统计          跨边缘 / 跨线 / 高度 / 层间互谱或可生成的相关模型


  总体与实现         Gaussian / 非 Gaussian、局部缺陷、seed、域尺寸、采样间隔



PSD 不唯一确定实际轮廓。Gaussian 平稳场由均值与协方差确定总体；非 Gaussian 尾部、局部异常、非平
稳粗糙度须另加模型。无短波截止的自仿射理想谱可能有发散的斜率方差，不应无限外推到原子尺度。




MARK ROUGHNESS | Research & implementation                                                       06 / 22


---

### PDF 第 7 页


06 · SYNTHESIS



如何正确生成与保存随机轮廓
以长度 L 的周期超胞为例，取 qn=2πn/L。对正频率生成独立标准复 Gaussian 数 zn，满足 E|zn|²=1，再加
入共轭负频率：


                                                             𝑆(𝑞𝑛 )
                                    ℎ(𝑣) = 2 Re ∑ √                 𝑧𝑛 𝑒𝑖𝑞𝑛 𝑣
                                                    𝑛>0
                                                               𝐿

                                                           2
                                             𝔼[ℎ(𝑣)2 ] =     ∑ 𝑆(𝑞𝑛 )
                                                           𝐿 𝑛>0

上式明确了 Fourier 归一化。零频平均位置 / CD 作为独立参数保存；有实际低频总体变化时不能无条件删
掉。固定振幅只随机相位，与复 Gaussian 系数的统计不同。[1]

多边缘共同生成
                                                                     B(𝑞𝑛 )z𝑛
                                   S(𝑞) = B(𝑞)B(𝑞)† ,         a𝑛 =     √
                                                                         𝐿

每个频率的系数向量覆盖不同边缘 / 条纹 / 高度模式。由互谱矩阵的 Cholesky 或特征分解生成；负频率取共
轭，保证轮廓为实数。

生成后的必要检查
 • RMS 与 PSD 积分是否一致；实际带内方差和目标方差分别是多少。

 • 左右 / 邻线相关是否正确；周期首尾是否连续；最小线宽 / 间距是否满足约束。

 • 有限 L 漏掉的低频、有限采样漏掉的高频有多少；损失是否随 ξ 改变。

 • 保存 master 轮廓或 Fourier 系数，使换网格、换求解器及截止比较时始终是同一几何。


   单次扫描固定一个 realization。改变扫描位置不重新抽 seed；比较网格或截止时也使用同一 master 几
   何。


每个 seed 强制相同 RMS 可用于标明的控制变量实验，但会改变无条件 Gaussian 总体。裁剪大波动也会改
变 PSD 与分布；若需要截断分布，应将其写入模型并报告拒绝率 / 截断规则。




MARK ROUGHNESS | Research & implementation                                      07 / 22


---

### PDF 第 8 页


07 · VISUAL EXAMPLE



同样粗糙，边缘相关方式可以完全不同




图 1 合成几何示例。显示比例用于解释中心摆动与宽度变化；不是 AH53 实际 SEM，也不是电磁仿真结果。

第一种模式让左右边缘同向移动，第二种模式让左右边缘反向移动。即便单边 RMS 相同，前者优先改变局部
中心，后者优先改变局部 CD；光学响应需分别计算。

多个 Fourier 分量的系数和相位决定一条具体边缘。叠加几何后交给求解器是严格建模；只有弱扰动响应经过
验证，才可对各模式响应作一阶叠加。[4–6]




MARK ROUGHNESS | Research & implementation               08 / 22


---

### PDF 第 9 页


08 · MULTISCALE EXAMPLE



相关长度与删细节，是两种不同实验




图2   合成随机轮廓、理论频谱与同一 seed 的低通示例。上部为比较形状统一样本 RMS；下部截止比较保留原低频系数，不
再归一化。所有曲线均非电磁结果。

相同 RMS 下，短 ξ 将更多方差放到短尺度；长 ξ 对应缓慢边缘漂移，可能在有限光斑内近似偏移 / 倾斜。不
能仅按“毛刺多不多”评估 AL 影响。


   截止实验：高频删除后总 RMS 通常降低。若将剩余波形放大回原 RMS，就同时改变了低频，无法单独判
   断高频贡献。




MARK ROUGHNESS | Research & implementation                 09 / 22


---

### PDF 第 10 页


09 · 3D GEOMETRY



把边缘模型接到已有截面放样
保留之前的 B 样条截面 / 放样作为几何承载层，随机生成器只负责产生边界位移或截面参数。Fourier、B 样
条和 KL 承担不同工作，并不互相排斥。

                                                  𝐴
                                      ℎ𝑗 (𝑣, 𝑤) = ∑ 𝜓𝑎 (𝑤)𝑧𝑗,𝑎 (𝑣)
                                                 𝑎=0


  表达方式                    适合用途                                  需要检查

  Fourier / FFT           平稳场、PSD 控制、频段截断                       周期延拓、有限域、谱泄漏


  B 样条 / 放样               侧壁、圆肩、footing、顶面；兼容现有模块               结点 / 拟合容差不能偷偷滤掉重要频段


  高度模态 ψa(w)              从同形挤出加入顶部 / 底部差异                      ψ0=1 只是高度完全相关假设


  KL / PCA                测得协方差后减少随机维数                          99% 几何方差不保证 99% KPI 效应


  局部基函数 / wavelet         某段变粗、缺口、非平稳影响                         与背景随机场避免重复 RMS


  封闭网格 / level set        桥接、断线、悬垂、孤岛                           拓扑、网格有效性和材料占据



第一版的高度假设
先将同一条沿 v 的随机轮廓通过厚度挤出，在已有平均侧壁角 / 圆角 / footing 上定义位移。随后增加“顶部
强、底部弱”“有限高度相关”等模式。不应在每个高度切片独立抽样，否则会生成未定义、可能不现实的高
度高频。

SEM + TEM 能给什么，不能给什么
顶视 SEM 通常是三维投影与电子成像响应共同形成的边缘。van Kessel 等发现，在其研究条件下观测 LER
可低于真实侧壁粗糙度；不能把顶视轮廓当作所有高度的真实轮廓。[9] TEM / 截面信息可约束平均形状和部
分高度变化，但有限截面也不能唯一恢复整片随机侧壁。




MARK ROUGHNESS | Research & implementation                                               10 / 22


---

### PDF 第 11 页


10 · RCWA



随机超胞：管理好人工周期
沿 v 的变化破坏原来的条纹平移不变性。严格 RCWA 应使用两个横向维度的周期超胞，并输出双指标复振幅
矩阵。超胞尺寸 Lu、Lv 对应：

                                                     2𝜋ℓ                      2𝜋𝑛
                                    𝑘𝑢,ℓ = 𝑘𝑢,in +       ,   𝑘𝑣,𝑛 = 𝑘𝑣,in +
                                                     𝐿𝑢                        𝐿𝑣

                                         Rℓ,𝑛 = {𝑟𝑠𝑠 , 𝑟𝑠𝑝 , 𝑟𝑝𝑠 , 𝑟𝑝𝑝 }
                                                                       ℓ,𝑛


若 Lu=NpP，原母周期第 m 阶对应 l=Np m。其余 l 是跨线变化带来的通道，不能按旧 m 标签混在一起。只
有每个母周期重复相同扰动，u 方向才保留原周期。

 • 超胞内生成多条线及其相关性。只生成一条再复制，会强制所有线完全相关。

 • v 方向使用周期连续生成；任意片段首尾硬接会增加人为尖点与高频。

 • 分别提高几何采样、厚度分层与场 Fourier 模式；它们不是同一个精度旋钮。

 • 增大 Lu / Lv，比较同一物理角域的功率、复场与 KPI，检查副本耦合和角谱分辨率。[13,14]

为什么可能非常昂贵

                    𝑁𝑘 = (2𝑀𝑢 + 1)(2𝑀𝑣 + 1),                          memory ∼ 𝒪(𝑁𝑘2 )
标准密集矩阵 RCWA 的核心分解常有约 O(Nk³) 成本。Lv 增大而短波尺度不变时，Mv 也须增加。“很长超
胞 + 极短粗糙周期”不适合直接穷举。材料边界指示函数还会产生高频，轮廓带宽不等于所需场模式数。[3]


   Lumerical 在 Y 传播下 KU=X、KV=Z。当前官方文档包含后来新增功能；正式脚本按你的 2023 R2.1 实
   机核对，尤其材料模型与网格设置。[14]




MARK ROUGHNESS | Research & implementation                                               11 / 22


---

### PDF 第 12 页


11 · FDTD



3D FDTD：严格基准与有限 Mark 校验
原 2D XY FDTD 对应 Z 方向均匀，不能严格模拟沿条纹随机边缘。独立求解多个二维截面再平均，可以研究
缓慢变截面的近似，但会漏掉截面耦合与出平面散射。


  阶段                      建模与输出                                  目的

  3D 周期小超胞                与 RCWA 同一连续几何 / 材料 / 入射；保存反射 E/H 或二维   分离几何与求解器差异
                          角谱


  有限 Mark + 有限光           横向 PML、固定随机几何、多个扫描位置；保存二维角谱            检验有限边缘和实际扫
  斑                                                              描



网格不能决定物理粗糙度
先固定连续 master 几何和保留带宽，再离散。最短保留周期 Λmin 的采样至少满足 Nyquist；每周期约 6–
10 点可作为几何描绘起点，但不是场精度验收。薄层、曲率、材料内波长和局部场增强仍可能要求更细网格。

1 nm 界面位移不必然要求整个模型采用 1 nm 网格：验证过的共形 / 亚像素处理可能表达亚网格位移。这不
保证它能表达沿边缘 1 nm 周期的起伏。Meep 官方列出亚像素平滑对色散、损耗、尖角与局部曲率的限制。
[16]

非均匀网格特别需要的校验
非均匀网格减少远处单元数，但最细单元仍影响显式时间步。极弱粗糙散射中，理想与扰动结构应使用匹配网
格；横向局部细化也可能产生假散射。Ansys 的缺陷计量方案特别提醒此问题。[13]


   成本量级示例：16×8×2 μm 的均匀 10 nm 网格约有 2.56 亿单元，仅 6 个双精度场数组约 12.3 GB，尚
   未包含材料、PML、DFT 等。此例用于说明成本，并非推荐域尺寸。


你们自研非均匀 Meep 链的既有限定范围验收，不自动证明复杂有损 3D rough Mark 已达到精度；少量严格
算例应构成这一应用的专门验证。




MARK ROUGHNESS | Research & implementation                               12 / 22


---

### PDF 第 13 页


12 · DETECTION



从二维复角谱到信号，保留相干性
随机边缘产生离散主阶之外的散射。超胞输出 Rl,n；有限 Mark 输出 A(ku,kv)。后处理需使用圆瞳、零级挡
板、偏振和真实 RSI 配对关系，不能只对旧 m 做功率加权。


                                         𝑘𝑢2 + 𝑘𝑣2 ≤ (𝑘0 NA)2
示意地，令两条光路后的配对场为 b+、b−。一对模式的干涉项可写为下式；指数符号依坐标约定：

                             𝐼𝑚 (Δ𝑢) = ‖b+ ‖2 + ‖b− ‖2 + 2 Re[𝐶𝑚 𝑒−𝑖2𝐺𝑚 Δ𝑢 ]

                                                                     2𝜋𝑚
                                             𝐶𝑚 = b†− b+ ,    𝐺𝑚 =
                                                                      𝑃

一般须保留复振幅乘积和相位。已有 Im=|rm|² 的缩约、Km 表可在原对称条件下作为基准；随机不对称结构
需检验能否继续缩约。只累计各 n 功率会丢掉相干交叉项。

每个 seed 先走完光路，再做统计

                                𝐼(𝑥) = b† Q(𝑥)b,             𝔼[𝐼(𝑥)] = Tr[Q(𝑥)W]

                                       W = 𝔼[bb† ] = b̄ b̄ † + Cov(b)

先平均各 seed 的复场再平方会漏掉协方差。第一版无需显式构造巨大 W：每个 realization 分别计算曲线及
AL/WQ/APD，再统计。KPI 的均值也不等于对平均曲线计算的 KPI。

静态粗糙度不自动使散射光失相干，也不等于时间噪声。对互不相干入射源点，在固定几何上分别传播到探测
器再加权相加强度。有限光斑扫描还须考虑照明与形貌相对位置，不能默认只加平移相位。[13]




MARK ROUGHNESS | Research & implementation                                         13 / 22


---

### PDF 第 14 页


13 · PHYSICAL SCALES



哪些“很细”的变化可能不重要？
区分三个长度：横向起伏振幅 σ、沿边缘周期 Λ、统计相关长度 ξ。小振幅不等于短周期；短周期也不等于小
影响。材料反差、局部场、偏振与窄缝都参与决定响应。[3,5,12]

NA 是直接旁带筛选，不是几何删减线
仅在正入射、基准沿 v 均匀、同一 u 母周期阶 m、弱扰动一阶散射下，有 kv,out=qv、ku,out=2πm/P：

                                                                     2𝜋𝑚 2
                                             |𝑞𝑣 | ≤ √(𝑘0 NA)2 − (      )
                                                                      𝑃




  643 nm，NA=0.6，P=16 μm           一阶 v 旁带可入瞳的最短周
                                  期

  m=0                             1.072 μm


  m=1                             1.074 μm


  m=5                             1.137 μm


  m=10                            1.443 μm


  m=14                            3.085 μm



上表由波矢关系计算。m=0 仅用于解释光瞳；零级挡板单独作用。高 q 直接旁带被挡住，并不排除近场与二
阶回耦改变主阶。有限光斑、斜照和跨线无序会改变耦合。

一个只用于理解的局部相位模型
                                                      2   2
                               𝔼[𝑒−𝑖𝐺𝑚 ℎ ] = 𝑒−𝐺𝑚 𝜎 /2                  (ℎ Gaussian)

即使零均值位移，相干分量也可能衰减。该式是 Gaussian 特征函数；用作 Mark 通用修正需要额外假设。
Debye–Waller 因子有研究明确的适用边界，不能替代严格计算。[7,8]


   小于 λ/10、位于 NA 外、小于 SEM 像素或 FDTD 网格，都不能单独证明“无光学影响”。




MARK ROUGHNESS | Research & implementation                                             14 / 22


---

### PDF 第 15 页


14 · ERROR CRITERION



按最终 KPI 灵敏度选择保留频带
以下是本课题的数学推导。令 a 为零均值实随机几何系数，协方差 C；K 为可微的实际 KPI。基准附近：

                                                               1
                                             𝒦(a) ≃ 𝒦0 + gT a + aT Ha
                                                               2

                                                                           1
                                   Var(𝒦) ≃ gT Cg,           𝔼[𝒦] − 𝒦0 ≃     Tr(HC)
                                                                           2

一阶项决定散布，二阶项可产生平均偏移。零均值边缘不保证平均信号不变；对称总体的某些有符号位置偏差
可因对称性为零，单个 Mark 偏差及总体散布仍须计算。

若单边缘的一阶变化写成 δK=∫gK(v)h(v)dv，删除 |q|>qc 的误差方差近似为：

                                        2                                       d𝑞
                                       𝜎𝒦,>𝑞   ≃∫              ̃ (𝑞)|2 𝑆ℎ (𝑞)
                                                             |𝑔𝒦
                                             𝑐
                                                    |𝑞|>𝑞𝑐                      2𝜋

它把“该频段有多少粗糙度”与“测量对该频段多敏感”相乘。多边缘应使用互谱；非平稳或频带相关应使用
完整协方差 / 条件模型。这是一阶估计，仍需检查二阶偏移与严格仿真残差。

为什么只看强度相对误差不够
若仅拟合平移 I0(x−Δ)，实际变化为 δI，加权最小二乘的一阶偏差是：

                                                   ∫ 𝑤(𝑥)𝐼0 ′(𝑥) 𝛿𝐼(𝑥) d𝑥
                                             Δ≃−
                                                     ∫ 𝑤(𝑥)[𝐼0 ′(𝑥)]2 d𝑥

像“曲线平移”的微小变化会造成位置偏差。若同时拟合背景、增益、相位，应用实际多参数                                             Jacobian。对
±m 相位定位的简例，|δx|=P|δφ|/(4π|m|)；P=16 μm、m=1 时，1 mrad 对应约 1.273 nm。这是灵敏度换
算，不是粗糙度误差预测。




MARK ROUGHNESS | Research & implementation                                                  15 / 22


---

### PDF 第 16 页


15 · VALIDATION



同一随机边缘，逐步添加更细变化
可以交给仿真 Runner 的实验
 • 固定 master Fourier 系数、材料、基准形状、照明、光路及 seed。

 • 构造嵌套带宽：例如最短保留周期 2、1、0.5、0.2、0.1、0.05 μm。它们只是筛选点，须适配超胞，不是
   已认可的截止。

 • 每个带宽先收敛数值误差，再比较复 Jones / 角谱、干涉项、曲线及 KPI。

 • 记录同 seed 的 d=Kfull−Klowpass；增加 seed，检查成对误差均值、散布和统计不确定度。

 • 超出预算就增加带宽，或用验证过的等效修正；降采样前先抗混叠。

几类收敛要分别判断

  对象                保持不变                     主要输出

  数值收敛              同一连续几何、随机实现              网格 / 时间 / 谐波 / 分层差异


  物理带宽              同 master 已保留的低频          新增短尺度造成的复场 / KPI 变化


  统计收敛              模型与数值设置                  均值、标准差、分位的置信区间


  超胞 / 有限尺寸         同统计模型及可比物理角域             人工周期、副本耦合、有限光斑



不能让粗网格“自然抹平”代替物理截止实验。极小复振幅附近，不用相对相位误差单独验收，应检查绝对复
场误差和最终信号。


   阈值来自项目误差预算。本次没有实测 PSD、KPI 预算及严格求解结果，因此不宣称“20 nm 以下可忽
   略”，也不承诺固定 seed 数量足够认证尾部概率。




MARK ROUGHNESS | Research & implementation                         16 / 22


---

### PDF 第 17 页


16 · ACCELERATION



先有限差分，再考虑微扰核与等效界面
第一版先用现有求解器作为黑箱。对少量边缘模式 φj 和空间频率，计算 +a、−a 与基准：

                                                𝒦(+𝑎𝜙𝑗 ) − 𝒦(−𝑎𝜙𝑗 )
                                         𝑔𝑗 ≃
                                                        2𝑎

                                             𝒦(+𝑎𝜙𝑗 ) + 𝒦(−𝑎𝜙𝑗 ) − 2𝒦0
                                     𝐻𝑗𝑗 ≃
                                                        𝑎2

a 应高于差分噪声且仍在小扰动范围；以 a/2 抽查稳定性。有限光斑下测试正弦 / 余弦相位。最敏感参数对再
算 F(A,B)−F(A,0)−F(0,B)+F(0,0) 交互项。


  方法                   适合范围                               需要验证

  响应核 / PSD 传播         弱粗糙，基准固定，大量统计扫描                    严格复场 / KPI 残差；Heusinger 理论支持 [5]


  移动边界 / adjoint       需要许多边界自由度梯度                        界面不连续、有损归一化和伴随定义 [12]


  各向异性等效界面             短相关、小振幅、尺度分离                       主阶复场、偏振与 KPI；不照搬文献拟合参数 [3]



Johnson 的经典结果表明，高反差边界位移不能用任取一侧的 Δε|E|² 处理。其论文主要针对无损介质本征 /
模耦合；有损 Si/MoSi 散射要正确推导伴随形式。[12]


   严格路径始终保留。大振幅、桥接 / 断线、局部共振、强场窄缝或明显二阶交互时升级模型。不能把“孤
   立缺陷在空气中的 FDTD 场”直接加到 RCWA 背景；背景激励与耦合必须一致。




MARK ROUGHNESS | Research & implementation                                                   17 / 22


---

### PDF 第 18 页


17 · IMPLEMENTATION



给现有项目的分阶段实施计划
  阶段                具体工作                                      完成标志

  A · 几何            PSD + Gaussian 生成器；中心 / 宽度、相关性、seed、短波截   轮廓与统计、约束均可复现
                    止；接放样


  B · 确定性校验         零粗糙、单正弦、双频；纯中心 / 纯宽度；少量幅值                 2D 退化一致，3D 模式可解
                                                              释


  C · 严格随机超         同几何 RCWA / 3D FDTD；约 6–12 个代表场景           分开数值、带宽和周期误差
  胞


  D · 截止            同 master 频带扫描；多 seed 成对误差                 给出绑定具体光学条件的截
                                                              止表


  E · 批量统计          敏感参数先单变量、后交互；验证过的快模型                      KPI 分布及不确定度、严格
                                                              抽查


  F · 有限 Mark       38 μm 光斑和扫描；二维瞳孔 / RSI                    评估超胞结论的迁移能力



初始筛选建议，不是工艺测量值
保留 AH53 基准：母周期 16 μm、子周期 3.2 μm、线宽 1.6 μm、高 300 nm、λ=643 nm。可从
σ=0/2/5/10/20 nm、ξ=0.05/0.2/1/5 μm、H=0.5/0.8、纯中心 / 纯宽度中选择代表点，避免全因子展开。后续
由 SEM/TEM 替换范围。

每个场景先少量 seed 估计散布，再按置信区间追加；少量样本只能探索。膜厚、侧壁角、上下层倾斜等其他
非理想先保持可控，单项响应明确后再加交互。


   AI 负责生成配置、队列、完整性检查、响应拟合与选择下一组算例。物理轮廓由可复现生成器产生；训练
   / 验证按整个 seed 或几何分组，不能将同一 Mark 的扫描点分到两边。




MARK ROUGHNESS | Research & implementation                                 18 / 22


---

### PDF 第 19 页


18 · DATA CONTRACT



数据接口与最小交付
  对象               必存内容

  geometry         坐标、单位、层结构、基准版本、CD 参考高度、master 轮廓 / 系数及 hash


  roughness        RMS 的 1σ / 3σ 定义、PSD 与归一化、ξ/H、物理 / 计算截止、相关、seed


  solver           版本、网格 / KU/KV / 切片、边界、材料拟合、源、参考面、收敛


  EM               复 Jones / E/H、二维波矢、传播 / 倏逝标志、振幅与功率归一化分开


  optics / KPI     光斑定义、NA / 挡板、偏振、RSI、曲线、KPI 算法版本、每 seed 结果


  statistics       均值、散布、截止成对误差、置信区间、失败 / 几何拒绝案例



最小伪代码

  master = generate_joint_random_geometry(model, seed)
  for cutoff in nested_bandwidths:
     geometry = lowpass(master, cutoff) # 不恢复原 RMS
     field = solve_with_convergence(geometry)
     signal = full_optical_scan(field, optics)
     kpi = existing_kpi_algorithm(signal)
     compare_with_same_seed_reference(kpi)
  aggregate_per_seed_kpis_and_paired_errors()


有限光斑使 field 可能依赖扫描位置，此时应逐位置求解，或使用验证过的入射 / 出射 S 矩阵重构。上面的场
复用只适用于可复用表示，单一平面波结果不能直接替代任意有限光斑响应。

第一份可靠项目成果
形成“在指定波长、偏振、光斑、几何与 KPI 下，某些频段可删除 / 需要等效 / 必须保留”的表，附严格基准
和不确定度，而不是一个对所有 Mark 通用的 nm 阈值。




MARK ROUGHNESS | Research & implementation                           19 / 22


---

### PDF 第 20 页


REFERENCES · 1/3



参考文献与可核查来源
[1] C. A. Mack (2013). Generating random rough edges, surfaces, and volumes. Applied Optics 52(7),
1472–1480.
10.1364/AO.52.001472 · 原始来源 / 全文
作者全文；谱合成与有限采样偏差。


[2] C. A. Mack (2011). Analytic form for the power spectral density in one, two, and three
dimensions. JM3 10(4), 040501.
10.1117/1.3663567 · 原始来源 / 全文
作者全文；协方差和 PSD。


[3] B. C. Bergner, T. A. Germer, T. J. Suleski (2010). Effective medium approximations for modeling
optical reflectance from gratings with rough edges. JOSA A 27(5), 1083–1090.
10.1364/JOSAA.27.001083 · 原始来源 / 全文
NIST 全文；RCWA 与各向异性 EMA。


[4] A. Kato, S. Burger, F. Scholze (2012). Analytical modeling and three-dimensional finite element
simulation of line edge roughness in scatterometry. Applied Optics 51(27), 6457–6464.
10.1364/AO.51.006457 · 原始来源 / 全文
作者预印本全文；正弦模式与 3D FEM。


[5] M. Heusinger, D. Michaelis, T. Flügel-Paul, U. D. Zeitner (2018). Diffuse scattering due to
stochastic disturbances of 1D-gratings on the example of line edge roughness. Optics Express
26(21), 28104–28118.
10.1364/OE.26.028104 · 原始来源 / 全文
作者摘要及机构说明；小扰动 PSD 响应分离。


[6] A. Fernández Herrero, F. Scholze, G. Dai, V. Soltwisch (2022). Analysis of Line-Edge Roughness
Using EUV Scatterometry. Nanomanufacturing and Metrology 5, 149–158.
10.1007/s41871-022-00126-w · 原始来源 / 全文
开放全文；随机粗糙、线间相关与高度。




MARK ROUGHNESS | Research & implementation                                                        20 / 22


---

### PDF 第 21 页


REFERENCES · 2/3



参考文献与可核查来源
[7] H. Gross, S. Heidenreich, M. Bär (2017). Impact of different stochastic line edge roughness
patterns on measurements in scatterometry - A simulation study. Measurement 98, 339–346.
10.1016/j.measurement.2016.08.027 · 原始来源 / 全文
出版社摘要；Fourier aperture 近似及衰减限制。


[8] A. Fernández Herrero, M. Pflüger, J. Probst, F. Scholze, V. Soltwisch (2019). Applicability of the
Debye-Waller damping factor for the determination of the line-edge roughness of lamellar gratings.
Optics Express 27(22), 32490–32507.
10.1364/OE.27.032490 · 原始来源 / 全文
作者摘要；DWF 适用边界。


[9] L. van Kessel, T. Huisman, C. W. Hagen (2020). Understanding the influence of three-dimensional
sidewall roughness on observed line-edge roughness in scanning electron microscopy images. JM3
19(3), 034002.
10.1117/1.JMM.19.3.034002 · 原始来源 / 全文
机构作者摘要；SEM 三维投影。


[10] C. A. Mack (2013). Systematic errors in the measurement of power spectral density. JM3 12(3),
033016.
10.1117/1.JMM.12.3.033016 · 原始来源 / 全文
作者全文；混叠、泄漏、平均和噪声。


[11] C. A. Mack (2015). More systematic errors in the measurement of power spectral density. JM3
14(3), 033502.
10.1117/1.JMM.14.3.033502 · 原始来源 / 全文
作者全文；去趋势与低频 PSD。


[12] S. G. Johnson et al. (2002). Perturbation theory for Maxwell’s equations with shifting material
boundaries. Physical Review E 65, 066611.
10.1103/PhysRevE.65.066611 · 原始来源 / 全文
作者全文；移动界面的一阶响应。




MARK ROUGHNESS | Research & implementation                                                        21 / 22


---

### PDF 第 22 页


REFERENCES · 3/3



参考文献与可核查来源
[13] Ansys Optics. Optical Metrology - S-Matrix Methodology.
官方技术文档 · 原始来源 / 全文
超胞、光路复用和人工网格散射。


[14] Ansys Optics. RCWA Solver - Simulation Object.
官方技术文档 · 原始来源 / 全文
周期、分层、KU/KV 与版本差异。


[15] Ansys Optics. Tips for adding surface roughness to structures; sroughness - Script command.
官方技术文档 · 原始来源 / 全文
RMS / 相关长度；周期与 seed。


[16] Meep documentation. Subpixel Smoothing.
官方技术文档 · 原始来源 / 全文
数值亚像素处理与色散 / 曲率限制。


[17] T. A. Germer (2007). Effect of line and trench profile variation on specular and diffuse
reflectance from a periodic structure. JOSA A 24(3), 696–701.
10.1364/JOSAA.24.000696 · 原始来源 / 全文
机构作者摘要；平均结构不等于平均响应。


[18] C. A. Mack, B. D. Bunday (2017). Using the Analytical Linescan Model for SEM Metrology. Proc.
SPIE 10145.
作者会议论文 · 原始来源 / 全文
作者全文；滤波与 SEM 噪声。



使用实测数据时
先估计 SEM 噪声底和可信频段，再拟合 PSD。图像平滑会改变粗糙度，独立去趋势会压低低频。记录视场、
像素、边缘提取、漂移校正、观测长度与误差条。未观测高频作为不确定性场景，不能把噪声直接输入几何，
也不能宣布它不存在。[9–11,18]




MARK ROUGHNESS | Research & implementation                                                      22 / 22