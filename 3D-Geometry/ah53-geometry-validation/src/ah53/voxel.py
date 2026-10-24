"""Actual uint8 material labels [Z,Y,X], center sampled and written sequentially."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .common import GeometryBase,dump_json

class VoxelModel(GeometryBase):
    @classmethod
    def from_model(cls,source,path,spacing_nm=10.):
        path=Path(path);path.mkdir(parents=True,exist_ok=True);h=float(spacing_nm);b=source.bounds
        nx,ny,nz=[int(round((b[k+1]-b[k])/h)) for k in (0,2,4)]
        if any(abs((b[k+1]-b[k])/h-n)>1e-8 for k,n in zip((0,2,4),(nx,ny,nz))):raise ValueError('Bounds must align with requested exact isotropic spacing')
        labels=np.lib.format.open_memmap(path/'labels.npy',mode='w+',dtype=np.uint8,shape=(nz,ny,nx));ys=b[2]+(np.arange(ny)+.5)*h;rows=np.arange(ny);counts=np.zeros(3,np.int64)
        for iz in range(nz):
            z=b[4]+(iz+.5)*h;slab=labels[iz];slab[:]=0;slab[ys<0]=2
            for line in range(source.n_lines):
                left,right=source.boundaries(line,ys,z);valid=np.isfinite(left)&np.isfinite(right)&(ys>=0)
                # Cell centers within the source material interval, inclusive ties.
                starts=np.ceil((np.where(valid,left,b[0])-b[0])/h-.5).astype(np.int64);stops=np.floor((np.where(valid,right,b[0])-b[0])/h-.5).astype(np.int64)+1
                starts=np.clip(starts,0,nx);stops=np.clip(stops,0,nx)
                for iy in rows[valid]:slab[iy,starts[iy]:stops[iy]]=1
            counts+=np.bincount(slab.ravel(),minlength=3)
            if iz%256==0:labels.flush()
        labels.flush();meta=dict(source.metadata,kind='voxel',model_id=path.name,source_model=source.metadata['model_id'],operation='center_sample_reloaded_source' if source.kind!='reference' else 'direct_independent_reference_center_sampling',spacing_nm=h,origin=[b[0],b[2],b[4]],array_shape_zyx=[nz,ny,nx],axis_order='ZYX',array_payload_bytes=int(labels.nbytes),material_counts=counts.tolist(),material_volume_nm3=float(counts[1]*h**3),classification_rule='closed source stripe intervals at voxel centers; substrate y<0; outside domain air',query='actual saved label array only; boundaries are cell-face transitions; no smoothing',source_information='continuous reference truth' if source.kind=='reference' else 'saved upstream representation')
        # Remove inherited fields which would falsely describe a label payload.
        for key in ('triangle_sha256','vertex_sha256','vertex_count','face_count','ring_shape','coefficient_count'):meta.pop(key,None)
        dump_json(path/'metadata.json',meta);del labels;return cls.load(path)

    @classmethod
    def load(cls,path):
        path=Path(path);obj=cls();obj._setup(json.loads((path/'metadata.json').read_text(encoding='utf-8')),path);obj.labels=np.load(path/'labels.npy',mmap_mode='r');obj.spacing=float(obj.metadata['spacing_nm']);obj.origin=np.array(obj.metadata['origin']);return obj

    def material_at(self,x,y,z):
        xx,yy,zz=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float),np.asarray(z,float));ix=np.floor((xx-self.origin[0])/self.spacing).astype(int);iy=np.floor((yy-self.origin[1])/self.spacing).astype(int);iz=np.floor((zz-self.origin[2])/self.spacing).astype(int);nz,ny,nx=self.labels.shape
        valid=(ix>=0)&(ix<nx)&(iy>=0)&(iy<ny)&(iz>=0)&(iz<nz);out=np.zeros(xx.shape,np.uint8);out[valid]=self.labels[iz[valid],iy[valid],ix[valid]];return out

    def _indices_for_line(self,line):
        h=self.spacing;center=self.centers[line];a=max(0,int(np.floor((center-1100-self.origin[0])/h)));b=min(self.labels.shape[2],int(np.ceil((center+1100-self.origin[0])/h)));return a,b

    def boundaries(self,line,y,z):
        yy,zz=np.broadcast_arrays(np.asarray(y,float),np.asarray(z,float));left=np.full(yy.shape,np.nan);right=left.copy();h=self.spacing;iy=np.floor((yy-self.origin[1])/h).astype(int);iz=np.floor((zz-self.origin[2])/h).astype(int);nz,ny,nx=self.labels.shape;a,b=self._indices_for_line(line)
        valid=(iy>=0)&(iy<ny)&(iz>=0)&(iz<nz)&(yy>=0)
        for row in np.unique(np.stack([iz[valid],iy[valid]],axis=1),axis=0):
            take=valid&(iz==row[0])&(iy==row[1]);ids=np.flatnonzero(self.labels[row[0],row[1],a:b]==1)
            if len(ids):left[take]=self.origin[0]+(a+ids[0])*h;right[take]=self.origin[0]+(a+ids[-1]+1)*h
        return left,right

    def contour(self,line,z,step_nm=2.):
        if z<self.bounds[4] or z>self.bounds[5]:return np.empty((0,2))
        h=self.spacing;iz=int(np.floor((z-self.origin[2])/h));iz=min(max(iz,0),self.labels.shape[0]-1);a,b=self._indices_for_line(line);slab=self.labels[iz,:,a:b];occupied=np.any(slab==1,axis=1);rows=np.flatnonzero(occupied)
        if not len(rows):return np.empty((0,2))
        left=[];right=[]
        for iy in rows:
            ids=np.flatnonzero(slab[iy]==1);xL=self.origin[0]+(a+ids[0])*h;xR=self.origin[0]+(a+ids[-1]+1)*h;y0=self.origin[1]+iy*h;y1=y0+h
            left.extend([(xL,y0),(xL,y1)]);right.extend([(xR,y0),(xR,y1)])
        p=np.array(left+right[::-1]+[left[0]],float);keep=np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-10];return p[keep]

    def mesh(self,boundary_step_nm=20.,z_step_nm=160.,line=None,z_range=None,roi=None,max_faces=200000):
        if roi is None:
            if line is None:raise ValueError('Raw voxel exposed faces require a bounded ROI; use labelled coarse preview for full mark')
            zr=z_range if z_range is not None else [-200,200];c=self.centers[int(line)];roi=[c-1100,c+1100,0,self.bounds[3],zr[0],zr[1]]
        h=self.spacing;lo=np.floor((np.array(roi)[[0,2,4]]-self.origin)/h).astype(int);hi=np.ceil((np.array(roi)[[1,3,5]]-self.origin)/h).astype(int);shape=np.array(self.labels.shape[::-1]);lo=np.maximum(lo,0);hi=np.minimum(hi,shape)
        if np.any(hi<=lo):return np.empty((0,3)),np.empty((0,3),np.int32)
        # Include one-cell halo so ROI cuts never masquerade as physical faces.
        hl=np.maximum(lo-1,0);hh=np.minimum(hi+1,shape);block=np.asarray(self.labels[hl[2]:hh[2],hl[1]:hh[1],hl[0]:hh[0]]==1);pad=np.pad(block,1)
        vertices=[];faces=[];face_n=0
        corners=[np.array(v) for v in [((0,0,0),(0,0,1),(0,1,1),(0,1,0)),((1,0,0),(1,1,0),(1,1,1),(1,0,1)),((0,0,0),(1,0,0),(1,0,1),(0,0,1)),((0,1,0),(0,1,1),(1,1,1),(1,1,0)),((0,0,0),(0,1,0),(1,1,0),(1,0,0)),((0,0,1),(1,0,1),(1,1,1),(0,1,1))]]
        for axis in range(3):
            for direction in (-1,1):
                sl=[slice(1,-1)]*3;sl[2-axis]=slice(0,-2) if direction<0 else slice(2,None);exposed=block&~pad[tuple(sl)];iz,iy,ix=np.nonzero(exposed);indices=np.stack([ix,iy,iz],1)+hl;keep=np.all((indices>=lo)&(indices<hi),axis=1);indices=indices[keep]
                if not len(indices):continue
                quad=self.origin+(indices[:,None,:]+corners[axis*2+(direction>0)][None])*h;vertices.append(quad.reshape(-1,3));start=face_n*4;idx=np.arange(len(indices)*4).reshape(-1,4)+start;faces.extend([idx[:,[0,1,2]],idx[:,[0,2,3]]]);face_n+=len(indices)
        if not vertices:return np.empty((0,3)),np.empty((0,3),np.int32)
        if face_n*2>max_faces:raise ValueError(f'ROI has {face_n*2} raw triangles; narrow ROI or raise max_faces explicitly')
        return np.concatenate(vertices),np.concatenate(faces).astype(np.int32)
