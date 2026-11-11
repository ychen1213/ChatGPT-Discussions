"""Spot-check the phase/ROI cross-term example on a doubled spatial grid."""
from pathlib import Path
import json
import numpy as np
from scipy.fft import fft2,ifftshift,fftfreq
import run_optical_coupling as m

out=Path(__file__).resolve().parent
results={}
for pname,ky,r,edge in [('disk_r020',0.,.2,None),('disk_r010_y006',.06,.1,None),('disk_r020_edge_y004',0.,.2,.04)]:
    coarse=np.genfromtxt(out/f'scan_n512_phase_upper_pi_{pname}.csv',delimiter=',',names=True)
    cross=coarse['same_arm_xy_a']+coarse['same_arm_xy_b']
    j=int(np.argmax(abs(cross)));s=float(coarse['s_um'][j])
    item={'s_um':s,'coarse_same_arm_xy':float(cross[j]),'coarse_raw_sum':float(coarse['raw_sum'][j]),
          'coarse_max_raw_sum':float(max(coarse['raw_sum']))}
    n=1024;dx=m.DOMAIN/n;co=(np.arange(n)-n//2)*dx;u,v=np.meshgrid(co,co)
    fx,fy=np.meshgrid(fftfreq(n,dx),fftfreq(n,dx))
    pupil=(np.hypot(fx-.5,fy-ky)<=r)&(np.hypot(fx,fy)<=m.NA/m.WAVELENGTH)
    if edge is not None:pupil&=fy>=edge
    amp=np.sqrt(2/(np.pi*m.W**2))*np.exp(-(u*u+v*v)/m.W**2)
    mx,my,_,_=m.masks(u+s,v,dx,'phase_upper_pi')
    ex=fft2(ifftshift(amp*mx*2*m.R*np.cos(2*np.pi*(u+s)/m.PITCH)),norm='ortho',workers=2)
    ey=fft2(ifftshift(amp*my*2*m.R*np.cos(2*np.pi*v/m.PITCH)),norm='ortho',workers=2)
    neg=(-np.arange(n))%n;exb=ex[np.ix_(neg,neg)];eyb=ey[np.ix_(neg,neg)]
    c=2*np.real(np.vdot(ey[pupil],ex[pupil])+np.vdot(eyb[pupil],exb[pupil]))*dx**2
    raw=(np.sum(abs((ex+ey)[pupil])**2)+np.sum(abs((exb+eyb)[pupil])**2))*dx**2
    item.update(fine_same_arm_xy=float(c),fine_raw_sum=float(raw),
                same_arm_xy_change_over_coarse_max_raw=float(abs(c-cross[j])/max(coarse['raw_sum'])))
    results[pname]=item
(out/'phase_coupling_spotcheck.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
