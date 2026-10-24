"""Shared coordinates and storage only; no candidate calls reference geometry."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np

REGIONS = ('left_wall','left_shoulder','top','right_shoulder','right_wall','bottom')
REGION_LENGTHS = (330.,130.,1600.,180.,330.,1720.)

def dump_json(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item()),encoding='utf-8')

def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()

def u_nodes(step_nm=10., include_bottom=True):
    return np.concatenate([i+np.linspace(0,1,max(4,int(np.ceil(length/step_nm)))+1)[:-1] for i,length in enumerate(REGION_LENGTHS[:6 if include_bottom else 5])]+[np.array([6. if include_bottom else 5.])])

def z_nodes(bounds, step, shifted=False):
    a,b=bounds[4:6]
    if shifted:
        return np.unique(np.r_[a,np.arange(a+step/2,b,step),b])
    return np.linspace(a,b,int(np.ceil((b-a)/step))+1)

def polygon_area(points):
    p=np.asarray(points)
    return abs(float(np.sum(p[:-1,0]*p[1:,1]-p[1:,0]*p[:-1,1])))/2

def polygon_boundaries(poly,ys):
    """Intervals of a y-unimodal closed section, including rounded summit."""
    p=np.asarray(poly); peak=int(np.argmax(p[:,1])); yy=np.asarray(ys,float)
    left=p[:peak+1]; right=p[peak:]
    # Bottom closure must not enter the descending side interpolation.
    right=right[:np.flatnonzero(right[:,1]<=1e-8)[0]+1] if np.any(right[:,1]<=1e-8) else right
    if np.any(np.diff(left[:,1]) < -1e-6) or np.any(np.diff(right[:,1]) > 1e-6):
        raise ValueError('Section is not Y-unimodal; a single left/right interval would lose material topology')
    il=np.r_[True,np.diff(left[:,1])>1e-10]; ir=np.r_[True,np.diff(right[::-1,1])>1e-10]
    l=np.interp(yy,left[il,1],left[il,0]); rr=right[::-1][ir]
    r=np.interp(yy,rr[:,1],rr[:,0])
    ok=(yy>=0)&(yy<=p[peak,1])
    return np.where(ok,l,np.nan),np.where(ok,r,np.nan)

def loft_mesh(rings):
    """rings=(line,z,u,3); no duplicate closure vertex, outward triangles."""
    nl,nz,nu,_=rings.shape; vertices=np.asarray(rings,dtype=np.float64).reshape(-1,3)
    base=np.arange(nl*nz*nu,dtype=np.int64).reshape(nl,nz,nu)[:,:-1]
    nxt=np.roll(base,-1,axis=2); upper=base+nu; upper_next=nxt+nu
    side=np.stack([np.stack([base,upper,upper_next],-1),np.stack([base,upper_next,nxt],-1)],-2).reshape(-1,3)
    # Cross sections are clockwise in XY. Center fan seals artificial Z cuts.
    centers=rings[:,[0,-1]].mean(axis=2).reshape(-1,3)
    center_ids=np.arange(len(vertices),len(vertices)+len(centers)).reshape(nl,2)
    caps=[]
    for line in range(nl):
        for end,zi in enumerate((0,nz-1)):
            ids=(line*nz+zi)*nu+np.arange(nu); following=np.roll(ids,-1)
            tri=np.stack([np.full(nu,center_ids[line,end]),ids,following],1)
            if end==1:tri=tri[:,::-1]
            caps.append(tri)
    return np.concatenate([vertices,centers]),np.concatenate([side]+caps).astype(np.int32)

class GeometryBase:
    def _setup(self,metadata,path=None):
        self.metadata=metadata; self.path=Path(path) if path is not None else None
        self.kind=metadata['kind']; self.bounds=np.array(metadata['bounds'],float)
        self.centers=np.array(metadata['centers'],float); self.ids=list(metadata['ids']); self.n_lines=len(self.ids)
        self.scene=metadata['scene']; self._section_cache={}

    @property
    def resource_bytes(self):
        return int(self.metadata.get('array_payload_bytes',0))

    def boundaries(self,line,y,z):
        yy,zz=np.broadcast_arrays(np.asarray(y,float),np.asarray(z,float)); l=np.full(yy.shape,np.nan); r=l.copy()
        for zp in np.unique(zz):
            take=zz==zp
            if self.bounds[4]<=zp<=self.bounds[5]:
                key=(int(line),float(zp))
                if key not in self._section_cache:
                    if len(self._section_cache)>64:self._section_cache.clear()
                    self._section_cache[key]=self.contour(int(line),float(zp),step_nm=0.5)
                l[take],r[take]=polygon_boundaries(self._section_cache[key],yy[take])
        return l,r

    def material_at(self,x,y,z):
        xx,yy,zz=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float),np.asarray(z,float)); out=np.zeros(xx.shape,np.uint8)
        domain=(xx>=self.bounds[0])&(xx<=self.bounds[1])&(yy>=self.bounds[2])&(yy<=self.bounds[3])&(zz>=self.bounds[4])&(zz<=self.bounds[5])
        out[domain&(yy<0)]=2
        for line in range(self.n_lines):
            l,r=self.boundaries(line,yy,zz); out[domain&(yy>=0)&(xx>=l)&(xx<=r)]=1
        return out

    def volume(self,segment_nm=40.,order=4,contour_step_nm=1.):
        if 'material_volume_nm3' in self.metadata:return float(self.metadata['material_volume_nm3'])
        # Independent physical stations avoid scoring an interpolating source
        # only at the Z observation knots. Four-point Gauss on <=40 nm panels
        # integrates degree-seven polynomials exactly within each spline span.
        edges=z_nodes(self.bounds,segment_nm);nodes,weights=np.polynomial.legendre.leggauss(order);total=0.
        for a,b in zip(edges[:-1],edges[1:]):
            for point,weight in zip((a+b)/2+(b-a)/2*nodes,weights):
                total+=(b-a)/2*weight*sum(polygon_area(self.contour(i,float(point),contour_step_nm)) for i in range(self.n_lines))
        return float(total)

    def mesh(self,boundary_step_nm=20.,z_step_nm=160.,line=None,z_range=None,roi=None,max_faces=200000):
        lines=list(range(self.n_lines)) if line is None else [int(line)]
        b=self.bounds.copy()
        if z_range is not None:b[4:6]=z_range
        if roi is not None:
            b[4:6]=roi[4:6];lines=[i for i in lines if self.centers[i]+1100>=roi[0] and self.centers[i]-1100<=roi[1]]
        us=u_nodes(boundary_step_nm)[:-1]; zs=z_nodes(b,z_step_nm)
        rings=np.empty((len(lines),len(zs),len(us),3))
        for j,i in enumerate(lines):
            for k,z in enumerate(zs):
                rings[j,k,:,:2]=self.evaluate(i,us,z);rings[j,k,:,2]=z
        vertices,faces=loft_mesh(rings)
        if roi is not None:
            tri=vertices[faces];lo=np.array(roi)[[0,2,4]];hi=np.array(roi)[[1,3,5]];faces=faces[np.all(tri.max(axis=1)>=lo,axis=1)&np.all(tri.min(axis=1)<=hi,axis=1)];ids,inverse=np.unique(faces,return_inverse=True);vertices=vertices[ids];faces=inverse.reshape(-1,3).astype(np.int32)
        return vertices,faces

def build_observations(reference,path,boundary_step_nm=10.,z_step_nm=40.):
    path=Path(path);path.mkdir(parents=True,exist_ok=True)
    us=u_nodes(boundary_step_nm);zs=z_nodes(reference.bounds,z_step_nm)
    pts=np.lib.format.open_memmap(path/'points.npy',mode='w+',dtype=np.float64,shape=(reference.n_lines,len(zs),len(us),2))
    max_interval=0.;max_height=0.;min_gap=float('inf');min_width=float('inf')
    for line in range(reference.n_lines):
        for k,z in enumerate(zs):
            pts[line,k]=reference.evaluate(line,us,z)
            section=pts[line,k];max_interval=max(max_interval,float(np.linalg.norm(np.diff(section,axis=0),axis=1).max()));max_height=max(max_height,float(section[:,1].max()))
            peak=np.argmax(section[:,1]);right_end=np.where(us==5)[0][0]
            if np.any(np.diff(section[:peak+1,1]) < -1e-8) or np.any(np.diff(section[peak:right_end+1,1]) > 1e-8):raise ValueError('Reference section violates single interval in X')
            ls,rs=polygon_boundaries(section,[30.,150.,270.]);min_width=min(min_width,float(np.nanmin(rs-ls)))
            if line: min_gap=min(min_gap,float(section[:,0].min()-pts[line-1,k,:,0].max()))
    if max_height>reference.bounds[3] or min_gap<=0 or min_width<=0:raise ValueError('Geometry exceeds bounds, stripes overlap, or sampled interior width non-positive')
    pts.flush(); np.save(path/'u.npy',us);np.save(path/'z.npy',zs)
    meta=dict(reference.metadata,kind='observations',model_id=path.name,source_model=reference.metadata['model_id'],operation='sample_independent_analytic_reference',boundary_step_nm=float(boundary_step_nm),z_step_nm=float(z_step_nm),point_count=int(np.prod(pts.shape[:-1])),array_payload_bytes=int(pts.nbytes+us.nbytes+zs.nbytes),observation_sha256=file_hash(path/'points.npy'),sampling='Common piecewise ordered contour samples; nominal per-region arc-length upper envelopes; no fitted model used',measured_max_contour_chord_nm=max_interval,measured_max_height_nm=max_height,measured_min_stripe_gap_nm=min_gap,measured_min_width_at_30_150_270_nm=min_width,y_unimodality_checked_at_all_observed_sections=True)
    dump_json(path/'metadata.json',meta);return path

def load_model(path):
    path=Path(path);meta=json.loads((path/'metadata.json').read_text(encoding='utf-8'));kind=meta['kind']
    from .reference_geometry import ReferenceGeometry
    from .parametric import ParametricModel
    from .surface import SurfaceModel
    from .voxel import VoxelModel
    return {'reference':ReferenceGeometry,'parametric':ParametricModel,'surface':SurfaceModel,'voxel':VoxelModel}[kind].load(path)
