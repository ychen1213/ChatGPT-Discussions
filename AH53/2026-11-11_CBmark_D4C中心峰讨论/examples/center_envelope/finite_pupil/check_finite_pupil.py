"""Controlled CB envelope calculation, NOT a D4C fit.

Run: uv run --with numpy --with scipy --with matplotlib check_finite_pupil.py
Lengths are um; FFT spatial frequencies are cycles/um. Macro-mask is a true
binary triangular X region, integrated exactly over pixels to avoid staircase
phase against the numerical grid. The field uses pixel-averaged mask values,
which converge to the binary-mask field as the mesh is refined.
"""
from pathlib import Path
import csv, json
import numpy as np
from scipy.integrate import quad
from scipy.special import erf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
L, W, DOMAIN, PITCH, WAVELENGTH = 40., 12., 80., 2., .633
RADII = [.05, .1, .2, .4]
S = np.linspace(0, 5, 101)

def pixel_mask_x(u, v, s, dx):
    """Exact area fraction of |y| >= |x| inside [-L/2,L/2]^2."""
    xl, xh = u+s-dx/2, u+s+dx/2
    def primitive(y):
        return .5*(np.maximum(xh+y,0)**2-np.maximum(xl+y,0)**2
                   +np.maximum(xh-y,0)**2-np.maximum(xl-y,0)**2)
    ans = np.zeros_like(u)
    for yy in (v, -v):
        lo, hi = np.maximum(yy-dx/2,0), np.minimum(yy+dx/2,L/2)
        valid=hi>lo
        ans += np.where(valid, primitive(hi)-primitive(lo), 0)
    return np.clip(ans/dx**2,0,1)

def metrics(values):
    values=np.asarray(values)
    peaks=values[np.arange(0,101,20)]
    drops=peaks[:-1]-peaks[1:]
    return dict(peaks=peaks.tolist(), normalized_peaks=(peaks/peaks[0]).tolist(),
                drops=drops.tolist(), first_over_second=float(drops[0]/drops[1]),
                successive_drop_ratios=(drops[:-1]/drops[1:]).tolist())

def full_collection():
    a=L/2
    px=lambda u:np.sqrt(2/np.pi)/W*np.exp(-2*u*u/W**2)
    upper=erf(np.sqrt(2)*a/W)
    q,t=[],[]
    for s in S:
        fq=lambda u:px(u)*(upper-erf(np.sqrt(2)*abs(u+s)/W))
        ft=lambda u:px(u)*(upper-erf(np.sqrt(2)*(abs(u)+s)/W))
        q.append(quad(fq,-a-s,a-s,points=[-s],epsabs=1e-12)[0])
        t.append(quad(ft,-a+s,a-s,points=[0],epsabs=1e-12)[0])
    return np.array(q),np.array(t)

def run_grid(n):
    dx=DOMAIN/n
    coordinate=(np.arange(n)-n//2)*dx
    u,v=np.meshgrid(coordinate,coordinate)
    amplitude=np.sqrt(2/(np.pi*W**2))*np.exp(-(u*u+v*v)/W**2)
    f=np.fft.fftfreq(n,dx)
    fx,fy=np.meshgrid(f,f)
    kr=np.hypot(fx,fy)
    disks={r:kr<=r for r in RADII}
    neg=(-np.arange(n))%n
    qs={r:[] for r in RADII}; ts={r:[] for r in RADII}
    for s in S:
        mask=pixel_mask_x(u,v,float(s),dx)
        fs=np.fft.fft2(np.fft.ifftshift(amplitude*mask),norm='ortho')
        flipped=fs[np.ix_(neg,neg)]
        for r,pupil in disks.items():
            qs[r].append(np.sum(abs(fs[pupil])**2)*dx**2)
            ts[r].append(np.real(np.sum(fs[pupil]*np.conj(flipped[pupil])))*dx**2)
    results={}
    for r in RADII:
        q=np.array(qs[r]); t=np.array(ts[r]); carrier=np.cos(4*np.pi*S/PITCH)
        results[str(r)]=dict(q=q,t=t,plus=q+t*carrier,minus=q-t*carrier,
                             raw_sum=2*q,constructive=q+t,modulation=t)
    return results

def full_xy(n=512):
    """Raw coherent X+Y versus separately summed powers in fixed pupils."""
    dx=DOMAIN/n
    coordinate=(np.arange(n)-n//2)*dx
    u,v=np.meshgrid(coordinate,coordinate)
    amplitude=np.sqrt(2/(np.pi*W**2))*np.exp(-(u*u+v*v)/W**2)
    fx,fy=np.meshgrid(np.fft.fftfreq(n,dx),np.fft.fftfreq(n,dx))
    kr=np.hypot(fx,fy); g=1/PITCH
    physical=(kr<=.45/WAVELENGTH)&(kr>=.7*g)
    pupils={'annulus':physical,
            'X_half_wedge':physical&(fx>0)&(abs(fx)>abs(fy)),
            'X_disk_0.1':physical&(np.hypot(fx-g,fy)<=.1),
            'X_disk_0.2':physical&(np.hypot(fx-g,fy)<=.2)}
    neg=(-np.arange(n))%n
    records={name:dict(coherent=[],incoherent=[],cross=[],port_plus=[],port_minus=[],raw_sum=[]) for name in pupils}
    for s in S:
        x=u+s
        mx=pixel_mask_x(u,v,float(s),dx)
        # For the complementary Y region, exact square pixel fraction minus X.
        sx=np.clip(np.minimum(x+dx/2,L/2)-np.maximum(x-dx/2,-L/2),0,dx)/dx
        sy=np.clip(np.minimum(v+dx/2,L/2)-np.maximum(v-dx/2,-L/2),0,dx)/dx
        my=np.clip(sx*sy-mx,0,1)
        ex=amplitude*mx*2*np.cos(2*np.pi*x/PITCH)
        ey=amplitude*my*2*np.cos(2*np.pi*v/PITCH)
        exf=np.fft.fft2(np.fft.ifftshift(ex),norm='ortho')
        eyf=np.fft.fft2(np.fft.ifftshift(ey),norm='ortho')
        total=exf+eyf; inv=total[np.ix_(neg,neg)]
        for name,pupil in pupils.items():
            coh=np.sum(abs(total[pupil])**2)*dx**2
            inc=np.sum((abs(exf[pupil])**2+abs(eyf[pupil])**2))*dx**2
            plus=.5*np.sum(abs(total[pupil]+inv[pupil])**2)*dx**2
            minus=.5*np.sum(abs(total[pupil]-inv[pupil])**2)*dx**2
            for key,value in [('coherent',coh),('incoherent',inc),('cross',coh-inc),('port_plus',plus),('port_minus',minus),('raw_sum',plus+minus)]:
                records[name][key].append(float(value))
    return records

def main():
    q,t=full_collection()
    full=dict(q=q,t=t,plus=q+t*np.cos(4*np.pi*S/PITCH),minus=q-t*np.cos(4*np.pi*S/PITCH),raw_sum=2*q,constructive=q+t,modulation=t)
    grids={str(n):run_grid(n) for n in (512,1024)}
    summary={'parameters':dict(L=L,w=W,domain=DOMAIN,pitch=PITCH,wavelength=WAVELENGTH,step=.05,radii_cycles_per_um=RADII,
                              equivalent_local_angular_radii=[WAVELENGTH*r for r in RADII]),
             'full_collection':{key:metrics(full[key]) for key in ('q','modulation','constructive','raw_sum')},'grids':{},'convergence':{}}
    for ns,results in grids.items():
        summary['grids'][ns]={r:{key:metrics(values[key]) for key in ('q','modulation','constructive','raw_sum')} for r,values in results.items()}
    for r in map(str,RADII):
        summary['convergence'][r]={key:float(np.max(abs(grids['512'][r][key]-grids['1024'][r][key]))/grids['1024'][r]['constructive'][0]) for key in ('q','t','constructive')}
    xy=full_xy()
    summary['full_xy']={name:{key:metrics(values) for key,values in data.items()} for name,data in xy.items()}
    for ns,results in grids.items():
        for r,data in results.items():
            with (OUT/f'envelope_n{ns}_r{r}.csv').open('w',newline='') as f:
                writer=csv.writer(f); writer.writerow(['s_um',*data]);writer.writerows(zip(S,*data.values()))
    with (OUT/'full_collection.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['s_um',*full]);writer.writerows(zip(S,*full.values()))
    for name,data in xy.items():
        with (OUT/f'full_xy_{name}.csv').open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['s_um',*data]);writer.writerows(zip(S,*data.values()))
    (OUT/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
    for ax,key,title in zip(axes,['constructive','modulation','raw_sum'],['Constructive peak envelope q+t','Modulation envelope t','Complementary-port sum 2q']):
        ax.plot(S,full[key]/full[key][0],label='Full collection',lw=2,color='black')
        for r,data in grids['1024'].items():ax.plot(S,data[key]/data[key][0],label=f'Radius {r} /um')
        ax.set(xlabel='s (um)',ylabel='Normalized to own s=0',title=title);ax.grid(alpha=.3)
    axes[0].legend(fontsize=8)
    fig.suptitle('Controlled step-CB geometry: p=2 um, L=40 um, Gaussian w=12 um; fixed isolated order coefficients')
    fig.savefig(OUT/'envelopes.png',dpi=160);plt.close(fig)
    for tag in ['full_collection']:
        print(tag,{k:summary[tag][k]['first_over_second'] for k in summary[tag]})
    for r,data in summary['grids']['1024'].items():
        print('disk',r,{k:round(v['first_over_second'],6) for k,v in data.items()})
    for name,data in summary['full_xy'].items():
        print('full_xy',name,{k:round(data[k]['first_over_second'],6) for k in ['coherent','incoherent','cross','port_plus','raw_sum']})
    print('convergence',summary['convergence'])

if __name__=='__main__':main()
