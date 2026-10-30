"""1D alignment-mark scan: distinguish moving the MARK from moving the entire FIELD.

Self-contained post-processing illustration (not a Maxwell solver).
Requires numpy and matplotlib. Run: python fft_mark_scan_comparison.py

Definitions:
 g(x) = exp(-(x/w)**2), w=19 um (assumed 1/e^2 INTENSITY radius)
 r(x) = cos(2*pi*x/p), p=3.2 um (idealised +/-1-only grating)
 real scan, infinite grating: g(x)*r(x-s)
 incorrect rigid-field translation: g(x-s)*r(x-s)
 real scan, finite grating: g(x)*rect((x-s)/L)*r(x-s)

Detector proxy: +kx paired with -kx after matched pupil relay:
 C(s)=sum_{k>0} A_s(+k)*conj(A_s(-k))*dk;
 modulation=2*Re(C). This assumes coherent mode matching and ignores
 polarization/other optical phases; replace pupil and weights as appropriate.
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Register a CJK font for the Chinese axis and legend labels.
cjk_font = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if Path(cjk_font).is_file():
    fm.fontManager.addfont(cjk_font)
    plt.rcParams['font.family'] = fm.FontProperties(fname=cjk_font).get_name()
plt.rcParams['axes.unicode_minus'] = False

p = 3.2  # um
K = 2*np.pi/p
w = 19.0  # um
N_periods = 9
Lmark = N_periods*p
lambda_um = 0.643
NA = 0.6
kcut = 2*np.pi/lambda_um * NA
Lbox=256.0
dx=0.04
x=np.arange(-Lbox/2,Lbox/2,dx)
N=x.size
k = 2*np.pi*np.fft.fftshift(np.fft.fftfreq(N, d=dx))
# Additional +/-1 band selection, after the 0th-order stop and NA cutoff.
plus = np.where((k>0.2) & (k<kcut) & (abs(k-K)<0.4))[0]
minus=N-plus
assert np.allclose(k[plus], -k[minus])
dk=2*np.pi/Lbox
g=np.exp(-(x/w)**2)
s_positions=np.linspace(-24,24,481)

def compute_C(e):
    spectrum=dx*np.fft.fftshift(np.fft.fft(np.fft.ifftshift(e)))
    return np.sum(spectrum[plus]*np.conj(spectrum[minus]))*dk

cases = {'ideal':[], 'wrong':[], 'finite':[]}
for s in s_positions:
    cases['ideal'].append(compute_C(g*np.cos(K*(x-s))))
    cases['wrong'].append(compute_C(np.exp(-((x-s)/w)**2)*np.cos(K*(x-s))))
    window=(abs(x-s)<=Lmark/2).astype(float)
    cases['finite'].append(compute_C(g*window*np.cos(K*(x-s))))
cases={key:np.asarray(val) for key,val in cases.items()}
zero=np.argmin(abs(s_positions))

fig, ax = plt.subplots(figsize=(11.2,6.3), dpi=180)
for key, label in [
    ('ideal','正确：无限周期 Mark 移动，光斑固定'),
    ('wrong','错误：整个高斯出射场一起平移'),
    ('finite','正确：有限 9 周期 Mark 移动，光斑固定')]:
    ax.plot(s_positions, np.real(cases[key])/np.real(cases[key][zero]),
            linewidth=1.8 if key != 'finite' else 1.45,label=label)
ax.set(xlim=(-12,12),ylim=(-1.15,1.15),xlabel='Mark 位移 s (μm)',
       ylabel='干涉调制项 2 Re[C(s)] / 2 Re[C(0)]')
ax.grid(alpha=0.2)
ax.legend(fontsize=9, ncol=1, loc='lower left', framealpha=0.9)
ax.set_title('同一 ±1 级角谱干涉：平移 Mark ≠ 平移整个出射场')
fig.tight_layout()
fig.savefig(Path(__file__).with_name('fft_mark_scan_signals.png'),bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(11.2,6.3),dpi=180)
for key,label in [
    ('ideal','无限周期 Mark + 固定高斯照明'),
    ('wrong','整体平移高斯出射场'),
    ('finite','有限 9 周期 Mark + 固定高斯照明')]:
    ax.plot(s_positions, abs(cases[key])/abs(cases[key][zero]),linewidth=2,label=label)
ax.set(xlim=(-24,24),ylim=(0,1.12),xlabel='Mark 位移 s (μm)',
       ylabel='复干涉项幅值 |C(s)| / |C(0)|')
ax.grid(alpha=0.2)
ax.legend(fontsize=9, loc='upper right',framealpha=0.9)
ax.set_title('包络并非唯一的高斯：有限尺寸和 ±k 配对方式也会改变包络')
fig.tight_layout()
fig.savefig(Path(__file__).with_name('fft_mark_scan_envelopes.png'),bbox_inches='tight')
plt.close(fig)

# Validate expected analytic results in the ideal single-order limit.
expected_ideal = np.cos(2*K*s_positions)
expected_wrong = np.exp(-2*(s_positions/w)**2)*np.cos(2*K*s_positions)
assert np.max(abs(np.real(cases['ideal'])/np.real(cases['ideal'][zero]) - expected_ideal)) < 1e-7
assert np.max(abs(np.real(cases['wrong'])/np.real(cases['wrong'][zero]) - expected_wrong)) < 1e-7
print('PASS: ideal model = cos(2K s); rigid-field model = exp[-2(s/w)^2] cos(2K s).')
print('Finite-mark data is obtained from FFT for each scan point (no FDTD resimulation).')
