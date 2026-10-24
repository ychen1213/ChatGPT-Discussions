"""Independent readback/numerical audit after the formal voxel trial has finished.

Does not rebuild models, tune reconstruction settings, or change metric caches.
The two numerical models are fixed in advance: local_5nm P_sigma05 and T_MC.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy import ndimage
from shapely import contains_xy, distance, points
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ah53.reference_geometry import ReferenceGeometry
from ah53.voxel_reconstruction import load_reconstruction
from ah53.voxel_reconstruction_metrics import (
    LabelGrid, clip_segments_above, contour_segments, rasterize_section,
    section_pair_distance,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def tree_hashes(directory, exclude=()):
    directory = Path(directory)
    return {p.relative_to(directory).as_posix(): sha256(p)
            for p in sorted(directory.rglob("*"))
            if p.is_file() and p.relative_to(directory).as_posix() not in exclude}


def expected_records(config):
    profiles = [p["name"] for p in config["P_profiles"]]
    result = []
    for name in [c["name"] for c in config["cases"]] + config["challenges"]:
        selected = ["P_sigma05"] if name in ("through_hole", "merging_bridge") else profiles
        result.extend(name + "__" + p for p in ["T_MC", *selected])
    return result


def required_files(out, config):
    required = [out / "input_manifest.json", out / "protocol.json"]
    required.extend(out / "build_records" / (model_id + ".json") for model_id in expected_records(config))
    for profile in ("P_sigma05", "T_MC"):
        model_id = "local_5nm__" + profile
        required.extend([out / "metrics" / (model_id + ".json"),
                         out / "models" / model_id / "worker_result.json"])
    return required


def forbidden_metadata_keys(obj, prefix=""):
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = prefix + "." + key if prefix else key
            if key in {"config", "centers", "ids", "reference_definition", "local_feature"}:
                found.append(path)
            found.extend(forbidden_metadata_keys(value, path))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            found.extend(forbidden_metadata_keys(value, f"{prefix}[{index}]"))
    return found


def audit_provenance(out, config):
    manifest = read(out / "input_manifest.json")
    protocol = read(out / "protocol.json")
    input_records, fingerprints = [], {}
    for case in manifest:
        directory = out / "inputs" / case["name"]
        labels_hash, grid_hash = sha256(directory / "labels.npy"), sha256(directory / "grid.json")
        grid = read(directory / "grid.json")
        checks = {
            "labels_match_manifest": labels_hash == case["input_labels_sha256"],
            "minimal_grid_only": set(grid) == set(config["allowed_grid_fields"]),
            "grid_matches_manifest": grid == case["grid"],
            "only_two_input_files": sorted(p.name for p in directory.iterdir()) == ["grid.json", "labels.npy"],
        }
        if case.get("source"):
            source = ROOT / "results" / config["source_run"] / "models" / case["source"] / "labels.npy"
            checks["labels_match_original_saved_voxels"] = labels_hash == sha256(source)
        input_records.append({"case": case["name"], "sha256": labels_hash,
                              "grid_sha256": grid_hash, "checks": checks, "passed": all(checks.values())})
        fingerprints[case["name"]] = (labels_hash, grid_hash)
    current_code = sha256(ROOT / "src/ah53/voxel_reconstruction.py")
    current_worker = sha256(ROOT / "scripts/voxel_reconstruction_worker.py")
    config_hash = sha256(ROOT / "configs/voxel_reconstruction.json")
    builds = []
    for model_id in expected_records(config):
        record = read(out / "build_records" / (model_id + ".json"))
        work = record["worker"]
        fp = record["build_fingerprint"]
        labels_hash, grid_hash = fingerprints[record["input_case"]]
        directory = out / "models" / model_id
        metadata = read(directory / record["kind"] / "metadata.json")
        forbidden = forbidden_metadata_keys(metadata)
        probes = work.get("forbidden_read_probes", [])
        checks = {
            "three_forbidden_reads_blocked": len(probes) == 3 and all(p.get("blocked") is True for p in probes),
            "exactly_three_blocked_reads": work.get("blocked_read_count") == 3,
            "no_unexpected_blocked_read": work.get("unexpected_blocked_reads") == [],
            "isolated_python": work.get("python_isolated") is True,
            "ah53_not_imported_in_worker": work.get("project_package_imported") is False,
            "initial_worker_only_two_scripts": sorted(work.get("initial_worker_files", [])) == ["reconstruction.py", "worker.py"],
            "initial_output_empty": work.get("initial_output_files") == [],
            "input_labels_fingerprint": fp.get("input_labels_sha256") == labels_hash == record.get("input_labels_sha256"),
            "input_grid_fingerprint": fp.get("input_grid_sha256") == grid_hash,
            "config_fingerprint": fp.get("config_sha256") == config_hash,
            "implementation_fingerprint": fp.get("implementation_sha256") == current_code == record.get("implementation_sha256"),
            "worker_fingerprint": fp.get("worker_sha256") == current_worker == record.get("worker_sha256"),
            "runtime_matches_protocol": fp.get("runtime_versions") == protocol["runtime_versions"],
            "metadata_has_no_truth_recipe_keys": not forbidden,
            "saved_artifacts_match_record": tree_hashes(directory, ("worker_result.json",)) == record["artifact_sha256"],
            "worker_tree_matches_record": tree_hashes(out / "workers" / model_id) == record["worker_directory_sha256"],
            "worker_result_matches_published_build_record": read(directory / "worker_result.json") == record,
        }
        builds.append({"model_id": model_id, "checks": checks,
                       "forbidden_metadata_keys": forbidden, "passed": all(checks.values())})
    protocol_checks = {
        "frozen_config_matches": protocol["config_sha256"] == config_hash and protocol["config"] == config,
        "frozen_manifest_matches": protocol["input_manifest_sha256"] == sha256(out / "input_manifest.json"),
        "complete_expected_build_matrix": len(builds) == len(expected_records(config)),
    }
    return {"input_count": len(input_records), "build_count": len(builds),
            "protocol_checks": protocol_checks, "inputs": input_records, "builds": builds,
            "passed": all(protocol_checks.values()) and all(r["passed"] for r in input_records + builds),
            "scope": "recheck recorded Python file-open guard probes and hashes; not an OS sandbox or researcher double-blind claim"}


def convergence(out):
    model_id = "local_5nm__P_sigma05"
    model = load_reconstruction(out / "models" / model_id, kind="P")
    formal = read(out / "metrics" / (model_id + ".json"))
    reference = ReferenceGeometry.load(ROOT / "results/20261024_v2/models/reference_local")
    minimum_y = formal["common_height_band_minimum_y_nm"]
    records = []
    for z in (413., 677.):
        truth = clip_segments_above(contour_segments(
            [reference.contour(line, z, step_nm=.25) for line in range(reference.n_lines)]), minimum_y)
        curves = {step: clip_segments_above(contour_segments(model.section(z, step_nm=step)), minimum_y)
                  for step in (.5, .25)}
        scores = {step: section_pair_distance(truth, curves[step], 2.)[0]["all"] for step in curves}
        delta = {key: abs(scores[.5][key] - scores[.25][key]) for key in ("rms_nm", "p95_nm", "max_nm")}
        direct = section_pair_distance(curves[.5], curves[.25], .5)[0]["all"]
        records.append({"z_nm": z, "step_0_5_nm": scores[.5], "step_0_25_nm": scores[.25],
                        "absolute_score_changes_nm": delta, "between_discretizations": direct,
                        "passed": max(delta.values()) < .02 and direct["max_nm"] < .02})
    return {"model_id": model_id, "reference_curve_step_nm": .25,
            "distance_sample_step_nm": 2., "threshold_nm": .02,
            "threshold_note": "predeclared numerical diagnostic; not a reconstruction-parameter tuning target",
            "minimum_y_nm": minimum_y, "records": records,
            "passed": all(r["passed"] for r in records)}


def sample_centers(grid, seed=20261024):
    rng = np.random.default_rng(seed)
    nz, ny, nx = grid.labels.shape
    selected_z = np.sort(rng.choice(nz, size=min(32, nz), replace=False))
    global_samples = np.column_stack((rng.choice(selected_z, 5000), rng.integers(ny, size=5000),
                                      rng.integers(nx, size=5000)))
    boundary_samples = []
    allocation = np.full(len(selected_z), 5000 // len(selected_z), int)
    allocation[:5000 % len(selected_z)] += 1
    for z, count in zip(selected_z, allocation):
        occupied = np.asarray(grid.labels[z] == 1)
        padded = np.pad(occupied, 1)
        edge = np.zeros_like(occupied)
        for adjacent in (padded[1:-1, :-2], padded[1:-1, 2:], padded[:-2, 1:-1], padded[2:, 1:-1]):
            edge |= occupied != adjacent
        band = ndimage.binary_dilation(edge, iterations=1)
        candidates = np.flatnonzero(band)
        chosen = rng.choice(candidates, size=count, replace=len(candidates) < count)
        y, x = np.unravel_index(chosen, (ny, nx))
        boundary_samples.append(np.column_stack((np.full(count, z), y, x)))
    samples = np.concatenate((global_samples, *boundary_samples))
    return samples.astype(int), np.r_[np.zeros(5000, int), np.ones(5000, int)], selected_z


def independent_center_classification(out):
    grid = LabelGrid.load(out / "inputs/local_5nm")
    samples, strata, selected_z = sample_centers(grid)
    reports = []
    for profile, kind in (("P_sigma05", "P"), ("T_MC", "T")):
        model_id = "local_5nm__" + profile
        model = load_reconstruction(out / "models" / model_id, kind=kind)
        raster_inside, independent_inside, ties = (np.zeros(len(samples), bool) for _ in range(3))
        for iz in selected_z:
            selected = np.flatnonzero(samples[:, 0] == iz)
            iy, ix = samples[selected, 1], samples[selected, 2]
            z = grid.origin[2] + (iz + .5) * grid.spacing[2]
            x = grid.origin[0] + (ix + .5) * grid.spacing[0]
            y = grid.origin[1] + (iy + .5) * grid.spacing[1]
            rings = model.section(float(z), step_nm=.5)
            mask, _ = rasterize_section(rings, grid.labels.shape[1:], grid.origin[:2], grid.spacing[:2])
            raster_inside[selected] = mask[iy, ix]
            sample_points = points(x, y)
            for ring in rings:
                polygon = Polygon(ring)
                independent_inside[selected] ^= contains_xy(polygon, x, y)
                ties[selected] |= distance(polygon.boundary, sample_points) <= 1e-8
        mismatch = raster_inside != independent_inside
        records = []
        for index, name in ((0, "whole_XY_domain"), (1, "label_transition_boundary_band")):
            take = strata == index
            records.append({"stratum": name, "samples": int(take.sum()),
                            "points_within_1e_8_nm_of_polygon_boundary": int((take & ties).sum()),
                            "raw_disagreements": int((take & mismatch).sum()),
                            "disagreements_excluding_boundary_ties": int((take & mismatch & ~ties).sum())})
        reports.append({"model_id": model_id, "strata": records,
                        "total_disagreements_excluding_boundary_ties": int((mismatch & ~ties).sum()),
                        "passed": not bool(np.any(mismatch & ~ties))})
    return {"seed": 20261024, "sample_count_per_model": len(samples),
            "unique_sampled_cells": len(np.unique(samples, axis=0)),
            "selected_z_indices": selected_z.tolist(), "selected_z_plane_count": len(selected_z),
            "sample_selection": "5000 uniform XY samples on 32 seed-selected voxel Z planes plus 5000 samples in a one-cell dilation of label1/non1 transitions; reference never used for sampling",
            "independent_method": "Shapely contains_xy per closed polygon, XOR even-odd across loops; independent of scoring scanline rasterizer",
            "boundary_tie_handling": "distances <=1e-8 nm to polygon boundaries reported separately; no forced inside/outside verdict there",
            "limitation": "validates polygon classification at stated discretization and sampled planes, not full continuous P solid membership",
            "models": reports, "passed": all(r["passed"] for r in reports)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/20261024_voxel_reconstruction")
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    config = read(ROOT / "configs/voxel_reconstruction.json")
    missing = [str(p.relative_to(out)) for p in required_files(out, config) if not p.is_file()]
    if missing:
        raise SystemExit("Formal results not ready; no audit written. Missing: " + ", ".join(missing))
    started = time.perf_counter()
    print("Auditing frozen inputs and every formal reconstruction record", flush=True)
    provenance = audit_provenance(out, config)
    print("Checking P curve-discretization convergence on two fixed sections", flush=True)
    curve_check = convergence(out)
    print("Checking 10000 cell centers independently for P_sigma05 and T_MC", flush=True)
    centers = independent_center_classification(out)
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
              "audit_script_sha256": sha256(__file__), "provenance": provenance,
              "curve_discretization_convergence": curve_check,
              "independent_center_classification": centers,
              "passed": provenance["passed"] and curve_check["passed"] and centers["passed"],
              "seconds": time.perf_counter() - started}
    destination = out / "independent_audit.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(destination), "passed": result["passed"], "seconds": result["seconds"]}), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
