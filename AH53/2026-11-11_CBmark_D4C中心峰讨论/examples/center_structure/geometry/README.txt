【2026-11-11 对话后续更正】本文件保留历史计算用于追溯；中央排除带和局部偏振/小模式收集均缺乏用户实际 mark 与 D4C 光路依据，不是实际中心峰两倍关系的已验证原因。普通周期空槽已经包含在 RCWA 中，不应额外作为宏观排除窗口重复扣除。请先阅读本归档主题目录中的“2026-11-11_更正说明.md”。

本目录是受控构造实验，不是 D4C 数据，也未使用真实 RCWA R。

运行：uv run --with numpy --with scipy --with matplotlib geometry_experiments.py

固定参数：p=2 um，L=40 um，高斯光斑强度 G∝exp[-2(u²+v²)/w²]，w=12 um。
仅考虑 X 衍射通道的标量 ±1 复振幅 r+=r-=0.2，r0=0。
这个幅值用于受控对比，不能当成实际衍射效率。没有有限光瞳或探测模式筛选。
复场 E_s(u,v)=A(u,v) M_X(u+s,v) r[exp(iG0(x-delta(y)))+exp(-iG0(x-delta(y)))].
旋转臂为 E_s(-u,-v)，互补端口 I±=(1/2)∫|E_s±E_s(-u,-v)|²。

几何定义（均限制于边长 L 的外方框）：
1. ideal：X 区域 |y|>=|x|，Y 为其余部分。
2. xstrip_c：在 |x|<c/2 中统一采用 X 区域，替换原 Y 区域；不叠加 X/Y 系数。
3. crossblank_g：去掉 |x|<g/2 OR |y|<g/2 内的模型 ±1 衍射响应。
4. squareblank_g：去掉 |x|<g/2 AND |y|<g/2 内的模型 ±1 衍射响应。
5. registry：X 上下两区域的条纹相对位移 delta，实际通过 exp(∓iG0 delta) 改变 ±1 系数相位。
   anchored-top 版本上方 delta=0、下方=p/4 或 p/2；另有对称 recentered 版本±p/8。

留白只意味着此模型中的 ±1 光栅分量为零；不意味着真实材料总反射率为零。
真实交叉刻蚀区域不能用 X+Y 系数机械相加，需其自身 RCWA/材料模型。

积分方法：所有 0/1 几何边界保留，y 方向高斯质量解析积分，x 在每个边界处分段后做 96 点 Gauss-Legendre 积分。
用于显示的像素几何图不参与信号计算。96 与 192 点结果最大差 1.20e-14。
扫描范围 0..5 um，步长 .01 um。真实峰通过 scipy.find_peaks 后局部三次样条优化；CSV 同时保存完整扫描及峰位置。
所有绝对功率保留。图中只用 ideal 中心 plus 值作共同参考，未对每条曲线分别归一化。

核心结果（真实峰的 D0/D1，后面三次下降的 CV）：
ideal                   1.01136, 2.83%
xstrip c=.5             1.01986, 2.81%
xstrip c=1              1.02517, 2.80%
crossblank g=.5         1.87978, 2.70%
crossblank g=1          2.19898, 4.55%
squareblank g=1         0.97870, 2.89%
squareblank g=2         0.91873, 3.01%
registry bottom=p/4     1.01757，第一 plus 峰移到 s=.2450 um
registry bottom=p/2     1.02111，s=0 plus 为零，第一 plus 峰移到 s=.4948 um
registry centered±p/8   1.01162，中心仍为亮峰

crossblank 的因果分解：对于 X 区域，十字留白等价于删掉中央竖条 H=1{|x|<g/2}。
M_A M_B=I_A I_B(1-H_A-H_B+H_A H_B)。最后的重叠孔项 H_AH_B 仅在 |s|<g/2 存在。
它在 s=0 提供一个局部相干交叉项，在第一侧峰 s≈1 um 已严格为零。
g=.5：该项中心 plus 贡献 .004283365724，原 plus=.071367899929。
g=1：该项中心 plus 贡献 .005207199948，原 plus=.069520231481。
删除此交叉项作为代数诊断，保持其他各项不变，整数位置 D0/D1 从 1.88156/2.20159 回到 1.03316/1.05165。
这说明具体的内部缺口产生了中心独有的重叠贡献，并非普通三角条纹长度最大就必然造成两倍。
代数删除交叉项只是因果定位；不代表另一个可直接制造的实体 mark。

通道限制：H_AH_B 项在 minus 端口符号相反，在 plus+minus 中完全抵消。
因此这些结果可解释单干涉端口或调制度的中心增强，不能直接归因为匹配互补端口的原始和信号。
要解释后一种信号，必须同时检查单臂收集功率、检测模式、光阑或实际 SUM/DIFF 定义。

文件：
geometry_experiments.py：全部实验和绘图。
summary.json：模型、参数、完整数值摘要、收敛、因果分解。
scans.csv：q、t、两臂功率、跨臂项、plus、minus、sum。
actual_plus_peaks.csv：真实局部峰位置和功率。
hole_overlap_decomposition.csv：中央孔相交项的独立贡献和移除对照。
center_geometry.png：中心几何与相位原点示意。
geometry_scans.png：几何 q/t、扫描曲线和差值。
registry_scans.png：上下相位的端口、峰位置与互补和对比。
hole_overlap_decomposition.png：中央孔相交项的因果分解图。
