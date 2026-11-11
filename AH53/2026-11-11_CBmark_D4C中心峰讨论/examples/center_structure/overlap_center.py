"""Explicit three-region CB model; central cross-grating coefficients assumed.

Run: uv run --with numpy --with scipy --with matplotlib overlap_center.py
This is a controlled scalar postprocessing experiment, not D4C or local RCWA.
"""
from pathlib import Path
import csv
import json
import numpy as np
from scipy.signal import find_peaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent / "overlap"
L, W, P, DOMAIN, R = 40., 12., 2., 80., .2
S = np.linspace(0, 5, 101)


def square_fraction(x, y, width, dx):
    fx = np.clip(np.minimum(x+dx/2, width/2)-np.maximum(x-dx/2, -width/2), 0, dx)/dx
    fy = np.clip(np.minimum(y+dx/2, width/2)-np.maximum(y-dx/2, -width/2), 0, dx)/dx
    return fx*fy


def x_fraction(x, y, width, dx):
    """Pixel area in |y|>=|x| inside square width, exact polygon integration."""
    lo, hi = x-dx/2, x+dx/2
    def primitive(v):
        return .5*(np.maximum(hi+v, 0)**2-np.maximum(lo+v, 0)**2
                   +np.maximum(hi-v, 0)**2-np.maximum(lo-v, 0)**2)
    area = np.zeros_like(x)
    for cy in (y, -y):
        lower = np.maximum(cy-dx/2, 0)
        upper = np.minimum(cy+dx/2, width/2)
        area += np.where(upper>lower, primitive(upper)-primitive(lower), 0)
    return np.clip(area/dx**2, 0, 1)


def local_maxima(values):
    v = np.asarray(values)
    # s=0 is separately labelled, even if it is not a maximum.
    indexes = find_peaks(v, prominence=max(float(np.ptp(v))*1e-4, 1e-12))[0]
    if v[0] >= v[1]:
        indexes = np.r_[0, indexes]
    pos, peak = S[indexes], v[indexes]
    drops = np.diff(-peak)
    return dict(s0=float(v[0]), s0_is_one_sided_max=bool(v[0]>=v[1]),
                peak_positions_um=pos.tolist(), peaks=peak.tolist(), drops=drops.tolist(),
                first_drop_ratio=float(drops[0]/drops[1]) if len(drops)>1 and np.all(drops[:2]>0) else None)


def run(n=512, scan=S):
    dx = DOMAIN/n
    axis = (np.arange(n)-n//2)*dx
    u,v = np.meshgrid(axis, axis)
    a = np.sqrt(2/(np.pi*W**2))*np.exp(-(u*u+v*v)/W**2)
    fx,fy = np.meshgrid(np.fft.fftfreq(n, dx),np.fft.fftfreq(n, dx))
    g = 1/P
    pupils = dict(wide_x=np.hypot(fx-g, fy)<=.2,
                  narrow_x=np.hypot(fx-g, fy)<=.05,
                  shifted_x=np.hypot(fx-g, fy-.08)<=.1)
    # Physical objective cutoff is fixed for all local pupils.
    physical = np.hypot(fx,fy)<=.45/.633
    pupils = {k:p&physical for k,p in pupils.items()}
    neg = (-np.arange(n))%n
    inv = lambda f:f[np.ix_(neg,neg)]
    fft = lambda e:np.fft.fft2(np.fft.ifftshift(e), norm="ortho")
    rec=[]
    identity_error=0.
    for s in scan:
        x=u+s
        sq = square_fraction(x,v,L,dx)
        mx = x_fraction(x,v,L,dx)
        my = sq-mx
        gx,gy=2*R*np.cos(2*np.pi*x/P),2*R*np.cos(2*np.pi*v/P)
        base=fft(a*(mx*gx+my*gy))
        for width in (1., 2.):
            c=square_fraction(x,v,width,dx)
            cx=x_fraction(x,v,width,dx)
            cy=c-cx
            bulk=base-fft(a*(cx*gx+cy*gy))
            new_x=fft(a*c*gx/np.sqrt(2))
            new_y=fft(a*c*gy/np.sqrt(2))
            for phase in (0., np.pi/2, np.pi):
                center=new_x+np.exp(1j*phase)*new_y
                total=bulk+center
                rotated=inv(total)
                for pname,pupil in pupils.items():
                    power=lambda f:float(np.sum(abs(f[pupil])**2)*dx**2)
                    bulk_power,center_power=power(bulk),power(center)
                    cross=float(2*np.real(np.sum(bulk[pupil]*np.conj(center[pupil])))*dx**2)
                    coherent=power(total)
                    err=abs(coherent-bulk_power-center_power-cross)
                    identity_error=max(identity_error,err)
                    plus=.5*power(total+rotated)
                    minus=.5*power(total-rotated)
                    rec.append(dict(s_um=float(s), width_um=width, center_phase_rad=float(phase),
                                    pupil=pname, reference_single_arm=power(base),
                                    single_arm=coherent, bulk_power=bulk_power,
                                    center_power=center_power, bulk_center_cross=cross,
                                    plus=plus, minus=minus, raw_sum=plus+minus))
    return rec,identity_error


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows,error=run()
    assert error<1e-12
    with (OUT/"curves.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    groups={}
    for width in (1.,2.):
        for phase in (0.,np.pi/2,np.pi):
            for pupil in ("wide_x","narrow_x","shifted_x"):
                data=[r for r in rows if r["width_um"]==width and r["center_phase_rad"]==phase and r["pupil"]==pupil]
                key=f"width{width:g}_phase{phase/np.pi:g}pi_{pupil}"
                idx=[0,20,40,60,80,100]
                groups[key]=dict(width_um=width,center_phase_rad=phase,pupil=pupil,
                                 plus=local_maxima([r["plus"] for r in data]),
                                 raw_sum=local_maxima([r["raw_sum"] for r in data]),
                                 center_single_arm_cross_at_0_1_2_3_4_5=[data[i]["bulk_center_cross"] for i in idx],
                                 single_arm_at_0_1_2_3_4_5=[data[i]["single_arm"] for i in idx],
                                 reference_single_arm_at_0_1_2_3_4_5=[data[i]["reference_single_arm"] for i in idx])
    from scipy.special import erf
    fraction={str(g):float(erf(g/(np.sqrt(2)*W))**2) for g in (1.,2.)}
    refined,refined_error=run(1024,scan=np.array([0.,1.,2.]))
    checks=[]
    for high in refined:
        low=next(r for r in rows if all(r[k]==high[k] for k in ("s_um","width_um","center_phase_rad","pupil")))
        checks.append(abs(high["plus"]-low["plus"])/max(abs(high["plus"]),1e-8))
    summary=dict(parameters=dict(L_um=L,w_um=W,pitch_um=P,r_plus_minus=R,domain_um=DOMAIN,n=512,scan_step_um=.05),
                 model="Three disjoint regions, central four orders r/sqrt(2), phase chi on Y orders. No center RCWA solved.",
                 central_gaussian_power_fraction=fraction,
                 decomposition_max_abs_error=error,
                 key_point_refinement_max_relative_plus_error=float(max(checks)),
                 groups=groups)
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
    for ax,pname in zip(axes,("wide_x","narrow_x","shifted_x")):
        data0=[r for r in rows if r["width_um"]==2. and r["center_phase_rad"]==0 and r["pupil"]==pname]
        scale=2*data0[0]["reference_single_arm"]
        for phase in (0.,np.pi/2,np.pi):
            data=[r for r in rows if r["width_um"]==2. and r["center_phase_rad"]==phase and r["pupil"]==pname]
            ax.plot(S,np.array([r["plus"] for r in data])/scale,label=f"Center Y phase {phase/np.pi:g} pi")
        ax.set(title=pname,xlabel="s (um)",ylabel="Plus / fixed ideal center scale")
        ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle("Conditional cross-grating center, square 2 um: fixed total order-coefficient norm")
    fig.savefig(OUT/"overlap_center.png",dpi=150);plt.close(fig)
    print(json.dumps(dict(power_fraction=fraction,decomposition_error=error,
                          max_refinement_error=max(checks)),indent=2))


if __name__=="__main__":main()
