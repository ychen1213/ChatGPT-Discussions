CB mark 中心峰包络：受控计算核验

本目录没有使用公司 D4C 曲线，也没有使用用户的实际 RCWA R。
只固定对称的等效 ±1 级系数，检验候选包络机制是否能复现描述的规律。
所有长度单位为微米；p=2，构成性载波间距 h=p/2=1。

check_center_models.py
  对比条纹长度、均匀二维旋转交集、Gaussian 加权单窗口 q、
  旋转共同覆盖 t 和单端口构成性包络 q+t。
  L=10,20,40,80；w 对数采样 0.8..40，共 1920 组 q/t/(q+t) 结果。
  其中 68 组 D0/D1 在 1.8..2.2；没有一组同时满足
  后面 D1,D2,D3 的变异系数小于等于 10%。这仅限所测模型和参数范围。
  同时独立检查真实波形局部极大值：当 w=1.67 时，虽然在 nh 处
  采样包络能给出 D0/D1 约 1.97，实际单端口波形在 0..5 内
  只剩中心和一个侧峰，不能描述一串等间距、逐步下降的侧峰。
  有限二维积分与无限区域解析式误差约 3.4e-15；互补和误差 1.1e-16。
  生成 model_comparison.csv、model_summary.json、center_envelope_checks.png。

finite_pupil/check_finite_pupil.py
  L=40,w=12，固定孤立级次，以 Fourier envelope 计算有限收集。
  step mask 用像素内真实二值区域的面积平均离散，512 与1024网格比较。
  0.05,0.1,0.2,0.4 cycles/um 的局部圆光瞳均未给出 D0/D1=2。
  所有有限光瞳都把中心折点变圆，第一下降比第二下降小。
  主实验512到1024的构成性包络最大差异低于中心信号的0.033%。
  另有全场X+Y相干/非相干比较；它只用了512网格，属于补充示例。
  全场示例的波长0.633、NA0.45、中央遮挡0.7G均非用户已知参数。
  生成逐项CSV、results.json、envelopes.png。

说明
  Dn=Pn-P(n+1)，报告的是绝对差，不是百分比差。
  q+t 表示构成性相位位置的包络采样；真实局部峰位会发生偏移。
  脚本对真实局部峰另行检查，未把包络采样一律称作实际峰值。
  互补端口原始功率和为2q；旋转共同覆盖干涉项t在和中抵消。
  独立级次近似和标量场模型不能预测真实角点的矢量电磁散射。
  没有根据上述结果为mask人为设置中心加权，也没有拟合D4C数据。

运行（需要uv联网或已有依赖缓存）
  uv run --with numpy --with scipy --with matplotlib check_center_models.py
  uv run --with numpy --with scipy --with matplotlib finite_pupil/check_finite_pupil.py
