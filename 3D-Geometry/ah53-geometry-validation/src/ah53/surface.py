"""Actual closed triangle meshes, including saved connectivity and exact XY sections."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .common import GeometryBase,REGIONS,u_nodes,z_nodes,loft_mesh,dump_json,file_hash

class SurfaceModel(GeometryBase):
    @classmethod
    def _store(cls,points,u,z,meta,path):
        path=Path(path);path.mkdir(parents=True,exist_ok=True)
        if abs(u[-1]-6)<1e-9:u=u[:-1];points=points[:,:,:-1]
        rings=np.empty((*points.shape[:-1],3),np.float64);rings[...,:2]=points;rings[...,2]=z[None,:,None]
        vertices,faces=loft_mesh(rings)
        np.save(path/'vertices.npy',vertices);np.save(path/'faces.npy',faces);np.save(path/'u.npy',u);np.save(path/'z.npy',z)
        # Connectivity is a closed manifold by construction. Verify all triangles have positive area.
        area_min=float('inf');degenerate=0;volume=0.
        for start in range(0,len(faces),200000):
            tri=vertices[faces[start:start+200000]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1)/2
            area_min=min(area_min,float(area.min()));degenerate+=int(np.count_nonzero(area<1e-10));volume+=float(np.sum(tri[:,0]*np.cross(tri[:,1],tri[:,2]))/6)
        if degenerate:raise ValueError(f'degenerate triangles: {degenerate}')
        meta.update(kind='surface',model_id=path.name,vertex_count=len(vertices),face_count=len(faces),ring_shape=list(rings.shape[:3]),array_payload_bytes=vertices.nbytes+faces.nbytes+u.nbytes+z.nbytes,material_volume_nm3=abs(volume),min_triangle_area_nm2=area_min,degenerate_triangle_count=degenerate,topology='separate closed outward-oriented genus0 stripe solids; bottom and artificial Z-end caps retained',face_materials={'inside':1,'free_surface_outside':0,'bottom_outside':2,'bottom_rule':'side face f: contour index = floor(f/2) mod nu; u[index]>=5 identifies the single shared stripe/substrate interface; all other side faces are stripe/air','artificial_z_end_caps_outside':0,'end_caps_excluded_from_free_surface_metrics':True,'orientation':'outward from material1'},query='Intersections of actual saved triangle vertices and face connectivity in the containing Z slab; structured mesh optimization, not arbitrary mesh benchmark',triangle_sha256=file_hash(path/'faces.npy'),vertex_sha256=file_hash(path/'vertices.npy'))
        dump_json(path/'metadata.json',meta);return cls.load(path)

    @classmethod
    def from_observations(cls,obs,path):
        obs=Path(obs);meta=json.loads((obs/'metadata.json').read_text(encoding='utf-8'));meta.update(source_model=meta['model_id'],operation='direct_observation_loft_no_parametric_fit',source_observation_sha256=meta['observation_sha256'])
        return cls._store(np.load(obs/'points.npy',mmap_mode='r'),np.load(obs/'u.npy'),np.load(obs/'z.npy'),meta,path)

    @classmethod
    def from_model(cls,model,path,boundary_step_nm=10.,z_step_nm=40.):
        # Half-step shifted interior Z stations avoid the special case of exporting
        # interpolating splines only at their input knots (which equals T_direct).
        u=u_nodes(boundary_step_nm);z=z_nodes(model.bounds,z_step_nm,shifted=True)
        pts=np.empty((model.n_lines,len(z),len(u),2))
        for line in range(model.n_lines):
            for k,zp in enumerate(z):pts[line,k]=model.evaluate(line,u,zp)
        meta=dict(model.metadata,source_model=model.metadata['model_id'],operation='triangulate_reloaded_parametric_source',boundary_step_nm=boundary_step_nm,z_step_nm=z_step_nm,export_z_phase_nm=z_step_nm/2)
        return cls._store(pts,u,z,meta,path)

    @classmethod
    def load(cls,path):
        path=Path(path);obj=cls();obj._setup(json.loads((path/'metadata.json').read_text(encoding='utf-8')),path)
        obj.vertices=np.load(path/'vertices.npy',mmap_mode='r');obj.faces=np.load(path/'faces.npy',mmap_mode='r');obj.u=np.load(path/'u.npy');obj.z=np.load(path/'z.npy');obj._nl,obj._nz,obj._nu=obj.metadata['ring_shape']
        return obj

    def _section(self,line,z):
        if not self.bounds[4]<=z<=self.bounds[5]:return np.empty((0,2)),np.empty(0)
        slab=min(len(self.z)-2,max(0,int(np.searchsorted(self.z,z,side='right')-1)));alpha=(z-self.z[slab])/(self.z[slab+1]-self.z[slab])
        # The first triangle is [lower_i,upper_i,upper_i+1]. Use its actual
        # saved indices, not a bilinear quad, to retain diagonal intersections.
        start=(line*(self._nz-1)+slab)*self._nu*2;tri=self.vertices[self.faces[start:start+2*self._nu:2]]
        edge=(1-alpha)*tri[:,0,:2]+alpha*tri[:,1,:2];diagonal=(1-alpha)*tri[:,0,:2]+alpha*tri[:,2,:2]
        pts=np.stack([edge,diagonal],axis=1).reshape(-1,2)
        unext=np.r_[self.u[1:],6.];us=np.stack([self.u,(1-alpha)*self.u+alpha*unext],axis=1).ravel()
        keep=np.r_[True,np.linalg.norm(np.diff(pts,axis=0),axis=1)>1e-9];return np.vstack([pts[keep],pts[0]]),np.r_[us[keep],6.]

    def contour(self,line,z,step_nm=2.):return self._section(line,float(z))[0]
    def region_contour(self,line,z,region,step_nm=2.):
        j=REGIONS.index(region) if isinstance(region,str) else int(region);p,u=self._section(line,float(z));return p[(u>=j-1e-10)&(u<=j+1+1e-10)]
    def evaluate(self,line,u,z):
        p,us=self._section(line,float(z));uu=np.asarray(u,float)
        return np.stack([np.interp(uu,us,p[:,0]),np.interp(uu,us,p[:,1])],axis=-1)

    def mesh(self,boundary_step_nm=20.,z_step_nm=160.,line=None,z_range=None,roi=None,max_faces=200000):
        lines=list(range(self.n_lines)) if line is None else [int(line)]
        zr=self.bounds[4:6] if z_range is None else z_range
        if roi is not None:zr=roi[4:6];lines=[i for i in lines if self.centers[i]+1000>=roi[0] and self.centers[i]-1000<=roi[1]]
        exact=(boundary_step_nm<=self.metadata.get('boundary_step_nm',10) and z_step_nm<=self.metadata.get('z_step_nm',40)) or (roi is not None and roi[5]-roi[4]<=4000)
        if exact:
            slabs=np.flatnonzero((self.z[:-1]<=zr[1])&(self.z[1:]>=zr[0]));chunks=[]
            for i in lines:
                for slab in slabs:
                    start=(i*(self._nz-1)+slab)*self._nu*2;chunks.append(np.asarray(self.faces[start:start+self._nu*2]))
                cap_start=self._nl*(self._nz-1)*self._nu*2+i*2*self._nu
                if zr[0]<=self.z[0]:chunks.append(np.asarray(self.faces[cap_start:cap_start+self._nu]))
                if zr[1]>=self.z[-1]:chunks.append(np.asarray(self.faces[cap_start+self._nu:cap_start+2*self._nu]))
            if not chunks:return np.empty((0,3)),np.empty((0,3),np.int32)
            faces=np.concatenate(chunks)
            if roi is not None:
                tri=self.vertices[faces];lo=np.array(roi)[[0,2,4]];hi=np.array(roi)[[1,3,5]];faces=faces[np.all(tri.max(axis=1)>=lo,axis=1)&np.all(tri.min(axis=1)<=hi,axis=1)]
            ids,inverse=np.unique(faces,return_inverse=True);self.last_preview_metadata={'mode':'actual_saved_triangles','triangle_count':len(faces),'geometry_error_nm':0.}
            return np.asarray(self.vertices[ids]),inverse.reshape(-1,3).astype(np.int32)
        zi=np.flatnonzero((self.z>=zr[0])&(self.z<=zr[1]));zskip=max(1,int(z_step_nm/max(np.median(np.diff(self.z)),1)))
        zi=np.unique(np.r_[zi[::zskip],zi[-1]]) if len(zi) else np.array([],int)
        if len(zi)<2:return np.empty((0,3)),np.empty((0,3),np.int32)
        uskip=max(1,int(boundary_step_nm/self.metadata.get('boundary_step_nm',10)))
        ui=np.unique(np.r_[np.arange(0,self._nu,uskip),[np.argmin(abs(self.u-j)) for j in range(6)]])
        rings=self.vertices[:self._nl*self._nz*self._nu].reshape(self._nl,self._nz,self._nu,3)[np.ix_(lines,zi,ui)]
        self.last_preview_metadata={'mode':'display_only_reloft_of_subsampled_saved_rings','z_stride':zskip,'contour_stride':uskip,'actual_max_z_gap_nm':float(np.diff(self.z[zi]).max()),'not_for_metrics':True}
        return loft_mesh(rings)

    def edited_copy(self,path,line=1,z_center=400.,z_halfwidth=320.,displacement_nm=10.):
        pts=np.array(self.vertices[:self._nl*self._nz*self._nu].reshape(self._nl,self._nz,self._nu,3)[...,:2]);a=np.clip(1-((self.z-z_center)/z_halfwidth)**2,0,1)**2;b=np.where((self.u>=1)&(self.u<=2),np.sin(np.pi*(self.u-1))**2,0.)
        delta=displacement_nm*a[:,None]*b[None,:];pts[line,:,:,0]+=delta
        meta=dict(self.metadata,source_model=self.metadata['model_id'],operation='local_left_shoulder_vertex_edit_no_reconnection',edit={'line':line,'z_center':z_center,'z_halfwidth':z_halfwidth,'requested_max_displacement_nm':displacement_nm,'changed_vertex_x_coordinates':int(np.count_nonzero(delta)),'definition':'same compact quartic z × sin² shoulder physical displacement field evaluated at saved vertex parameters'})
        return self._store(pts,self.u,self.z,meta,path)
