【2026-11-11 对话后续更正】本文件保留历史计算用于追溯；中央排除带和局部偏振/小模式收集均缺乏用户实际 mark 与 D4C 光路依据，不是实际中心峰两倍关系的已验证原因。普通周期空槽已经包含在 RCWA 中，不应额外作为宏观排除窗口重复扣除。请先阅读本归档主题目录中的“2026-11-11_更正说明.md”。

CB 中心结构与收集光路：构造及数据

入口：CB中心结构与光路耦合_构造和数据.html
这是可离线打开的中文说明，含结构图、真实局部峰表、严格项分解和交互曲线。
交互部分可选结构/光瞳/端口，切换时保留同一功率标度。

本次全部为受控标量后处理，没有公司D4C数据，没有调用真实RCWA R。
p=2um为用户已知，其余L40/w12/r±0.2/r0=0及λ0.633/NA0.45是示例假设。

已验证结论
1. 几何对照下，十字留白g0.5/1um使单个相长端口实际峰D0/D1=1.8798/2.1990，
   后续D1,D2,D3的CV为2.70%/4.55%。贯通X区、中心方孔和上下相位变化不产生同样规律。
2. 严格分解发现空带交集 +H_A H_B，仅|s|<g/2存在；删掉该代数项后，
   等间距采样下降比从1.88/2.20回到1.03/1.05。该项在原始互补和中严格抵消。
3. 同一g1结构经过有限光瞳后，宽圆盘r0.2 cycles/um的真实峰比约0.63，
   窄圆盘r0.1/0.05约0.38/0.35，因此不能把几何全收集结果直接移用到实际光路。
4. 上半X相位π+非对称光瞳，可使原始SUM+DIFF中的同臂X/Y交叉项达到约10%。
   对称光瞳时交叉项抵消。该效应与跨臂干涉项不同。
5. 条件性小模式正例：局部有效交叉偏振散射d0.3um，接收mode半径a0.5um，
   w12um、弱主通道η0.001、中心δ0.45，实际峰比2.0665、后续CV2.97%。
   同样中心项全模式收集时比值0.9768。这个例子要求实际存在该偏振/模式/相对强度。
   提高主通道到η0.08后同一中心项只给1.0248。它不能说明D4C硬件具备这些条件。
6. 没有一个已验证模型复现了“原始理想SUM+DIFF”的目标1um峰列。
   所以本次定位的是条件性候选原因及其适用端口，不是唯一确定D4C实际来源。

文件对应
geometry/geometry_experiments.py       精确step几何积分；真实峰；孔交集严格分解
geometry/summary.json                 结构、积分收敛和各项峰值摘要
geometry/actual_plus_peaks.csv        真正局部峰的位置及功率
geometry/hole_overlap_decomposition.csv  孔交集项及删除对照逐点数据
optical/run_optical_coupling.py       完整X+Y场、有限pupil、自参考两臂和交叉项
optical/peak_comparison.csv           几何/光瞳/网格的真实峰对照
optical/convergence.json              512→1024收敛；下降差值比比整条曲线更敏感
optical/phase_coupling_spotcheck.json  非对称收集的同臂X/Y交叉项1024单点复核
overlap_center.py, overlap/           互斥中心C区、假设四级系数、中心/外围相干项
review/mode_selection_example.py      中心小散射项+空间模式的解析及数值正例
review/efficiency_sweep.csv           主通道强度及所需中心系数的限制
review/raw_sum_samples_NOT_peaks.csv  单端口正例不能解释原始互补和的反证检查
make_explanation.py                  汇总数据生成离线中文HTML

复现命令
uv run --with numpy --with scipy --with matplotlib geometry/geometry_experiments.py
uv run --with numpy --with scipy --with matplotlib optical/run_optical_coupling.py
uv run --with numpy --with scipy --with matplotlib optical/run_optical_coupling.py --n 1024 --geometries ideal cross_gap1
uv run --with numpy --with scipy --with matplotlib overlap_center.py
uv run --with numpy --with scipy --with matplotlib review/mode_selection_example.py
uv run --with numpy --with scipy --with matplotlib make_explanation.py

接入真实R时：r=Ra；区分原始E系数与模态功率归一化；保留复相位；
X/Y/flat/center区域互斥；真实交叉刻蚀center不能直接令其场等于X+Y。
额外十字留白必须超出RCWA原周期单元的普通50%空槽，否则重复计数。
光瞳和像面场阑必须按实际光路先后顺序作用于复场。
