【2026-11-11 对话后续更正】本文件保留历史计算用于追溯；中央排除带和局部偏振/小模式收集均缺乏用户实际 mark 与 D4C 光路依据，不是实际中心峰两倍关系的已验证原因。普通周期空槽已经包含在 RCWA 中，不应额外作为宏观排除窗口重复扣除。请先阅读本归档主题目录中的“2026-11-11_更正说明.md”。

CONTROLLED FINITE-CB STRUCTURE AND OPTICAL COLLECTION TEST

This is a synthetic scalar optical model, NOT a fit to D4C or an actual RCWA export.
All lengths are micrometres; FFT frequencies are cycles per micrometre.
Incident Gaussian power is one. r+1=r-1=.2 are FIELD amplitudes, not 20% powers.
Each isolated infinite grating order would have 4% power in this scalar convention.
There is no renormalization between geometries, pupils, or scan positions.

GEOMETRIES
ideal: square |x|,|y|<=20; X region |y|>=|x|, Y is its complement.
cross_gap1: remove periodic diffracted fields where |x|<.5 OR |y|<.5.
square_gap2: remove periodic diffracted fields where |x|<1 AND |y|<1.
phase_upper_pi: upper X region multiplies BOTH +/-1 amplitudes by -1; lower X and Y unchanged.
This upper-X phase corresponds to a p/2=1 um line-origin shift for the retained +/-1 orders.
A gap means r+/-1=0 there. It does NOT assert zero physical total reflectivity of a blank surface.

OPTICAL MODEL
E=A(u,v)[mX(u+s,v)*2r*cos(2pi(u+s)/p)+mY(u+s,v)*2r*cos(2pi v/p)].
FFT is unitary. F_B(k)=F_A(-k), without complex conjugation.
Every fixed detector ROI is intersected with physical NA/wavelength = .45/.633.
Five ROIs: +X-order disks radius .20, .10, .05; disk .10 shifted ky +.06; disk .20 clipped ky>=.04.
SUM=.5 integral|F_A+F_B|^2; DIFF=.5 integral|F_A-F_B|^2.
Raw SUM+DIFF=Q_A+Q_B: the inter-arm interference cancels exactly.
Same-arm X/Y cross terms can survive in that raw sum if their diffracted fields overlap inside the ROI.

EXPORTED COLUMNS
power_a,power_b: collected one-arm coherent powers.
same_arm_xy_a,b: coherent X+Y power minus separately summed X and Y powers.
cross_arm_real: Re integral F_A*conj(F_B). It enters SUM/DIFF with opposite signs.
port_sum,port_diff,raw_sum,incoherent_raw_sum: unnormalized powers.

PEAKS AND LIMITS
Scan is 0..5 with .02 um step. True local maxima are found then refined by a local quadratic.
Peak sampling is not forced to s=n um. No right scan endpoint is called a peak.
phase_upper_pi has a central SUM dip, so its successive-peak ratio is NOT a center-to-side ratio.
Small high-frequency raw-sum ripples in cross-gap scans must be judged by grid convergence;
they are not evidence of a physical p/2 peak train. They disappear from the peak detector on N=1024.
The finite-pupil raw sums are predominantly smooth.
This finite-pupil test does not retain the ~2 center ratio produced by full-collection hole autocorrelation.
It demonstrates sensitivity of that mechanism to collection bandwidth, rather than proving the D4C cause.

NUMERICS
Masks use exact triangular/rectangular pixel area fractions; this avoids naive binary staircase jumps.
Carrier and Gaussian are evaluated at pixel centers, so convergence remains necessary.
The Fourier sampling interval is 1/80 cycles/um and is identical at N=512 and N=1024.
The N=1024 checks cover ideal and cross_gap1, which control the principal finite-pupil conclusion.
Across all tested pupils the ideal SUM curve changes by at most 0.126% of the fine central value;
the cross-gap SUM changes by at most 0.275%. Ratios of small differences are more sensitive:
e.g. the cross-gap wide-pupil D0/D1 changes .6595 -> .6333; narrow-pupil ratios change more.
Thus quote wide-pupil results at roughly two significant figures and do not claim exact convergence of every ratio.
The conclusion that these finite-pupil ratios remain far below two is stable at both grids.

FILES
parameters.json: all numerical and ROI settings.
scan_n*.csv: every scan and decomposition.
summary_n*.json: actual maxima, absolute drops, ratios, complementary-port identity errors.
peak_comparison.csv: compact table for all cases.
convergence.json: maximum curve differences and drop-ratio convergence (when N=1024 exists).
phase_coupling_spotcheck.json: N=1024 checks of same-arm X/Y overlap for phase_upper_pi.
pupil_effect_summary.png: focused summary, uses N=1024 when available.
optical_comparison_n512.png: all four geometries, with one common power scale.
cross_term_decomposition_n512.png: inter-arm versus same-arm contributions.

RUN
uv run --with numpy --with scipy --with matplotlib run_optical_coupling.py
uv run --with numpy --with scipy --with matplotlib run_optical_coupling.py --n 1024 --geometries ideal cross_gap1
uv run --with numpy --with matplotlib finish_report.py

CONVERGENCE VALUES
ideal disk_r020: R512=0.511946, R1024=0.512311; max SUM error/central=0.00056095
ideal disk_r010: R512=0.381009, R1024=0.381207; max SUM error/central=0.000455502
ideal disk_r005: R512=0.350100, R1024=0.350283; max SUM error/central=0.000382023
ideal disk_r010_y006: R512=0.377942, R1024=0.378137; max SUM error/central=0.000448838
ideal disk_r020_edge_y004: R512=0.687628, R1024=0.687478; max SUM error/central=0.00125892
cross_gap1 disk_r020: R512=0.659534, R1024=0.633346; max SUM error/central=0.00274718
cross_gap1 disk_r010: R512=0.415288, R1024=0.376369; max SUM error/central=0.0025828
cross_gap1 disk_r005: R512=0.405360, R1024=0.348889; max SUM error/central=0.00257893
cross_gap1 disk_r010_y006: R512=0.418070, R1024=0.377283; max SUM error/central=0.00270302
cross_gap1 disk_r020_edge_y004: R512=0.721656, R1024=0.718714; max SUM error/central=0.00158217
