"""Re-evaluate auxiliary volumes at independent Z quadrature stations only.

No geometry payload, reference config, lineage hash, surface metric or
construction measurement is modified. Invoke after all model workers finish.
"""
from pathlib import Path
import gc
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from ah53 import load_model
from ah53.evaluate import write_json


def repair(output):
    from run_validation import RSSMonitor
    output=Path(output);start=time.perf_counter();cache={};costs={}
    definition={
        'reference_and_parametric':'Cross-section polygon areas at independent 4-point Gauss-Legendre stations inside <=40 nm Z panels; no station coincides with an input Z knot.',
        'z_panel_nm':40.,'gauss_order':4,'contour_chord_target_nm':1.,
        'triangle':'Exact divergence-theorem volume of the saved oriented triangle mesh.',
        'voxel':'Exact persisted material-1 label count times isotropic cell volume.',
        'scope':'Auxiliary volume accuracy; no substitution for local boundary errors.'}
    def volume(model_id):
        if model_id not in cache:
            tick=time.perf_counter();model=load_model(output/'models'/model_id)
            cache[model_id]=float(model.volume())
            costs[model_id]={'kind':model.kind,'seconds':time.perf_counter()-tick,'volume_nm3':cache[model_id]}
            del model;gc.collect()
        return cache[model_id]
    changes=[]
    with RSSMonitor() as memory:
        truth={scene:volume('reference_'+scene) for scene in ('local','full')}
        ref=load_model(output/'models'/'reference_local');tick=time.perf_counter()
        fine=float(ref.volume(segment_nm=40.,order=8,contour_step_nm=1.))
        convergence={'reference_scene':'local','baseline_order':4,'refined_order':8,'panel_nm':40.,
                     'baseline_nm3':truth['local'],'refined_nm3':fine,
                     'difference_nm3':fine-truth['local'],
                     'relative_difference':abs(fine-truth['local'])/fine,
                     'refinement_seconds':time.perf_counter()-tick,
                     'interpretation':'Observed independent quadrature convergence; contour discretization remains the separately checked 1 nm chord rule.'}
        del ref
        for path in sorted((output/'details').glob('*.json')):
            data=json.loads(path.read_text(encoding='utf-8'))
            if data.get('status')!='completed':continue
            previous=dict(data['metrics']['volume']);candidate=volume(data['id']);reference=truth[data['scene']]
            revised={'reference_stripe_nm3':reference,'candidate_stripe_nm3':candidate,
                     'relative_error':(candidate-reference)/reference,'definition':definition}
            data['metrics']['volume']=revised
            data['volume_readback_audit']='Independent quadrature update from unchanged saved models; timing and memory in volume_quadrature_audit.json'
            write_json(path,data)
            changes.append({'model_id':data['id'],'previous':previous,'revised':revised})
        prep_path=output/'preparation.json';prep=json.loads(prep_path.read_text(encoding='utf-8'))
        prep['reference_volumes_nm3']=truth;prep['volume_quadrature']=definition
        write_json(prep_path,prep)
    record={'status':'completed','saved_models_unchanged':True,'reason':'Previous trapezoid stations aligned with interpolating model input knots; independent quadrature avoids that sampling bias.',
            'definition':definition,'convergence':convergence,'model_costs':costs,'updated_model_count':len(changes),
            'changes':changes,'seconds':time.perf_counter()-start,'memory':memory.record()}
    write_json(output/'volume_quadrature_audit.json',record)
    return record


if __name__=='__main__':
    output=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results'/'20261024_v2'
    result=repair(output)
    print(json.dumps({'volume_audit':result['status'],'updated_models':result['updated_model_count'],'seconds':result['seconds']}),flush=True)
