"""Independent analytic reference: trigonometric walls, Bezier shoulders, parabolic crown."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
import numpy as np
from .common import GeometryBase,REGIONS,u_nodes,dump_json

class ReferenceGeometry(GeometryBase):
    def __init__(self,scene='local',config=None):
        if config is None:config=Path(__file__).resolve().parents[2]/'configs'/'default.json'
        self.config=json.loads(Path(config).read_text(encoding='utf-8')) if isinstance(config,(str,Path)) else config
        c=self.config;nom=c['nominal'];sc=c['scenes'][scene]
        ids=[f'm{m}_s{s}' for m in sc['mother_ids'] for s in range(3)]
        centers=[m*nom['mother_period_nm']+off for m in sc['mother_ids'] for off in nom['stripe_offsets_nm']]
        meta={'kind':'reference','scene':scene,'model_id':f'reference_{scene}','bounds':sc['bounds_nm'],'centers':centers,'ids':ids,'units':'nm','materials':c['materials'],'config':c,'array_payload_bytes':0,'reference_definition':'Independent analytic piecewise contour; no spline/triangle/voxel dependency','local_feature':c['synthetic']['local_feature'],'sections_y_unimodal':True}
        self._setup(meta);self._phases={}

    def _field(self,line,field,z,rms):
        syn=self.config['synthetic'];stable=int.from_bytes(hashlib.sha256((str(syn['seed'])+'|'+self.ids[line]+'|'+str(field)).encode()).digest()[:8],'little')
        key=(line,field)
        if key not in self._phases:self._phases[key]=np.random.default_rng(stable).uniform(0,2*np.pi,len(syn['wavelengths_nm']))
        wl=np.array(syn['wavelengths_nm']);w=np.array(syn['spectral_weights']);w=w/np.sqrt(np.sum(w*w)/2)*rms
        zz=np.asarray(z,float)
        return np.sum(w*np.sin(zz[...,None]*2*np.pi/wl+self._phases[key]),axis=-1)

    def parameters(self,line,z):
        syn=self.config['synthetic'];nom=self.config['nominal'];z=float(z)
        C=self.centers[line]+self._field(line,0,z,syn['center_rms_nm']);W=nom['design_cd_nm']+self._field(line,1,z,syn['full_width_rms_nm'])
        feature=syn['local_feature'];bump=np.exp(-np.log(2)*((z-feature['z_center_nm'])/feature['z_hwhm_nm'])**2) if self.ids[line]==feature['stable_stripe_id'] else 0.
        H=nom['height_nm']+self._field(line,2,z,syn['height_rms_nm'])+feature['height_nm']*bump
        # use stable line id phase for crop identity, not local array index
        sid=sum(ord(ch) for ch in self.ids[line]);rL,rR=np.array(syn['shoulder_scale_nm'])*(1+syn['shoulder_relative_variation']*np.sin(z/1300+sid*np.array([1.1,2.3])+np.array([.3,1.7])))
        return float(C),float(W),float(H),float(rL),float(rR),float(bump)

    def _wall(self,line,y,z,side,parameters=None,derivative=False):
        C,W,H,rL,rR,bump=self.parameters(line,z) if parameters is None else parameters
        sy=self.config['synthetic'];yy=np.asarray(y,float);t=yy/300.;angle=sy['left_angle_deg'] if side==0 else sy['right_angle_deg'];slope=1/np.tan(np.deg2rad(angle))*(1 if side==0 else -1)
        amp=sy['wall_bending_nm'][side]*(1 if side==0 else -1);res=self._field(line,3+side,z,sy['height_residual_rms_nm'])
        if derivative:
            val=slope+amp*np.pi/300*np.cos(np.pi*t)+res*2*np.pi/300*np.cos(2*np.pi*(t-.5))
            if side==0:val+=sy['local_feature']['left_displacement_nm']*bump*2*np.pi/300*np.cos(2*np.pi*(t-.5))
            return val
        val=C+(-W/2 if side==0 else W/2)+slope*(yy-sy['reference_y_nm'])+amp*(np.sin(np.pi*t)-1)+res*np.sin(2*np.pi*(t-.5))
        if side==0:val+=sy['local_feature']['left_displacement_nm']*bump*np.sin(2*np.pi*(t-.5))
        return val

    def evaluate(self,line,u,z):
        scalar=np.ndim(u)==0;uu=np.atleast_1d(np.asarray(u,float));out=np.empty((len(uu),2));p=self.parameters(line,z);C,W,H,rL,rR,bump=p
        rise=self.config['synthetic']['top_transverse_rise_nm'];yl=H-rise-rL;yr=H-rise-rR
        xl=float(self._wall(line,yl,z,0,p));xr=float(self._wall(line,yr,z,1,p));a=xl+rL;b=xr-rR;mid=(a+b)/2;half=(b-a)/2
        def bezier(t,ctrl):
            t=t[:,None];return (1-t)**3*ctrl[0]+3*(1-t)**2*t*ctrl[1]+3*(1-t)*t*t*ctrl[2]+t**3*ctrl[3]
        for region in range(6):
            take=(uu>=region)&(uu<region+1 if region<5 else uu<=6);v=uu[take]-region
            if not np.any(take):continue
            if region==0:y=v*yl;out[take]=np.column_stack([self._wall(line,y,z,0,p),y])
            elif region==1:
                k=.55228475*rL;ctrl=np.array([[xl,yl],[xl+k*float(self._wall(line,yl,z,0,p,True)),yl+k],[a-k,H-rise-k*2*rise/half],[a,H-rise]])
                out[take]=bezier(v,ctrl)
            elif region==2:x=a+(b-a)*v;out[take]=np.column_stack([x,H-rise*((x-mid)/half)**2])
            elif region==3:
                k=.55228475*rR;ctrl=np.array([[b,H-rise],[b+k,H-rise-k*2*rise/half],[xr+k*float(self._wall(line,yr,z,1,p,True)),yr+k],[xr,yr]])
                out[take]=bezier(v,ctrl)
            elif region==4:y=(1-v)*yr;out[take]=np.column_stack([self._wall(line,y,z,1,p),y])
            else:ll=float(self._wall(line,0,z,0,p));rr=float(self._wall(line,0,z,1,p));out[take]=np.column_stack([rr+(ll-rr)*v,np.zeros_like(v)])
        return out[0] if scalar else out

    def contour(self,line,z,step_nm=2.):return self.evaluate(line,u_nodes(step_nm),z)
    def region_contour(self,line,z,region,step_nm=2.):
        from .common import REGION_LENGTHS
        k=REGIONS.index(region) if isinstance(region,str) else int(region)
        return self.evaluate(line,k+np.linspace(0,1,max(3,int(np.ceil(REGION_LENGTHS[k]/step_nm)))+1),z)

    def save(self,path):
        path=Path(path);path.mkdir(parents=True,exist_ok=True);dump_json(path/'metadata.json',self.metadata);self.path=path;return self
    @classmethod
    def load(cls,path):
        meta=json.loads((Path(path)/'metadata.json').read_text(encoding='utf-8'));obj=cls(meta['scene'],meta['config']);obj.path=Path(path);return obj
