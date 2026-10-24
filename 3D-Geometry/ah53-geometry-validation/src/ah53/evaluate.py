"""Independent physical-coordinate evaluation of persisted AH53 representations.

Distances are bidirectional, arc-length weighted XY-section distances to actual
line segments. They are deliberately not called full-3D Hausdorff distances.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

REGIONS = ("left_wall", "left_shoulder", "top", "right_shoulder", "right_wall")


def json_clean(value):
    if isinstance(value, dict):
        return {str(k): json_clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_clean(value.tolist())
    if isinstance(value, np.generic):
        return json_clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path, data):
    Path(path).write_text(json.dumps(json_clean(data), ensure_ascii=False,
                                   indent=2, allow_nan=False) + "\n", encoding="utf-8")


def file_inventory(path):
    """Hash exact saved files, streaming large label arrays without loading them."""
    path = Path(path)
    files = []
    aggregate = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        h = hashlib.sha256()
        with file.open("rb") as stream:
            while chunk := stream.read(4 * 1024 * 1024):
                h.update(chunk)
        entry = {"name": file.relative_to(path).as_posix(), "bytes": file.stat().st_size,
                 "sha256": h.hexdigest()}
        aggregate.update((entry["name"] + "\0" + entry["sha256"]).encode())
        files.append(entry)
    return {"sha256": aggregate.hexdigest(), "file_bytes": sum(f["bytes"] for f in files),
            "files": files}


def stats(values, weights=None):
    values = np.asarray(values, float).ravel()
    weights = np.ones(values.size) if weights is None else np.asarray(weights, float).ravel()
    ok = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    missing = int((~ok).sum())
    values, weights = values[ok], weights[ok]
    if not values.size:
        return {"rms_nm": None, "p95_nm": None, "max_nm": None,
                "mean_signed_nm": None, "samples": 0, "missing": missing}
    order = np.argsort(np.abs(values))
    cumulative = np.cumsum(weights[order])
    q = int(np.searchsorted(cumulative, 0.95 * cumulative[-1]))
    return {"rms_nm": float(np.sqrt(np.average(values * values, weights=weights))),
            "p95_nm": float(abs(values[order[min(q, values.size - 1)]])),
            "max_nm": float(np.max(np.abs(values))),
            "mean_signed_nm": float(np.average(values, weights=weights)),
            "samples": int(values.size), "missing": missing}


class SegmentSet:
    """Exact point-to-polyline distance accelerated by conservative midpoint bounds."""
    def __init__(self, starts, ends, region=None):
        starts, ends = np.asarray(starts, float), np.asarray(ends, float)
        length = np.linalg.norm(ends - starts, axis=1)
        valid = length > 1e-10
        self.a, self.b, self.length = starts[valid], ends[valid], length[valid]
        self.delta = self.b - self.a
        self.mid = (self.a + self.b) / 2
        self.tree = cKDTree(self.mid)
        self.maxhalf = float(np.max(self.length) / 2)
        self.region = np.zeros(len(self.a), dtype=int) if region is None else np.asarray(region)[valid]

    def sample(self, step=2.0):
        n = np.maximum(1, np.ceil(self.length / step).astype(int))
        ids = np.repeat(np.arange(len(n)), n)
        offset = np.repeat(np.cumsum(n) - n, n)
        t = (np.arange(len(ids)) - offset + 0.5) / n[ids]
        return (self.a[ids] + t[:, None] * self.delta[ids],
                self.length[ids] / n[ids], self.region[ids], ids)

    def distances(self, points, return_index=False):
        points = np.asarray(points, float)
        k = min(12, len(self.a))
        dm, ix = self.tree.query(points, k=k)
        if k == 1:
            dm, ix = dm[:, None], ix[:, None]
        aa, dd = self.a[ix], self.delta[ix]
        tt = np.clip(np.sum((points[:, None] - aa) * dd, axis=2) /
                     (self.length[ix] ** 2), 0, 1)
        dist = np.linalg.norm(points[:, None] - aa - tt[:, :, None] * dd, axis=2)
        best = np.argmin(dist, axis=1)
        distance, nearest = dist[np.arange(len(points)), best], ix[np.arange(len(points)), best]
        # Every unseen segment is at least d(midpoint)-half_length away.
        # A radius fallback makes this exact even for very unequal segment lengths.
        uncertain = np.nonzero(dm[:, -1] <= distance + self.maxhalf + 1e-12)[0] if k < len(self.a) else []
        for row in uncertain:
            candidates = np.asarray(self.tree.query_ball_point(points[row], distance[row] + self.maxhalf + 1e-10))
            delta = self.delta[candidates]
            t = np.clip(np.sum((points[row] - self.a[candidates]) * delta, axis=1) /
                        self.length[candidates] ** 2, 0, 1)
            d = np.linalg.norm(points[row] - self.a[candidates] - t[:, None] * delta, axis=1)
            j = int(np.argmin(d))
            distance[row], nearest[row] = d[j], candidates[j]
        return (distance, nearest) if return_index else distance


def segments(model, line, z, step=1.0, with_regions=False):
    if with_regions:
        aa, bb, rr = [], [], []
        for index, name in enumerate(REGIONS):
            p = np.asarray(model.region_contour(line, z, name, step_nm=step), float)
            aa.append(p[:-1]); bb.append(p[1:]); rr.append(np.full(max(0, len(p)-1), index))
        return SegmentSet(np.concatenate(aa), np.concatenate(bb), np.concatenate(rr))
    p = np.asarray(model.contour(line, z, step_nm=step), float)
    a, b = p[:-1], p[1:]
    # Exclude artificial substrate contact/bottom, never dilute free-surface errors.
    keep = ~((np.abs(a[:, 1]) < 1e-7) & (np.abs(b[:, 1]) < 1e-7))
    return SegmentSet(a[keep], b[keep])


def section_positions(scene):
    if scene == "local":
        return np.array([-1783., -1167., -443., 137., 413., 677., 1549.])
    return np.array([-21873., -13761., -1783., 137., 413., 677., 12749., 21317.])


def section_distance(reference, candidate, z_positions, lines=None, step=1.0, sample_step=2.0,
                     reference_regions=True):
    lines = list(range(len(reference.centers))) if lines is None else lines
    values = {name: [[], []] for name in REGIONS}
    directions = {"reference_to_candidate": [[], []], "candidate_to_reference": [[], []]}
    sections_out = []
    for line in lines:
        for z in z_positions:
            truth = segments(reference, line, float(z), step, with_regions=reference_regions)
            actual = segments(candidate, line, float(z), step)
            p, w, region, _ = truth.sample(sample_step)
            d = actual.distances(p)
            q, v, _, _ = actual.sample(sample_step * 1.013)
            e, nearest = truth.distances(q, return_index=True)
            assigned = truth.region[nearest]
            directions["reference_to_candidate"][0].append(d)
            directions["reference_to_candidate"][1].append(w)
            directions["candidate_to_reference"][0].append(e)
            directions["candidate_to_reference"][1].append(v)
            for index, name in enumerate(REGIONS):
                values[name][0].extend((d[region == index], e[assigned == index]))
                values[name][1].extend((w[region == index], v[assigned == index]))
            sections_out.append({"line": int(line), "z_nm": float(z),
                                 **stats(np.r_[d, e], np.r_[w, v])})
    output = {"definition": "bidirectional arc-length-weighted XY-section point-to-segment distance",
              "z_positions_nm": np.asarray(z_positions).tolist(), "line_indices": lines,
              "curve_step_nm": step, "quadrature_max_step_nm": sample_step * 1.013,
              "region_assignment": "candidate samples assigned by nearest reference segment",
              "sections": sections_out}
    all_d, all_w = [], []
    for name, (vv, ww) in directions.items():
        v, w = np.concatenate(vv), np.concatenate(ww)
        output[name] = stats(v, w); all_d.append(v); all_w.append(w)
    output["all"] = stats(np.concatenate(all_d), np.concatenate(all_w))
    output["regions"] = {name: stats(np.concatenate(v), np.concatenate(w))
                         for name, (v, w) in values.items()}
    return output


def top_intersections(contour, x):
    contour = np.asarray(contour)
    a, b = contour[:-1], contour[1:]
    answer = np.full(len(np.atleast_1d(x)), np.nan)
    for i, xx in enumerate(np.atleast_1d(x)):
        dx = b[:, 0] - a[:, 0]
        ok = (np.abs(dx) > 1e-12) & (xx >= np.minimum(a[:, 0], b[:, 0])) & (xx <= np.maximum(a[:, 0], b[:, 0]))
        if np.any(ok):
            t = (xx - a[ok, 0]) / dx[ok]
            answer[i] = np.max(a[ok, 1] + t * (b[ok, 1] - a[ok, 1]))
    return answer


def edge_features(z, edge, truth):
    edge, truth = np.asarray(edge), np.asarray(truth)
    valid = np.isfinite(edge) & np.isfinite(truth)
    if not valid.all():
        return {"missing": int((~valid).sum())}
    a, b = edge - edge.mean(), truth - truth.mean()
    freq = np.fft.rfftfreq(len(z), d=float(z[1] - z[0]))
    aa = np.abs(np.fft.rfft(a)) ** 2 / len(z) ** 2
    bb = np.abs(np.fft.rfft(b)) ** 2 / len(z) ** 2
    if len(aa) > 2:
        aa[1:-1] *= 2; bb[1:-1] *= 2
    bands = {}
    for name, low, high in (("short_160_600nm", 160., 600.), ("long_600_4000nm", 600., 4000.)):
        mask = (freq >= 1/high) & (freq <= 1/low)
        actual_power, ref_power = float(aa[mask].sum()), float(bb[mask].sum())
        bands[name] = {"candidate_nm2": actual_power, "reference_nm2": ref_power,
                       "ratio": actual_power/ref_power if ref_power > 1e-15 else None,
                       "frequency_bins": int(mask.sum())}
    return {"rms_nm": float(np.sqrt(np.mean(a*a))),
            "reference_rms_nm": float(np.sqrt(np.mean(b*b))),
            "correlation": float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 1e-12 else None,
            "bands": bands, "missing": 0}


def physical_profiles(reference, candidate, scene, output_npz=None):
    b = np.asarray(reference.bounds)
    spacing = 16. if scene == "local" else 32.
    count = int((b[5]-b[4])/spacing)
    # Cell-centred independent evaluation positions: no endpoints and no 40/80nm nodes.
    z = b[4] + (np.arange(count)+0.371)*((b[5]-b[4])/count)
    heights = np.array([30., 150., 270.])
    truth = np.empty((len(reference.centers), 3, 2, len(z)))
    predicted = np.empty_like(truth)
    for line in range(len(reference.centers)):
        yy = np.broadcast_to(heights[:, None], (3,len(z)))
        zz = np.broadcast_to(z[None,:], yy.shape)
        truth[line] = np.moveaxis(np.asarray(reference.boundaries(line, yy, zz)),0,1)
        predicted[line] = np.moveaxis(np.asarray(candidate.boundaries(line, yy, zz)),0,1)
    errors = predicted-truth
    per_height = {}
    for yi, y in enumerate(heights):
        err = errors[:, yi]
        per_height[str(int(y))] = {"cd": stats(err[:, 1]-err[:, 0]),
                                   "center": stats((err[:, 1]+err[:, 0])/2),
                                   "left": stats(err[:, 0]), "right": stats(err[:, 1]),
                                   "missing_intersection_pairs": int(np.any(~np.isfinite(predicted[:, yi]), axis=1).sum())}
    features = {}
    for line in range(len(reference.centers)):
        for yi, y in enumerate(heights):
            for si, side in enumerate(("left", "right")):
                features[f"line{line}_y{int(y)}_{side}"] = edge_features(z, predicted[line, yi, si], truth[line, yi, si])
    cd = predicted[:, 1, 1]-predicted[:, 1, 0]
    center = (predicted[:, 1, 1]+predicted[:, 1, 0])/2
    actual = {"width_y150_mean_nm": float(np.nanmean(cd)),
              "width_y150_fluctuation_rms_nm": np.nanstd(cd, axis=1).tolist(),
              "center_y150_fluctuation_rms_nm": np.nanstd(center, axis=1).tolist()}
    height_z = z[::4]
    height_actual = np.array([[np.max(candidate.contour(line,zz,step_nm=1)[:,1])
                               for zz in height_z] for line in range(len(reference.centers))])
    height_reference = np.array([[np.max(reference.contour(line,zz,step_nm=1)[:,1])
                                  for zz in height_z] for line in range(len(reference.centers))])
    actual.update({"height_maximum_per_section_rms_nm":np.std(height_actual,axis=1).tolist(),
                   "height_range_nm":[float(height_actual.min()),float(height_actual.max())],
                   "height_measurement_z_spacing_nm":float(height_z[1]-height_z[0])})
    tops = []; reference_tops = []
    for line in range(len(reference.centers)):
        for zz in section_positions(scene):
            xx = np.asarray(reference.centers)[line] + np.array([-500., -250., 0., 250., 500.])
            reference_tops.extend(top_intersections(reference.contour(line, zz, step_nm=1), xx))
            tops.extend(top_intersections(candidate.contour(line, zz, step_nm=1), xx))
    if output_npz:
        np.savez_compressed(output_npz, z_nm=z, heights_nm=heights, reference=truth,
                            candidate=predicted, top_reference_nm=reference_tops, top_candidate_nm=tops,
                            height_z_nm=height_z,height_reference_nm=height_reference,height_candidate_nm=height_actual)
    return {"fixed_height_nm": heights.tolist(), "evaluation_z_spacing_nm": float(z[1]-z[0]),
            "demeaning": "subtract each line's mean at each fixed physical Y; no detrending",
            "per_height": per_height, "edge_features": features, "actual_geometry": actual,
            "top_height": {**stats(np.asarray(tops)-reference_tops),
                           "physical_x_offsets_from_nominal_center_nm": [-500,-250,0,250,500],
                           "reference_height_range_nm": [float(min(reference_tops)), float(max(reference_tops))]}}


def material_metrics(reference, candidate, scene, seed=912450):
    rng = np.random.default_rng(seed)
    b = np.asarray(reference.bounds)
    n = 20000
    points = rng.uniform(b[[0,2,4]], b[[1,3,5]], (n,3))
    z_planes = b[4]+(np.arange(37)+.371)*(b[5]-b[4])/37
    points[:,2] = rng.choice(z_planes,n)
    expected = reference.material_at(*points.T)
    actual = candidate.material_at(*points.T)
    global_fraction = float(np.mean(actual != expected))
    # Fixed physical +/-20nm normal band on all free-surface regions, top included.
    near_points = []
    for line in range(len(reference.centers)):
        for z in section_positions(scene):
            seg = segments(reference, line, z, 1)
            p, weight, _, ids = seg.sample(8)
            normal = np.c_[-seg.delta[ids, 1], seg.delta[ids, 0]] / seg.length[ids,None]
            keep = rng.choice(len(p), size=min(220,len(p)), replace=False,
                              p=weight/weight.sum())
            q = p[keep] + normal[keep] * rng.uniform(-20,20,(len(keep),1))
            near_points.append(np.c_[q, np.full(len(q), z)])
    q = np.concatenate(near_points)
    expected = reference.material_at(*q.T); actual = candidate.material_at(*q.T)
    return {"global_fraction": global_fraction, "global_samples": n,
            "global_z_planes_nm": z_planes.tolist(),
            "near_boundary_fraction": float(np.mean(actual != expected)),
            "near_boundary_samples": len(q), "band_halfwidth_nm": 20.,
            "sampling": "global random XY on 37 independent fixed Z planes; fixed normal band around complete free XY contours; deterministic seed",
            "confusion_rows_expected_cols_candidate": np.bincount(expected.astype(int)*3+actual.astype(int),minlength=9).reshape(3,3).tolist()}


def evaluate_model(reference, candidate, scene, output_npz=None, volume_reference=None):
    import time
    start = time.perf_counter()
    boundary = section_distance(reference, candidate, section_positions(scene))
    profile = physical_profiles(reference, candidate, scene, output_npz)
    materials = material_metrics(reference, candidate, scene)
    reference_volume = float(reference.volume()) if volume_reference is None else float(volume_reference)
    represented_volume = float(candidate.volume())
    return {"section_distance": boundary, "profiles": profile, "material": materials,
            "volume": {"reference_stripe_nm3": reference_volume, "candidate_stripe_nm3": represented_volume,
                       "relative_error": (represented_volume-reference_volume)/reference_volume},
            "evaluation_seconds": time.perf_counter()-start}


def convergence_check(reference):
    records = []
    for line, z in ((1, 413.), (1, 677.)):
        coarse = segments(reference,line,z,1.,with_regions=True)
        fine = segments(reference,line,z,.25,with_regions=True)
        a,w,_,_=coarse.sample(.5); b,v,_,_=fine.sample(.5)
        records.append({"line": line, "z_nm": z,
                        **stats(np.r_[fine.distances(a),coarse.distances(b)],np.r_[w,v])})
    return {"baseline_curve_step_nm":1.,"refined_curve_step_nm":.25,
            "locations":"central stripe local bump and shoulder challenge; free contour including round summit",
            "observed_discretization_estimate_nm":max(r["max_nm"] for r in records),
            "interpretation":"sampled convergence evidence, not a rigorous global analytic error bound",
            "records":records}
