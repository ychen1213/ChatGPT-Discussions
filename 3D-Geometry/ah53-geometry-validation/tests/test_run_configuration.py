"""Configuration propagation and stale-result protection, without model builds."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run_validation import A_CASES,B_CASES,configured_specs,config_fingerprint,validate_resume_config


def default_config():
    return json.loads((ROOT/"configs"/"default.json").read_text(encoding="utf-8"))


def test_default_specifications_preserve_the_completed_run():
    a,b=configured_specs(default_config())
    assert [s["id"] for s in a]==[s["id"] for s in A_CASES]
    assert [s["id"] for s in b]==[s["id"] for s in B_CASES]
    for spec,original in zip(a,A_CASES):
        for key in ("boundary_step_nm","z_step_nm","voxel_nm"):
            assert spec[key]==original[key]
    assert all(s["resource_fraction_limit"]==.6 for s in a+b)


def test_changed_sampling_reaches_all_independent_and_conversion_specs():
    config=default_config()
    config["sampling"]["fine"]={"boundary_step_nm":8,"z_step_nm":32,"voxel_nm":4}
    config["sampling"]["full"]={"boundary_step_nm":12,"z_step_nm":60,"voxel_nm":20}
    config["numerics"]["resource_available_fraction"]=.4
    a,b=configured_specs(config)
    for spec in a+b:
        assert spec["resource_fraction_limit"]==.4
        assert spec["configuration_sha256"]==config_fingerprint(config)
        if spec["scene"]=="full":
            assert (spec["boundary_step_nm"],spec["z_step_nm"],spec["voxel_nm"])==(12,60,20)
        elif spec in b or spec["level"]=="fine":
            assert (spec["boundary_step_nm"],spec["z_step_nm"],spec["voxel_nm"])==(8,32,4)
    assert a[-1]["id"]=="full_V_direct_20nm"
    assert {s["voxel_nm"] for s in b if s["scene"]=="local"}=={4}


def test_resume_accepts_legacy_saved_config_but_rejects_any_stale_case(tmp_path):
    config=default_config()
    reference=tmp_path/"models"/"reference_local"
    reference.mkdir(parents=True)
    metadata=reference/"metadata.json"
    metadata.write_text(json.dumps({"config":config}),encoding="utf-8")
    assert validate_resume_config(tmp_path,config)==config_fingerprint(config)
    changed=deepcopy(config);changed["sampling"]["fine"]["voxel_nm"]=4
    with pytest.raises(ValueError,match="Configuration differs"):
        validate_resume_config(tmp_path,changed)
    # Updating a manifest must not hide stale individual completed records.
    metadata.write_text(json.dumps({"config":changed}),encoding="utf-8")
    details=tmp_path/"details";details.mkdir()
    (details/"local_P_fine.json").write_text(json.dumps({"model_metadata":{"config":config}}),encoding="utf-8")
    with pytest.raises(ValueError,match="Configuration differs"):
        validate_resume_config(tmp_path,changed)


def test_unverifiable_resume_and_invalid_budget_are_rejected(tmp_path):
    config=default_config()
    (tmp_path/"preparation.json").write_text("{}",encoding="utf-8")
    with pytest.raises(ValueError,match="no verifiable"):
        validate_resume_config(tmp_path,config)
    config["numerics"]["resource_available_fraction"]=0
    with pytest.raises(ValueError,match="resource_available_fraction"):
        configured_specs(config)
