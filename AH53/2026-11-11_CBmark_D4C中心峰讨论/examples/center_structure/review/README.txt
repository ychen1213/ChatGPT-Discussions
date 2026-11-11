【2026-11-11 对话后续更正】本文件保留历史计算用于追溯；中央排除带和局部偏振/小模式收集均缺乏用户实际 mark 与 D4C 光路依据，不是实际中心峰两倍关系的已验证原因。普通周期空槽已经包含在 RCWA 中，不应额外作为宏观排除窗口重复扣除。请先阅读本归档主题目录中的“2026-11-11_更正说明.md”。

Conditional center-structure and mode-selection example
=====================================================

This is an existence construction, NOT a D4C diagnosis, fit, or a prediction
from the user's RCWA R. No D4C data or user R is available here.

Assumptions
-----------
1. Main signal is one constructive SRI port for an isolated X +/-1 pair,
   not the raw complementary SUM+DIFF. Ideal Gaussian-illuminated CB wedges
   extend beyond the spot: w=12 um, p=2 um, h=1 um.
   I_main(s) = eta_main [q(s)+t(s)cos(2pi s)],
   q=(1-erf(s/w)^2)/2, t=erfc(|s|/w)^2/2.
2. A hypothetical center has an additional cross-polarized local Jones term
   delta_r(x,y)=delta exp[-(x^2+y^2)/d^2], d=0.3 um.
   Its shape is specified at the FIELD level. It is an unknown effective
   center response, not derived from a sum of X and Y 1D RCWA solutions.
3. The detector receives this orthogonal polarization in a normalized even
   Gaussian image-plane mode of radius a. Main and center powers therefore
   add. In the SRI this even mode has equal amplitude in the direct and
   rotated arms, so it exits the constructive port at zero relative phase.
   The example needs an actual collection channel with this property. It
   does not establish that D4C has such a channel.
4. eta_main is the main port's central DETECTED power / incident power.
   eta_main=0.001 in the positive example is deliberately weak collection.
   It cannot silently be replaced by typical reflectance or diffraction
   efficiency values. The corresponding simple local X reflection column
   has Fourier coefficients r_+=r_-=sqrt(eta_main), and its thin-Jones
   reconstruction is bounded pointwise by 2 sqrt(eta_main). A sufficient
   conservative column bound is 4 eta_main + delta^2 <= 1. This is a
   pointwise bound, not an inference from the sum of modal powers.

Analytic mode overlap
--------------------
Use normalized incident and receiver fields in 2D:
 A=(2/pi)^0.5/w exp[-(u^2+v^2)/w^2]
 psi=(2/pi)^0.5/a exp[-(u^2+v^2)/a^2].
At scan s the center Jones term is delta_r(u+s,v).

alpha = w^-2+a^-2+d^-2
b^2 = 1/(w^-2+a^-2)
c(s) = delta [2/(w a alpha)] exp[-s^2/(b^2+d^2)]
J_mode(s)=|c(s)|^2.

If all spatial modes of exactly the SAME center field are instead collected:
J_all(s)=delta^2 d^2/(w^2+d^2) exp[-2s^2/(w^2+d^2)].

At w=12,a=0.5,d=0.3:
 J_mode(1)/J_mode(0)=0.00276737,
 J_all(1)/J_all(0)=0.98621567.
Thus fixed wide illumination does not preclude a narrow scan response IF
collection selects a small image-plane mode. Geometry alone with full
collection produces a wide response.

Numerical results (ACTUAL local maxima, refined by scalar optimization)
---------------------------------------------------------------------
eta_main=0.001,delta=0.45:
 main only: R01=1.01162; P_n/eta=[1,.9064543,.8139833,.7240505,.6377926]
 small mode: R01=2.06654; P_n/eta=[1.0984443,.9067462,.8139833,.7240505,.6377926]
 all modes: R01=.97681; P_n/eta=[1.1264834,1.0312145,.9336837,.8357637,.7392121]
The small-mode decrement sequence is
 [.1916982,.0927628,.0899329,.0862579] times eta_main.
The last three have CV=2.97%.
The first side maximum is near s=0.994, not exactly s=1.

Efficiency limitation
--------------------
Fixed delta=0.45 and a=0.5:
 eta=.001 -> J0/eta=.098444, R01=2.06654
 eta=.01  -> J0/eta=.009844, R01=1.11741
 eta=.08  -> J0/eta=.001231, R01=1.02485
Required delta for R01=2 is .43553,1.37728,3.89553 respectively.
The last two exceed even unity and are not passive in this local model.
Using delta_max=sqrt(1-4eta), the maximum R is 1.51256 at eta=.01 and
1.05604 at eta=.08. These are sufficient-model bounds for this center
term and detection mode, not universal scattering bounds on other marks.
Therefore the positive example depends on a weak main detected channel;
it is not a generic prediction for strongly collected CB diffraction.

Complementary SUM+DIFF limitation
--------------------------------
The same hypothetical system has raw sum I_sum=2 eta_main q+J_mode.
It is monotonic for s>0 and contains NO periodic side peaks. The script
explicitly counts these. At integer nh the sampled decrement ratio can
be tuned, but those are NOT local maxima and later sampled decrements
have about 29% CV. This example cannot reproduce a comb of raw SUM+DIFF
peaks. Such peaks need a separately demonstrated carrier-producing term
in the actual forward chain (e.g. selected intra-arm order cross terms).

Files
-----
mode_selection_example.py : complete reproducible analytic/numeric model
mode_scan.csv             : receiver size and delta scan, true local maxima
efficiency_sweep.csv      : main-channel efficiency and passivity checks
raw_sum_samples_NOT_peaks.csv : raw complementary-sum falsification check
summary.json              : selected results and conditional matches
mode_selection.png        : actual traces, maxima, absolute decrements

Center-mask modeling rules
--------------------------
For gaps/joins, make region ownership disjoint. Use X-only, Y-only,
background/flat, and center regions. A physical X/Y overlap is a new
material structure; assigning F_X+F_Y to it double counts the material
response and is not a prediction of a crossed relief. Its center operator
must be supplied by a local calculation, calibration, or an explicitly
bounded effective assumption such as the delta_r used here.

Do not erase a gap's reflected field by default. If a flat region reflects,
use its r_flat. The final pupil may reject its specular term, but this must
be done in the optical propagation rather than by calling the gap zero.

For a top/bottom phase registry delta_top/delta_bottom, multiply the mth
RCWA coefficient by exp[-i m G delta_region]. At a p/2 relative shift,
odd orders change sign. It can make central interference destructive;
there is no universal positive center enhancement or factor of two.

To isolate structure-collection coupling with the same incident power:
 Delta_structure(P)=I(center,P)-I(reference,P).
 Compare this for full collection and the actual finite pupil/mode.
 A normalized interaction diagnostic is the difference of these deltas,
 but inspect raw unnormalized powers too; pupil loss must not be rescaled
 away independently for every mark setting.

