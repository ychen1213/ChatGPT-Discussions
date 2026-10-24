"""Reconstruct boundaries from *only* a labelled array and a minimal grid.

This module deliberately has no imports from the rest of ``ah53``.  Its input
contract is labels.npy plus grid.json; generation recipes, stripe centres,
analytic contours, region identities and reference geometry are never inputs.

P is a deliberately restricted family: one hole-free closed contour per tracked
component, present through the complete Z stack.  Unsupported topology is
reported, never silently filled.  T is a binary-material marching-cubes mesh.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.interpolate import BSpline, make_interp_spline
from skimage.measure import find_contours, marching_cubes


class UnsupportedTopology(ValueError):
    """The observed topology cannot be represented by this P family."""


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_input(path):
    path = Path(path)
    grid = json.loads((path / "grid.json").read_text(encoding="utf-8"))
    required = {"origin_xyz_nm", "spacing_nm", "axis_order", "units", "materials"}
    if set(grid) != required:
        raise ValueError(f"grid.json must contain exactly {sorted(required)}")
    if grid["axis_order"] != "ZYX" or grid["units"] != "nm":
        raise ValueError("Only a ZYX array in nm is supported")
    if grid["materials"] != {"0": "air", "1": "stripe", "2": "substrate"}:
        raise ValueError("Expected material labels 0=air, 1=stripe, 2=substrate")
    h = float(grid["spacing_nm"])
    origin = np.asarray(grid["origin_xyz_nm"], dtype=float)
    if origin.shape != (3,) or not np.all(np.isfinite(origin)) or not h > 0:
        raise ValueError("Invalid origin or spacing")
    labels = np.load(path / "labels.npy", mmap_mode="r", allow_pickle=False)
    if labels.ndim != 3 or labels.dtype != np.uint8 or min(labels.shape) < 2:
        raise ValueError("Expected a uint8 ZYX array, with at least two cells per axis")
    return labels, grid, origin, h


def _signed_area(points):
    q = np.asarray(points)
    return .5 * np.sum(q[:-1, 0] * q[1:, 1] - q[1:, 0] * q[:-1, 1])


def _canonical_contour(points):
    """CCW, starting at the leftmost point at the observed minimum Y."""
    q = np.asarray(points, dtype=float)
    if np.linalg.norm(q[0] - q[-1]) < 1e-8:
        q = q[:-1]
    keep = np.r_[True, np.linalg.norm(np.diff(q, axis=0), axis=1) > 1e-9]
    q = q[keep]
    closed = np.vstack([q, q[0]])
    if _signed_area(closed) < 0:
        q = q[::-1]
    start = np.lexsort((q[:, 0], q[:, 1]))[0]
    q = np.roll(q, -int(start), axis=0)
    return np.vstack([q, q[0]])


def _resample_contour(contour, count):
    distances = np.r_[0., np.cumsum(np.linalg.norm(np.diff(contour, axis=0), axis=1))]
    targets = np.linspace(0., distances[-1], count, endpoint=False)
    return np.column_stack([np.interp(targets, distances, contour[:, k]) for k in (0, 1)])


def _extract_tracks(labels, origin, h, z_step_nm):
    """Check every slice; use image connectivity and overlap for correspondence."""
    nz = labels.shape[0]
    stride = max(1, int(round(z_step_nm / h)))
    selected = set(range(0, nz, stride)) | {nz - 1}
    tracks = None
    previous = None
    previous_map = None
    count0 = None
    z_indices = []
    min_overlap_fraction = 1.
    perimeter_ranges = None
    for iz in range(nz):
        mask = np.asarray(labels[iz] == 1)
        cc, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
        if count == 0:
            raise UnsupportedTopology(f"Z slice {iz}: no target component; P requires through-going components")
        if count0 is None:
            count0 = count
            boxes = ndimage.find_objects(cc)
            # Initial identities are discovered from the labelled slice, sorted by X.
            means = ndimage.center_of_mass(mask, cc, np.arange(1, count + 1))
            order = np.argsort([p[1] for p in means]) + 1
            current_map = {int(label): int(track) for track, label in enumerate(order)}
            tracks = [[] for _ in range(count)]
            perimeter_ranges = [[np.inf, 0.] for _ in range(count)]
        else:
            if count != count0:
                raise UnsupportedTopology(f"Z slice {iz}: component count changed {count0}->{count}; birth/death/merge/split unsupported")
            # Every old component must overlap exactly one new component and vice versa.
            joint = np.bincount((previous.ravel() * (count + 1) + cc.ravel()), minlength=(count + 1) ** 2)
            overlap = joint.reshape(count + 1, count + 1)[1:, 1:]
            graph = overlap > 0
            if np.any(graph.sum(axis=0) != 1) or np.any(graph.sum(axis=1) != 1):
                raise UnsupportedTopology(f"Z slice {iz}: component correspondence is not one-to-one by observed overlap")
            current_map = {int(np.argmax(graph[old - 1]) + 1): previous_map[old] for old in previous_map}
            area = np.bincount(cc.ravel(), minlength=count + 1)[1:]
            min_overlap_fraction = min(min_overlap_fraction, float(np.min(overlap.sum(axis=0) / area)))
            boxes = ndimage.find_objects(cc)
        for label, box in enumerate(boxes, 1):
            sub = cc[box] == label
            # Test holes on *all* input slices, including the slices omitted from fitting.
            if np.any(ndimage.binary_fill_holes(sub) != sub):
                raise UnsupportedTopology(f"Z slice {iz}, component {label}: an internal hole is present")
            padded = np.pad(sub, 1)
            rings = find_contours(padded.astype(np.uint8), .5, fully_connected="high")
            if len(rings) != 1:
                raise UnsupportedTopology(f"Z slice {iz}, component {label}: expected one boundary, found {len(rings)}")
            # find_contours coordinates are row,column at sample centres.  Padding
            # shifts them by -1; original centres add +0.5 cell.
            yx = rings[0] + np.array([box[0].start, box[1].start]) - .5
            xy = origin[:2] + yx[:, ::-1] * h
            ring = _canonical_contour(xy)
            track = current_map[label]
            tracks[track].append(ring)
            length = float(np.linalg.norm(np.diff(ring, axis=0), axis=1).sum())
            perimeter_ranges[track][0] = min(perimeter_ranges[track][0], length)
            perimeter_ranges[track][1] = max(perimeter_ranges[track][1], length)
        if iz in selected:
            z_indices.append(iz)
        previous, previous_map = cc, current_map
    return tracks, np.asarray(z_indices), {
        "checked_slice_count": nz,
        "tracked_components": count0,
        "selected_slice_count": len(z_indices),
        "z_stride_cells": stride,
        "minimum_adjacent_overlap_fraction": min_overlap_fraction,
        "perimeter_ranges_nm": perimeter_ranges,
        "connectivity_2d": 8,
        "correspondence": "exactly one nonzero adjacent-slice component overlap in each direction",
        "start_point": "leftmost X at observed minimum Y; counterclockwise orientation",
    }


def _build_p(labels, grid, origin, h, path, contour_step_nm, z_step_nm, smoothing_nm):
    path.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    meta = {
        "kind": "P", "status": "running", "grid": grid,
        "array_shape_zyx": list(labels.shape),
        "z_bounds_nm": [float(origin[2]), float(origin[2] + labels.shape[0] * h)],
        "input_information": "labels.npy and minimal grid.json only",
        "contour_step_nm": contour_step_nm, "z_step_nm": z_step_nm,
        "smoothing_nm": smoothing_nm,
        "smoothing_rule": "Gaussian filter of XY samples on every original Z slice before Z subsampling: contour sigma=smoothing_nm/(maximum_perimeter/sample_count), mode=wrap; Z sigma=smoothing_nm/voxel_spacing_nm, mode=nearest; same physical sigma in both directions",
        "family_limit": "fixed count of through-going components, one hole-free closed contour per component, unambiguous adjacent overlap",
        "end_rule": "nearest continuation from first/last voxel centre to the corresponding domain end face",
        "parameterization": "normalized cumulative contour arc length at every selected slice; same normalized coordinate matched across Z",
    }
    try:
        tracks, z_indices, diagnostics = _extract_tracks(labels, origin, h, z_step_nm)
    except UnsupportedTopology as exc:
        meta.update(status="unsupported_topology", reason=str(exc), build_seconds=time.perf_counter() - started)
        _write_json(path / "metadata.json", meta)
        return meta
    from shapely.geometry import Polygon
    arrays = {}
    z = origin[2] + (z_indices + .5) * h
    kz = min(3, len(z) - 1)
    counts = []
    invalid = []
    for i, rings in enumerate(tracks):
        max_length = diagnostics["perimeter_ranges_nm"][i][1]
        n = max(12, int(np.ceil(max_length / contour_step_nm)))
        counts.append(n)
        samples = np.asarray([_resample_contour(q, n) for q in rings])
        if smoothing_nm > 0:
            sigma_samples = smoothing_nm / (max_length / n)
            samples = ndimage.gaussian_filter1d(samples, sigma_samples, axis=1, mode="wrap")
            samples = ndimage.gaussian_filter1d(samples, smoothing_nm / h, axis=0, mode="nearest")
        for j, points in enumerate(samples):
            if not Polygon(points).is_valid:
                invalid.append({"component": i, "z_index": j, "stage": "resampled_or_smoothed"})
        samples = samples[z_indices]
        samples = np.concatenate([samples, samples[:, :1]], axis=1)
        u = np.linspace(0., 1., n + 1)
        contour_spline = make_interp_spline(u, samples, k=3, axis=1, bc_type="periodic")
        # contour_spline.c is [u coefficient, Z observation, XY].
        z_spline = make_interp_spline(z, contour_spline.c, k=kz, axis=1)
        # z_spline.c is [Z coefficient, u coefficient, XY].
        arrays[f"u_knots_{i}"] = contour_spline.t
        arrays[f"z_knots_{i}"] = z_spline.t
        arrays[f"coefficients_{i}"] = z_spline.c
    arrays["z_observations_nm"] = z
    np.savez(path / "coefficients.npz", **arrays)
    meta.update(status="ok", n_components=len(tracks), u_degree=3, z_degree=kz,
                contour_sample_counts=counts, diagnostics=diagnostics,
                coefficient_layout="[Z coefficient, contour coefficient, XY]",
                validity_checks={"invalid_observed_polygons": invalid})
    _write_json(path / "metadata.json", meta)
    obj = ParametricReconstruction(path)
    # A model that creates a self-intersection is reported as invalid rather than repaired.
    # All voxel-centre Z positions are checked; between these planes no theorem is claimed.
    invalid_sections = []
    for iz in range(labels.shape[0]):
        zi = origin[2] + (iz + .5) * h
        for component, ring in enumerate(obj.section(zi, step_nm=max(h / 2, 1.))):
            polygon = Polygon(ring)
            if not polygon.is_valid or polygon.area <= 0:
                invalid_sections.append({"component": component, "z_index": iz})
    meta["validity_checks"].update(checked_fitted_z_centres=labels.shape[0], invalid_fitted_sections=invalid_sections,
        limitation="polygonal inspection at voxel-centre planes; does not prove continuous-surface injectivity between planes")
    if invalid or invalid_sections:
        meta["status"] = "invalid_geometry"
    meta["build_seconds"] = time.perf_counter() - started
    meta["payload_bytes"] = (path / "coefficients.npz").stat().st_size
    _write_json(path / "metadata.json", meta)
    return meta


def _build_t(labels, grid, origin, h, path):
    path.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    # Convert equality to a binary indicator BEFORE interpolation.  In particular
    # substrate label 2 is outside target material, not a larger scalar value.
    binary = np.pad(labels == 1, 1, constant_values=False)
    vertices_zyx, faces, _, _ = marching_cubes(binary, level=.5, spacing=(h, h, h),
                                             method="lewiner", allow_degenerate=False)
    vertices = np.asarray(vertices_zyx[:, ::-1] + origin - .5 * h, dtype=np.float32)
    # Reversing ZYX to XYZ changes handedness.  Check the signed enclosed
    # volume explicitly after this coordinate conversion instead of assuming
    # a library convention for triangle orientation.
    faces = np.asarray(faces[:, [0, 2, 1]], dtype=np.int32)
    signed_volume = 0.
    for a in range(0, len(faces), 250_000):
        tri = np.asarray(vertices[faces[a:a + 250_000]], dtype=float)
        signed_volume += float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.)
    if signed_volume < 0:
        faces = faces[:, [0, 2, 1]].copy()
        signed_volume = -signed_volume
    np.save(path / "vertices.npy", vertices)
    np.save(path / "faces.npy", faces)
    meta = {
        "kind": "T", "status": "ok", "grid": grid,
        "array_shape_zyx": list(labels.shape),
        "z_bounds_nm": [float(origin[2]), float(origin[2] + labels.shape[0] * h)],
        "input_information": "labels.npy and minimal grid.json only",
        "algorithm": "Lewiner marching cubes on binary (labels == 1), isovalue 0.5, one zero halo, no mesh smoothing/decimation",
        "end_rule": "zero halo creates an inferred cap at both observed domain ends; these are scan-window closures",
        "vertex_count": len(vertices), "face_count": len(faces),
        "signed_volume_nm3": signed_volume, "winding": "outward; positive signed enclosed volume",
        "payload_bytes": (path / "vertices.npy").stat().st_size + (path / "faces.npy").stat().st_size,
        "build_seconds": time.perf_counter() - started,
    }
    _write_json(path / "metadata.json", meta)
    return meta


def reconstruct_from_voxels(input_dir, output_dir, *, kinds=("P", "T"), kind=None,
                            contour_step_nm=None, z_step_nm=None, smoothing_nm=0.):
    """Save actual P coefficients and/or actual T vertices/faces.

    Output folders are output_dir/P and output_dir/T.  P topology refusal is a
    normal result with status ``unsupported_topology`` and no coefficient file.
    ``smoothing_nm`` is a Gaussian sigma along contour arc length and Z, applied
    to all original slices before Z subsampling.  It is never a reference-derived
    error tolerance.  Default sample steps are 2h and 4h.
    """
    labels, grid, origin, h = _load_input(input_dir)
    output_dir = Path(output_dir)
    if kind is not None:
        kinds = (kind,)
    if isinstance(kinds, str):
        kinds = (kinds,)
    if not set(kinds) <= {"P", "T"}:
        raise ValueError("kinds must contain P and/or T")
    contour_step_nm = 2 * h if contour_step_nm is None else float(contour_step_nm)
    z_step_nm = 4 * h if z_step_nm is None else float(z_step_nm)
    smoothing_nm = float(smoothing_nm)
    if contour_step_nm <= 0 or z_step_nm <= 0 or smoothing_nm < 0:
        raise ValueError("Sampling steps must be positive and smoothing nonnegative")
    results = {}
    # T first; its validity does not depend on whether P supports the topology.
    if "T" in kinds:
        results["T"] = _build_t(labels, grid, origin, h, output_dir / "T")
    if "P" in kinds:
        results["P"] = _build_p(labels, grid, origin, h, output_dir / "P", contour_step_nm, z_step_nm, smoothing_nm)
    return results


class ParametricReconstruction:
    kind = "P"

    def __init__(self, path):
        self.path = Path(path)
        self.metadata = json.loads((self.path / "metadata.json").read_text(encoding="utf-8"))
        if self.metadata["status"] not in ("ok", "invalid_geometry"):
            raise UnsupportedTopology(self.metadata.get("reason", self.metadata["status"]))
        with np.load(self.path / "coefficients.npz", allow_pickle=False) as data:
            self.z_observations = data["z_observations_nm"].copy()
            self.u_knots = [data[f"u_knots_{i}"].copy() for i in range(self.metadata["n_components"])]
            self.z_splines = [BSpline(data[f"z_knots_{i}"], data[f"coefficients_{i}"], self.metadata["z_degree"], axis=0)
                              for i in range(self.metadata["n_components"])]
        self.n_components = self.metadata["n_components"]
        self.z_bounds = self.metadata["z_bounds_nm"]
        self.payload_bytes = self.metadata.get("payload_bytes", (self.path / "coefficients.npz").stat().st_size)

    def section(self, z_nm, step_nm=2.):
        z = float(z_nm)
        if z < self.z_bounds[0] or z > self.z_bounds[1]:
            return []
        z = np.clip(z, self.z_observations[0], self.z_observations[-1])
        output = []
        for i, z_spline in enumerate(self.z_splines):
            length = self.metadata["diagnostics"]["perimeter_ranges_nm"][i][1]
            count = max(16, int(np.ceil(length / float(step_nm))))
            u = np.linspace(0., 1., count + 1)
            coefficients = z_spline(z)
            ring = BSpline(self.u_knots[i], coefficients, self.metadata["u_degree"], axis=0, extrapolate="periodic")(u)
            ring[-1] = ring[0]
            output.append(ring)
        return output

    def contains(self, points_xyz):
        return _contains_by_sections(self, points_xyz)


class TriangleReconstruction:
    kind = "T"

    def __init__(self, path):
        self.path = Path(path)
        self.metadata = json.loads((self.path / "metadata.json").read_text(encoding="utf-8"))
        self.vertices = np.load(self.path / "vertices.npy", mmap_mode="r", allow_pickle=False)
        self.faces = np.load(self.path / "faces.npy", mmap_mode="r", allow_pickle=False)
        self.z_bounds = self.metadata["z_bounds_nm"]
        self.payload_bytes = self.metadata["payload_bytes"]
        self.h = float(self.metadata["grid"]["spacing_nm"])
        self._origin_z = float(self.metadata["grid"]["origin_xyz_nm"][2])
        self._face_order = self._bin_offsets = None

    def _index_faces(self):
        n = len(self.faces)
        bins = np.empty(n, np.int32)
        for a in range(0, n, 250_000):
            b = min(a + 250_000, n)
            lo = self.vertices[self.faces[a:b], 2].min(axis=1)
            bins[a:b] = np.floor((lo - self._origin_z) / self.h + 1e-6).astype(np.int32)
        self._min_bin = int(bins.min())
        bins -= self._min_bin
        self._face_order = np.argsort(bins, kind="stable")
        self._bin_offsets = np.r_[0, np.cumsum(np.bincount(bins))]

    def section(self, z_nm, step_nm=2.):
        """Intersect the saved triangles, using a one-cell Z bucket index."""
        z = float(z_nm)
        if z < self.z_bounds[0] or z > self.z_bounds[1]:
            return []
        if self._face_order is None:
            self._index_faces()
        # An exact end cap has no unique transverse contour; use its interior limit.
        eps = self.h * 1e-7
        z = min(max(z, self.z_bounds[0] + eps), self.z_bounds[1] - eps)
        k = int(np.floor((z - self._origin_z) / self.h)) - self._min_bin
        first = max(0, k - 1)
        last = min(len(self._bin_offsets) - 1, k + 1)
        if first >= last:
            return []
        ids = self._face_order[self._bin_offsets[first]:self._bin_offsets[last]]
        triangles = np.asarray(self.vertices[self.faces[ids]], dtype=float)
        d = triangles[:, :, 2] - z
        signs = d >= 0
        cut = np.any(signs, axis=1) & ~np.all(signs, axis=1)
        triangles, d, signs = triangles[cut], d[cut], signs[cut]
        if not len(triangles):
            return []
        segments = np.empty((len(triangles), 2, 2), float)
        written = np.zeros(len(triangles), np.int8)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            take = signs[:, a] != signs[:, b]
            rows = np.flatnonzero(take)
            fraction = d[take, a] / (d[take, a] - d[take, b])
            point = triangles[take, a, :2] + fraction[:, None] * (triangles[take, b, :2] - triangles[take, a, :2])
            segments[rows, written[rows]] = point
            written[rows] += 1
        segments = segments[np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1) > 1e-7]
        return _segments_to_rings(segments, tolerance=max(1e-5, self.h * 1e-6))

    def contains(self, points_xyz):
        return _contains_by_sections(self, points_xyz)


def _segments_to_rings(segments, tolerance):
    if not len(segments):
        return []
    points = segments.reshape(-1, 2)
    _, first, inverse = np.unique(np.rint(points / tolerance).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    vertices = points[first]
    edges = np.sort(inverse.reshape(-1, 2), axis=1)
    edges = np.unique(edges[edges[:, 0] != edges[:, 1]], axis=0)
    adjacency = [[] for _ in range(len(vertices))]
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    if any(len(x) not in (0, 2) for x in adjacency):
        raise ValueError("Saved triangle-plane intersection is not a collection of closed degree-two loops")
    seen = set()
    rings = []
    for start, neighbours in enumerate(adjacency):
        if start in seen or not neighbours:
            continue
        ring = [start]
        previous, current = start, neighbours[0]
        while current != start:
            if current in seen:
                raise ValueError("Unexpected repeated node in triangle-plane contour")
            ring.append(current)
            seen.add(current)
            nxt = adjacency[current]
            previous, current = current, nxt[0] if nxt[0] != previous else nxt[1]
        seen.add(start)
        ring.append(start)
        rings.append(vertices[ring])
    return rings


def _contains_by_sections(model, points_xyz):
    """Even/odd closed-contour classification; holes are retained regardless of winding."""
    from shapely import contains_xy
    from shapely.geometry import Polygon
    points = np.asarray(points_xyz, dtype=float)
    original_shape = points.shape[:-1]
    points = points.reshape(-1, 3)
    result = np.zeros(len(points), bool)
    for z in np.unique(points[:, 2]):
        select = np.flatnonzero(points[:, 2] == z)
        inside = np.zeros(len(select), bool)
        for ring in model.section(z):
            inside ^= contains_xy(Polygon(ring), points[select, 0], points[select, 1])
        result[select] = inside
    return result.reshape(original_shape)


def load_reconstruction(output_dir, kind="P"):
    path = Path(output_dir)
    if not (path / "metadata.json").exists():
        path = path / kind
    return ParametricReconstruction(path) if kind == "P" else TriangleReconstruction(path)
