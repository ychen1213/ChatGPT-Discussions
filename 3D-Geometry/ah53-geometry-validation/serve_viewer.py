"""Offline AH53 viewer. Queries are made against each saved model, never a substitute.

Run .venv\\Scripts\\python.exe serve_viewer.py [--port 8765] [--no-browser].
All geometry coordinates and API values are in nm.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
from datetime import datetime
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import socket
from pathlib import Path
import sys
import threading
import time
import traceback
from urllib.parse import parse_qs, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from ah53 import load_model

RUN_ROOT: Path | None = None
CATALOG: dict[str, dict] = {}
MODEL_LOCK = threading.RLock()
MESH_LOCK = threading.RLock()


def safe(value):
    if isinstance(value, np.ndarray): return safe(value.tolist())
    if isinstance(value, np.generic): return safe(value.item())
    if isinstance(value, dict): return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value): return None
    if isinstance(value, Path): return str(value)
    return value


def classify(metadata, identifier):
    token = (identifier + " " + str(metadata.get("operation", ""))).lower()
    kind = str(metadata.get("kind", metadata.get("representation", ""))).lower()
    if identifier.lower().startswith("reference") or kind == "reference": return "reference", "reference", ["A", "B1", "B2", "B3", "B4"], "合成参考"
    if kind in ("parametric", "p") or "_p_" in identifier.lower() or "parametric" in identifier.lower():
        return "parametric", "P", ["A", "B1", "B2", "B3"], "参数化 · 已保存系数"
    if "v_from_t_direct" in token or "v_from_tdirect" in token or "v_from_direct" in token or "b4" in token:
        return "voxel", "V_from_T_direct", ["B4"], "体素 · 直接三角面导出"
    if "v_from_t" in token or "b3" in token:
        return "voxel", "V_from_T_from_P", ["B3"], "体素 · 参数化经三角面导出"
    if "v_from_p" in token or "b2" in token:
        return "voxel", "V_from_P", ["B2"], "体素 · 参数化直接导出"
    if "t_from_p" in token or "b1" in token:
        return "surface", "T_from_P", ["B1", "B3"], "三角面 · 参数化导出"
    if kind in ("surface", "explicit", "triangle", "mesh") or "t_direct" in token or "surface" in token:
        return "surface", "T_direct", ["A", "B4"], "直接三角面 · 观测轮廓放样"
    if kind == "voxel" or "v_direct" in token or "voxel" in token:
        return "voxel", "V_direct", ["A"], "直接体素 · 参考中心采样"
    return kind, kind, ["A"], identifier


def discover():
    global RUN_ROOT, CATALOG
    candidates = [RUN_ROOT] if RUN_ROOT else sorted((ROOT / "results").glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = {}
    for run in candidates:
        if not run or not (run / "models").exists(): continue
        for path in sorted((run / "models").rglob("metadata.json")):
            try:
                meta = json.loads(path.read_text(encoding="utf-8"))
                if meta.get("kind") == "observations": continue
                ident = str(meta.get("model_id", path.parent.name))
                if "edit" in ident.lower(): continue
                kind, family, routes, label = classify(meta, ident)
                model = load_model(path.parent)
                bounds = np.asarray(model.bounds).tolist()
                kind = model.kind
                scene = str(meta.get("scene", "full" if bounds[1]-bounds[0] > 20000 else "local"))
                if scene not in ("full", "local"): scene = "full" if bounds[1]-bounds[0] > 20000 else "local"
                density = str(meta.get("density", "fine" if "fine" in ident.lower() else "coarse" if "coarse" in ident.lower() else "default"))
                spacing = getattr(model, "spacing", None)
                if spacing is not None: label += f" · {float(np.asarray(spacing).flat[0]):g} nm 单元"
                elif density in ("fine", "coarse"): label += " · " + {"fine":"精细", "coarse":"基础"}[density]
                result[ident] = dict(id=ident, kind=kind, family=family, routes=routes, label=label, scene=scene, bounds=bounds, density=density, path=path.parent, metadata=meta)
            except Exception as exc:
                print(f"Skip incomplete model {path}: {exc}", flush=True)
        if result:
            RUN_ROOT = run
            break
    CATALOG = result
    return [safe({k:v for k,v in d.items() if k not in ("path", "metadata")}) for d in result.values()]


@lru_cache(maxsize=18)
def model_for(identifier):
    if identifier not in CATALOG: raise ValueError(f"Unknown saved model: {identifier}")
    with MODEL_LOCK: return load_model(CATALOG[identifier]["path"])


def view_bounds(model, scope, z):
    b = np.array(model.bounds, dtype=float).copy()
    b[2] = -30
    b[3] = max(b[3], 340)
    if scope == "period": b[0], b[1] = max(b[0], -8000), min(b[1], 8000)
    if scope == "stripe":
        b[0], b[1] = -950, 950
        b[4], b[5] = max(b[4],z-600), min(b[5],z+600)
    if scope == "shoulder":
        b[0], b[1], b[2], b[3] = -880, -580, 205, 345
        b[4], b[5] = max(b[4],z-200), min(b[5],z+200)
    if b[5]-b[4] < 1: b[4] = b[5]-1
    return b


def choose_lines(model, bounds):
    centers = np.asarray(model.centers)
    return [i for i,c in enumerate(centers) if bounds[0]-1100 <= c <= bounds[1]+1100]


def resample_closed(points, count):
    p=np.asarray(points,float)
    if len(p)<3: return np.empty((0,2))
    if not np.allclose(p[0],p[-1]): p=np.vstack([p,p[0]])
    distances=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    keep=np.r_[True,np.diff(distances)>1e-10];p=p[keep];distances=distances[keep]
    target=np.linspace(0,distances[-1],count,endpoint=False)
    return np.column_stack([np.interp(target,distances,p[:,i]) for i in range(2)])


def point_poly_distance(points, poly):
    if not len(points) or not len(poly): return 0.
    a=np.asarray(poly);b=np.roll(a,-1,axis=0);d=b-a;den=np.sum(d*d,axis=1)
    maximum=0.
    for chunk in np.array_split(np.asarray(points), max(1,int(len(points)/400))):
        v=chunk[:,None,:]-a[None,:,:]
        t=np.clip(np.sum(v*d[None,:,:],axis=2)/np.maximum(den,1e-20),0,1)
        dist=np.linalg.norm(v-t[:,:,None]*d[None,:,:],axis=2)
        maximum=max(maximum,float(np.min(dist,axis=1).max()))
    return maximum


def voxel_overview(model, bounds, scope):
    """Loft saved-label contours for overview only; quantify the sampled loss.

    These are explicitly display triangles, not a new stored source model and
    never used by validation. Local scopes call raw exposed-cell mesh instead.
    """
    count=144
    zstep=320. if bounds[5]-bounds[4]>5000 else 160.
    zs=np.linspace(bounds[4]+model.spacing*.51,bounds[5]-model.spacing*.51,max(2,int(np.ceil((bounds[5]-bounds[4])/zstep))+1))
    vertices=[];faces=[];errors=[];sources=[]
    for line in choose_lines(model,bounds):
        rings=[]
        for z in zs:
            p=np.asarray(model.contour(line,float(z),step_nm=float(model.spacing)))
            ring=resample_closed(p,count)
            if len(ring)!=count: continue
            rings.append(ring)
        if len(rings)!=len(zs): continue
        offset=len(vertices)
        for z,ring in zip(zs,rings): vertices.extend(np.column_stack([ring,np.full(count,z)]))
        for k in range(len(zs)-1):
            for j in range(count):
                a=offset+k*count+j;b=offset+k*count+(j+1)%count;c=a+count;d=b+count
                faces.extend([[a,c,b],[b,c,d]])
        # Display caps triangulate by a central point, valid for x-simple sections.
        for k,flip in [(0,True),(len(zs)-1,False)]:
            center=np.mean(rings[k],axis=0);ci=len(vertices);vertices.append([*center,zs[k]])
            for j in range(count):
                tri=[ci,offset+k*count+j,offset+k*count+(j+1)%count]
                faces.append(tri[::-1] if flip else tri)
        for k in np.unique(np.linspace(0,len(zs)-2,min(7,len(zs)-1),dtype=int)):
            mid=(zs[k]+zs[k+1])/2
            real=np.asarray(model.contour(line,float(mid),step_nm=float(model.spacing)))
            preview=(rings[k]+rings[k+1])/2
            errors.append(max(point_poly_distance(real,preview),point_poly_distance(preview,real)))
    return np.asarray(vertices,dtype=np.float32),np.asarray(faces,dtype=np.int32),dict(mode="simplified_saved_voxel_contour_loft",z_step_nm=float(np.max(np.diff(zs))),contour_points=count,measured_sample_max_nm=max(errors,default=0),error_scope="每条纹最多 7 个 Z 中点，实际标签轮廓与显示轮廓双向线段距离；不是全域上界",note="全域简化预览；局部圆肩/单条纹读取原始体素外露面。")


def crop_mesh(vertices,faces,bounds):
    if not len(faces): return vertices,faces
    tri=vertices[faces]
    mask=np.ones(len(faces),bool)
    for axis in range(3): mask &= (tri[:,:,axis].max(axis=1)>=bounds[axis*2])&(tri[:,:,axis].min(axis=1)<=bounds[axis*2+1])
    faces=faces[mask]
    if not len(faces): return np.empty((0,3)),np.empty((0,3),dtype=int)
    used,inverse=np.unique(faces,return_inverse=True)
    return vertices[used],inverse.reshape(-1,3)


def preview_error(model,vertices,faces,bounds):
    """Actual display-triangle/XY-plane intersections, against the source model.

    This is a bounded-size sampled diagnostic, not a claimed Hausdorff bound.
    End caps and the intentionally cropped boundaries are excluded.
    """
    tri=vertices[faces]; zlo=tri[:,:,2].min(axis=1);zhi=tri[:,:,2].max(axis=1)
    tests=np.linspace(bounds[4],bounds[5],7)[1:-1]+.123
    maxima=[]
    for z in tests:
        t=tri[(zlo<z)&(zhi>z)]
        segments=[]
        for triangle in t:
            points=[]
            for a,b in ((0,1),(1,2),(2,0)):
                pa,pb=triangle[a],triangle[b]
                if (pa[2]<=z<pb[2]) or (pb[2]<=z<pa[2]):points.append(pa[:2]+(z-pa[2])/(pb[2]-pa[2])*(pb[:2]-pa[:2]))
            if len(points)==2:segments.append(points)
        if not segments:continue
        segments=np.asarray(segments)
        for line in choose_lines(model,bounds):
            center=model.centers[line]
            seg=segments[(segments[:,:,0].mean(axis=1)>center-1200)&(segments[:,:,0].mean(axis=1)<center+1200)]
            if not len(seg):continue
            actual=np.asarray(model.contour(line,float(z),step_nm=2.))
            if len(actual)>600:actual=actual[::int(np.ceil(len(actual)/600))]
            a=seg[:,0];d=seg[:,1]-a;den=np.sum(d*d,axis=1)
            maximum=0.
            for chunk in np.array_split(actual,max(1,len(actual)//160)):
                v=chunk[:,None,:]-a[None,:,:];p=np.clip(np.sum(v*d[None,:,:],axis=2)/np.maximum(den,1e-20),0,1)
                dist=np.linalg.norm(v-p[:,:,None]*d[None,:,:],axis=2);maximum=max(maximum,float(dist.min(axis=1).max()))
            maxima.append(max(maximum,point_poly_distance(np.concatenate([seg[:,0],seg.mean(axis=1)]),actual)))
    return dict(measured_sample_max_nm=max(maxima,default=0),sample_z_nm=tests.tolist(),error_scope="5 个 Z 平面、当前范围内条纹；真实显示三角片截面与源模型截面双向线段距离（源轮廓最多 600 点）；不是全域误差上界")


@lru_cache(maxsize=10)
def mesh_data(identifier,scope,z):
    with MESH_LOCK:
        preview_dir=RUN_ROOT/"previews";preview_dir.mkdir(exist_ok=True)
        inputs=sorted(CATALOG[identifier]["path"].glob("*"))
        signature=hashlib.sha256(("viewer_mesh_v4"+str([(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in inputs if p.is_file()])).encode()).hexdigest()
        cachefile=preview_dir/f"{identifier}_{scope}_{z:g}_display_mesh.json.gz"
        if cachefile.exists():
            with gzip.open(cachefile,"rt",encoding="utf-8") as stream:
                cached=json.load(stream)
            if cached.get("cache_signature")==signature:return cached["data"]
        model=model_for(identifier);bounds=view_bounds(model,scope,z)
        start=time.perf_counter()
        if model.kind=="voxel" and scope in ("full","period"):
            vertices,faces,display=voxel_overview(model,bounds,scope)
            display["note"]+=f" 显示抽样截面最大偏差 {display['measured_sample_max_nm']:.2f} nm（非全域上界）。"
        else:
            step=2 if scope=="shoulder" else 8 if scope=="stripe" else 30
            zstep=20 if scope=="shoulder" else 40 if scope=="stripe" else 320 if bounds[5]-bounds[4]>5000 else 160
            line=int(np.argmin(abs(model.centers))) if scope in ("stripe","shoulder") else None
            face_limit=750000 if model.kind=="voxel" and scope=="stripe" else 300000
            output=model.mesh(boundary_step_nm=step,z_step_nm=zstep,line=line,roi=bounds.tolist(),max_faces=face_limit)
            vertices,faces=np.asarray(output[0]),np.asarray(output[1])
            vertices,faces=crop_mesh(vertices,faces,bounds)
            display=dict(mode="raw_exposed_voxel_faces" if model.kind=="voxel" else "saved_triangle_preview" if model.kind=="surface" else "display_triangulation_of_saved_model",boundary_step_nm=step,z_step_nm=zstep,note="局部原始体素外露面" if model.kind=="voxel" else "原保存网格的显示预览" if model.kind=="surface" else "由已保存系数生成显示三角片；统计使用源模型。")
            if model.kind=="surface":
                display.update(getattr(model,"last_preview_metadata",{}))
                if display["mode"]=="actual_saved_triangles":display["note"]="直接读取原保存顶点与三角连接；局部未简化。"
            if model.kind in ("parametric","reference"):
                display["note"]=("全域简化预览；" if scope in ("full","period") else "局部显示三角化；")+display["note"]
            if scope in ("full","period") and model.kind!="voxel":
                display.update(preview_error(model,vertices,faces,bounds))
                display["note"]+=f" 显示抽样截面最大偏差 {display['measured_sample_max_nm']:.2f} nm（非全域上界）。"
        display.update(vertex_count=len(vertices),face_count=len(faces),build_seconds=time.perf_counter()-start,coordinate_units="nm",scope=scope)
        if not len(vertices): raise ValueError("所选观察区域中没有表面，请改变 Z 截面或观察范围。")
        label=CATALOG[identifier]["label"]
        if model.kind=="voxel": label += " · 局部原始阶梯边界" if scope in ("stripe","shoulder") else " · 全域简化预览"
        elif scope in ("full","period"): label += " · 全域预览"
        payload=safe(dict(vertices=vertices.ravel(),faces=faces.ravel(),view_bounds=bounds,metadata=dict(model.metadata,model_id=identifier),display=display,display_label=label))
        (preview_dir/f"{identifier}_{scope}_display.json").write_text(json.dumps(safe(dict(source_model=identifier,display=display)),ensure_ascii=False,indent=2),encoding="utf-8")
        with gzip.open(cachefile,"wt",encoding="utf-8",compresslevel=3) as stream:json.dump(dict(cache_signature=signature,data=payload),stream,ensure_ascii=False,separators=(",",":"))
        return payload


def overlay_models(identifier):
    current=CATALOG[identifier];scene=current["scene"]
    result=[(identifier,"current")]
    for family,role in [("reference","reference"),("T_direct","direct"),("T_from_P","derived")]:
        candidates=[d for d in CATALOG.values() if d["scene"]==scene and d["family"]==family and d["id"]!=identifier]
        candidates.sort(key=lambda d:(d["density"]!="fine",d["id"]))
        if candidates: result.append((candidates[0]["id"],role))
    return result


def section_data(identifier,scope,z,y,overlay):
    selected=model_for(identifier);b=view_bounds(selected,scope,z)
    line=int(np.argmin(np.abs(np.asarray(selected.centers))))
    # XY always follows the central stripe. It remains legible in the full view.
    xy_bounds=[-950,950,-30,max(340,float(selected.bounds[3]))] if scope!="shoulder" else [-880,-580,205,345]
    xz_bounds=[-950,950,float(b[4]),float(b[5])]
    models=overlay_models(identifier) if overlay else [(identifier,"current")]
    xy=[];xz=[]
    note="中央条纹；X、Y、Z 均为 nm，横纵轴独立刻度。"
    for ident,role in models:
        model=model_for(ident);li=int(np.argmin(np.abs(np.asarray(model.centers))))
        z_actual=float(np.clip(z,float(model.bounds[4])+1e-7,float(model.bounds[5])-1e-7))
        contour=np.asarray(model.contour(li,z_actual,step_nm=1.))
        xy.append(dict(role=role,model_id=ident,lines=[contour]))
        if model.kind=="voxel":
            spacing=float(model.spacing);origin=np.asarray(model.origin)
            iz=int(np.floor((z_actual-origin[2])/spacing));iy=int(np.floor((y-origin[1])/spacing))
            if role=="current": note=f"体素实际切片：Z 层 [{origin[2]+iz*spacing:g}, {origin[2]+(iz+1)*spacing:g}) nm；Y 层 [{origin[1]+iy*spacing:g}, {origin[1]+(iy+1)*spacing:g}) nm；单元 {spacing:g} nm。坐标轴独立刻度。"
            lo=max(0,int(np.floor((b[4]-origin[2])/spacing)));hi=min(model.labels.shape[0],int(np.ceil((b[5]-origin[2])/spacing)))
            zz=origin[2]+(np.arange(lo,hi)+.5)*spacing
            L,R=model.boundaries(li,np.full(len(zz),y),zz)
            ze=origin[2]+np.arange(lo,hi+1)*spacing
            left=np.column_stack([np.repeat(L,2),np.column_stack([ze[:-1],ze[1:]]).ravel()])
            right=np.column_stack([np.repeat(R,2),np.column_stack([ze[:-1],ze[1:]]).ravel()])
        else:
            zz=np.linspace(max(b[4],model.bounds[4])+1e-6,min(b[5],model.bounds[5])-1e-6,max(241,int(np.ceil((b[5]-b[4])/40))+1))
            if role=="current":note+=f" XZ 曲线采样 ΔZ ≤ {np.diff(zz).max():.2f} nm；几何边界按需查询。"
            L,R=model.boundaries(li,np.full(len(zz),y),zz)
            left=np.column_stack([L,zz]);right=np.column_stack([R,zz])
        poly=np.vstack([left,right[::-1],left[:1]]) if len(left) else np.empty((0,2))
        xz.append(dict(role=role,model_id=ident,lines=[poly]))
    return safe(dict(z=z,y=y,xy=xy,xz=xz,xy_bounds=xy_bounds,xz_bounds=xz_bounds,note=note,query_source="saved model contour and material boundaries; no cross-branch replacement",models=[m[0] for m in models]))


class LocalServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can admit duplicate listeners, unlike POSIX behavior.
    # Exclusive bind makes the occupied-port fallback real and deterministic.
    allow_reuse_address=False
    def server_bind(self):
        if hasattr(socket,"SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,fmt,*args):
        if "/api/" in str(args[0] if args else ""): print(datetime.now().strftime("%H:%M:%S"),fmt%args,flush=True)
    def json_response(self,value,status=200):
        payload=json.dumps(safe(value),ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8")
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(payload)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        url=urlsplit(self.path)
        if url.path=="/favicon.ico":
            self.send_response(204);self.end_headers();return
        if not url.path.startswith("/api/"):
            if url.path=="/": self.path="/viewer/index.html"
            return super().do_GET()
        try:
            q={k:v[0] for k,v in parse_qs(url.query).items()}
            if url.path=="/api/catalog": return self.json_response(dict(models=discover(),run=str(RUN_ROOT)))
            ident=q.get("model","");scope=q.get("scope","full");z=float(q.get("z",0));y=float(q.get("y",150))
            if scope not in ("full","period","stripe","shoulder"): raise ValueError("Unknown scope")
            if not math.isfinite(z) or not math.isfinite(y): raise ValueError("Coordinates must be finite")
            if url.path=="/api/mesh": return self.json_response(mesh_data(ident,scope,round(z,3) if scope in ("shoulder","stripe") else 0))
            if url.path=="/api/sections": return self.json_response(section_data(ident,scope,z,y,q.get("overlay","1")=="1"))
            self.json_response(dict(error="Unknown API"),404)
        except Exception as exc:
            traceback.print_exc();self.json_response(dict(error=str(exc)),500)
    def do_POST(self):
        if self.path!="/api/screenshot": return self.json_response(dict(error="Unknown endpoint"),404)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size>20_000_000: raise ValueError("Screenshot exceeds 20 MB")
            data=json.loads(self.rfile.read(size));raw=base64.b64decode(data["png"].split(",",1)[1],validate=True)
            if not raw.startswith(b"\x89PNG\r\n\x1a\n"): raise ValueError("Expected PNG")
            directory=RUN_ROOT/"figures"/"screenshots";directory.mkdir(parents=True,exist_ok=True)
            stem="AH53_view_"+datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file=directory/(stem+".png");file.write_bytes(raw)
            file.with_suffix(".json").write_text(json.dumps(data.get("metadata",{}),ensure_ascii=False,indent=2),encoding="utf-8")
            self.json_response(dict(file=str(file),name=file.name))
        except Exception as exc: self.json_response(dict(error=str(exc)),400)


def main():
    global RUN_ROOT
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8765);parser.add_argument("--no-browser",action="store_true");parser.add_argument("--results",type=Path);args=parser.parse_args()
    if args.results: RUN_ROOT=args.results.resolve()
    models=discover()
    if not models: raise SystemExit("No saved models. Run .venv\\Scripts\\python.exe run_validation.py first.")
    try: server=LocalServer(("127.0.0.1",args.port),Handler)
    except OSError:
        server=LocalServer(("127.0.0.1",0),Handler)
        print(f"Port {args.port} busy; selected {server.server_address[1]}.",flush=True)
    address=f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"AH53 offline viewer: {address}\nResults: {RUN_ROOT}\nKeep this terminal open. Ctrl+C stops the server.",flush=True)
    if not args.no_browser: threading.Timer(.8,lambda:webbrowser.open(address)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__=="__main__": main()
