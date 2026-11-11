"""Controlled finite-CB diffraction / self-reference calculation, not a D4C fit.

Run: uv run --with numpy --with scipy --with matplotlib run_optical_coupling.py
All lengths in um. FFT frequencies in cycles/um. Fixed field coefficients
r_(+1)=r_(-1)=0.2, r_0=0 for X and Y regions. A "gap" removes these periodic
diffracted fields, not the total physical reflection from a blank surface.

No scan-dependent normalization or fitted parameters. Input Gaussian has unit
incident power. SUM and DIFF are matched ideal complementary ports. The
second arm is F(-kx,-ky), not F*(-kx,-ky). Fixed physical NA and fixed ROIs.
"""
from pathlib import Path
import csv, json, argparse
import numpy as np
from scipy.fft import fft2, ifftshift, fftfreq
from scipy.signal import find_peaks
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
L, W, DOMAIN, PITCH, WAVELENGTH, NA, R = 40., 12., 80., 2., .633, .45, .2
S = np.linspace(0., 5., 251)
GEOMETRIES = ('ideal','cross_gap1','square_gap2','phase_upper_pi')
PUPILS = ('disk_r020','disk_r010','disk_r005','disk_r010_y006','disk_r020_edge_y004')
FIELDS = ('power_a','power_b','same_arm_xy_a','same_arm_xy_b','cross_arm_real',
          'port_sum','port_diff','raw_sum','incoherent_raw_sum')

def rect_parts(x, y, dx, xmin, xmax, ymin, ymax):
    """Exact pixel area fractions for X-upper, X-lower and all of a rectangle."""
    xl=np.maximum(x-dx/2,xmin); xh=np.minimum(x+dx/2,xmax)
    yl=np.maximum(y-dx/2,ymin); yh=np.minimum(y+dx/2,ymax)
    valid=(xh>xl)&(yh>yl)
    def prim(z):
        return .5*(np.maximum(xh+z,0)**2-np.maximum(xl+z,0)**2+
                   np.maximum(xh-z,0)**2-np.maximum(xl-z,0)**2)
    ulo=np.maximum(yl,0); uhi=np.maximum(yh,0)
    dlo=np.maximum(-yh,0); dhi=np.maximum(-yl,0)
    up=np.where(valid&(uhi>ulo),prim(uhi)-prim(ulo),0)/dx**2
    low=np.where(valid&(dhi>dlo),prim(dhi)-prim(dlo),0)/dx**2
    square=np.where(valid,(xh-xl)*(yh-yl),0)/dx**2
    return np.clip(up,0,1),np.clip(low,0,1),np.clip(square,0,1)

def masks(x,y,dx,geometry):
    a=L/2
    if geometry=='cross_gap1':
        up=np.zeros_like(x); low=up.copy(); square=up.copy()
        for xlim in ((-a,-.5),(.5,a)):
            for ylim in ((-a,-.5),(.5,a)):
                uu,ll,ss=rect_parts(x,y,dx,*xlim,*ylim)
                up+=uu;low+=ll;square+=ss
    else:
        up,low,square=rect_parts(x,y,dx,-a,a,-a,a)
        if geometry=='square_gap2':
            uu,ll,ss=rect_parts(x,y,dx,-1,1,-1,1)
            up-=uu;low-=ll;square-=ss
    mx=up+low
    my=np.clip(square-mx,0,1)
    signed_x=low-up if geometry=='phase_upper_pi' else mx
    return signed_x,my,mx,square

def peak_metrics(y):
    """True sampled extrema refined by a local quadratic; never sample only n*h."""
    y=np.asarray(y)
    idx,_=find_peaks(y,prominence=max(np.ptp(y)*.002,1e-10),distance=15)
    ix=list(idx)
    if y[0]>y[1]: ix=[0]+ix
    # Scan endpoint is not reported as a local maximum.
    positions=[];heights=[]
    for i in ix:
        if i==0:
            positions.append(float(S[0]));heights.append(float(y[0]));continue
        off=.5*(y[i-1]-y[i+1])/(y[i-1]-2*y[i]+y[i+1])
        val=y[i]-.25*(y[i-1]-y[i+1])*off
        positions.append(float(S[i]+off*(S[1]-S[0])));heights.append(float(val))
    drops=np.diff(-np.asarray(heights))
    ratios=np.divide(drops[:-1],drops[1:],out=np.full(max(len(drops)-1,0),np.nan),where=abs(drops[1:])>1e-13)
    return {'peak_positions_um':positions,'peak_heights':heights,
            'absolute_drops':drops.tolist(),'successive_drop_ratios':ratios.tolist(),
            'peak_count':len(ix),'has_central_maximum':bool(ix and ix[0]==0),
            'all_drops_positive':bool(len(drops) and np.all(drops>0))}

def run(n, geometries=GEOMETRIES):
    dx=DOMAIN/n
    co=(np.arange(n)-n//2)*dx
    u,v=np.meshgrid(co,co)
    amp=np.sqrt(2/(np.pi*W**2))*np.exp(-(u*u+v*v)/W**2)
    fx,fy=np.meshgrid(fftfreq(n,dx),fftfreq(n,dx))
    physical=np.hypot(fx,fy)<=NA/WAVELENGTH
    g=1/PITCH
    pupils={
        'disk_r020':physical&(np.hypot(fx-g,fy)<=.20),
        'disk_r010':physical&(np.hypot(fx-g,fy)<=.10),
        'disk_r005':physical&(np.hypot(fx-g,fy)<=.05),
        'disk_r010_y006':physical&(np.hypot(fx-g,fy-.06)<=.10),
        'disk_r020_edge_y004':physical&(np.hypot(fx-g,fy)<=.20)&(fy>=.04),
    }
    # Store flattened indices once. Negative-frequency index exactly maps FFT grid.
    neg=(-np.arange(n))%n
    records={geom:{name:{field:[] for field in FIELDS} for name in pupils} for geom in geometries}
    for si,s in enumerate(S):
        x=u+s
        cx=2*R*np.cos(2*np.pi*x/PITCH)
        cy=2*R*np.cos(2*np.pi*v/PITCH)
        for geom in geometries:
            signed_x,my,_,_=masks(x,v,dx,geom)
            exf=fft2(ifftshift(amp*signed_x*cx),norm='ortho',workers=2)
            eyf=fft2(ifftshift(amp*my*cy),norm='ortho',workers=2)
            total=exf+eyf
            rev=total[np.ix_(neg,neg)]
            rex=exf[np.ix_(neg,neg)];rey=eyf[np.ix_(neg,neg)]
            for name,pup in pupils.items():
                a=total[pup];b=rev[pup]
                qa=np.vdot(a,a).real*dx**2;qb=np.vdot(b,b).real*dx**2
                ia=np.sum(abs(exf[pup])**2+abs(eyf[pup])**2)*dx**2
                ib=np.sum(abs(rex[pup])**2+abs(rey[pup])**2)*dx**2
                c=np.vdot(b,a).real*dx**2
                plus=.5*(qa+qb)+c;minus=.5*(qa+qb)-c
                vals=(qa,qb,qa-ia,qb-ib,c,plus,minus,qa+qb,ia+ib)
                for key,val in zip(FIELDS,vals):records[geom][name][key].append(float(val))
        if si%50==0:print(f'n={n}, s={s:.2f}: completed',flush=True)
    for geom in geometries:
        for name in pupils:
            d=records[geom][name]
            with (OUT/f'scan_n{n}_{geom}_{name}.csv').open('w',newline='') as f:
                cw=csv.writer(f);cw.writerow(['s_um',*FIELDS]);cw.writerows(zip(S,*[d[k] for k in FIELDS]))
    return records

def finite_json(x):
    if isinstance(x,dict):return {k:finite_json(v) for k,v in x.items()}
    if isinstance(x,list):return [finite_json(v) for v in x]
    if isinstance(x,float) and not np.isfinite(x):return None
    return x

def write_summary(records,n):
    summary={geom:{pup:{key:peak_metrics(d[key]) for key in ('port_sum','port_diff','raw_sum','incoherent_raw_sum')}
                   for pup,d in per_geom.items()} for geom,per_geom in records.items()}
    for geom,per_geom in records.items():
        for pup,d in per_geom.items():
            a=np.array(d['port_sum']);b=np.array(d['port_diff']);q=np.array(d['raw_sum'])
            summary[geom][pup]['checks']={
                'max_complement_error':float(np.max(abs(a+b-q))),
                'max_same_arm_xy_fraction_of_raw':float(np.max(abs(np.array(d['same_arm_xy_a'])+np.array(d['same_arm_xy_b'])))/max(q)),
                'central_port_sum':d['port_sum'][0],
                'central_raw_sum':d['raw_sum'][0],
                'max_cross_arm_real':float(max(abs(np.array(d['cross_arm_real'])))),
            }
    (OUT/f'summary_n{n}.json').write_text(json.dumps(finite_json(summary),indent=2),encoding='utf-8')
    return summary

def draw(records,n):
    # Unified scale: same baseline ideal/wide-pupil s=0 for all curves.
    scale=records['ideal']['disk_r020']['port_sum'][0]
    fig,axes=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
    for col,pup in enumerate(('disk_r020','disk_r010_y006','disk_r020_edge_y004')):
        for geom in GEOMETRIES:
            axes[0,col].plot(S,np.array(records[geom][pup]['port_sum'])/scale,label=geom)
            axes[1,col].plot(S,np.array(records[geom][pup]['raw_sum'])/scale,label=geom)
        axes[0,col].set_title(pup)
        axes[0,col].set_ylabel('SUM port / one fixed baseline')
        axes[1,col].set_ylabel('SUM+DIFF / same fixed baseline')
        for row in (0,1):axes[row,col].set_xlabel('s (um)');axes[row,col].grid(alpha=.25)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Controlled finite-CB field: p=2 um; L=40 um; Gaussian w=12 um; r+/-1=0.2; NA=0.45')
    fig.savefig(OUT/f'optical_comparison_n{n}.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,4.4),constrained_layout=True)
    for ax,geom in zip(axes,('cross_gap1','square_gap2','phase_upper_pi')):
        pup='disk_r020_edge_y004';d=records[geom][pup]
        ax.plot(S,np.array(d['raw_sum'])/scale,label='coherent raw sum')
        ax.plot(S,np.array(d['incoherent_raw_sum'])/scale,label='X/Y powers separately')
        ax.plot(S,(np.array(d['same_arm_xy_a'])+np.array(d['same_arm_xy_b']))/scale,label='same-arm X/Y cross term')
        ax.plot(S,np.array(d['cross_arm_real'])/scale,label='inter-arm C (cancels in raw sum)',alpha=.7)
        ax.set(title=geom,xlabel='s (um)',ylabel='One fixed baseline');ax.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    fig.suptitle('Fixed clipped pupil: separate same-arm interference from inter-arm interference')
    fig.savefig(OUT/f'cross_term_decomposition_n{n}.png',dpi=170);plt.close(fig)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--n',type=int,default=512)
    parser.add_argument('--geometries',nargs='*',default=list(GEOMETRIES));args=parser.parse_args()
    records=run(args.n,tuple(args.geometries));summary=write_summary(records,args.n)
    params=dict(pitch_um=PITCH,L_um=L,gaussian_intensity_1e2_radius_um=W,domain_um=DOMAIN,
                wavelength_um=WAVELENGTH,NA=NA,r_pm1_real=R,r0=0.,scan_step_um=float(S[1]-S[0]),
                central_cross_gap_width_um=1.,central_square_gap_side_um=2.,
                phase_upper_pi='Both X orders in upper triangle multiply exp(i*pi); lower X and both Y regions unchanged',
                roi_definitions={'disk_r020':'(fx-.5)^2+fy^2 <= .2^2',
                    'disk_r010':'(fx-.5)^2+fy^2 <= .1^2',
                    'disk_r005':'(fx-.5)^2+fy^2 <= .05^2',
                    'disk_r010_y006':'(fx-.5)^2+(fy-.06)^2 <= .1^2',
                    'disk_r020_edge_y004':'disk_r020 AND fy >= .04'},
                all_rois_intersect_physical_pupil='fx^2+fy^2 <= (NA/wavelength)^2',
                sum_diff_definition='I_SUM=.5 ||F(k)+F(-k)||^2; I_DIFF=.5 ||F(k)-F(-k)||^2 within fixed ROI',
                no_fitting=True,physical_limitations=['scalar single-mode illumination','synthetic RCWA order coefficients',
                    'no central blank r0 scattering','no finite-height electromagnetic boundary solution','ideal rotation and splitter'])
    (OUT/'parameters.json').write_text(json.dumps(params,indent=2),encoding='utf-8')
    if tuple(args.geometries)==GEOMETRIES:draw(records,args.n)
    for geom in args.geometries:
        for pup in PUPILS:
            m=summary[geom][pup]['port_sum'];rs=summary[geom][pup]['raw_sum']
            print(geom,pup,'SUM peaks',np.round(m['peak_heights'][:5],8).tolist(),
                  'ratios',np.round(m['successive_drop_ratios'][:3],5).tolist(),
                  'raw peaks',rs['peak_count'],flush=True)

if __name__=='__main__':main()
