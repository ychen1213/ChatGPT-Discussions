"""Post-run readback audits; never constructs or changes any saved model.

Adds exact pairwise final label comparisons, saved-query isolation evidence and
optional height-curve supplements from completed persisted representations.
"""
from pathlib import Path
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src")]
import numpy as np
from ah53 import load_model
from ah53.evaluate import write_json
from run_validation import finalize,RSSMonitor,refresh_edit_report


def main():
    import argparse
    parser=argparse.ArgumentParser(description="Audit saved models without rebuilding them")
    parser.add_argument("--output",type=Path,default=ROOT/"results"/"20261024_v2")
    output=parser.parse_args().output.resolve()
    saved_manifest=json.loads((output/"manifest.json").read_text(encoding="utf-8"))
    run_config=saved_manifest["configuration"]
    from run_validation import validate_resume_config
    validate_resume_config(output,run_config)
    start=time.perf_counter()
    supplemented=[]
    for detail in sorted((output/"details").glob("*.json")):
        data=json.loads(detail.read_text(encoding="utf-8"))
        actual=data["metrics"]["profiles"]["actual_geometry"]
        if "height_maximum_per_section_rms_nm" in actual:continue
        model=load_model(output/data["model_path"])
        reference=load_model(output/"models"/f"reference_{data['scene']}")
        profiles=output/"profiles"/(data["id"]+".npz")
        with np.load(profiles) as f:arrays={key:f[key] for key in f.files}
        z=arrays["z_nm"][::4]
        candidate=np.array([[np.max(model.contour(line,zz,step_nm=1)[:,1]) for zz in z]
                            for line in range(len(model.centers))])
        truth=np.array([[np.max(reference.contour(line,zz,step_nm=1)[:,1]) for zz in z]
                        for line in range(len(model.centers))])
        actual.update({"height_maximum_per_section_rms_nm":np.std(candidate,axis=1).tolist(),
                       "height_range_nm":[float(candidate.min()),float(candidate.max())],
                       "height_measurement_z_spacing_nm":float(z[1]-z[0])})
        arrays.update(height_z_nm=z,height_reference_nm=truth,height_candidate_nm=candidate)
        np.savez_compressed(profiles,**arrays)
        data["height_supplement"]="Added by querying saved model, without rebuilding representation"
        write_json(detail,data);supplemented.append(data["id"])
    pairwise=[]
    with RSSMonitor() as memory:
        for left,right in (("local_V_from_P","local_V_from_T"),
                           ("local_V_from_T","local_V_from_Tdirect"),
                           ("local_V_from_P","local_V_from_Tdirect")):
            a=load_model(output/"models"/left);b=load_model(output/"models"/right)
            assert a.labels.shape==b.labels.shape
            assert a.spacing==b.spacing and np.array_equal(a.origin,b.origin)
            counts=np.zeros((3,3),np.int64)
            t=time.perf_counter()
            for i in range(0,a.labels.shape[0],16):
                key=np.asarray(a.labels[i:i+16])*3+np.asarray(b.labels[i:i+16])
                counts+=np.bincount(key.ravel(),minlength=9).reshape(3,3)
            changed=int(counts.sum()-np.trace(counts))
            labels=np.arange(3)
            delta=(counts.sum(axis=0)-counts.sum(axis=1))*a.spacing**3
            stripe_union=int(counts[1,:].sum()+counts[:,1].sum()-counts[1,1])
            pairwise.append({"left_model":left,"right_model":right,"same_grid_verified":True,
                             "shape_zyx":list(a.labels.shape),"spacing_nm":a.spacing,"origin_nm":a.origin.tolist(),
                             "rows_left_cols_right_material_counts":counts.tolist(),
                             "total_cells":int(a.labels.size),"changed_cells":changed,
                             "changed_global_fraction":changed/int(a.labels.size),
                             "changed_fraction_of_stripe_union":changed/stripe_union,
                             "material_volume_delta_right_minus_left_nm3":dict(zip(map(str,labels),map(float,delta))),
                             "air_to_stripe_cells":int(counts[0,1]),"stripe_to_air_cells":int(counts[1,0]),
                             "comparison_seconds":time.perf_counter()-t})
    write_json(output/"voxel_pairwise.json",{"comparison":"exact persisted label-array cell equality; no reference call",
                                             "chunk_z_slices":16,"pairs":pairwise,"memory":memory.record()})
    from scripts.repair_volume_metrics import repair
    volume_audit=repair(output)
    refresh_edit_report(output)
    manifest_path=output/"manifest.json"
    started=saved_manifest["started_utc"]
    finalize(output,started,ROOT/"configs"/"default.json",config=run_config)
    write_json(output/"post_run_audit.json",{
        "height_curve_supplemented_ids":supplemented,"seconds":time.perf_counter()-start,
        "saved_models_unchanged":True,
        "material_interface_rule":{"stripe_id":1,"air_id":0,"substrate_id":2,
                                   "surface_face_rule":"Saved outward stripe triangles at Y=0 interface to substrate; remaining faces interface to air. Finite Z caps close the computational window.",
                                   "substrate":"Analytic rectangular domain Y<0 saved in model bounds; no optical parameters implied"},
        "reference_numeric_query":"Reference is analytic C(u,Z); material tests invert controlled0.5nm chords. Section metrics use1nm chords with measured0.25nm refinement; see preparation.json.",
        "volume_audit":"volume_quadrature_audit.json",
        "volume_numeric_query":"Reference and parametric section polygon area integrated at independent4point Gauss stations in40nm panels; triangle volume uses actual oriented faces; voxel volume is exact count times cell volume. Volume quadrature is auxiliary, not a boundary-error substitute."})
    print(json.dumps({"post_run_audit":"completed","height_supplements":supplemented,
                      "pairwise_changed_cells":[p["changed_cells"] for p in pairwise]}),flush=True)


if __name__=="__main__":main()
