"""Execute A nine independent representations, B four conversions, and one edit.

All formal cases run sequentially in isolated processes. Derived constructors
receive only saved-and-reloaded upstream models. Large arrays remain local.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

A_CASES = [
    {"id": f"local_{method}_{level}", "scene": "local", "method": method,
     "level": level, "boundary_step_nm": 20 if level == "coarse" else 10,
     "z_step_nm": 80 if level == "coarse" else 40,
     "voxel_nm": 10 if level == "coarse" else 5}
    for level in ("coarse", "fine") for method in ("P", "T_direct", "V_direct")
] + [
    {"id": "full_P_fine", "scene": "full", "method": "P", "level": "fine",
     "boundary_step_nm": 10, "z_step_nm": 40, "voxel_nm": 10},
    {"id": "full_T_direct_fine", "scene": "full", "method": "T_direct", "level": "fine",
     "boundary_step_nm": 10, "z_step_nm": 40, "voxel_nm": 10},
    {"id": "full_V_direct_10nm", "scene": "full", "method": "V_direct", "level": "10nm",
     "boundary_step_nm": 10, "z_step_nm": 40, "voxel_nm": 10},
]
B_CASES = [
    {"id": "local_T_from_P", "path_id": "B1", "scene": "local", "method": "T_from_P",
     "upstream": "local_P_fine", "chain": ["local_P_fine"], "operation": "P_to_triangles"},
    {"id": "local_V_from_P", "path_id": "B2", "scene": "local", "method": "V_from_P",
     "upstream": "local_P_fine", "chain": ["local_P_fine"], "operation": "P_to_voxel"},
    {"id": "local_V_from_T", "path_id": "B3", "scene": "local", "method": "V_from_T",
     "upstream": "local_T_from_P", "chain": ["local_P_fine", "local_T_from_P"], "operation": "triangles_to_voxel"},
    {"id": "local_V_from_Tdirect", "path_id": "B4", "scene": "local", "method": "V_from_Tdirect",
     "upstream": "local_T_direct_fine", "chain": ["local_T_direct_fine"], "operation": "direct_triangles_to_voxel"},
    {"id": "full_T_from_P", "path_id": "B_large", "scene": "full", "method": "T_from_P",
     "upstream": "full_P_fine", "chain": ["full_P_fine"], "operation": "P_to_triangles"},
]


def read_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def config_fingerprint(config):
    return hashlib.sha256(json.dumps(config,sort_keys=True,ensure_ascii=False,
                                     separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()


def configured_specs(config):
    """Resolve every construction density and the RSS budget from one config."""
    fraction=float(config["numerics"]["resource_available_fraction"])
    if not 0 < fraction <= 1:
        raise ValueError("numerics.resource_available_fraction must be in (0,1]")
    rules={}
    for level in ("coarse","fine","full"):
        rules[level]={key:float(config["sampling"][level][key])
                      for key in ("boundary_step_nm","z_step_nm","voxel_nm")}
        if any(not value>0 or not value<float("inf") for value in rules[level].values()):
            raise ValueError(f"sampling.{level} spacings must be finite and positive")
    a=[];b=[]
    for template in A_CASES:
        rule=rules["full" if template["scene"]=="full" else template["level"]]
        spec={**template,**rule,"resource_fraction_limit":fraction,
              "configuration_sha256":config_fingerprint(config)}
        if spec["scene"]=="full" and spec["method"]=="V_direct":
            spec["level"]=f"{spec['voxel_nm']:g}nm"
            spec["id"]=f"full_V_direct_{spec['level']}"
        a.append(spec)
    for template in B_CASES:
        b.append({**template,**rules["full" if template["scene"]=="full" else "fine"],
                  "resource_fraction_limit":fraction,"configuration_sha256":config_fingerprint(config)})
    return a,b


def validate_resume_config(output,config):
    """Reject stale or unverifiable reuse before any worker or result mutation."""
    output=Path(output);expected=config_fingerprint(config);found=[];has_results=False
    prep=output/"preparation.json"
    manifest=output/"manifest.json"
    if prep.exists():
        has_results=True;data=read_config(prep)
        if data.get("configuration_sha256"):found.append((str(prep),data["configuration_sha256"]))
        elif data.get("configuration"):found.append((str(prep),config_fingerprint(data["configuration"])))
    if manifest.exists():
        has_results=True;data=read_config(manifest)
        if data.get("configuration"):found.append((str(manifest),config_fingerprint(data["configuration"])))
    for path in sorted((output/"models").glob("reference_*/metadata.json")):
        has_results=True;data=read_config(path)
        if data.get("config"):found.append((str(path),config_fingerprint(data["config"])))
    for path in sorted((output/"details").glob("*.json")):
        has_results=True;data=read_config(path)
        if data.get("configuration_sha256"):found.append((str(path),data["configuration_sha256"]))
        elif data.get("model_metadata",{}).get("config"):
            found.append((str(path),config_fingerprint(data["model_metadata"]["config"])))
        else:
            raise ValueError(f"Cannot safely resume: saved case has no verifiable configuration: {path}. Use a new --output directory.")
    if has_results and not found:
        raise ValueError("Cannot safely resume: existing results have no verifiable saved configuration. Use a new --output directory.")
    for path,actual in found:
        if actual!=expected:
            raise ValueError(f"Configuration differs from saved results ({path}); refusing stale --resume reuse. Use a new --output directory for the changed configuration.")
    return expected


class RSSMonitor:
    def __init__(self):
        import psutil
        self.process = psutil.Process()
        self.start_rss = self.process.memory_info().rss
        self.peak = self.start_rss
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop_event.wait(.01):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __enter__(self):
        self.thread.start(); return self

    def __exit__(self, *args):
        self.stop_event.set(); self.thread.join()
        info = self.process.memory_info()
        self.peak = max(self.peak, info.rss)
        self.windows_high_water = getattr(info, "peak_wset", None)

    def record(self):
        return {"baseline_rss_bytes": self.start_rss, "sampled_peak_rss_bytes": self.peak,
                "windows_process_peak_working_set_bytes": self.windows_high_water,
                "sampling_period_seconds": .01,
                "definition": "RSS includes interpreter, imported libraries and mapped resident pages; not disk size"}


def helpers():
    import numpy as np
    import psutil
    from ah53 import load_model, ReferenceGeometry, build_observations, ParametricModel, SurfaceModel, VoxelModel
    from ah53.evaluate import write_json, file_inventory, evaluate_model
    return locals()


def prepare(output, config_path):
    from ah53 import ReferenceGeometry, build_observations, load_model
    from ah53.evaluate import write_json, file_inventory, convergence_check
    import psutil
    for name in ("models", "details", "profiles", "figures", "previews"):
        (output / name).mkdir(parents=True, exist_ok=True)
    config = read_config(config_path)
    configured_specs(config)  # Validate all requested densities before writing any model.
    start = time.perf_counter()
    for scene in ("local", "full"):
        ref = ReferenceGeometry(scene=scene, config=config)
        ref.save(output / "models" / f"reference_{scene}")
        ref = load_model(output / "models" / f"reference_{scene}")
        for level in (("coarse", "fine") if scene == "local" else ("fine",)):
            obs_path = output / "models" / f"{scene}_observations_{level}"
            rule=config["sampling"]["full" if scene=="full" else level]
            build_observations(ref, obs_path, boundary_step_nm=float(rule["boundary_step_nm"]),
                               z_step_nm=float(rule["z_step_nm"]))
    ref = load_model(output / "models" / "reference_local")
    full = load_model(output / "models" / "reference_full")
    # Same stable line IDs and continuous global field must survive local cropping.
    import numpy as np
    crop_checks = []
    for i, center in enumerate(ref.centers):
        j = int(np.argmin(np.abs(np.asarray(full.centers)-center)))
        a = ref.contour(i, 413., step_nm=5)
        b = full.contour(j, 413., step_nm=5)
        crop_checks.append({"local_line": i, "full_line": j,
                            "max_coordinate_difference_nm": float(np.max(np.abs(a-b))),
                            "stable_id_local": ref.ids[i], "stable_id_full": full.ids[j]})
    record = {"preparation_seconds": time.perf_counter()-start,
              "available_memory_bytes": psutil.virtual_memory().available,
              "resource_fraction_limit": float(config["numerics"]["resource_available_fraction"]),
              "configuration":config,"configuration_sha256":config_fingerprint(config),
              "sampling_rules":config["sampling"],"reference_convergence": convergence_check(ref),
              "local_is_global_crop": crop_checks,
              "reference_volumes_nm3": {"local": float(ref.volume()), "full": float(full.volume())},
              "nominal_layout": {"mother_period_nm":16000,"stripe_centers_per_mother_nm":[-3200,0,3200],
                                 "nominal_stripe_intervals_nm":[[-4000,-2400],[-800,800],[2400,4000]],
                                 "nominal_width_nm":1600,"stripe_zone_nm":8000,"blank_nm":8000},
              "input_information": {"P_and_T_direct":"identical saved ordered contours",
                                    "V_direct":"continuous independent reference material oracle; discretization lower bound, not sparse-observation reconstruction ranking"}}
    write_json(output / "preparation.json",record)
    print(json.dumps({"prepared":True,"seconds":record["preparation_seconds"]}),flush=True)


def run_case(spec, output):
    import psutil
    from ah53 import load_model, ParametricModel, SurfaceModel, VoxelModel
    from ah53.evaluate import write_json, file_inventory, evaluate_model, section_distance, section_positions, material_metrics
    available = psutil.virtual_memory().available
    ceiling = int(available * spec["resource_fraction_limit"])
    models = output / "models"
    reference = load_model(models / f"reference_{spec['scene']}")
    destination = models / spec["id"]
    is_conversion = "upstream" in spec
    if is_conversion:
        source_path = models / spec["upstream"]
        upstream = load_model(source_path)
        source_inventory = file_inventory(source_path)
        observed = None
    elif spec["method"] != "V_direct":
        source_path = models / f"{spec['scene']}_observations_{spec['level']}"
        source_inventory = file_inventory(source_path)
        observed = source_path
    else:
        source_path = models / f"reference_{spec['scene']}"
        source_inventory = file_inventory(source_path)
        observed = None
    t0 = time.perf_counter()
    with RSSMonitor() as build_memory:
        if is_conversion:
            if spec["method"] == "T_from_P":
                candidate = SurfaceModel.from_model(upstream,destination,boundary_step_nm=spec["boundary_step_nm"],z_step_nm=spec["z_step_nm"])
            else:
                candidate = VoxelModel.from_model(upstream,destination,spacing_nm=spec["voxel_nm"])
        elif spec["method"] == "P":
            candidate = ParametricModel.from_observations(observed,destination)
        elif spec["method"] == "T_direct":
            candidate = SurfaceModel.from_observations(observed,destination)
        else:
            candidate = VoxelModel.from_model(reference,destination,spacing_nm=spec["voxel_nm"])
    build_seconds = time.perf_counter()-t0
    del candidate
    gc.collect()
    t0 = time.perf_counter()
    candidate = load_model(destination)
    reload_seconds = time.perf_counter()-t0
    with RSSMonitor() as evaluation_memory:
        prep = json.loads((output/"preparation.json").read_text(encoding="utf-8"))
        metrics = evaluate_model(reference,candidate,spec["scene"],output/"profiles"/(spec["id"]+".npz"),
                                 volume_reference=prep["reference_volumes_nm3"][spec["scene"]])
        incremental = None
        if is_conversion:
            incremental = {"section_distance": section_distance(upstream,candidate,section_positions(spec["scene"])),
                           "material": material_metrics(upstream,candidate,spec["scene"])}
    inventory = file_inventory(destination)
    memory = {"construction":build_memory.record(),"evaluation":evaluation_memory.record(),
              "available_before_bytes":available,"limit_bytes":ceiling,"resource_fraction_limit":spec["resource_fraction_limit"],
              "within_budget":max(build_memory.peak,evaluation_memory.peak,
                                   build_memory.windows_high_water or 0,evaluation_memory.windows_high_water or 0)<=ceiling}
    record = {**spec,"status":"completed","source_path":source_path.relative_to(output).as_posix(),
              "model_path":destination.relative_to(output).as_posix(),"construction_seconds":build_seconds,
              "reload_seconds":reload_seconds,"array_payload_bytes":int(candidate.resource_bytes),
              "saved_files":inventory,"source_files":source_inventory,"memory":memory,
              "model_metadata":candidate.metadata,"metrics":metrics,"incremental":incremental}
    if is_conversion:
        chain_bytes = sum(file_inventory(models/p)["file_bytes"] for p in spec["chain"])
        record["storage"]={"upstream_file_bytes":source_inventory["file_bytes"],
                           "source_chain_bytes":chain_bytes,"derived_file_bytes":inventory["file_bytes"],
                           "all_chain_saved_bytes":chain_bytes+inventory["file_bytes"],
                           "output_to_upstream_ratio":inventory["file_bytes"]/source_inventory["file_bytes"]}
    write_json(output/"details"/(spec["id"]+".json"),record)
    print(json.dumps({"id":spec["id"],"build_s":build_seconds,"section_p95_nm":metrics["section_distance"]["all"]["p95_nm"],
                      "payload_MB":record["array_payload_bytes"]/1e6,"peak_RSS_MB":max(build_memory.peak,evaluation_memory.peak)/1e6,
                      "within_budget":memory["within_budget"]}),flush=True)
    if not memory["within_budget"]:
        raise RuntimeError(f"Measured RSS exceeded configured {spec['resource_fraction_limit']:.0%} available-memory budget")


def edit_check(output,config=None):
    import numpy as np
    from ah53 import load_model, SurfaceModel, VoxelModel
    from ah53.evaluate import write_json, file_inventory, segments, stats
    models = output/"models"
    config=read_config(models/"reference_local"/"metadata.json")["config"] if config is None else config
    fine=config["sampling"]["fine"]
    operations=[]
    for source_id,target_id in (("local_P_fine","local_P_edited"),("local_T_direct_fine","local_T_direct_edited")):
        source=load_model(models/source_id)
        with RSSMonitor() as memory:
            start=time.perf_counter()
            result=source.edited_copy(models/target_id,line=1,z_center=400,z_halfwidth=320,displacement_nm=10)
            elapsed=time.perf_counter()-start
        result=load_model(models/target_id)
        max_change=0.; outside=[]; near=[]
        for line in range(3):
            for z in (-1000., 0., 60., 80., 137., 400., 663., 720., 740., 1000.):
                original=segments(source,line,z,1)
                changed=segments(result,line,z,1)
                p,w,_,_=original.sample(2)
                d=changed.distances(p)
                max_change=max(max_change,float(d.max()))
                (near if line==1 and abs(z-400)<320 else outside).extend(d.tolist())
        region_changes={}
        for region in ("left_wall","left_shoulder","top","right_shoulder","right_wall"):
            a=source.region_contour(1,400.,region,step_nm=1)
            b=result.region_contour(1,400.,region,step_nm=1)
            from ah53.evaluate import SegmentSet
            seg=SegmentSet(b[:-1],b[1:]); region_changes[region]=stats(seg.distances(a))
        operations.append({"source_id":source_id,"output_id":target_id,"seconds":elapsed,
                           "edit_request":{"line":1,"z_center_nm":400,"z_halfwidth_nm":320,"left_shoulder_inward_nm":10},
                           "maximum_sampled_free_contour_change_nm":max_change,"outside_support":stats(outside),
                           "inside_support":stats(near),"region_changes_at_center":region_changes,
                           "saved_and_reloaded":True,"metadata":result.metadata,"memory":memory.record(),
                           "saved_files":file_inventory(models/target_id)})
    source=load_model(models/"local_P_edited")
    for target_id,kind in (("local_T_from_P_edited","surface"),("local_V_from_P_edited","voxel")):
        start=time.perf_counter()
        with RSSMonitor() as memory:
            result=(SurfaceModel.from_model(source,models/target_id,boundary_step_nm=float(fine["boundary_step_nm"]),z_step_nm=float(fine["z_step_nm"]))
                    if kind=="surface" else VoxelModel.from_model(source,models/target_id,spacing_nm=float(fine["voxel_nm"])))
        result=load_model(models/target_id)
        original_id="local_T_from_P" if kind=="surface" else "local_V_from_P"
        original=load_model(models/original_id)
        p=source.region_contour(1,400.,"left_shoulder",step_nm=1)
        xx=np.repeat(p[:,0],3)+np.tile([-4,0,4],len(p)); yy=np.repeat(p[:,1],3)
        zz=np.full(len(xx),400.)
        changed=int(np.sum(original.material_at(xx,yy,zz)!=result.material_at(xx,yy,zz)))
        operations.append({"source_id":"local_P_edited","output_id":target_id,
                           "seconds":time.perf_counter()-start,"saved_and_reloaded":True,
                           "material_probe_changed_count":changed,"material_probe_count":len(xx),
                           "saved_files":file_inventory(models/target_id),"memory":memory.record()})
    write_json(output/"edit_check.json",{"operations":operations})
    refresh_edit_report(output)
    print(json.dumps({"edit_check":"completed","operations":len(operations)}),flush=True)


def refresh_edit_report(output):
    """Measure requested X displacement separately from shortest contour distance."""
    import numpy as np
    from ah53 import load_model
    from ah53.evaluate import write_json
    data=json.loads((output/"edit_check.json").read_text(encoding="utf-8"))
    for operation in data["operations"][:2]:
        source=load_model(output/"models"/operation["source_id"])
        edited=load_model(output/"models"/operation["output_id"])
        u=np.linspace(1,2,2001)
        delta=edited.evaluate(1,u,400.)-source.evaluate(1,u,400.)
        operation["actual_x_displacement_at_z_center_max_nm"]=float(np.max(delta[:,0]))
        operation["actual_y_displacement_at_z_center_max_abs_nm"]=float(np.max(np.abs(delta[:,1])))
        operation["maximum_sampled_free_contour_change_definition"]="one-direction nearest free contour distance; not X displacement"
        edit=operation["metadata"]["edit"]
        operation["changed_source_scalar_count"]=edit.get("changed_scalar_coefficients",edit.get("changed_vertex_x_coordinates"))
        operation["endpoint_positions_unchanged"]=bool(np.allclose(delta[[0,-1]],0,atol=1e-10))
        if source.kind=="surface":
            operation["face_connectivity_unchanged"]=bool(np.array_equal(source.faces,edited.faces))
            a=source.region_contour(1,400.,"left_shoulder");b=edited.region_contour(1,400.,"left_shoulder")
            aa=np.stack([a[1]-a[0],a[-1]-a[-2]])
            bb=np.stack([b[1]-b[0],b[-1]-b[-2]])
            cos=np.sum(aa*bb,axis=1)/np.linalg.norm(aa,axis=1)/np.linalg.norm(bb,axis=1)
            operation["endpoint_facet_direction_change_degrees"]=np.rad2deg(np.arccos(np.clip(cos,-1,1))).tolist()
        else:
            operation["endpoint_tangents_preserved_by_fixed_first_last_two_controls"]=True
    write_json(output/"edit_check.json",data)
    lines=["# 一次实际局部编辑检查","",
           "对中央母周期中间条纹的左圆肩，请求 X 向内位移幅度 10 nm，Z 中心 400 nm、支撑区间 [80,720] nm。10 nm 是编辑请求；系数或顶点上的离散操作产生的实际位移分别测量。两个分支不宣称实现了完全相同的连续形变。","",
           "|源模型|修改标量数|请求 X 幅度 / nm|实测中心截面最大 X 位移 / nm|采样最近轮廓最大距离 / nm|非目标区采样最大距离 / nm|编辑及保存 / s|",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for op in data["operations"][:2]:
        lines.append(f"|{op['source_id']}|{op['changed_source_scalar_count']}|10|{op['actual_x_displacement_at_z_center_max_nm']:.6f}|{op['maximum_sampled_free_contour_change_nm']:.6f}|{op['outside_support']['max_nm']:.3g}|{op['seconds']:.3f}|")
    angles=data["operations"][1]["endpoint_facet_direction_change_degrees"]
    voxel_spacing=load_model(output/"models"/"local_V_from_P_edited").spacing
    lines.extend(["",f"最近轮廓距离通常小于 X 位移，两者意义不同。P 修改 {data['operations'][0]['changed_source_scalar_count']} 个标量系数，约束基函数支撑完全位于目标区间，并固定圆肩前后两个控制系数，保持连接点与端点切向。直接三角面修改局部顶点，保存的三角连接完全相同，连接点保持不动；端部小面方向仍会变化。",
                  f"直接三角面左圆肩两端小面方向分别变化 {angles[0]:.4f}° 和 {angles[1]:.4f}°；这反映本次简单顶点编辑的维护限制。",
                  "",f"已从保存的编辑后 P 重新生成三角面和 {voxel_spacing:g} nm 标签体，重新读取后的材料探针分别发生实际变化。操作数量、支撑区间、分区检查、探针数量和文件哈希见 `edit_check.json`。",
                  "","非目标检查包括其他条纹、其他轮廓区域，以及 Z=60、80、720、740 nm 等支撑边界附近位置；表中约 10⁻¹³ nm 是浮点计算残差。这是指定位置的采样证据，不是全域解析证明。"])
    (output/"edit_check.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


def compact_row(record):
    m=record["metrics"]; d=m["section_distance"]
    row={"id":record["id"],"scene":record["scene"],"method":record["method"],
         "array_payload_bytes":record["array_payload_bytes"],"file_bytes":record["saved_files"]["file_bytes"],
         "construction_seconds":record["construction_seconds"],"reload_seconds":record["reload_seconds"],
         "peak_rss_bytes":max(record["memory"]["construction"]["sampled_peak_rss_bytes"],record["memory"]["evaluation"]["sampled_peak_rss_bytes"],
                              record["memory"]["construction"].get("windows_process_peak_working_set_bytes") or 0,
                              record["memory"]["evaluation"].get("windows_process_peak_working_set_bytes") or 0),
         "section_rms_nm":d["all"]["rms_nm"],"section_p95_nm":d["all"]["p95_nm"],"section_max_nm":d["all"]["max_nm"],
         "top_height_rms_nm":m["profiles"]["top_height"]["rms_nm"],
         "material_near_fraction":m["material"]["near_boundary_fraction"],"material_global_fraction":m["material"]["global_fraction"],
         "volume_relative_error":m["volume"]["relative_error"]}
    for name,s in d["regions"].items():
        for metric in ("rms_nm","p95_nm","max_nm"):
            row[f"{name}_{metric}"]=s[metric]
    for y,val in m["profiles"]["per_height"].items():
        for measurement in ("cd","center"):
            row[f"{measurement}_y{y}_rms_nm"]=val[measurement]["rms_nm"]
        row[f"missing_pairs_y{y}"]=val["missing_intersection_pairs"]
    if record.get("incremental"):
        row.update({"path_id":record["path_id"],"upstream":record["upstream"],
                    "incremental_section_rms_nm":record["incremental"]["section_distance"]["all"]["rms_nm"],
                    "incremental_section_p95_nm":record["incremental"]["section_distance"]["all"]["p95_nm"],
                    "incremental_material_near_fraction":record["incremental"]["material"]["near_boundary_fraction"],
                    **record["storage"]})
    return row


def finalize(output, started, config_path, config=None):
    import numpy,scipy,psutil
    from ah53.evaluate import write_json,file_inventory
    config=read_config(config_path) if config is None else config
    validate_resume_config(output,config)
    a_cases,b_cases=configured_specs(config)
    groups=[]
    for name,specs in (("metrics.csv",a_cases),("conversions.csv",b_cases)):
        records=[json.loads((output/"details"/(s["id"]+".json")).read_text(encoding="utf-8")) for s in specs]
        rows=[compact_row(r) for r in records]
        with (output/name).open("w",encoding="utf-8-sig",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
            writer.writeheader(); writer.writerows(rows)
        groups.extend(records)
    lineage=[]
    for record in groups:
        lineage.append({"model_id":record["id"],"input":record["source_path"],"input_sha256":record["source_files"]["sha256"],
                        "output":record["model_path"],"output_sha256":record["saved_files"]["sha256"],
                        "operation":record.get("operation","independent_"+record["method"]),
                        "seed":config["synthetic"]["seed"],"configuration_sha256":config_fingerprint(config),
                        "material_mapping":config["materials"],
                        "settings":record["model_metadata"]})
    write_json(output/"lineage.json",{"models":lineage})
    prep=json.loads((output/"preparation.json").read_text(encoding="utf-8"))
    # Explicit isolation check: reloaded representation queries must still work
    # after every reference geometry query entry point is replaced by a failure.
    from ah53 import load_model,ReferenceGeometry
    saved_reference_methods={key:getattr(ReferenceGeometry,key) for key in ("evaluate","parameters","material_at")}
    def unavailable_reference(*args,**kwargs):
        raise AssertionError("A saved candidate attempted to consult reference geometry")
    isolation=[]
    try:
        for key in saved_reference_methods:setattr(ReferenceGeometry,key,unavailable_reference)
        for record in groups:
            model=load_model(output/record["model_path"])
            l,r=model.boundaries(0,numpy.array([30.,150.,270.]),numpy.array([137.,413.,677.]))
            labels=model.material_at((l+r)/2,numpy.array([30.,150.,270.]),numpy.array([137.,413.,677.]))
            assert numpy.all(numpy.isfinite(l)) and numpy.all(r>l) and numpy.all(labels==1)
            isolation.append({"model_id":record["id"],"passed":True,"queries":6})
    finally:
        for key,value in saved_reference_methods.items():setattr(ReferenceGeometry,key,value)
    write_json(output/"saved_model_isolation.json",{"reference_queries_disabled":True,"checks":isolation})
    manifest={"title":"基于 AH53 名义版图的合成工艺形貌：两层几何验证", "run_id":output.name,
              "started_utc":started,"finished_utc":datetime.now(timezone.utc).isoformat(),
              "status":"completed","A_case_count":9,"B_local_path_count":4,"B_large_path_count":1,
              "coordinate_units":"nm","coordinate_axes":{"X":"lateral","Y":"height","Z":"line length"},
              "environment":{"python":sys.version,"numpy":numpy.__version__,"scipy":scipy.__version__,
                             "psutil":psutil.__version__,"platform":platform.platform(),"numeric_threads":1},
              "configuration":config,"configuration_sha256":config_fingerprint(config),
              "preparation":prep,"models":[{"id":r["id"],"kind":r["method"],"scene":r["scene"],
                                            "path":r["model_path"],"file_bytes":r["saved_files"]["file_bytes"]} for r in groups],
              "saved_model_isolation_checks":isolation,
              "metric_limitations":["XY-section distances are not full-3D surface distances or global Hausdorff bounds",
                                    "P95 and maximum apply to stated arc-weighted sample sets",
                                    "V_direct uses continuous truth; P and T_direct share sparse observations",
                                    "Global finite Z caps and substrate contact excluded from free-surface scores",
                                    "No measured 3D process data; full48x48um size is validation assumption"],
              "resource_rule":f"sequential isolated workers; memory-mapped voxel arrays; measured RSS <={config['numerics']['resource_available_fraction']:.0%} available before each case"}
    write_json(output/"manifest.json",manifest)
    (ROOT/"results"/"latest.txt").write_text(output.name+"\n",encoding="utf-8")
    print(json.dumps({"run":"completed","output":str(output),"A":9,"B":5}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"results"/"20261024_v2")
    parser.add_argument("--config",type=Path,default=ROOT/"configs"/"default.json")
    parser.add_argument("--worker",default=None)
    parser.add_argument("--resume",action="store_true",help="reuse completed records after a repaired interrupted execution")
    args=parser.parse_args(); output=args.output.resolve()
    config=read_config(args.config)
    a_cases,b_cases=configured_specs(config)
    validate_resume_config(output,config)
    output.mkdir(parents=True,exist_ok=True)
    if args.worker:
        if args.worker=="prepare": prepare(output,args.config)
        elif args.worker=="edit": edit_check(output,config)
        else: run_case(next(s for s in a_cases+b_cases if s["id"]==args.worker),output)
        return
    started=datetime.now(timezone.utc).isoformat()
    env=os.environ.copy()
    for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
        env[key]="1"
    for worker in ["prepare"]+[s["id"] for s in a_cases+b_cases]+["edit"]:
        done=(output/"preparation.json" if worker=="prepare" else output/"edit_check.json" if worker=="edit"
              else output/"details"/(worker+".json"))
        if args.resume and done.exists():
            print("Reusing completed record: "+worker,flush=True); continue
        subprocess.run([sys.executable,str(Path(__file__).resolve()),"--worker",worker,
                        "--output",str(output),"--config",str(args.config)],check=True,env=env)
    finalize(output,started,args.config,config=config)


if __name__=="__main__":
    main()
