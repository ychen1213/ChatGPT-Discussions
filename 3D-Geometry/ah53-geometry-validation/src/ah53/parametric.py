"""Persisted tensor B-splines of ordered section parts, fitted only to observations."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import make_interp_spline,BSpline
from .common import GeometryBase,REGIONS,REGION_LENGTHS,u_nodes,dump_json,file_hash

class ParametricModel(GeometryBase):
    @classmethod
    def from_observations(cls,obs,path):
        obs=Path(obs);path=Path(path);path.mkdir(parents=True,exist_ok=True)
        meta=json.loads((obs/'metadata.json').read_text(encoding='utf-8'));us=np.load(obs/'u.npy');zs=np.load(obs/'z.npy');pts=np.load(obs/'points.npy',mmap_mode='r')
        arrays={};count=0
        for j in range(6):
            take=(us>=j)&(us<=j+1);u=us[take]
            su=make_interp_spline(u,np.moveaxis(pts[:,:,take,:],2,0),k=3,axis=0)
            sz=make_interp_spline(zs,np.moveaxis(su.c,2,0),k=3,axis=0)
            # [z coefficients,u coefficients,line,xy] -> [line,z,u,xy]
            coeff=np.moveaxis(sz.c,2,0);arrays[f'c{j}']=coeff;arrays[f'u{j}']=su.t;arrays[f'z{j}']=sz.t;count+=coeff.size
        np.savez(path/'splines.npz',**arrays)
        meta.update(kind='parametric',model_id=path.name,source_model=meta['model_id'],operation='piecewise_tensor_cubic_interpolation_of_common_observations',coefficient_count=count,spline_degree=[3,3],array_payload_bytes=sum(v.nbytes for v in arrays.values()),parameterization='six ordered contour parts C(u,Z); effective height is max Y; left/right interval queries invert the unimodal saved contour',parameterization_reason='The crown has finite tangent in contour coordinates but unbounded |dX/dY| at its summit. Uniform-Y cubic interpolation amplifies endpoint coordinate error. Piecewise contour coordinates retain common arc-length observation spacing and bounded tangents; left/right representation remains mathematically valid.',source_observation_sha256=meta['observation_sha256'])
        dump_json(path/'metadata.json',meta);return cls.load(path)

    @classmethod
    def load(cls,path):
        path=Path(path);obj=cls();obj._setup(json.loads((path/'metadata.json').read_text(encoding='utf-8')),path)
        with np.load(path/'splines.npz') as f:obj.arrays={k:f[k] for k in f.files}
        obj._z_splines=[BSpline(obj.arrays[f'z{j}'],np.moveaxis(obj.arrays[f'c{j}'],1,0),3,axis=0,extrapolate=False) for j in range(6)]
        return obj

    def evaluate(self,line,u,z):
        scalar=np.ndim(u)==0;uu=np.atleast_1d(u).astype(float);out=np.empty((len(uu),2))
        for j in range(6):
            take=(uu>=j)&(uu<j+1 if j<5 else uu<=6)
            if np.any(take):
                coeff=self._z_splines[j](float(z))[line]
                out[take]=BSpline(self.arrays[f'u{j}'],coeff,3,extrapolate=False)(uu[take])
        return out[0] if scalar else out

    def contour(self,line,z,step_nm=2.):return self.evaluate(line,u_nodes(step_nm),z)
    def region_contour(self,line,z,region,step_nm=2.):
        j=REGIONS.index(region) if isinstance(region,str) else int(region)
        return self.evaluate(line,j+np.linspace(0,1,max(3,int(np.ceil(REGION_LENGTHS[j]/step_nm)))+1),z)

    def edited_copy(self,path,line=1,z_center=400.,z_halfwidth=320.,displacement_nm=10.):
        path=Path(path);path.mkdir(parents=True,exist_ok=True);arrays={k:v.copy() for k,v in self.arrays.items()};j=1;c=arrays['c1'];tz=arrays['z1'];tu=arrays['u1']
        gz=np.array([np.mean(tz[i+1:i+4]) for i in range(c.shape[1])]);gu=np.array([np.mean(tu[i+1:i+4]) for i in range(c.shape[2])])
        support_inside=(tz[:len(gz)]>=z_center-z_halfwidth)&(tz[4:4+len(gz)]<=z_center+z_halfwidth)
        a=np.clip(1-((gz-z_center)/z_halfwidth)**2,0,1)**2*support_inside;b=np.sin(np.pi*(gu-1))**2
        b[:2]=0.;b[-2:]=0. # preserve positions and tangents at shoulder joins
        delta=displacement_nm*a[:,None]*b[None,:];c[line,:,:,0]+=delta
        np.savez(path/'splines.npz',**arrays);meta=dict(self.metadata,model_id=path.name,source_model=self.metadata['model_id'],operation='local_left_shoulder_control_edit',edit={'line':line,'z_center':z_center,'z_halfwidth':z_halfwidth,'requested_max_displacement_nm':displacement_nm,'changed_scalar_coefficients':int(np.count_nonzero(delta)),'definition':'compact quartic z envelope times sin² shoulder coordinate; only coefficients whose whole B-spline support lies inside target interval; first/last two u coefficients fixed to preserve joins and tangents; actual displacement measured after reload','guaranteed_support_z_nm':[z_center-z_halfwidth,z_center+z_halfwidth]})
        dump_json(path/'metadata.json',meta);return self.load(path)
