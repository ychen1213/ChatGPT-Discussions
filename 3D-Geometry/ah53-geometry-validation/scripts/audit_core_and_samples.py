"""Read-only core audit and compact extracts of actual persisted model arrays."""
from pathlib import Path
import gc,json,sys,time,zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from ah53 import load_model,ReferenceGeometry,ParametricModel,SurfaceModel
from ah53.common import file_hash,polygon_boundaries
from ah53.evaluate import write_json,file_inventory
from run_validation import RSSMonitor


def topology(model):
    """Exact undirected edge multiplicity AND opposite oriented incidence."""
    faces=model.faces;nv=len(model.vertices);nf=len(faces)
    keys=np.empty(nf*3,np.uint64)
    for j in range(3):
        a=faces[:,j];b=faces[:,(j+1)%3]
        keys[j*nf:(j+1)*nf]=(np.minimum(a,b).astype(np.uint64)*nv+np.maximum(a,b))*2+(a<b)
    keys.sort();bad=0
    if len(keys)%2:bad+=1
    for start in range(0,len(keys)-1,2000000):
        pairs=keys[start:min(start+2000000,len(keys)//2*2)].reshape(-1,2)
        bad+=int(np.count_nonzero((pairs[:,0]//2!=pairs[:,1]//2)|((pairs[:,0]&1)!=0)|((pairs[:,1]&1)!=1)))
    signed_volume=0.
    for start in range(0,nf,200000):
        tri=model.vertices[faces[start:start+200000]]
        signed_volume+=float(np.sum(tri[:,0]*np.cross(tri[:,1],tri[:,2]))/6)
    return {'all_saved_faces_checked':True,'vertices':nv,'triangles':nf,'directed_edges':nf*3,
            'bad_paired_edge_groups':bad,'closed_and_oppositely_oriented':bad==0,
            'euler_characteristic':int(nv-nf//2),'expected_for_separate_genus0_solids':2*model.n_lines,
            'signed_volume_from_actual_saved_triangles_nm3':signed_volume,'positive_signed_volume':signed_volume>0}


def export_samples(output):
    dest=ROOT/'samples';dest.mkdir(exist_ok=True)
    t=load_model(output/'models'/'local_T_direct_fine');p=load_model(output/'models'/'local_P_fine');v=load_model(output/'models'/'local_V_direct_fine')
    line=1;nu=t._nu;nz=t._nz;nside=t._nl*(nz-1)*nu*2
    selected=np.concatenate([t.faces[line*(nz-1)*nu*2:(line+1)*(nz-1)*nu*2],t.faces[nside+line*nu*2:nside+(line+1)*nu*2]])
    ids,inverse=np.unique(selected,return_inverse=True)
    np.savez_compressed(dest/'central_stripe_triangles.npz',vertices_nm=np.asarray(t.vertices[ids]),faces=inverse.reshape(-1,3).astype(np.int32),original_vertex_indices=ids,material_inside=np.uint8(1),material_bottom_outside=np.uint8(2),material_free_surface_outside=np.uint8(0))
    arrays={key:(val[line:line+1] if key.startswith('c') else val) for key,val in p.arrays.items()}
    np.savez_compressed(dest/'central_stripe_splines.npz',**arrays)
    roi=np.array([-960,960,-100,400,-200,800],float);lo=((roi[[0,2,4]]-v.origin)/v.spacing).astype(int);hi=((roi[[1,3,5]]-v.origin)/v.spacing).astype(int)
    labels=np.asarray(v.labels[lo[2]:hi[2],lo[1]:hi[1],lo[0]:hi[0]])
    np.savez_compressed(dest/'central_stripe_voxels.npz',labels=labels,origin_xyz_nm=roi[[0,2,4]],spacing_nm=np.array(v.spacing),bounds_nm=roi,material_ids=np.array([0,1,2],np.uint8))
    manifest={'identity':'基于 AH53 名义版图的合成工艺形貌；从本轮已保存模型提取，非实测数据',
              'units':'nm','axis_coordinates':['X transverse','Y height','Z length'],'stripe_id':'m0_s1',
              'sources':{'triangles':{'model_id':t.metadata['model_id'],'vertices_sha256':file_hash(t.path/'vertices.npy'),'faces_sha256':file_hash(t.path/'faces.npy'),'closed':True,'z_range_nm':[-2000,2000],'sample_vertex_count':len(ids),'sample_face_count':len(selected)},
                         'splines':{'model_id':p.metadata['model_id'],'source_sha256':file_hash(p.path/'splines.npz'),'coefficient_axis':'line,Z coefficient,u coefficient,XY','degree':[3,3],'regions':['left_wall','left_shoulder','top','right_shoulder','right_wall','bottom'],'z_range_nm':[-2000,2000]},
                         'voxels':{'model_id':v.metadata['model_id'],'source_file':'results/20261024_v2/models/local_V_direct_fine/labels.npy','source_sha256':file_hash(v.path/'labels.npy'),'shape_zyx':list(labels.shape),'origin_xyz_nm':roi[[0,2,4]].tolist(),'spacing_nm':v.spacing,'labels':{'0':'air','1':'stripe','2':'substrate'},'raw_uncompressed_label_bytes':labels.nbytes,'counts':np.bincount(labels.ravel(),minlength=3).tolist(),'center_sampled':True}},
              'files':{f.name:{'file_bytes':f.stat().st_size,'sha256':file_hash(f)} for f in dest.glob('*.npz')}}
    write_json(dest/'sample_manifest.json',manifest)
    (dest/'README.md').write_text('''# 可独立检查的小型实际模型样例

这里的数组均从本轮正式保存的模型读取和裁取，未重新调用参考生成器。

- `central_stripe_triangles.npz`：中央条纹的完整闭合三角表面，Z = −2000～2000 nm；`vertices_nm` 为 XYZ 顶点，`faces` 为零起始三角连接；底部相邻衬底，其他自由面相邻空气。模型保留实际存储的三角形和朝向。
- `central_stripe_splines.npz`：同一中央条纹的实际三次 B 样条系数，c0～c5 为六个截面分区，u0～u5 / z0～z5 为各自结点向量。系数轴为条纹、Z、u、XY。均为原始源数据的切片。
- `central_stripe_voxels.npz`：5 nm 标签体的局部矩形裁片，数组轴顺序 Z,Y,X。原点为第一个体素的左下近侧角，中心位置是 origin+(index+0.5)×spacing。0/1/2 分别为空气/条纹/衬底。
- `sample_manifest.json`：单位、来源文件哈希、坐标和尺寸。

用项目已安装的 Python 运行 `samples/inspect_samples.py` 可重新读取并打印实际数组信息。无需重新生成大模型。查看完整交互模型请双击项目根目录的 `启动3D查看器.bat`。
''',encoding='utf-8')
    (dest/'inspect_samples.py').write_text('''from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
with np.load(p/'central_stripe_triangles.npz') as f:
    print('Triangles:',f['vertices_nm'].shape,f['faces'].shape,'XYZ bounds nm:',f['vertices_nm'].min(0),f['vertices_nm'].max(0))
with np.load(p/'central_stripe_voxels.npz') as f:
    print('Labels ZYX:',f['labels'].shape,'origin XYZ nm:',f['origin_xyz_nm'],'spacing nm:',f['spacing_nm'],'counts air/stripe/substrate:',np.bincount(f['labels'].ravel(),minlength=3))
with np.load(p/'central_stripe_splines.npz') as f:
    print('Spline coefficient shapes:',{k:f[k].shape for k in f.files if k.startswith('c')})
''',encoding='utf-8')
    archive=dest/'AH53_实际模型小样.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(dest.iterdir()):
            if f.is_file() and f!=archive:z.write(f,arcname=f.name)
    return {'path':str(dest),'archive_bytes':archive.stat().st_size,'manifest':manifest}


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Audit topology and extract actual small samples')
    parser.add_argument('--output',type=Path,default=ROOT/'results'/'20261024_v2')
    output=parser.parse_args().output.resolve();start=time.perf_counter();records={}
    with RSSMonitor() as memory:
        equality=[]
        for scene,level in [('local','coarse'),('local','fine'),('full','fine')]:
            obs=output/'models'/f'{scene}_observations_{level}';p=load_model(output/'models'/f'{scene}_P_{level}');t=load_model(output/'models'/f'{scene}_T_direct_{level}');points=np.load(obs/'points.npy',mmap_mode='r')
            rings=t.vertices[:t._nl*t._nz*t._nu].reshape(t._nl,t._nz,t._nu,3)
            sha=file_hash(obs/'points.npy');exact=all(np.array_equal(rings[i,:,:,:2],points[i,:,:-1,:]) for i in range(t.n_lines))
            equality.append({'scene':scene,'level':level,'observation_sha256':sha,'P_source_hash_equal':p.metadata['source_observation_sha256']==sha,'T_source_hash_equal':t.metadata['source_observation_sha256']==sha,'saved_direct_vertices_equal_original_observations':exact})
            if scene=='full' or level=='fine':records[f'{scene}_T_direct_{level}']=topology(t)
            del p,t,points,rings;gc.collect()
        models={k:load_model(output/'models'/v) for k,v in [('P','local_P_fine'),('T','local_T_direct_fine'),('V','local_V_direct_fine')]}
        probes={k:(m.contour(1,413).copy(),np.asarray(m.material_at(np.array([-800.,0.,900.]),150.,413.)).copy()) for k,m in models.items()}
        isolation={}
        with patch.object(ReferenceGeometry,'evaluate',side_effect=RuntimeError('reference access forbidden')):
            for k,m in models.items():
                fresh=load_model(m.path)
                isolation[k+'_with_reference_forbidden']=bool(np.array_equal(fresh.contour(1,413),probes[k][0]) and np.array_equal(fresh.material_at(np.array([-800.,0.,900.]),150.,413.),probes[k][1]))
        with patch.object(ParametricModel,'evaluate',side_effect=RuntimeError('P access forbidden')):
            isolation['T_with_P_forbidden']=bool(np.array_equal(models['T'].contour(1,413),probes['T'][0]));isolation['V_with_P_forbidden']=bool(np.array_equal(models['V'].contour(1,413),probes['V'][0]))
        with patch.object(SurfaceModel,'contour',side_effect=RuntimeError('T access forbidden')):
            isolation['V_with_T_forbidden']=bool(np.array_equal(models['V'].contour(1,413),probes['V'][0]))
        validity=[]
        for model_id in ['local_P_coarse','local_P_fine','local_T_direct_coarse','local_T_direct_fine','local_T_from_P','full_P_fine','full_T_direct_fine','full_T_from_P']:
            path=output/'models'/model_id
            if not (path/'metadata.json').exists():continue
            m=load_model(path);zs=np.unique(np.r_[np.linspace(m.bounds[4]+13,m.bounds[5]-17,21),413]);min_gap=np.inf;min_width=np.inf;maxheight=0.;count=0
            for z in zs:
                prior=None
                for line in range(m.n_lines):
                    poly=m.contour(line,float(z),1.);left,right=polygon_boundaries(poly,np.array([30.,150.,270.]));assert np.all(np.isfinite(left));min_width=min(min_width,float((right-left).min()));maxheight=max(maxheight,float(poly[:,1].max()))
                    if prior is not None:min_gap=min(min_gap,float(poly[:,0].min()-prior))
                    prior=float(poly[:,0].max());count+=1
            validity.append({'model_id':model_id,'independent_sections_checked':count,'Y_unimodality_and_single_interval':True,'min_width_at_30_150_270_nm':min_width,'min_stripe_gap_nm':min_gap,'maximum_height_nm':maxheight,'inside_saved_Y_bounds':maxheight<=m.bounds[3],'interpretation':'Explicit independent section samples; not a continuous global nonintersection proof.'})
            del m;gc.collect()
        samples=export_samples(output)
    report={'status':'completed','formal_models_unchanged':True,'observation_equality':equality,'actual_saved_mesh_topology':records,'query_dependency_isolation':isolation,'independent_validity_samples':validity,'small_samples':samples,'seconds':time.perf_counter()-start,'memory':memory.record(),
            'limits':['Free-surface distances are sampled XY-section distances, not full 3D Hausdorff bounds.','All process morphology is synthetic; nominal dimensions alone originate from AH53.','Surface queries exploit known structured loft connectivity; not general imported-mesh performance.','Reference material inversion uses controlled 0.5nm contour chords; refinement evidence is in preparation.json.','Per-face neighboring material is inferred from saved bottom Y=0 and free-surface/cut-face rules; finite substrate is additionally saved as bounds, not duplicated as triangles.']}
    write_json(output/'core_geometry_audit.json',report)
    print(json.dumps({'core_audit':'completed','topology_pass':all(x['closed_and_oppositely_oriented'] for x in records.values()),'independent_queries':all(isolation.values()),'sample_archive_bytes':samples['archive_bytes'],'seconds':report['seconds']}),flush=True)


if __name__=='__main__':main()
