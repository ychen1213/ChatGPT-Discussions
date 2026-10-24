"""Independent, persisted-model scoring for the label-only reconstruction trial.

Only this module may load the synthetic reference.  Reconstruction never imports
it.  Surface distances are XY-section distances, not a 3D Hausdorff distance.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from shapely.geometry import LinearRing, Point, Polygon

from .evaluate import SegmentSet, json_clean, stats


BASE_Z_NM = np.array([-1783., -1167., -443., 137., 413., 677., 1549.])
DEFAULT_OPTIONS = {"curve_step_nm": 0.5, "quadrature_step_nm": 2.0,
                   "phase_offset_in_voxels": 0.37,
                   "material_curve_step_nm": 0.5,
                   "contact_exclusion_height_in_voxels": 2.0}


def normalized_options(options=None):
    result = dict(DEFAULT_OPTIONS, **(options or {}))
    if "distance_sample_step_nm" in result:
        result["quadrature_step_nm"] = result["distance_sample_step_nm"]
    if "additional_z_shift_in_voxels" in result:
        result["phase_offset_in_voxels"] = result["additional_z_shift_in_voxels"]
    if "free_surface_clearance_in_voxels" in result:
        result["contact_exclusion_height_in_voxels"] = result["free_surface_clearance_in_voxels"]
    return result


@dataclass
class LabelGrid:
    labels: np.ndarray
    origin: np.ndarray
    spacing: np.ndarray
    path: Path
    metadata: dict

    @classmethod
    def load(cls, path):
        path = Path(path)
        meta = json.loads((path / "grid.json").read_text(encoding="utf-8"))
        if meta.get("axis_order") != "ZYX" or meta.get("units") != "nm":
            raise ValueError("Scoring requires ZYX labels and physical nm units")
        spacing = np.broadcast_to(np.asarray(meta["spacing_nm"], float), (3,)).copy()
        return cls(np.load(path / "labels.npy", mmap_mode="r"),
                   np.asarray(meta["origin_xyz_nm"], float), spacing, path, meta)

    def section_index(self, z_nm):
        k = int(np.floor((z_nm - self.origin[2]) / self.spacing[2]))
        if k < 0 or k >= self.labels.shape[0]:
            raise ValueError("Section lies outside supplied label volume")
        return k

    @property
    def z_bounds(self):
        return [float(self.origin[2]),
                float(self.origin[2] + self.labels.shape[0] * self.spacing[2])]


def registered_positions(grid, options=None):
    options = normalized_options(options)
    base = np.asarray(options.get("z_nm", BASE_Z_NM), float)
    z = np.r_[base, base + options["phase_offset_in_voxels"] * grid.spacing[2]]
    lo, hi = grid.z_bounds
    return z[(z > lo) & (z < hi)]


def planar_substrate_height(grid):
    """Infer a planar label-2 upper face from labels, never from reference config.

    Reject the planar-interface shortcut if material 2 is not a complete set of
    bottom rows.  The current AH53 inputs satisfy this check at every Z plane.
    """
    top_row = None
    for slab in grid.labels:
        counts = np.count_nonzero(slab == 2, axis=1)
        if np.any((counts != 0) & (counts != slab.shape[1])):
            return None
        rows = np.flatnonzero(counts)
        if not len(rows) or not np.array_equal(rows, np.arange(rows[-1] + 1)):
            return None
        if top_row is None:
            top_row = int(rows[-1])
        elif top_row != rows[-1]:
            return None
    return float(grid.origin[1] + (top_row + 1) * grid.spacing[1])


def voxel_section_segments(grid, z_nm, free_only=True):
    """Exact exposed cell-face segments; no known centers or single-interval fit.

    Includes all label-1 components and holes.  With free_only=True only 1/0
    interfaces are used; 1/2 contact faces are omitted by their actual labels.
    """
    slab = np.asarray(grid.labels[grid.section_index(z_nm)])
    padded = np.pad(slab, 1, constant_values=0)
    occupied = slab == 1
    starts, ends = [], []
    neighbors = (padded[1:-1, :-2], padded[1:-1, 2:],
                 padded[:-2, 1:-1], padded[2:, 1:-1])
    corners = (((0, 0), (0, 1)), ((1, 0), (1, 1)),
               ((0, 0), (1, 0)), ((0, 1), (1, 1)))
    for adjacent, (a, b) in zip(neighbors, corners):
        mask = occupied & ((adjacent == 0) if free_only else (adjacent != 1))
        iy, ix = np.nonzero(mask)
        cell = np.column_stack((ix, iy))
        starts.append(grid.origin[:2] + (cell + a) * grid.spacing[:2])
        ends.append(grid.origin[:2] + (cell + b) * grid.spacing[:2])
    return np.concatenate(starts), np.concatenate(ends)


def contour_segments(contours, contact_y_nm=None):
    starts, ends = [], []
    for contour in contours:
        p = np.asarray(contour, float)
        if len(p) < 3:
            continue
        if np.linalg.norm(p[0] - p[-1]) > 1e-8:
            p = np.vstack((p, p[0]))
        a, b = p[:-1], p[1:]
        keep = np.linalg.norm(b - a, axis=1) > 1e-10
        if contact_y_nm is not None:
            keep &= ~((abs(a[:, 1] - contact_y_nm) < 1e-7) &
                      (abs(b[:, 1] - contact_y_nm) < 1e-7))
        starts.append(a[keep]); ends.append(b[keep])
    if not starts:
        return np.empty((0, 2)), np.empty((0, 2))
    return np.concatenate(starts), np.concatenate(ends)


def clip_segments_above(segments, minimum_y_nm):
    """Same physical height mask for truth, voxels, P and T; clip crossing edges."""
    a, b = (np.asarray(x, float).copy() for x in segments)
    keep = (a[:, 1] >= minimum_y_nm) | (b[:, 1] >= minimum_y_nm)
    a, b = a[keep], b[keep]
    a_low = a[:, 1] < minimum_y_nm
    b_low = b[:, 1] < minimum_y_nm
    if np.any(a_low):
        fraction = (minimum_y_nm - a[a_low, 1]) / (b[a_low, 1] - a[a_low, 1])
        a[a_low] += fraction[:, None] * (b[a_low] - a[a_low])
    if np.any(b_low):
        fraction = (minimum_y_nm - b[b_low, 1]) / (a[b_low, 1] - b[b_low, 1])
        b[b_low] += fraction[:, None] * (a[b_low] - b[b_low])
    keep = np.linalg.norm(b - a, axis=1) > 1e-10
    return a[keep], b[keep]


def _reference_segments(reference, z_nm, curve_step_nm, closed=False):
    # Reference's native region names are used only on the truth side.  Candidate
    # curves are pooled; no truth centers/count/order are used to match objects.
    starts, ends = [], []
    for line in range(reference.n_lines):
        for region in range(6 if closed else 5):
            p = reference.region_contour(line, float(z_nm), region,
                                         step_nm=curve_step_nm)
            starts.append(p[:-1]); ends.append(p[1:])
    return np.concatenate(starts), np.concatenate(ends)


def section_pair_distance(first_segments, second_segments, sample_step_nm=2.):
    if not len(first_segments[0]) or not len(second_segments[0]):
        return {"status": "missing_surface", "all": stats([])}, None
    first, second = SegmentSet(*first_segments), SegmentSet(*second_segments)
    p, w, _, _ = first.sample(sample_step_nm)
    q, v, _, _ = second.sample(sample_step_nm * 1.013)
    d, e = second.distances(p), first.distances(q)
    return {"status": "ok", "first_to_second": stats(d, w),
            "second_to_first": stats(e, v),
            "all": stats(np.r_[d, e], np.r_[w, v]),
            "first_length_nm": float(first.length.sum()),
            "second_length_nm": float(second.length.sum())}, (d, w, e, v)


def compare_sections(first, second, z_positions, sample_step_nm=2.):
    records, values, weights, forward, fw, reverse, rw = [], [], [], [], [], [], []
    for z in z_positions:
        report, arrays = section_pair_distance(first(float(z)), second(float(z)), sample_step_nm)
        records.append({"z_nm": float(z), **report})
        if arrays is not None:
            d, w, e, v = arrays
            values.extend((d, e)); weights.extend((w, v))
            forward.append(d); fw.append(w); reverse.append(e); rw.append(v)
    cat = lambda x: np.concatenate(x) if x else np.array([])
    return {"definition": "bidirectional arc-length-weighted XY-section point-to-segment distance",
            "not_a_full_3d_hausdorff_distance": True,
            "object_matching": "all components pooled; no reference-center pairing",
            "z_positions_nm": np.asarray(z_positions).tolist(),
            "quadrature_max_step_nm": sample_step_nm * 1.013,
            "missing_sections": sum(x["status"] != "ok" for x in records),
            "first_to_second": stats(cat(forward), cat(fw)),
            "second_to_first": stats(cat(reverse), cat(rw)),
            "all": stats(cat(values), cat(weights)), "sections": records}


def rasterize_section(contours, shape_yx, origin_xy, spacing_xy):
    """Even-odd scanline classification of every supplied XY cell center.

    Segment-to-row assignment is vectorized. Nested loops toggle parity, so
    interior holes remain holes; no min/max envelope or stripe identity is used.
    """
    ny, nx = shape_yx
    origin_xy, spacing_xy = np.asarray(origin_xy), np.asarray(spacing_xy)
    mask = np.zeros((ny, nx), bool)
    a, b = contour_segments(contours)
    if not len(a):
        return mask, {"odd_intersection_rows": 0, "horizontal_center_ties": 0,
                      "x_center_ties": 0}
    dy = b[:, 1] - a[:, 1]
    horizontal = abs(dy) <= 1e-12
    horizontal_at = (a[horizontal, 1] - origin_xy[1]) / spacing_xy[1] - .5
    hties = int(np.count_nonzero(abs(horizontal_at - np.rint(horizontal_at)) < 1e-9))
    a, b, dy = a[~horizontal], b[~horizontal], dy[~horizontal]
    low, high = np.minimum(a[:, 1], b[:, 1]), np.maximum(a[:, 1], b[:, 1])
    # Lower endpoint included, upper excluded avoids double-counting shared nodes.
    first = np.clip(np.ceil((low - origin_xy[1]) / spacing_xy[1] - .5).astype(int), 0, ny)
    stop = np.clip(np.ceil((high - origin_xy[1]) / spacing_xy[1] - .5).astype(int), 0, ny)
    count = np.maximum(stop - first, 0)
    ids = np.repeat(np.arange(len(a)), count)
    if not len(ids):
        return mask, {"odd_intersection_rows": 0, "horizontal_center_ties": hties,
                      "x_center_ties": 0}
    offsets = np.repeat(np.cumsum(count) - count, count)
    rows = first[ids] + np.arange(len(ids)) - offsets
    y = origin_xy[1] + (rows + .5) * spacing_xy[1]
    x = a[ids, 0] + (y - a[ids, 1]) * (b[ids, 0] - a[ids, 0]) / dy[ids]
    order = np.lexsort((x, rows)); rows, x = rows[order], x[order]
    center_x = (x - origin_xy[0]) / spacing_xy[0] - .5
    ties = int(np.count_nonzero(abs(center_x - np.rint(center_x)) < 1e-9))
    row_ids, firsts, counts = np.unique(rows, return_index=True, return_counts=True)
    odd = 0
    for row, begin, number in zip(row_ids, firsts, counts):
        if number % 2:
            odd += 1
            continue
        bounds = center_x[begin:begin + number]
        for left, right in zip(bounds[::2], bounds[1::2]):
            start = max(0, int(np.ceil(left - 1e-9)))
            end = min(nx, int(np.floor(right + 1e-9)) + 1)
            if end > start:
                mask[row, start:end] = True
    return mask, {"odd_intersection_rows": odd, "horizontal_center_ties": hties,
                  "x_center_ties": ties}


def section_topology(contours):
    records, polygons = [], []
    for ring in contours:
        p = np.asarray(ring, float)
        closed = len(p) >= 4 and bool(np.linalg.norm(p[0] - p[-1]) < 1e-7)
        try:
            polygon, line = Polygon(p), LinearRing(p)
            valid, simple, area = bool(polygon.is_valid), bool(line.is_simple), float(polygon.area)
        except (ValueError, TypeError):
            polygon, valid, simple, area = None, False, False, None
        polygons.append(polygon)
        records.append({"closed": closed, "simple": simple, "polygon_valid": valid,
                        "unsigned_area_nm2": area, "points": len(p)})
    depths = []
    for index, (ring, polygon) in enumerate(zip(contours, polygons)):
        if polygon is None or not polygon.is_valid:
            depths.append(None)
            continue
        point = Point(np.asarray(ring)[0])
        depth = sum(p is not None and p.is_valid and j != index and p.contains(point)
                    for j, p in enumerate(polygons))
        depths.append(depth)
    area = sum(((-1) ** depth) * rec["unsigned_area_nm2"]
               for depth, rec in zip(depths, records) if depth is not None)
    boundary_intersections = sum(
        a is not None and b is not None and a.is_valid and b.is_valid and a.boundary.intersects(b.boundary)
        for i, a in enumerate(polygons) for b in polygons[i + 1:])
    return {"ring_count": len(records),
            "material_components_2d": sum(d is not None and d % 2 == 0 for d in depths),
            "hole_count_2d": sum(d is not None and d % 2 == 1 for d in depths),
            "all_closed": all(r["closed"] for r in records),
            "ring_boundary_intersections": int(boundary_intersections),
            "all_simple_valid": not boundary_intersections and all(r["simple"] and r["polygon_valid"] for r in records),
            "signed_material_area_nm2": float(area), "rings": records}


def material_consistency(grid, model, curve_step_nm=.5):
    """Full supplied grid, all Z/Y/X centers, against saved model sections."""
    start_time = time.perf_counter()
    confusion = np.zeros((3, 2), np.int64)
    diagnostics = {"odd_intersection_rows": 0, "horizontal_center_ties": 0, "x_center_ties": 0}
    invalid_sections, area_sum, sampled_vertices = 0, 0., 0
    for iz, slab in enumerate(grid.labels):
        z = grid.origin[2] + (iz + .5) * grid.spacing[2]
        contours = model.section(float(z), step_nm=curve_step_nm)
        mask, diag = rasterize_section(contours, slab.shape, grid.origin[:2], grid.spacing[:2])
        confusion += np.bincount(slab.ravel().astype(np.int64) * 2 + mask.ravel(), minlength=6).reshape(3, 2)
        for key, value in diag.items():
            diagnostics[key] += value
        topo = section_topology(contours)
        invalid_sections += int(not topo["all_simple_valid"] or not topo["all_closed"])
        area_sum += topo["signed_material_area_nm2"]
        sampled_vertices += sum(len(c) for c in contours)
    tp = int(confusion[1, 1]); fn = int(confusion[1, 0])
    fp = int(confusion[0, 1] + confusion[2, 1]); tn = int(confusion[0, 0] + confusion[2, 0])
    cell_volume = float(np.prod(grid.spacing))
    truth_count = tp + fn; predicted_count = tp + fp
    return {"scope": "every center of every cell in the supplied grid; no random sampling or truth bbox",
            "evaluated_cells": int(np.prod(grid.labels.shape)),
            "evaluated_z_planes": int(grid.labels.shape[0]),
            "curve_step_nm_for_P": curve_step_nm,
            "triangle_sections_exact_for_T": True,
            "confusion_rows_input_0_1_2_cols_candidate_outside_inside_stripe": confusion.tolist(),
            "true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn,
            "false_positive_air": int(confusion[0, 1]), "false_positive_substrate": int(confusion[2, 1]),
            "iou": tp / (tp + fp + fn) if tp + fp + fn else 1.,
            "mismatch_fraction": (fp + fn) / (tp + fp + fn + tn),
            "input_material_cell_count": truth_count, "reconstructed_material_cell_count": predicted_count,
            "input_voxel_material_volume_nm3": truth_count * cell_volume,
            "reconstructed_center_classified_volume_nm3": predicted_count * cell_volume,
            "section_integrated_continuous_volume_nm3": area_sum * grid.spacing[2],
            "continuous_volume_rule": "midpoint quadrature of polygon areas on every voxel Z center; P curves discretized at stated step",
            "center_tie_rule": "inclusive X interval endpoints with 1e-9-cell tolerance; half-open Y crossings; tie counts reported",
            "section_diagnostics": diagnostics, "invalid_or_open_section_planes": invalid_sections,
            "total_section_vertices_processed": sampled_vertices,
            "seconds": time.perf_counter() - start_time}


def mesh_topology(vertices, faces):
    """Audit persisted triangle indices, sharing at most O(F) auxiliary storage."""
    start_time = time.perf_counter()
    vertices, faces = np.asarray(vertices), np.asarray(faces)
    nv, nf = len(vertices), len(faces)
    if not nf or np.min(faces) < 0 or np.max(faces) >= nv:
        return {"status": "empty_or_invalid_indices"}
    keys = np.empty(nf * 3, np.uint64)
    positive_keys = []
    area_min, degenerate, signed_volume = float("inf"), 0, 0.
    for begin in range(0, nf, 200000):
        f = faces[begin:begin + 200000]
        tri = vertices[f].astype(np.float64)
        cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        area = np.linalg.norm(cross, axis=1) / 2
        area_min = min(area_min, float(area.min()))
        degenerate += int(np.count_nonzero(area <= 1e-10))
        signed_volume += float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6)
        for edge in range(3):
            a, b = f[:, edge].astype(np.uint64), f[:, (edge + 1) % 3].astype(np.uint64)
            key = np.minimum(a, b) * np.uint64(nv) + np.maximum(a, b)
            keys[edge * nf + begin:edge * nf + begin + len(f)] = key
            positive_keys.append(key[a < b])
    unique, edge_counts = np.unique(keys, return_counts=True)
    del keys
    positive, positive_counts = np.unique(np.concatenate(positive_keys), return_counts=True)
    del positive_keys
    pos_at = np.searchsorted(unique, positive)
    positive_count_per_edge = np.zeros(len(unique), np.uint8)
    positive_count_per_edge[pos_at] = np.minimum(positive_counts, 255)
    inconsistent = int(np.count_nonzero((edge_counts == 2) & (positive_count_per_edge != 1)))
    del positive, positive_counts, pos_at, positive_count_per_edge
    a = (unique // np.uint64(nv)).astype(np.int64)
    b = (unique % np.uint64(nv)).astype(np.int64)
    used = np.unique(np.r_[a, b])
    graph = coo_matrix((np.ones(len(a), np.uint8), (a, b)), shape=(nv, nv)).tocsr()
    _, labels = connected_components(graph, directed=False)
    component_ids = np.unique(labels[used])
    vcounts = np.bincount(labels[used])
    ecounts = np.bincount(labels[a], minlength=len(vcounts))
    fcounts = np.bincount(labels[faces[:, 0]], minlength=len(vcounts))
    components = [{"vertices": int(vcounts[c]), "edges": int(ecounts[c]),
                   "faces": int(fcounts[c]), "euler_characteristic": int(vcounts[c] - ecounts[c] + fcounts[c])}
                  for c in component_ids]
    boundary = int(np.count_nonzero(edge_counts == 1)); nonmanifold = int(np.count_nonzero(edge_counts > 2))
    return {"status": "ok", "source": "actual persisted vertices.npy and faces.npy",
            "vertices": nv, "used_vertices": len(used), "unused_vertices": nv - len(used),
            "faces": nf, "unique_edges": len(unique), "connected_components": len(component_ids),
            "boundary_edges": boundary, "nonmanifold_edges": nonmanifold,
            "inconsistently_oriented_two_face_edges": inconsistent,
            "closed_edge_manifold": boundary == 0 and nonmanifold == 0,
            "degenerate_triangles": degenerate, "minimum_triangle_area_nm2": area_min,
            "signed_volume_nm3": signed_volume, "absolute_signed_volume_nm3": abs(signed_volume),
            "euler_characteristic": int(len(used) - len(unique) + nf),
            "components": components,
            "scope_note": "checks shared-edge incidence, orientation and connectivity; does not prove absence of triangle self-intersections or vertex nonmanifoldness",
            "caps_note": "bottom/contact and artificial Z caps included in closed-solid topology and volume only",
            "seconds": time.perf_counter() - start_time}


def audit_model(model, z_positions, contact_y_nm=None, curve_step_nm=.5):
    sections = [{"z_nm": float(z), **section_topology(model.section(float(z), step_nm=curve_step_nm))}
                for z in z_positions]
    result = {"section_scope": "sampled XY planes; no proof over every continuous Z",
              "sections": sections,
              "all_sampled_rings_closed": all(x["all_closed"] for x in sections),
              "all_sampled_rings_simple_valid": all(x["all_simple_valid"] for x in sections),
              "material_component_counts": sorted(set(x["material_components_2d"] for x in sections)),
              "hole_counts": sorted(set(x["hole_count_2d"] for x in sections))}
    if hasattr(model, "vertices") and hasattr(model, "faces"):
        result["saved_mesh"] = mesh_topology(model.vertices, model.faces)
    else:
        result["representation_limit"] = "fixed-correspondence periodic contour loft; unsupported topology must be rejected by reconstruction, not filled in scoring"
    return result


def evaluate_voxel_baseline(input_dir, reference_dir, options=None):
    options = normalized_options(options)
    grid = LabelGrid.load(input_dir)
    z = registered_positions(grid, options)
    contact = planar_substrate_height(grid)
    minimum_y = None if contact is None else contact + options["contact_exclusion_height_in_voxels"] * grid.spacing[1]
    result, closed_result = None, None
    if reference_dir is not None:
        if minimum_y is None:
            raise ValueError("The registered common-height band requires a verified planar substrate interface")
        from .reference_geometry import ReferenceGeometry
        reference = ReferenceGeometry.load(reference_dir)
        truth = lambda zz: _reference_segments(reference, zz, options["curve_step_nm"], closed=True)
        voxel = lambda zz: voxel_section_segments(grid, zz, free_only=False)
        result = compare_sections(lambda zz: clip_segments_above(truth(zz), minimum_y),
                                  lambda zz: clip_segments_above(voxel(zz), minimum_y), z,
                                  options["quadrature_step_nm"])
        closed_result = compare_sections(truth, voxel, z, options["quadrature_step_nm"])
    return {"options": options, "input_directory": str(Path(input_dir).resolve()),
            "input_spacing_xyz_nm": grid.spacing.tolist(),
            "input_shape_zyx": list(grid.labels.shape), "planar_substrate_interface_y_nm": contact,
            "common_height_band_minimum_y_nm": minimum_y,
            "reference_curve_step_nm": options["curve_step_nm"],
            "input_voxel_to_reference": result,
            "input_voxel_to_reference_closed": closed_result,
            "distance_exclusions": "main distance uses identical Y >= contact + 2h band and clipped crossing segments; *_closed includes all XY interfaces including bottom; artificial Z caps absent from interior XY cuts"}


def evaluate_saved(input_dir, model_dir, kind, reference_dir, options=None, baseline=None):
    """Read persisted P/T and hidden reference in evaluator, return JSON-safe data."""
    from .voxel_reconstruction import load_reconstruction
    started = time.perf_counter()
    options = normalized_options(options)
    grid = LabelGrid.load(input_dir)
    baseline = baseline or evaluate_voxel_baseline(input_dir, reference_dir, options)
    contact = baseline["planar_substrate_interface_y_nm"]
    if contact is None:
        raise ValueError("This trial's free-surface comparison requires verified planar substrate contact; label baseline itself supports general interfaces")
    metadata_path = Path(model_dir) / "metadata.json"
    if not metadata_path.exists():
        metadata_path = Path(model_dir) / kind / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") == "unsupported_topology":
        return {"status": "unsupported_topology", "kind": kind,
                "model_metadata": metadata, "reason": metadata.get("reason"),
                "input_voxel_to_reference": baseline["input_voxel_to_reference"],
                "evaluation_seconds": time.perf_counter() - started}
    model = load_reconstruction(model_dir, kind=kind)
    z = registered_positions(grid, options)
    minimum_y = contact + options["contact_exclusion_height_in_voxels"] * grid.spacing[1]
    actual_closed = lambda zz: contour_segments(model.section(zz, step_nm=options["curve_step_nm"]))
    reference_comparison, reference_closed_comparison = None, None
    voxel_closed_fn = lambda zz: voxel_section_segments(grid, zz, free_only=False)
    voxel_fn = lambda zz: clip_segments_above(voxel_closed_fn(zz), minimum_y)
    # Cache only the 14 independent sections, not full-volume mesh copies.
    section_cache = {float(zz): actual_closed(float(zz)) for zz in z}
    actual_closed = lambda zz: section_cache[float(zz)]
    actual = lambda zz: clip_segments_above(actual_closed(zz), minimum_y)
    if reference_dir is not None:
        from .reference_geometry import ReferenceGeometry
        reference = ReferenceGeometry.load(reference_dir)
        reference_closed_fn = lambda zz: _reference_segments(reference, zz, options["curve_step_nm"], closed=True)
        reference_fn = lambda zz: clip_segments_above(reference_closed_fn(zz), minimum_y)
        reference_comparison = compare_sections(reference_fn, actual, z, options["quadrature_step_nm"])
        reference_closed_comparison = compare_sections(reference_closed_fn, actual_closed, z, options["quadrature_step_nm"])
    result = {"status": "evaluated", "kind": kind,
              "geometry_status": model.metadata.get("status", "unknown"),
              "model_directory": str(Path(model_dir).resolve()), "options": options,
              "input_spacing_xyz_nm": grid.spacing.tolist(), "input_shape_zyx": list(grid.labels.shape),
              "planar_substrate_interface_y_nm": contact,
              "common_height_band_minimum_y_nm": minimum_y,
              "reconstructed_to_reference": reference_comparison,
              "reconstructed_to_reference_closed": reference_closed_comparison,
              "reconstructed_to_input_voxel_surface": compare_sections(voxel_fn, actual, z, options["quadrature_step_nm"]),
              "reconstructed_to_input_voxel_surface_closed": compare_sections(voxel_closed_fn, actual_closed, z, options["quadrature_step_nm"]),
              "input_voxel_to_reference": baseline["input_voxel_to_reference"],
              "input_voxel_to_reference_closed": baseline.get("input_voxel_to_reference_closed"),
              "distance_direction_note": "first=reference or input voxel; second=reconstructed model",
              "distance_exclusions": "main distance uses identical Y >= contact + 2h band for P/T/V/reference, clipping crossing segments; *_closed includes all physical XY boundaries and bottom corner changes; artificial Z end caps absent from interior XY cuts; not directly comparable to previous experiment free-surface scores",
              "material_consistency": material_consistency(grid, model, options["material_curve_step_nm"]),
              "topology": audit_model(model, z, contact, options["curve_step_nm"]),
              "model_metadata": model.metadata}
    result["evaluation_seconds"] = time.perf_counter() - started
    return json_clean(result)
