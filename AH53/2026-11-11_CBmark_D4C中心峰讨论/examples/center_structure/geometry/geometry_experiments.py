"""Synthetic CB X-order-channel geometry experiments, not D4C/RCWA data.

Run: uv run --with numpy --with scipy --with matplotlib geometry_experiments.py
No spatial raster enters signal quadrature. Piecewise Gauss-Legendre integration
and analytic Gaussian y integrals preserve exact binary mask boundaries.
"""
from pathlib import Path
import csv
import json
import numpy as np
from scipy.special import erf
from scipy.signal import find_peaks
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize_scalar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

OUT = Path(__file__).resolve().parent
L, W, P, R = 40., 12., 2., .2
G = 2*np.pi/P
S = np.linspace(0, 5, 501)
CASES = [
    dict(id='ideal', kind='ideal', width=0., dt=0., db=0., label='Ideal CB'),
    dict(id='xstrip_0p5', kind='xstrip', width=.5, dt=0., db=0., label='X bridge c=0.5 um'),
    dict(id='xstrip_1', kind='xstrip', width=1., dt=0., db=0., label='X bridge c=1 um'),
    dict(id='crossblank_0p5', kind='crossblank', width=.5, dt=0., db=0., label='Cross blank g=0.5 um'),
    dict(id='crossblank_1', kind='crossblank', width=1., dt=0., db=0., label='Cross blank g=1 um'),
    dict(id='squareblank_1', kind='squareblank', width=1., dt=0., db=0., label='Square blank g=1 um'),
    dict(id='squareblank_2', kind='squareblank', width=2., dt=0., db=0., label='Square blank g=2 um'),
    dict(id='registry_p4', kind='ideal', width=0., dt=0., db=.5, label='Registry: top=0, bottom=p/4'),
    dict(id='registry_p2', kind='ideal', width=0., dt=0., db=1., label='Registry: top=0, bottom=p/2'),
    dict(id='registry_p4_centered', kind='ideal', width=0., dt=-.25, db=.25, label='Registry: top=-p/8, bottom=p/8'),
]


def lower_y(x, case):
    """For this family X exists at abs(y) in [a(x), L/2]."""
    a = np.abs(x).copy()
    valid = a <= L/2
    z = case['width']/2
    if case['kind'] == 'xstrip':
        a = np.where(a < z, 0., a)
    elif case['kind'] == 'crossblank':
        valid &= a >= z
        a = np.maximum(a, z)
    elif case['kind'] == 'squareblank':
        a = np.where(a < z, np.maximum(a, z), a)
    return a, valid


def y_mass(a, valid):
    return np.where(valid, erf(np.sqrt(2)*L/(2*W))-erf(np.sqrt(2)*a/W), 0.)


def signal_one(s, case, order=96):
    # Every macro-mask discontinuity in x is an explicit quadrature boundary.
    # Additional u=0 splits the crossover max(abs(u+s),abs(s-u)).
    cuts = {-L/2-s, L/2+s, 0.}
    for b in (-L/2, -case['width']/2, 0., case['width']/2, L/2):
        cuts.update((b-s, s-b))
    cuts = sorted(cuts)
    nodes, weights = LEGENDRE[order]
    u = np.concatenate([(hi-lo)/2*nodes+(hi+lo)/2 for lo,hi in zip(cuts[:-1], cuts[1:]) if hi>lo])
    wt = np.concatenate([(hi-lo)/2*weights for lo,hi in zip(cuts[:-1], cuts[1:]) if hi>lo])
    wt *= np.sqrt(2/np.pi)/W*np.exp(-2*u*u/W**2)
    xa, xb = u+s, s-u
    aa, va = lower_y(xa, case)
    ab, vb = lower_y(xb, case)
    ma, mb = y_mass(aa, va), y_mass(ab, vb)
    mab = y_mass(np.maximum(aa,ab), va & vb)
    dt, db = case['dt'], case['db']
    cat, cab = np.cos(G*(xa-dt)), np.cos(G*(xa-db))
    # At positive detector y, rotated arm sees bottom mark half.
    cbt, cbb = np.cos(G*(xb-db)), np.cos(G*(xb-dt))
    pa = (2*R)**2*np.dot(wt, ma*(cat*cat+cab*cab)/2)
    pb = (2*R)**2*np.dot(wt, mb*(cbt*cbt+cbb*cbb)/2)
    cross = (2*R)**2*np.dot(wt, mab*(cat*cbt+cab*cbb)/2)
    q, t = np.dot(wt,ma), np.dot(wt,mab)
    return np.array([q,t,pa,pb,cross,(pa+pb)/2+cross,(pa+pb)/2-cross,pa+pb])


LEGENDRE = {n: np.polynomial.legendre.leggauss(n) for n in (96,192)}
COLS = ['q','t','power_arm_a','power_arm_b','interarm_cross','plus','minus','plus_minus_sum']


def actual_peaks(s, values):
    candidates = list(find_peaks(values)[0])
    if values[0] >= values[1]:
        candidates = [0]+candidates
    spline = CubicSpline(s,values)
    peaks=[]
    for idx in candidates:
        if idx==0:
            pos=0.
        else:
            res=minimize_scalar(lambda x:-float(spline(x)), bounds=(s[idx-1],s[idx+1]),method='bounded', options={'xatol':1e-11})
            pos=float(res.x)
        peaks.append((pos,float(spline(pos))))
    return peaks


def metrics(values):
    v=np.asarray(values)
    d=np.diff(-v)
    return dict(heights=v.tolist(), drops=d.tolist(), R01=float(d[0]/d[1]) if len(d)>1 and abs(d[1])>1e-13 else None,
                side_cv=float(np.std(d[1:4])/np.mean(d[1:4])) if len(d)>=4 and np.all(d[1:4]>1e-13) else None)


def mask_map(x,y,case):
    inside=(np.abs(x)<=L/2)&(np.abs(y)<=L/2)
    a,valid=lower_y(x,case)
    mx=inside&valid&(np.abs(y)>=a)
    my=inside & ~mx
    z=case['width']/2
    if case['kind']=='crossblank':
        blank=(np.abs(x)<z)|(np.abs(y)<z)
        my &= ~blank
    elif case['kind']=='squareblank':
        blank=(np.abs(x)<z)&(np.abs(y)<z)
        my &= ~blank
    return np.where(mx,1,np.where(my,2,0))


def hole_addback(s, gap, order=96):
    """Exact positive H_A H_B addback to cross term for X central blank strip.

    For s>=gap/2 the two displaced holes have disjoint support, giving zero.
    Return geometric t addback and physical cross-field addback in plus port.
    The latter enters minus port with opposite sign and cancels in their sum.
    """
    upper=gap/2-abs(s)
    if upper<=0:
        return np.array([0.,0.])
    nodes,weights=LEGENDRE[order]
    u=np.r_[upper/2*(nodes-1),upper/2*(nodes+1)]
    wt=np.r_[upper/2*weights,upper/2*weights]
    wt*=np.sqrt(2/np.pi)/W*np.exp(-2*u*u/W**2)
    m=y_mass(np.abs(u)+abs(s),np.ones(u.shape,dtype=bool))
    geometric=float(np.dot(wt,m))
    physical=float((2*R)**2*np.dot(wt,m*np.cos(G*(u+s))*np.cos(G*(s-u))))
    return np.array([geometric,physical])


def main():
    arrays={}
    rows=[]
    summary=[]
    maxima_rows=[]
    for case in CASES:
        data=np.array([signal_one(float(s),case) for s in S])
        arrays[case['id']]=data
        for s, vals in zip(S,data):
            rows.append(dict(case=case['id'],s_um=float(s),**dict(zip(COLS,map(float,vals)))))
        peaks=actual_peaks(S,data[:,5])
        for i,(pos,power) in enumerate(peaks):
            maxima_rows.append(dict(case=case['id'],peak_index=i,s_um=pos,power=power))
        nh=data[::100,5]
        peakvals=[v for pos,v in peaks[:5]]
        # Reference common normalization: ideal central plus power, no per-case scaling.
        summary.append(dict(**case, actual_plus_peak_positions_um=[p for p,v in peaks],
                            actual_plus_peaks=metrics(peakvals), integer_s_plus=metrics(nh),
                            center_plus=float(data[0,5]),center_sum=float(data[0,7]),
                            center_q=float(data[0,0]),center_t=float(data[0,1]),
                            complement_max_error=float(np.max(np.abs(data[:,5]+data[:,6]-data[:,7]))),
                            nonnegative_min=float(np.min(data[:,5:8]))))
    for filename,entries in [('scans.csv',rows),('actual_plus_peaks.csv',maxima_rows)]:
        with (OUT/filename).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(entries[0]))
            writer.writeheader();writer.writerows(entries)
    # Independent denser quadrature, same exact geometry, no discretization change.
    checks=[]
    for case in CASES:
        a=np.array([signal_one(float(s),case,96) for s in np.linspace(0,5,21)])
        b=np.array([signal_one(float(s),case,192) for s in np.linspace(0,5,21)])
        checks.append(dict(case=case['id'],max_abs_96_vs_192=float(np.max(np.abs(a-b)))))
    result=dict(description='Synthetic scalar X-order channel; not fitted D4C or actual RCWA data',
                parameters=dict(L_um=L,w_intensity_1e2_radius_um=W,p_um=P,r_plus1=R,r_minus1=R,r0=0.,scan_step_um=float(S[1]-S[0])),
                model='E_s(u,v)=A(u,v) M_X(u+s,v) r [exp(i G (u+s-delta(v)))+exp(-i G (u+s-delta(v)))]; rotated E_s(-u,-v). Iplus/minus=0.5 integral|E_s +/- E_s_rotated|^2.',
                blank_definition='Blank suppresses modelled diffracted +/-1 X and Y coefficients. It does not mean total reflectivity is zero.',
                normalization='Absolute synthetic dimensionless powers retained; all plot normalized to ideal central plus power.',
                quadrature='Analytic Gaussian y mass plus piecewise 96-point Gauss-Legendre x quadrature. Exact step boundaries; no raster used for signals.',
                quadrature_checks=checks,cases=summary)
    addback_rows=[]
    addback_summary=[]
    for case in [CASES[3],CASES[4]]:
        ab=np.array([hole_addback(float(s),case['width']) for s in S])
        data=arrays[case['id']]
        broad=data[:,5]-ab[:,1]
        ideal=arrays['ideal']
        for s,vals,a,b in zip(S,data,ab,broad):
            addback_rows.append(dict(case=case['id'],s_um=float(s),t_total=float(vals[1]),t_hole_intersection=float(a[0]),t_without_intersection=float(vals[1]-a[0]),plus_total=float(vals[5]),plus_hole_intersection=float(a[1]),plus_without_intersection=float(b),sum_hole_intersection=0.,t_delta_from_ideal=float(vals[1]-ideal[np.argmin(abs(S-s)),1])))
        nh=data[::100,5];nha=ab[::100,1]
        addback_summary.append(dict(case=case['id'],hole_intersection_support_abs_s_less_than_um=case['width']/2,
                                   t_hole_intersection_at_center=float(ab[0,0]),plus_hole_intersection_at_center=float(ab[0,1]),
                                   fraction_of_central_peak=float(ab[0,1]/data[0,5]),
                                   integer_peaks_with_addback=metrics(nh),integer_peaks_without_addback=metrics(nh-nha),
                                   actual_peaks_without_addback=actual_peaks(S,broad)))
    result['causal_hole_intersection_decomposition']=addback_summary
    with (OUT/'hole_overlap_decomposition.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(addback_rows[0]));writer.writeheader();writer.writerows(addback_rows)
    (OUT/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    np.savez_compressed(OUT/'arrays.npz',s=S,**arrays)
    make_plots(arrays)
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    norm=arrays['ideal'][0,5]
    for k,case in enumerate([CASES[3],CASES[4]]):
        ab=np.array([hole_addback(float(s),case['width']) for s in S])
        data=arrays[case['id']]
        axes[0,k].plot(S,data[:,5]/norm,label='Physical plus port')
        axes[0,k].plot(S,(data[:,5]-ab[:,1])/norm,'--',label='Cross-term hole addback removed')
        axes[0,k].plot(S,ab[:,1]/norm,label='Hole-intersection contribution')
        axes[0,k].set(title=case['label'],xlabel='Scan s (um)',ylabel='Power / ideal center plus')
        axes[0,k].legend(fontsize=8);axes[0,k].grid(alpha=.2)
        axes[1,k].plot(S,ab[:,0],label='Geometric t addback')
        axes[1,k].plot(S,ab[:,1]/(2*R)**2,label='Field cross addback / (2r)^2')
        axes[1,k].axvline(case['width']/2,color='k',ls=':',label='Hole intersections end')
        axes[1,k].set(xlim=(0,1.2),xlabel='Scan s (um)',ylabel='Gaussian-weighted contribution')
        axes[1,k].legend(fontsize=8);axes[1,k].grid(alpha=.2)
    fig.suptitle('Causal decomposition: (1-H_A)(1-H_B)=1-H_A-H_B+H_A H_B; SUM contribution cancels')
    fig.savefig(OUT/'hole_overlap_decomposition.png',dpi=180);plt.close(fig)
    print(json.dumps(dict(quadrature_max_error=max(x['max_abs_96_vs_192'] for x in checks),cases=[dict(case=r['id'],peak_s=r['actual_plus_peak_positions_um'][:5],actual_R01=r['actual_plus_peaks']['R01'],integer_R01=r['integer_s_plus']['R01'],center_plus=r['center_plus'],center_sum=r['center_sum']) for r in summary]),indent=2))


def make_plots(arrays):
    plt.rcParams.update({'font.size':10,'figure.dpi':150})
    cmap=ListedColormap(['#f6f6f6','#238ac7','#ee9847'])
    chosen=[CASES[i] for i in (0,2,4,6,7,8)]
    fig,axes=plt.subplots(2,3,figsize=(12,8),constrained_layout=True)
    z=np.linspace(-3,3,1001)
    xx,yy=np.meshgrid(z,z)
    for ax,case in zip(axes.flat,chosen):
        ax.imshow(mask_map(xx,yy,case),extent=(-3,3,-3,3),origin='lower',cmap=cmap,vmin=0,vmax=2,interpolation='nearest')
        # Show physical line ridges with p=2, duty=50%. Visualization only.
        mx=mask_map(xx,yy,case)==1
        phase=np.where(yy>=0,case['dt'],case['db'])
        gx=(np.cos(G*(xx-phase))>=0)&mx
        gy=(np.cos(G*yy)>=0)&(mask_map(xx,yy,case)==2)
        ax.contourf(xx,yy,np.where(gx|gy,1.,np.nan),levels=[.5,1.5],colors=['#182d3b'],alpha=.75)
        ax.set(title=case['label'],xlabel='Mark x (um)',ylabel='Mark y (um)',aspect='equal')
    fig.suptitle('Center geometry, p=2 um, duty=50% (schematic ridges); blue=X, orange=Y, white=blank',fontsize=12)
    fig.savefig(OUT/'center_geometry.png',dpi=180);plt.close(fig)
    norm=arrays['ideal'][0,5]
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    colors=plt.cm.tab10(np.linspace(0,1,10))
    for i,case in enumerate(CASES[:7]):
        vals=arrays[case['id']]
        axes[0,0].plot(S,vals[:,0]/arrays['ideal'][0,0],label=case['label'],color=colors[i])
        axes[0,1].plot(S,vals[:,1]/arrays['ideal'][0,1],label=case['label'],color=colors[i])
        axes[1,0].plot(S,vals[:,5]/norm,label=case['label'],color=colors[i])
        axes[1,1].plot(S,(vals[:,5]-arrays['ideal'][:,5])/norm,label=case['label'],color=colors[i])
    for ax,title in zip(axes.flat,['Single-mask illuminated fraction q','Rotated-mask overlap t','Full-collection plus-port scan','Change from ideal plus-port scan']):
        ax.set(title=title,xlabel='Scan s (um)',ylabel='Common reference normalization');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Geometry alone: L=40 um, w=12 um, r(+/-1)=0.2, r0=0; no pupil filtering')
    fig.savefig(OUT/'geometry_scans.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for case in [CASES[i] for i in (0,7,8,9)]:
        vals=arrays[case['id']]
        axes[0,0].plot(S,vals[:,5]/norm,label=case['label'])
        axes[0,1].plot(S,vals[:,6]/norm,label=case['label'])
        axes[1,0].plot(S,vals[:,7]/norm,label=case['label'])
        peaks=actual_peaks(S,vals[:,5]);xs=[p for p,v in peaks[:5]];ys=[v/norm for p,v in peaks[:5]]
        axes[1,1].plot(xs,ys,'o-',label=case['label'])
    for ax,title in zip(axes.flat,['Plus port','Minus port','Complementary SUM=plus+minus','Actual local maxima of plus port']):
        ax.set(title=title,xlabel='Scan s (um)',ylabel='Power / ideal center plus');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Changing upper/lower X-grating registry also changes carrier phase')
    fig.savefig(OUT/'registry_scans.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    main()
