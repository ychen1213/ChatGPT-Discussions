"""Prepare isolated label inputs, reconstruct P/T, and independently score them."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
CONFIG_PATH = ROOT / "configs/voxel_reconstruction.json"
RUNTIME_PACKAGES = ["numpy", "scipy", "scikit-image", "trimesh", "shapely"]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def runtime_versions():
    return {name: importlib.metadata.version(name) for name in RUNTIME_PACKAGES}


def inventory(directory, exclude=()):
    """Hash an exact tree; unexpected files also invalidate its cache."""
    directory = Path(directory)
    excluded = set(exclude)
    return {p.relative_to(directory).as_posix(): digest(p)
            for p in sorted(directory.rglob("*"))
            if p.is_file() and p.relative_to(directory).as_posix() not in excluded}


def validate_protocol(out, config):
    path = out / "protocol.json"
    if not path.exists():
        raise RuntimeError("No frozen protocol; run --phase prepare first")
    protocol = read(path)
    if protocol.get("config_sha256") != digest(CONFIG_PATH) or protocol.get("config") != config:
        raise RuntimeError("Frozen protocol differs from current configuration; use a new output directory")
    if protocol.get("runtime_versions") != runtime_versions():
        raise RuntimeError("Runtime versions changed since protocol freezing; use a new output directory")
    if protocol.get("input_manifest_sha256") != digest(out / "input_manifest.json"):
        raise RuntimeError("Frozen input manifest changed; use a new output directory")
    return protocol


def validate_inputs(out, config):
    """Check before any reconstruction/evaluation/cache reuse; never repair in place."""
    validate_protocol(out, config)
    manifest = read(out / "input_manifest.json")
    expected = {case["name"]: case for case in config["cases"]}
    names = [case["name"] for case in manifest]
    if len(names) != len(set(names)) or set(names) != set(expected) | set(config["challenges"]):
        raise RuntimeError("Input manifest cases differ from the frozen matrix")
    source_root = ROOT / "results" / config["source_run"] / "models"
    for case in manifest:
        target = out / "inputs" / case["name"]
        if {p.name for p in target.iterdir()} != {"labels.npy", "grid.json"}:
            raise RuntimeError(f"Unexpected files in sanitized input {case['name']}")
        grid = read(target / "grid.json")
        if set(grid) != set(config["allowed_grid_fields"]) or grid != case["grid"]:
            raise RuntimeError(f"Sanitized grid changed: {case['name']}")
        actual_hash = digest(target / "labels.npy")
        if actual_hash != case["input_labels_sha256"]:
            raise RuntimeError(f"Sanitized labels changed: {case['name']}; use a new output directory")
        data = np.load(target / "labels.npy", mmap_mode="r", allow_pickle=False)
        if list(data.shape) != case["array_shape_zyx"] or int(data.nbytes) != case["payload_bytes"]:
            raise RuntimeError(f"Input shape/payload changed: {case['name']}")
        if case["name"] in expected:
            spec = expected[case["name"]]
            if any(case.get(k) != v for k, v in spec.items()):
                raise RuntimeError(f"Manifest source differs from the frozen matrix: {case['name']}")
            source = source_root / spec["source"]
            meta = read(source / "metadata.json")
            source_grid = {"origin_xyz_nm": meta["origin"], "spacing_nm": meta["spacing_nm"],
                           "axis_order": meta["axis_order"], "units": meta["units"], "materials": meta["materials"]}
            if digest(source / "labels.npy") != actual_hash or source_grid != grid:
                raise RuntimeError(f"Source input changed: {case['name']}; use a new output directory")
        else:
            challenge, challenge_grid = make_challenge(case["name"])
            if grid != challenge_grid or not np.array_equal(data, challenge):
                raise RuntimeError(f"Challenge generator/input changed: {case['name']}; use a new output directory")
    return manifest


def build_fingerprint(out, case, kind, settings):
    return {"schema": 1, "kind": kind, "settings": settings,
            "input_labels_sha256": case["input_labels_sha256"],
            "input_grid_sha256": digest(out / "inputs" / case["name"] / "grid.json"),
            "config_sha256": digest(CONFIG_PATH),
            "implementation_sha256": digest(ROOT / "src/ah53/voxel_reconstruction.py"),
            "worker_sha256": digest(ROOT / "scripts/voxel_reconstruction_worker.py"),
            "runtime_versions": runtime_versions()}


def checked_build(out, model_id, expected):
    model = out / "models" / model_id
    record = read(model / "worker_result.json")
    if record.get("build_fingerprint") != expected:
        raise RuntimeError(f"Stale reconstruction cache {model_id}: input/settings/code/runtime changed; use a new output directory")
    if record.get("artifact_sha256") != inventory(model, exclude=("worker_result.json",)):
        raise RuntimeError(f"Reconstruction artifacts changed or are incomplete: {model_id}")
    work = out / "workers" / model_id
    expected_work = {"worker.py": expected["worker_sha256"],
                     "reconstruction.py": expected["implementation_sha256"]}
    if inventory(work) != expected_work:
        raise RuntimeError(f"Worker code tree changed: {model_id}")
    # The enriched worker record is authoritative and can restore this convenience copy.
    record_path = out / "build_records" / (model_id + ".json")
    if not record_path.exists():
        write(record_path, record)
    elif read(record_path) != record:
        raise RuntimeError(f"Build record differs from persisted worker provenance: {model_id}")
    return record


def metric_fingerprint(out, case, reference, options, build=None):
    return {"schema": 1, "input_labels_sha256": case["input_labels_sha256"],
            "input_grid_sha256": digest(out / "inputs" / case["name"] / "grid.json"),
            "config_sha256": digest(CONFIG_PATH), "options": options,
            "reference_artifact_sha256": inventory(reference) if reference is not None else None,
            "evaluation_code_sha256": {p.name: digest(p) for p in sorted((ROOT / "src/ah53").glob("*.py"))},
            "model_artifact_sha256": build.get("artifact_sha256") if build is not None else None,
            "build_fingerprint": build.get("build_fingerprint") if build is not None else None,
            "runtime_versions": runtime_versions()}


def checked_metric(path, expected, recompute):
    if not path.exists() or recompute:
        return None
    result = read(path)
    if result.get("evaluation_fingerprint") != expected:
        raise RuntimeError(f"Stale metric cache {path.name}; use --recompute-metrics to explicitly replace scores or use a new output directory")
    return result


def make_challenge(name):
    """Small independent categorical examples; no AH53 formula is evaluated."""
    labels = np.zeros((32, 40, 64), np.uint8)
    labels[:, :8, :] = 2
    if name == "merging_bridge":
        labels[:, 8:28, 8:20] = 1
        labels[:, 8:28, 44:56] = 1
        labels[12:20, 14:18, 20:44] = 1
    else:
        labels[:, 8:28, 20:44] = 1
        if name == "through_hole":
            labels[:, 14:20, 28:36] = 0
        elif name == "single_voxel_spur":
            labels[16, 28, 32] = 1
        elif name != "straight_control":
            raise ValueError(name)
    grid = {"origin_xyz_nm": [-320., -80., -160.], "spacing_nm": 10.,
            "axis_order": "ZYX", "units": "nm", "materials": {"0": "air", "1": "stripe", "2": "substrate"}}
    return labels, grid


def prepare(out, config):
    if (out / "protocol.json").exists():
        # Validate everything before writing: never overwrite inputs beneath cached builds.
        return validate_inputs(out, config)
    for name in ("models", "build_records", "metrics"):
        state = out / name
        if state.exists() and any(state.iterdir()):
            raise RuntimeError("Unfrozen output already contains builds/scores; use a new output directory")
    source_root = ROOT / "results" / config["source_run"] / "models"
    manifest = []
    for case in config["cases"]:
        source = source_root / case["source"]
        meta = read(source / "metadata.json")
        target = out / "inputs" / case["name"]
        target.mkdir(parents=True, exist_ok=True)
        if any(p.name not in ("labels.npy", "grid.json") for p in target.iterdir()):
            raise RuntimeError(f"Unexpected file in sanitized input directory: {target}")
        grid = {"origin_xyz_nm": meta["origin"], "spacing_nm": meta["spacing_nm"],
                "axis_order": meta["axis_order"], "units": meta["units"], "materials": meta["materials"]}
        assert set(grid) == set(config["allowed_grid_fields"])
        assert grid["spacing_nm"] == case["spacing_nm"]
        source_hash = digest(source / "labels.npy")
        destination = target / "labels.npy"
        if not destination.exists() or digest(destination) != source_hash:
            shutil.copyfile(source / "labels.npy", destination)
        assert digest(destination) == source_hash
        write(target / "grid.json", grid)
        data = np.load(destination, mmap_mode="r")
        manifest.append({**case, "input_kind": "AH53_saved_labels", "grid": grid,
                         "source_labels_sha256": source_hash, "input_labels_sha256": source_hash,
                         "array_shape_zyx": list(data.shape), "payload_bytes": int(data.nbytes),
                         "input_files": ["labels.npy", "grid.json"]})
    for name in config["challenges"]:
        labels, grid = make_challenge(name)
        target = out / "inputs" / name
        target.mkdir(parents=True, exist_ok=True)
        if any(p.name not in ("labels.npy", "grid.json") for p in target.iterdir()):
            raise RuntimeError(f"Unexpected file in sanitized input directory: {target}")
        np.save(target / "labels.npy", labels)
        write(target / "grid.json", grid)
        # Small reproducible datasets are published; main 256 MB input stays local.
        small = out / "challenge_inputs"
        small.mkdir(exist_ok=True)
        np.savez_compressed(small / (name + ".npz"), labels=labels,
                            origin_xyz_nm=np.array(grid["origin_xyz_nm"]), spacing_nm=np.array(grid["spacing_nm"]))
        manifest.append({"name": name, "input_kind": "independent_topology_challenge", "grid": grid,
                         "input_labels_sha256": digest(target / "labels.npy"),
                         "array_shape_zyx": list(labels.shape), "payload_bytes": int(labels.nbytes),
                         "input_files": ["labels.npy", "grid.json"]})
    write(out / "input_manifest.json", manifest)
    protocol = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "config": config,
                "config_sha256": digest(CONFIG_PATH),
                "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "runtime_versions": runtime_versions(),
                "input_manifest_sha256": digest(out / "input_manifest.json")}
    write(out / "protocol.json", protocol)
    return manifest


def profiles_for(case, config):
    h = case["grid"]["spacing_nm"]
    yield "T_MC", "T", {}
    profiles = config["P_profiles"]
    if case["name"] in ("through_hole", "merging_bridge"):
        profiles = [p for p in profiles if p["name"] == "P_sigma05"]
    for p in profiles:
        yield p["name"], "P", {"contour_step_nm": p["contour_step_in_voxels"] * h,
                               "z_step_nm": p["z_step_in_voxels"] * h,
                               "smoothing_nm": p["smoothing_sigma_in_voxels"] * h}


def reconstruct(out, config, selected=None):
    manifest = validate_inputs(out, config)
    source_root = ROOT / "results" / config["source_run"] / "models"
    for case in manifest:
        if selected and case["name"] not in selected:
            continue
        for profile, kind, settings in profiles_for(case, config):
            model_id = case["name"] + "__" + profile
            model = out / "models" / model_id
            result = model / "worker_result.json"
            fingerprint = build_fingerprint(out, case, kind, settings)
            if result.exists():
                record = checked_build(out, model_id, fingerprint)
                print(json.dumps({"cached": model_id, "status": record.get("status"), "cache_verified": True}), flush=True)
                continue
            if model.exists() and any(model.iterdir()):
                raise RuntimeError(f"Incomplete or prepopulated model output {model_id}; use a new output directory")
            work = out / "workers" / model_id
            work.mkdir(parents=True, exist_ok=True)
            if any(p.name not in ("worker.py", "reconstruction.py") or not p.is_file() for p in work.iterdir()):
                raise RuntimeError(f"Unexpected content in isolated worker directory {model_id}")
            shutil.copyfile(ROOT / "scripts/voxel_reconstruction_worker.py", work / "worker.py")
            shutil.copyfile(ROOT / "src/ah53/voxel_reconstruction.py", work / "reconstruction.py")
            command = [sys.executable, "-I", "-B", str(work / "worker.py"),
                       "--input", str(out / "inputs" / case["name"]), "--output", str(model),
                       "--kind", kind, "--settings", json.dumps(settings),
                       "--forbidden-probe", str(source_root / "reference_local" / "metadata.json"),
                       "--forbidden-probe", str(source_root / "local_V_direct_fine" / "metadata.json"),
                       "--forbidden-probe", str(ROOT / "src/ah53/reference_geometry.py")]
            print(json.dumps({"starting": model_id, "settings": settings}), flush=True)
            started = time.perf_counter()
            proc = subprocess.run(command, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
            log = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
                   "subprocess_seconds": time.perf_counter() - started}
            write(out / "execution_logs" / (model_id + ".json"), log)
            if proc.returncode:
                print(proc.stderr, flush=True)
                raise RuntimeError(f"Reconstruction failed: {model_id}; inspect execution log")
            record = read(result)
            record.update(model_id=model_id, input_case=case["name"], profile=profile, kind=kind,
                          settings=settings, input_labels_sha256=case["input_labels_sha256"],
                          implementation_sha256=digest(work / "reconstruction.py"),
                          worker_sha256=digest(work / "worker.py"),
                          build_fingerprint=fingerprint,
                          artifact_sha256=inventory(model, exclude=("worker_result.json",)),
                          worker_directory_sha256=inventory(work))
            write(result, record)
            write(out / "build_records" / (model_id + ".json"), record)
            print(proc.stdout.strip(), flush=True)


def evaluate(out, config, selected=None, recompute_metrics=False):
    from ah53.voxel_reconstruction_metrics import evaluate_saved, evaluate_voxel_baseline
    manifest = validate_inputs(out, config)
    reference_dir = ROOT / "results" / config["source_run"] / "models" / "reference_local"
    for case in manifest:
        if selected and case["name"] not in selected:
            continue
        inp = out / "inputs" / case["name"]
        reference = reference_dir if case["input_kind"] == "AH53_saved_labels" else None
        options = dict(config["evaluation"])
        if reference is None:
            grid = case["grid"]
            z0, h = grid["origin_xyz_nm"][2], grid["spacing_nm"]
            options["z_nm"] = [z0 + h * k for k in [2.37, 10.37, 15.37, 16.37, 22.37, 29.37]]
        basefile = out / "metrics" / (case["name"] + "__voxel_baseline.json")
        base_fingerprint = metric_fingerprint(out, case, reference, options)
        baseline = checked_metric(basefile, base_fingerprint, recompute_metrics)
        if baseline is None:
            print(json.dumps({"evaluating_baseline": case["name"]}), flush=True)
            baseline = evaluate_voxel_baseline(inp, reference, options=options)
            baseline["evaluation_fingerprint"] = base_fingerprint
            write(basefile, baseline)
        for profile, kind, settings in profiles_for(case, config):
            model_id = case["name"] + "__" + profile
            destination = out / "metrics" / (model_id + ".json")
            build = checked_build(out, model_id, build_fingerprint(out, case, kind, settings))
            fingerprint = metric_fingerprint(out, case, reference, options, build)
            if checked_metric(destination, fingerprint, recompute_metrics) is not None:
                continue
            if build.get("status") == "unsupported_topology":
                write(destination, {"model_id": model_id, "status": "unsupported_topology", "build": build,
                                    "evaluation_fingerprint": fingerprint})
                continue
            print(json.dumps({"evaluating": model_id}), flush=True)
            result = evaluate_saved(inp, out / "models" / model_id, kind, reference, options=options, baseline=baseline)
            result.update(model_id=model_id, input_case=case["name"], profile=profile, build=build,
                          evaluation_fingerprint=fingerprint)
            write(destination, result)
            print(json.dumps({"evaluated": model_id}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/20261024_voxel_reconstruction")
    parser.add_argument("--phase", choices=["prepare", "reconstruct", "evaluate", "all"], default="all")
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--recompute-metrics", action="store_true",
                        help="Explicitly replace selected scoring caches; preserve and verify all reconstruction artifacts")
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    config = read(CONFIG_PATH)
    if args.cases and not set(args.cases) <= ({c["name"] for c in config["cases"]} | set(config["challenges"])):
        raise ValueError("Unknown --cases name; nothing was run")
    if args.phase in ("prepare", "all"):
        manifest = prepare(out, config)
        print(json.dumps({"prepared_inputs": len(manifest), "output": str(out)}, ensure_ascii=True), flush=True)
    if args.phase in ("reconstruct", "all"):
        reconstruct(out, config, args.cases)
    if args.phase in ("evaluate", "all"):
        evaluate(out, config, args.cases, args.recompute_metrics)


if __name__ == "__main__":
    main()
