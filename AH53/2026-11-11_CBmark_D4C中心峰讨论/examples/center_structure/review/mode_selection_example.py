"""Conditional existence example, not a D4C model or fitted diagnosis.

Broad ideal CB constructive port + orthogonally detected central scatterer.
All lengths in um. The central scatterer is a bounded effective Jones term;
it is not computed by adding the RCWA fields of crossed X and Y gratings.
Run: uv run --with numpy --with scipy --with matplotlib mode_selection_example.py
"""
from pathlib import Path
import csv
import json
import numpy as np
from scipy.special import erf, erfc
from scipy.signal import find_peaks
from scipy.optimize import minimize_scalar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
W = 12.0
D = 0.3
ETA_MAIN = 0.001
P = 2.0

def main_port(s):
    s = np.asarray(s)
    q = 0.5 * (1-erf(s/W)**2)
    t = 0.5 * erfc(np.abs(s)/W)**2
    return ETA_MAIN * (q+t*np.cos(4*np.pi*s/P))

def defect_mode(s, a, delta):
    """Power after normalized 2D Gaussian-mode projection.

    incident A=(2/pi)^0.5/w exp[-r^2/w^2], normalized to unit power.
    mode psi=(2/pi)^0.5/a exp[-r^2/a^2], normalized likewise.
    Jones cross term delta*exp[-((u+s)^2+v^2)/d^2].
    Intensity is |<psi, delta_r A>|^2, not an arbitrary envelope.
    """
    alpha = W**-2 + a**-2 + D**-2
    b2 = 1/(W**-2 + a**-2)
    j0 = delta**2 * (2/(W*a*alpha))**2
    return j0*np.exp(-2*np.asarray(s)**2/(b2+D**2))

def defect_full_collection(s, delta):
    """All spatial modes of same central Jones perturbation collected."""
    return delta**2 * D**2/(W**2+D**2) * np.exp(-2*np.asarray(s)**2/(W**2+D**2))

def local_maxima(fun):
    grid = np.linspace(0, 4.6, 46001)
    vals = fun(grid)
    inds, _ = find_peaks(vals)
    xs = [0.0]
    ps = [float(fun(0.0))]
    for i in inds:
        result = minimize_scalar(lambda x: -float(fun(x)),
                                 bounds=(grid[i-1],grid[i+1]), method='bounded',
                                 options={'xatol':1e-13})
        xs.append(float(result.x)); ps.append(float(-result.fun))
    return np.asarray(xs[:5]), np.asarray(ps[:5])

def record(name, a, delta, fun):
    xs, ps = local_maxima(fun)
    ds = ps[:-1]-ps[1:]
    row = dict(case=name, a_um=a, delta=delta,
               center_extra_over_main=float((fun(0)-main_port(0))/ETA_MAIN),
               extra_at_1_over_0=None,
               R01=float(ds[0]/ds[1]),
               side_cv=float(np.std(ds[1:4])/np.mean(ds[1:4])),
               **{f's{n}':float(x) for n,x in enumerate(xs)},
               **{f'P{n}':float(x/ETA_MAIN) for n,x in enumerate(ps)},
               **{f'D{n}':float(x/ETA_MAIN) for n,x in enumerate(ds)})
    extra0=fun(0)-main_port(0)
    if extra0>0: row['extra_at_1_over_0']=float((fun(1)-main_port(1))/extra0)
    return row

def run():
    rows=[record('main only',None,0,main_port)]
    for a in (.4,.5,.7,1.,2.,4.):
        for delta in (.15,.25,.35,.45,.55,.65):
            rows.append(record('main + Gaussian receiver',a,delta,
                              lambda s,a=a,delta=delta:main_port(s)+defect_mode(s,a,delta)))
    for delta in (.25,.45,.65):
        rows.append(record('main + full collection',None,delta,
                            lambda s,delta=delta:main_port(s)+defect_full_collection(s,delta)))
    with (OUT/'mode_scan.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    selected=[rows[0]]+[r for r in rows if r['a_um']==.5 and r['delta'] in (.35,.45,.55)]
    selected += [r for r in rows if r['case']=='main + full collection' and r['delta']==.45]
    summary=dict(condition='hypothetical central cross-polarized scatterer and orthogonal power collection; no D4C data',
                 w_um=W,defect_d_um=D,main_center_power_fraction=ETA_MAIN,
                 field_amplitude_bounds='co-polarized reconstruction bounded by 2*sqrt(ETA_MAIN); sufficient pointwise bound 4*ETA_MAIN+delta^2<=1',
                 selected=selected,
                 matches=[r for r in rows if 1.8<r['R01']<2.2 and r['side_cv']<.1])
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    s=np.linspace(-4.3,4.3,17201)
    fig,ax=plt.subplots(1,3,figsize=(15,4.2))
    for label,fun in [('Main only',main_port),
                      ('Small mode a=0.5, delta=0.45',lambda x:main_port(x)+defect_mode(x,.5,.45)),
                      ('All modes, same defect',lambda x:main_port(x)+defect_full_collection(x,.45))]:
        ax[0].plot(s,fun(s)/ETA_MAIN,label=label,lw=1.2)
        xs,ps=local_maxima(fun);ax[1].plot(np.arange(len(ps)),ps/ETA_MAIN,'o-',label=label)
        ax[2].plot(np.arange(len(ps)-1),(ps[:-1]-ps[1:])/ETA_MAIN,'o-',label=label)
    ax[0].set(xlabel='Scan s (um)',ylabel='Power / main central peak',title='Actual modulated traces')
    ax[1].set(xlabel='Local peak number',ylabel='Actual local maximum / main center',title='Peak heights')
    ax[2].set(xlabel='Decrement number n',ylabel='D_n / main center',title='Absolute height decrements')
    for a in ax:a.grid(alpha=.25)
    ax[0].legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'mode_selection.png',dpi=180)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

    efficiency_rows=[]
    coefficient=(2/(W*.5*(W**-2+.5**-2+D**-2)))**2
    for eta in (.001,.01,.08):
        delta_bound=np.sqrt(1-4*eta)
        def base(s): return main_port(s)*eta/ETA_MAIN
        def ratio_at(delta):
            fun=lambda s:base(s)+defect_mode(s,.5,delta)
            xs,ps=local_maxima(fun);ds=ps[:-1]-ps[1:]
            return float(ds[0]/ds[1]),xs,ps,ds
        from scipy.optimize import brentq
        delta_for_r2=brentq(lambda delta:ratio_at(delta)[0]-2,0,5)
        for delta_label,delta in [('fixed 0.45',.45),('passive upper bound',delta_bound)]:
            ratio,xs,ps,ds=ratio_at(delta)
            efficiency_rows.append(dict(eta_main=eta,delta_label=delta_label,delta=float(delta),
                maximum_delta=float(delta_bound),
                J0_over_main=float(coefficient*delta**2/eta),R01=ratio,
                delta_required_for_R2=float(delta_for_r2),
                R2_feasible_under_this_passivity_bound=bool(delta_for_r2<=delta_bound),
                **{f'P{n}':float(x/eta) for n,x in enumerate(ps)},
                **{f'D{n}':float(x/eta) for n,x in enumerate(ds)}))
    with (OUT/'efficiency_sweep.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(efficiency_rows[0]));writer.writeheader();writer.writerows(efficiency_rows)
    print('Efficiency sweep:')
    print(json.dumps(efficiency_rows,indent=2))

    # Raw complementary sum: t cancels. There is no periodic carrier and no
    # sequence of actual local maxima. Values at nh are only samples.
    sum_rows=[]
    grid=np.linspace(0,4.6,46001)
    def sum_main(s): return ETA_MAIN*(1-erf(np.asarray(s)/W)**2)
    for delta in (0,.25,.35,.45):
        fun=lambda s:sum_main(s)+defect_mode(s,.5,delta)
        vals=fun(np.arange(5));diffs=vals[:-1]-vals[1:]
        peaks,_=find_peaks(fun(grid))
        sum_rows.append(dict(delta=delta,positive_side_local_peak_count=int(len(peaks)),
                             sampled_R01=float(diffs[0]/diffs[1]),
                             sampled_side_cv=float(np.std(diffs[1:4])/np.mean(diffs[1:4])),
                             **{f'sample{n}':float(v/ETA_MAIN) for n,v in enumerate(vals)},
                             **{f'sampled_D{n}':float(v/ETA_MAIN) for n,v in enumerate(diffs)}))
    with (OUT/'raw_sum_samples_NOT_peaks.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(sum_rows[0]));writer.writeheader();writer.writerows(sum_rows)
    print('Raw complementary sum (samples, not local maxima):')
    print(json.dumps(sum_rows,indent=2))

if __name__=='__main__':run()
