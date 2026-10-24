"""Run a small, reproducible comparison of three Mark shape representations.

Nine cases, one construction per case. These are geometry experiments, not
electromagnetic simulations, GUI tests, or statistically repeated benchmarks.
Run: python benchmark.py --output results
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


CASES = [
    {"id": f"local_{method}_{level}", "case": "local", "method": method,
     "level": level, "settings": (
         {"h_nm": 25.0 if level == "coarse" else 10.0} if method == "voxel"
         else {"dy_nm": 50.0 if level == "coarse" else 25.0,
               "dz_nm": 160.0 if level == "coarse" else 80.0})}
    for method in ("parametric", "surface", "voxel")
    for level in ("coarse", "fine")
] + [
    {"id": f"full_{method}_fine", "case": "full", "method": method,
     "level": "fine", "settings": (
         {"h_nm": 10.0} if method == "voxel"
         else {"dy_nm": 25.0, "dz_nm": 80.0})}
    for method in ("parametric", "surface", "voxel")
]


def peak_rss_bytes():
    """Process high-water mark, including Python, libraries and temporaries."""
    try:
        import resource
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(raw if sys.platform == "darwin" else raw * 1024)
    except (ImportError, AttributeError):
        return None


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def run_case(spec, output):
    import numpy as np
    from reference import ReferenceGeometry

    method = spec["method"]
    if method == "parametric":
        from parametric import ParametricRepresentation as Representation
    elif method == "surface":
        from explicit_surface import ExplicitSurfaceRepresentation as Representation
    else:
        from voxel import VoxelRepresentation as Representation

    ref = ReferenceGeometry(spec["case"])
    settings = spec["settings"]
    kwargs = ({"h": settings["h_nm"]} if method == "voxel" else
              {"dy": settings["dy_nm"], "dz": settings["dz_nm"]})
    baseline_rss = peak_rss_bytes()
    t0 = time.perf_counter()
    model = Representation(ref, **kwargs)
    construction_seconds = time.perf_counter() - t0
    construction_rss = peak_rss_bytes()

    def stats(values):
        values = np.asarray(values, dtype=np.float64).ravel()
        return {"mean_signed": float(np.mean(values)),
                "rms": float(np.sqrt(np.mean(values ** 2))),
                "p95_abs": float(np.percentile(np.abs(values), 95)),
                "max_abs": float(np.max(np.abs(values))),
                "samples": int(values.size)}

    # Same independent evaluation points for every representation of a case.
    rng = np.random.Generator(np.random.PCG64(137021))
    n_per_line = 6000
    y = rng.uniform(0.0, ref.height, n_per_line)
    z = rng.uniform(ref.zmin, ref.zmax, n_per_line)
    truth = np.stack([ref.boundaries(i, y, z) for i in range(ref.n_lines)])
    t0 = time.perf_counter()
    predicted = (model.boundaries_all(y, z) if method == "voxel" else
                 np.stack([model.boundaries(i, y, z)
                           for i in range(ref.n_lines)]))
    boundary_query_seconds = time.perf_counter() - t0
    errors = predicted - truth
    cd_errors = errors[:, 1, :] - errors[:, 0, :]
    center_errors = (errors[:, 1, :] + errors[:, 0, :]) / 2.0
    minimum_width = float(np.min(predicted[:, 1, :] - predicted[:, 0, :]))
    minimum_gap = float(np.min(predicted[1:, 0, :] - predicted[:-1, 1, :]))
    if minimum_width <= 0 or minimum_gap <= 0:
        raise ValueError("The represented ridges crossed or lost positive width")

    # Random material queries over the domain, plus a boundary-focused set.
    # Near-boundary disagreement avoids hiding boundary errors in uniform air.
    n_material = 20000
    rng = np.random.Generator(np.random.PCG64(912450))
    ux = rng.uniform(ref.xmin, ref.xmax, n_material)
    uy = rng.uniform(ref.ymin, ref.ymax, n_material)
    uz = rng.uniform(ref.zmin, ref.zmax, n_material)
    uniform_expected = ref.material_at(ux, uy, uz)
    uniform_actual = model.material_at(ux, uy, uz)
    by = rng.uniform(0.0, ref.height, n_material)
    bz = rng.uniform(ref.zmin, ref.zmax, n_material)
    lines = rng.integers(0, ref.n_lines, n_material)
    sides = rng.integers(0, 2, n_material)
    bx = np.empty(n_material, dtype=float)
    for line in range(ref.n_lines):
        mask = lines == line
        bounds = ref.boundaries(line, by[mask], bz[mask])
        bx[mask] = np.where(sides[mask] == 0, bounds[0], bounds[1])
    bx += rng.uniform(-20.0, 20.0, n_material)
    near_expected = ref.material_at(bx, by, bz)
    near_actual = model.material_at(bx, by, bz)

    reference_volume = ref.volume_reference()
    if method == "surface":
        mv = model.material_volumes_nm3()
        represented_volume = {"1": mv[1], "2": mv[2],
                              "domain": reference_volume["domain"]}
        represented_volume["0"] = reference_volume["domain"] - mv[1] - mv[2]
    else:
        represented_volume = model.volume()
    ridge_relative_error = ((represented_volume["1"] - reference_volume["1"])
                            / reference_volume["1"])

    topology = None
    if spec["id"] == "local_surface_fine":
        # One meaningful closure/orientation check, not a broad test suite.
        topology = model.check_geometry(local=True)
        if not all(topology[k] for k in ("finite_vertices", "valid_face_indices",
                                         "nonzero_faces")):
            raise ValueError("Triangle data check failed")
        for label in (1, 2):
            if not all(topology[f"material_{label}"][key]
                       for key in ("edge_closed", "consistent_orientation")):
                raise ValueError("A material's surface is not closed/oriented")
        model.save(output / "local_surface_fine.npz")

    profiles = None
    if spec["case"] == "local" and spec["level"] == "fine":
        py = np.linspace(0.0, ref.height, 501)
        cut_z = 742.0  # Deliberately not a construction node.
        pl, pr = model.boundaries(0, py, cut_z)
        tl, tr = ref.boundaries(0, py, cut_z)
        pz = np.linspace(ref.zmin, ref.zmax, 1025)
        cut_y = 137.0  # Deliberately not a construction node.
        _, along = model.boundaries(0, cut_y, pz)
        _, along_truth = ref.boundaries(0, cut_y, pz)
        profiles = {
            "cross_section": {"y_nm": py.tolist(), "z_nm": cut_z,
                              "left_nm": pl.tolist(), "right_nm": pr.tolist(),
                              "reference_left_nm": tl.tolist(),
                              "reference_right_nm": tr.tolist()},
            "along_length": {"z_nm": pz.tolist(), "y_nm": cut_y,
                             "right_nm": along.tolist(),
                             "reference_right_nm": along_truth.tolist()},
        }
    if method == "voxel":
        spacing = {"dx": model.hx, "dy": model.hy, "dz": model.hz}
    else:
        spacing = {"dy": float(model.y_nodes[1] - model.y_nodes[0]),
                   "dz": float(model.z_nodes[1] - model.z_nodes[0])}
    result = {
        **spec,
        "actual_spacing_nm": spacing,
        "domain_um": {"x": ref.width_x / 1000, "z": ref.length_z / 1000,
                      "y": (ref.height + ref.substrate) / 1000},
        "n_lines": ref.n_lines,
        "payload_bytes": model.payload_bytes,
        "counts": model.surface_counts,
        "construction_seconds": construction_seconds,
        "baseline_peak_rss_bytes": baseline_rss,
        "construction_peak_rss_bytes": construction_rss,
        "process_peak_rss_bytes": peak_rss_bytes(),
        "boundary_query_seconds": boundary_query_seconds,
        "boundary_error_nm": stats(errors),
        "left_boundary_error_nm": stats(errors[:, 0, :]),
        "right_boundary_error_nm": stats(errors[:, 1, :]),
        "cd_error_nm": stats(cd_errors),
        "center_error_nm": stats(center_errors),
        "sampled_minimum_width_nm": minimum_width,
        "sampled_minimum_gap_nm": minimum_gap,
        "material_disagreement": {
            "uniform_samples": n_material,
            "uniform_fraction": float(np.mean(uniform_actual != uniform_expected)),
            "near_boundary_samples": n_material,
            "near_boundary_band_halfwidth_nm": 20.0,
            "near_boundary_fraction": float(np.mean(near_actual != near_expected)),
        },
        "reference_volumes_nm3": reference_volume,
        "represented_volumes_nm3": represented_volume,
        "ridge_volume_relative_error": float(ridge_relative_error),
        "triangle_closure_check": topology,
        "profiles": profiles,
    }
    write_json(output / f"{spec['id']}.json", result)
    print(json.dumps({"id": spec["id"], "payload_bytes": result["payload_bytes"],
                      "p95_boundary_nm": result["boundary_error_nm"]["p95_abs"],
                      "build_s": construction_seconds,
                      "peak_rss_bytes": result["process_peak_rss_bytes"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--case-id", choices=[c["id"] for c in CASES],
                        help="Internal worker, or run one selected case")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.case_id:
        run_case(next(c for c in CASES if c["id"] == args.case_id), output)
        return

    started = datetime.now(timezone.utc).isoformat()
    # Sequential independent processes keep memory isolated and avoid running
    # several large voxel arrays concurrently. No averaging or repeats.
    worker_env = os.environ.copy()
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        worker_env[name] = "1"
    for spec in CASES:
        subprocess.run([sys.executable, str(Path(__file__).resolve()),
                        "--output", str(output), "--case-id", spec["id"]],
                       check=True, env=worker_env)

    import numpy as np
    import scipy
    from reference import ReferenceGeometry
    results = [json.loads((output / f"{c['id']}.json").read_text(encoding="utf-8"))
               for c in CASES]
    summary = {
        "title": "Mark geometry representation pilot",
        "run_started_utc": started,
        "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": sys.version.split()[0],
                        "numpy": np.__version__, "scipy": scipy.__version__,
                        "platform": platform.platform(),
                        "machine": platform.machine(),
                        "worker_numeric_threads": 1},
        "protocol": {
            "cases": 9, "repeats_per_case": 1,
            "boundary_yz_pairs_per_line": 6000,
            "evaluation_rng_seed": 137021,
            "material_rng_seed": 912450,
            "boundary_metric": "X displacement at equal Y,Z, not Hausdorff distance",
            "maximum_metric": "maximum over the sampled independent evaluation points",
            "payload": "stored model arrays and minimal metadata, excluding runtime overhead",
            "memory": "per-process peak RSS, including Python, libraries, and temporaries",
            "timing": "single run construction timing; not a statistical speed ranking",
            "sampling": "P and T use identical sidewall observation nodes; V samples cell centres",
            "scope": "smooth synthetic asymmetric cross-sections and height/length-dependent sidewalls",
            "out_of_scope": ["measured shape reconstruction", "holes", "airgaps", "topology changes",
                             "GUI integration", "Lumerical import", "electromagnetic computation"],
            "caveat": "this smooth fixed-topology reference favors a smooth interpolation prior",
        },
        "results": results,
    }
    write_json(output / "summary.json", summary)
    write_json(output / "reference_definition.json",
               {case: ReferenceGeometry(case).reference_metadata()
                for case in ("local", "full")})
    fields = ["id", "case", "method", "level", "payload_bytes",
              "construction_seconds", "construction_peak_rss_bytes", "process_peak_rss_bytes",
              "boundary_p95_nm", "boundary_sampled_max_nm", "boundary_rms_nm",
              "cd_p95_nm", "center_p95_nm", "ridge_volume_error_percent",
              "uniform_material_disagreement_percent", "near_boundary_disagreement_percent"]
    with (output / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = {key: result[key] for key in fields if key in result}
            row.update({
                "boundary_p95_nm": result["boundary_error_nm"]["p95_abs"],
                "boundary_sampled_max_nm": result["boundary_error_nm"]["max_abs"],
                "boundary_rms_nm": result["boundary_error_nm"]["rms"],
                "cd_p95_nm": result["cd_error_nm"]["p95_abs"],
                "center_p95_nm": result["center_error_nm"]["p95_abs"],
                "ridge_volume_error_percent": result["ridge_volume_relative_error"] * 100,
                "uniform_material_disagreement_percent": result["material_disagreement"]["uniform_fraction"] * 100,
                "near_boundary_disagreement_percent": result["material_disagreement"]["near_boundary_fraction"] * 100,
            })
            writer.writerow(row)
    print(f"Saved {len(results)} completed cases to {output}", flush=True)


if __name__ == "__main__":
    main()
