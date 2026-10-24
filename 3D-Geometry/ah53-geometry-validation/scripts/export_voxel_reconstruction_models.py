"""Export persisted voxel-reconstructed models; keep display meshes out of scoring.

T is copied exactly into binary PLY. P is sampled at registered display spacings
and capped with constrained polygon triangulation, never an unchecked centre fan.
The small viewer contains only a data-selected central component/Z window.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ah53.voxel_reconstruction import load_reconstruction
from ah53.voxel_reconstruction_metrics import mesh_topology


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def polygon_cap(ring):
    """Return CCW triangles using exactly the sampled boundary vertices."""
    ring = np.asarray(ring)
    polygon = Polygon(ring)
    if not polygon.is_valid or polygon.area <= 0:
        raise ValueError("Cannot cap an invalid sampled P polygon")
    parts = list(shapely.constrained_delaunay_triangles(polygon).geoms)
    union = shapely.union_all(parts)
    missing_area = float(polygon.symmetric_difference(union).area)
    if missing_area > max(1e-7, polygon.area * 1e-10):
        raise ValueError("Constrained cap triangulation does not cover the polygon exactly")
    tree = cKDTree(ring)
    faces = []
    for part in parts:
        points = np.asarray(part.exterior.coords)[:3]
        distance, indices = tree.query(points)
        if np.max(distance) > 1e-7 or len(np.unique(indices)) != 3:
            raise ValueError("Cap triangulation introduced an unmatched or degenerate vertex")
        a, b, c = ring[indices]
        ab, ac = b - a, c - a
        if ab[0] * ac[1] - ab[1] * ac[0] < 0:
            indices = indices[[0, 2, 1]]
        faces.append(indices)
    if len(faces) != len(ring) - 2:
        raise ValueError("Unexpected cap triangle count; boundary indices may be missing")
    return np.asarray(faces, np.int32), {"method": "Shapely/GEOS constrained Delaunay triangulation",
        "polygon_area_nm2": float(polygon.area), "symmetric_difference_area_nm2": missing_area,
        "triangle_count": len(faces), "boundary_vertices": len(ring)}


def sample_p(model, contour_step_nm=20., z_step_nm=40., z_bounds=None, components=None, caps=True):
    lo, hi = model.z_bounds if z_bounds is None else z_bounds
    z = np.linspace(lo, hi, int(np.ceil((hi - lo) / z_step_nm)) + 1)
    selected = list(range(model.n_components)) if components is None else list(components)
    sections = [model.section(float(zi), step_nm=contour_step_nm) for zi in z]
    vertices, faces, caps_info = [], [], []
    offset = 0
    for component in selected:
        rings = np.asarray([section[component][:-1] for section in sections])
        nz, n, _ = rings.shape
        cloud = np.concatenate((rings, np.broadcast_to(z[:, None, None], (nz, n, 1))), axis=2).reshape(-1, 3)
        # CCW XY contours, increasing Z: these two faces point outward.
        j = np.arange(n)
        all_faces = []
        for k in range(nz - 1):
            a, b = k * n + j, k * n + (j + 1) % n
            d, c = a + n, b + n
            all_faces.extend((np.column_stack((a, b, c)), np.column_stack((a, c, d))))
        if caps:
            low, low_info = polygon_cap(rings[0])
            high, high_info = polygon_cap(rings[-1])
            all_faces.extend((low[:, [0, 2, 1]], high + (nz - 1) * n))
            caps_info.append({"component": component, "low": low_info, "high": high_info})
        vertices.append(cloud)
        faces.append(np.concatenate(all_faces) + offset)
        offset += len(cloud)
    return np.concatenate(vertices).astype(np.float32), np.concatenate(faces).astype(np.int32), {
        "source": "reloaded P coefficients", "contour_step_nm": contour_step_nm,
        "contour_step_rule": "maximum observed perimeter / ceil(maximum perimeter / requested step); normalized contour parameter sampling",
        "z_step_nm": float(z[1] - z[0]), "requested_z_step_nm": z_step_nm,
        "z_bounds_nm": [float(lo), float(hi)], "z_plane_count": len(z), "components": selected,
        "caps": caps_info if caps else "none: deliberately open preview window",
        "not_scoring_geometry": True,
        "scope": "display/exchange approximation; formal P scoring reloads coefficients directly"}


def write_ply(path, vertices, faces, comment):
    """Binary little endian XYZ float32 and int32 faces; stream large arrays."""
    header = ("ply\nformat binary_little_endian 1.0\n"
              "comment AH53 coordinates in nanometres; X transverse Y height Z length\n"
              f"comment {comment}\n"
              f"element vertex {len(vertices)}\nproperty float x\nproperty float y\nproperty float z\n"
              f"element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n").encode("ascii")
    face_type = np.dtype([("count", "u1"), ("indices", "<i4", (3,))])
    with Path(path).open("wb") as stream:
        stream.write(header)
        for start in range(0, len(vertices), 250000):
            np.asarray(vertices[start:start + 250000], dtype="<f4").tofile(stream)
        for start in range(0, len(faces), 250000):
            block = faces[start:start + 250000]
            packed = np.empty(len(block), dtype=face_type)
            packed["count"] = 3
            packed["indices"] = block
            packed.tofile(stream)
    # Reopen the file and compare every saved coordinate and triangle index.
    with Path(path).open("rb") as stream:
        while stream.readline() != b"end_header\n":
            pass
        offset = stream.tell()
    saved_vertices = np.memmap(path, mode="r", dtype="<f4", offset=offset, shape=(len(vertices), 3))
    saved_faces = np.memmap(path, mode="r", dtype=face_type,
                           offset=offset + len(vertices) * 12, shape=(len(faces),))
    exact_vertices = all(np.array_equal(saved_vertices[a:a + 250000], np.asarray(vertices[a:a + 250000], np.float32))
                         for a in range(0, len(vertices), 250000))
    exact_faces = all(np.array_equal(saved_faces["indices"][a:a + 250000], faces[a:a + 250000])
                      for a in range(0, len(faces), 250000))
    if not exact_vertices or not exact_faces or not np.all(saved_faces["count"] == 3):
        raise ValueError("PLY round-trip did not preserve all vertices and triangles")
    del saved_vertices, saved_faces
    return {"path": str(Path(path).resolve()), "relative_path": Path(path).relative_to(ROOT).as_posix(),
            "bytes": Path(path).stat().st_size, "sha256": digest(path),
            "format": "binary_little_endian PLY, XYZ float32, triangle indices int32", "units": "nm",
            "roundtrip_every_vertex_and_face_exact": True}


def central_window(t_model, p_model):
    """Choose the middle observed component from T sections, with no truth metadata."""
    lo, hi = t_model.z_bounds
    mid = .5 * (lo + hi)
    rings = t_model.section(mid)
    extents = sorted([(float(r[:, 0].min()), float(r[:, 0].max())) for r in rings], key=lambda p: .5 * (p[0] + p[1]))
    which = len(extents) // 2
    xmin, xmax = extents[which]
    xmin = .5 * (extents[which - 1][1] + xmin) if which else xmin - 10 * t_model.h
    xmax = .5 * (xmax + extents[which + 1][0]) if which + 1 < len(extents) else xmax + 10 * t_model.h
    zmin, zmax = max(lo, mid - 500.), min(hi, mid + 500.)
    blocks = []
    for start in range(0, len(t_model.faces), 250000):
        faces = t_model.faces[start:start + 250000]
        tri = t_model.vertices[faces]
        keep = np.all((tri[:, :, 0] >= xmin) & (tri[:, :, 0] <= xmax) &
                      (tri[:, :, 2] >= zmin) & (tri[:, :, 2] <= zmax), axis=1)
        blocks.append(faces[keep])
    faces = np.concatenate(blocks)
    used, inverse = np.unique(faces, return_inverse=True)
    tv, tf = np.asarray(t_model.vertices[used]), inverse.reshape(-1, 3).astype(np.int32)
    middle_x = .5 * sum(extents[which])
    p_rings = p_model.section(mid)
    p_component = int(np.argmin([abs(.5 * (r[:, 0].min() + r[:, 0].max()) - middle_x) for r in p_rings]))
    pv, pf, sampling = sample_p(p_model, z_bounds=[zmin, zmax], components=[p_component], caps=False)
    return (pv, pf), (tv, tf), {"selection": "middle component discovered from actual T mid-Z section; nearest P component by observed X extent",
        "x_window_nm": [xmin, xmax], "z_window_nm": [zmin, zmax],
        "T_rule": "keep only saved original triangles fully inside the window, remap indices only; no decimation, interpolation or cap",
        "T_actual_bounds_xyz_nm": [tv.min(axis=0).tolist(), tv.max(axis=0).tolist()],
        "P_sampling": sampling, "closed_complete_model": False,
        "warning": "one observed component over a local approximately 1 um window; open artificial cut ends; not the full exported 4 um model"}


def encoded_mesh(vertices, faces):
    return {"vertex_count": len(vertices), "face_count": len(faces),
            "positions_f32_le": base64.b64encode(np.asarray(vertices, dtype="<f4").tobytes()).decode("ascii"),
            "indices_u32_le": base64.b64encode(np.asarray(faces, dtype="<u4").tobytes()).decode("ascii")}


def build_viewer(run, p_model, t_model, exports):
    p_preview, t_preview, selection = central_window(t_model, p_model)
    data = {"units": "nm", "selection": selection,
            "P": encoded_mesh(*p_preview), "T": encoded_mesh(*t_preview),
            "export_links": {k: v["relative_path"] for k, v in exports.items()}}
    packed = gzip.compress(json.dumps(data, separators=(",", ":")).encode("utf-8"), mtime=0)
    preview_path = run / "preview_meshes.json.gz"
    preview_path.write_bytes(packed)
    template = (ROOT / "scripts/voxel_reconstruction_viewer_template.html").read_text(encoding="utf-8")
    for tag, payload in [("@@PREVIEW_GZ@@", packed),
                         ("@@THREE_GZ@@", gzip.compress((ROOT / "viewer/vendor/three.module.js").read_bytes(), mtime=0)),
                         ("@@CONTROLS_GZ@@", gzip.compress((ROOT / "viewer/vendor/OrbitControls.js").read_bytes(), mtime=0))]:
        template = template.replace(tag, base64.b64encode(payload).decode("ascii"))
    from html import escape
    template = template.replace("@@THREE_LICENSE@@", escape((ROOT / "viewer/vendor/THREE-LICENSE.txt").read_text(encoding="utf-8")))
    path = ROOT / "AH53_体素重建_3D查看.html"
    path.write_text(template, encoding="utf-8")
    return {"html_path": str(path), "html_bytes": path.stat().st_size,
            "preview_path": preview_path.relative_to(ROOT).as_posix(), "preview_compressed_bytes": len(packed),
            "preview_sha256": digest(preview_path), "selection": selection,
            "P_vertices": len(p_preview[0]), "P_faces": len(p_preview[1]),
            "T_vertices": len(t_preview[0]), "T_faces": len(t_preview[1]),
            "network_required": False, "geometry_is_preview_only": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="20261024_voxel_reconstruction")
    parser.add_argument("--skip-viewer", action="store_true")
    args = parser.parse_args()
    run = ROOT / "results" / args.run
    export_dir = run / "exports"
    export_dir.mkdir(exist_ok=True)
    p_path = run / "models/local_5nm__P_sigma05/P"
    t_path = run / "models/local_5nm__T_MC/T"
    p, t = load_reconstruction(p_path, "P"), load_reconstruction(t_path, "T")
    pv, pf, p_sampling = sample_p(p)
    p_topology = mesh_topology(pv, pf)
    p_topology["source"] = "sampled P display/exchange mesh, then verified identical to every exported PLY coordinate and index"
    if not p_topology["closed_edge_manifold"] or p_topology["degenerate_triangles"] or p_topology["inconsistently_oriented_two_face_edges"]:
        raise ValueError("P display/export mesh failed closure/orientation/degeneracy checks")
    if p_topology["connected_components"] != p.n_components or p_topology["signed_volume_nm3"] <= 0:
        raise ValueError("P display/export mesh has wrong component count or orientation")
    p_export = write_ply(export_dir / "P_5nm_sigma05_display_20nm_40nm.ply", pv, pf,
                         "Derived P display/exchange mesh; sampled 20 nm contour and 40 nm Z; not scoring geometry")
    p_export.update(source_model="local_5nm__P_sigma05", sampling=p_sampling, topology=p_topology,
                    source_sha256={f.name: digest(f) for f in p_path.iterdir() if f.is_file()})
    t_export = write_ply(export_dir / "T_5nm_MC_exact.ply", t.vertices, t.faces,
                         "Exact persisted T_MC vertices and triangles; no simplification or smoothing")
    # Reuse a formal audit only when it is tied to these exact persisted files.
    formal_path = run / "metrics/local_5nm__T_MC.json"
    t_topology = None
    if formal_path.exists():
        formal = json.loads(formal_path.read_text(encoding="utf-8"))
        hashes = formal.get("build", {}).get("artifact_sha256", {})
        if all(hashes.get("T/" + name) == digest(t_path / name) for name in ("vertices.npy", "faces.npy")):
            t_topology = formal.get("topology", {}).get("saved_mesh")
    if t_topology is None:
        t_topology = mesh_topology(t.vertices, t.faces)
    t_export.update(source_model="local_5nm__T_MC", topology=t_topology,
                    source_sha256={f.name: digest(f) for f in t_path.iterdir() if f.is_file()},
                    transformation="none: original vertex values and triangle indices preserved exactly")
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "units": "nm",
              "scope": "all discovered components over the full 4 um local length; stripe material only, no substrate solid",
              "P": p_export, "T": t_export,
              "limits": ["P PLY is a separately sampled display/exchange mesh, not the evaluated P representation.",
                         "Both models include artificial scan-window end closures; these are not measured physical stripe ends.",
                         "Mesh edge/volume checks do not certify absence of all geometric self-intersections.",
                         "PLY does not enforce units; coordinates here are nanometres. Scale by 0.001 to interpret as micrometres."]}
    if not args.skip_viewer:
        result["viewer"] = build_viewer(run, p, t, {"P": p_export, "T": t_export})
    write_json(run / "export_manifest.json", result)
    print(json.dumps({"P_bytes": p_export["bytes"], "T_bytes": t_export["bytes"],
                      "P_faces": len(pf), "T_faces": len(t.faces),
                      "viewer_bytes": result.get("viewer", {}).get("html_bytes"),
                      "manifest": str(run / "export_manifest.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
