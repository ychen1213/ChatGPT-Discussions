"""Read saved scans, report convergence, and draw a compact fixed-pupil comparison."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
GEOMS=['ideal','cross_gap1','square_gap2','phase_upper_pi']
PUPS=['disk_r020','disk_r010','disk_r005','disk_r010_y006','disk_r020_edge_y004']

def main():
    d512=json.loads((OUT/'summary_n512.json').read_text())
    p1024=OUT/'summary_n1024.json'
    d1024=json.loads(p1024.read_text()) if p1024.exists() else {}
    convergence={}
    if d1024:
        for geom in d1024:
            convergence[geom]={}
            for pupil in PUPS:
                a=np.genfromtxt(OUT/f'scan_n512_{geom}_{pupil}.csv',delimiter=',',names=True)
                b=np.genfromtxt(OUT/f'scan_n1024_{geom}_{pupil}.csv',delimiter=',',names=True)
                fixed_scale=b['port_sum'][0]
                convergence[geom][pupil]={
                    'max_curve_error_over_fine_central_sum':{
                        key:float(np.max(abs(a[key]-b[key]))/fixed_scale)
                        for key in ['port_sum','port_diff','raw_sum','cross_arm_real','same_arm_xy_a']},
                    'R0_n512':d512[geom][pupil]['port_sum']['successive_drop_ratios'][0],
                    'R0_n1024':d1024[geom][pupil]['port_sum']['successive_drop_ratios'][0],
                    'central_sum_n512':float(a['port_sum'][0]),
                    'central_sum_n1024':float(b['port_sum'][0]),
                }
        (OUT/'convergence.json').write_text(json.dumps(convergence,indent=2),encoding='utf-8')
    with (OUT/'peak_comparison.csv').open('w',newline='') as f:
        cw=csv.writer(f)
        cw.writerow(['N','geometry','pupil','central_is_SUM_max','central_SUM','central_raw_SUM_PLUS_DIFF',
                     'first_peak_s_um','second_peak_s_um','third_peak_s_um','P0','P1','P2','P3','D0_D1',
                     'max_same_arm_XY_fraction_of_raw','complement_error'])
        for n,dd in [(512,d512),(1024,d1024)]:
            for geom,pg in dd.items():
                for pupil,x in pg.items():
                    m=x['port_sum'];c=x['checks']
                    cw.writerow([n,geom,pupil,m['has_central_maximum'],c['central_port_sum'],c['central_raw_sum'],
                        *m['peak_positions_um'][:3],*m['peak_heights'][:4],m['successive_drop_ratios'][0],
                        c['max_same_arm_xy_fraction_of_raw'],c['max_complement_error']])
    fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
    dd=d1024 if d1024 else d512
    n=1024 if d1024 else 512
    for geom in ['ideal','cross_gap1']:
        pp=np.arange(len(PUPS))
        rr=[dd[geom][p]['port_sum']['successive_drop_ratios'][0] for p in PUPS]
        axes[0].plot(pp,rr,'o-',label=geom)
    axes[0].axhline(2,c='black',ls='--',label='observed target ~2')
    axes[0].set_xticks(np.arange(len(PUPS)),['r .20','r .10','r .05','r .10\ny +.06','r .20\ny >=.04'])
    axes[0].set(ylabel='Actual peak drop ratio D0 / D1',title=f'Pupil effect, N={n}')
    for geom in ['ideal','cross_gap1']:
        a=np.genfromtxt(OUT/f'scan_n{n}_{geom}_disk_r020.csv',delimiter=',',names=True)
        axes[1].plot(a['s_um'],a['port_sum'],label=geom+' SUM')
        axes[2].plot(a['s_um'],a['raw_sum'],label=geom+' SUM+DIFF')
    axes[1].set(xlabel='s (um)',ylabel='Power / incident power',title='Fixed wide ROI: individual SUM port')
    axes[2].set(xlabel='s (um)',ylabel='Power / incident power',title='Matched complementary ports added')
    for ax in axes:ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle('Controlled finite-pupil calculation, not a D4C fit; r+/-1=.2, p=2 um, L=40 um, w=12 um')
    fig.savefig(OUT/'pupil_effect_summary.png',dpi=180);plt.close(fig)
    lines=[
        'CONTROLLED FINITE-CB STRUCTURE AND OPTICAL COLLECTION TEST',
        '',
        'This is a synthetic scalar optical model, NOT a fit to D4C or an actual RCWA export.',
        'All lengths are micrometres; FFT frequencies are cycles per micrometre.',
        'Incident Gaussian power is one. r+1=r-1=.2 are FIELD amplitudes, not 20% powers.',
        'Each isolated infinite grating order would have 4% power in this scalar convention.',
        'There is no renormalization between geometries, pupils, or scan positions.',
        '',
        'GEOMETRIES',
        'ideal: square |x|,|y|<=20; X region |y|>=|x|, Y is its complement.',
        'cross_gap1: remove periodic diffracted fields where |x|<.5 OR |y|<.5.',
        'square_gap2: remove periodic diffracted fields where |x|<1 AND |y|<1.',
        'phase_upper_pi: upper X region multiplies BOTH +/-1 amplitudes by -1; lower X and Y unchanged.',
        'This upper-X phase corresponds to a p/2=1 um line-origin shift for the retained +/-1 orders.',
        'A gap means r+/-1=0 there. It does NOT assert zero physical total reflectivity of a blank surface.',
        '',
        'OPTICAL MODEL',
        'E=A(u,v)[mX(u+s,v)*2r*cos(2pi(u+s)/p)+mY(u+s,v)*2r*cos(2pi v/p)].',
        'FFT is unitary. F_B(k)=F_A(-k), without complex conjugation.',
        'Every fixed detector ROI is intersected with physical NA/wavelength = .45/.633.',
        'Five ROIs: +X-order disks radius .20, .10, .05; disk .10 shifted ky +.06; disk .20 clipped ky>=.04.',
        'SUM=.5 integral|F_A+F_B|^2; DIFF=.5 integral|F_A-F_B|^2.',
        'Raw SUM+DIFF=Q_A+Q_B: the inter-arm interference cancels exactly.',
        'Same-arm X/Y cross terms can survive in that raw sum if their diffracted fields overlap inside the ROI.',
        '',
        'EXPORTED COLUMNS',
        'power_a,power_b: collected one-arm coherent powers.',
        'same_arm_xy_a,b: coherent X+Y power minus separately summed X and Y powers.',
        'cross_arm_real: Re integral F_A*conj(F_B). It enters SUM/DIFF with opposite signs.',
        'port_sum,port_diff,raw_sum,incoherent_raw_sum: unnormalized powers.',
        '',
        'PEAKS AND LIMITS',
        'Scan is 0..5 with .02 um step. True local maxima are found then refined by a local quadratic.',
        'Peak sampling is not forced to s=n um. No right scan endpoint is called a peak.',
        'phase_upper_pi has a central SUM dip, so its successive-peak ratio is NOT a center-to-side ratio.',
        'Small high-frequency raw-sum ripples in cross-gap scans must be judged by grid convergence;',
        'they are not evidence of a physical p/2 peak train. They disappear from the peak detector on N=1024.',
        'The finite-pupil raw sums are predominantly smooth.',
        'This finite-pupil test does not retain the ~2 center ratio produced by full-collection hole autocorrelation.',
        'It demonstrates sensitivity of that mechanism to collection bandwidth, rather than proving the D4C cause.',
        '',
        'NUMERICS',
        'Masks use exact triangular/rectangular pixel area fractions; this avoids naive binary staircase jumps.',
        'Carrier and Gaussian are evaluated at pixel centers, so convergence remains necessary.',
        'The Fourier sampling interval is 1/80 cycles/um and is identical at N=512 and N=1024.',
        'The N=1024 checks cover ideal and cross_gap1, which control the principal finite-pupil conclusion.',
        'Across all tested pupils the ideal SUM curve changes by at most 0.126% of the fine central value;',
        'the cross-gap SUM changes by at most 0.275%. Ratios of small differences are more sensitive:',
        'e.g. the cross-gap wide-pupil D0/D1 changes .6595 -> .6333; narrow-pupil ratios change more.',
        'Thus quote wide-pupil results at roughly two significant figures and do not claim exact convergence of every ratio.',
        'The conclusion that these finite-pupil ratios remain far below two is stable at both grids.',
        '',
        'FILES',
        'parameters.json: all numerical and ROI settings.',
        'scan_n*.csv: every scan and decomposition.',
        'summary_n*.json: actual maxima, absolute drops, ratios, complementary-port identity errors.',
        'peak_comparison.csv: compact table for all cases.',
        'convergence.json: maximum curve differences and drop-ratio convergence (when N=1024 exists).',
        'phase_coupling_spotcheck.json: N=1024 checks of same-arm X/Y overlap for phase_upper_pi.',
        'pupil_effect_summary.png: focused summary, uses N=1024 when available.',
        'optical_comparison_n512.png: all four geometries, with one common power scale.',
        'cross_term_decomposition_n512.png: inter-arm versus same-arm contributions.',
        '',
        'RUN',
        'uv run --with numpy --with scipy --with matplotlib run_optical_coupling.py',
        'uv run --with numpy --with scipy --with matplotlib run_optical_coupling.py --n 1024 --geometries ideal cross_gap1',
        'uv run --with numpy --with matplotlib finish_report.py',
    ]
    if convergence:
        lines+=['','CONVERGENCE VALUES']
        for geom,pp in convergence.items():
            for pupil,v in pp.items():lines.append(f'{geom} {pupil}: R512={v["R0_n512"]:.6f}, R1024={v["R0_n1024"]:.6f}; max SUM error/central={v["max_curve_error_over_fine_central_sum"]["port_sum"]:.6g}')
    (OUT/'README.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(convergence,indent=2))

if __name__=='__main__':main()
