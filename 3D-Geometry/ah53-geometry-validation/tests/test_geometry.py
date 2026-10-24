import numpy as np
from ah53 import ReferenceGeometry,build_observations,ParametricModel,SurfaceModel,VoxelModel,load_model

def test_nominal_and_crop_identity():
    local=ReferenceGeometry('local');full=ReferenceGeometry('full')
    assert np.array_equal(local.centers,[-3200,0,3200])
    assert np.array_equal(full.centers,[-19200,-16000,-12800,-3200,0,3200,12800,16000,19200])
    for i in range(3):
        for z in (-1793,123,400,1500):
            assert np.array_equal(local.contour(i,z),full.contour(i+3,z))

def test_reference_g1_and_material_domain():
    r=ReferenceGeometry()
    for line in range(3):
        for z in (-1500,400,1677):
            for join in (1,2,3,4):
                eps=1e-6;p=r.evaluate(line,np.array([join-eps,join,join+eps]),z);a=p[1]-p[0];b=p[2]-p[1];cos=np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b)
                assert cos>1-1e-8,(join,cos)
            p=r.contour(line,z,.5);peak=np.argmax(p[:,1]);assert np.all(np.diff(p[:peak+1,1])>=-1e-8)
    l,rr=r.boundaries(1,np.array([-1,150,500]),0);assert np.isnan(l[[0,2]]).all();assert rr[1]>l[1]
    assert r.material_at(0,-10,0)==2
    assert r.material_at(0,150,0)==1
    assert r.material_at(0,500,0)==0

def test_saved_branches_and_real_triangles(tmp_path):
    r=ReferenceGeometry();r.bounds[4:6]=[-160,160];r.metadata['bounds']=r.bounds.tolist()
    obs=build_observations(r,tmp_path/'obs',20,80);p=ParametricModel.from_observations(obs,tmp_path/'p');t=SurfaceModel.from_observations(obs,tmp_path/'t')
    for z in (-80,0,80):assert np.max(abs(p.contour(1,z,20)-r.contour(1,z,20)))<1e-8
    faces=np.asarray(t.faces);edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);keys=np.sort(edges,axis=1);unique,counts=np.unique(keys,axis=0,return_counts=True);assert np.all(counts==2)
    signed=np.sign(edges[:,1]-edges[:,0]);_,inverse=np.unique(keys,axis=0,return_inverse=True);assert np.all(np.bincount(inverse,weights=signed)==0)
    tri=t.vertices[t.faces];signedvolume=np.sum(tri[:,0]*np.cross(tri[:,1],tri[:,2]))/6;assert signedvolume>0
    # Plane intersection must contain diagonal crossings, not only ring edges.
    section=t.contour(1,33);assert len(section)>len(t.u)+1
    saved=load_model(tmp_path/'p');assert np.array_equal(saved.contour(1,33),p.contour(1,33))

def test_voxel_labels_and_exposed_faces(tmp_path):
    r=ReferenceGeometry();r.bounds=np.array([-8000,8000,-100,400,-20,20],float);r.metadata['bounds']=r.bounds.tolist()
    v=VoxelModel.from_model(r,tmp_path/'v',10);assert v.labels.shape==(4,50,1600)
    assert v.material_at(0,150,0)==1;assert v.material_at(0,-50,0)==2
    l,rr=v.boundaries(1,150,0);assert l%10==0 and rr%10==0
    vertices,faces=v.mesh(roi=[-900,-650,200,330,-20,20]);assert len(vertices)>0
    assert np.allclose((vertices-v.origin)/10,np.round((vertices-v.origin)/10))
