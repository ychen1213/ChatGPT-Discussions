"""Plot already-computed Mark representation results; never rerun a benchmark.

Usage: python plot_results.py --results results
Requires summary.json and local_surface_fine.npz in the results directory.
Figures use English labels and retain physical coordinate units explicitly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from explicit_surface import ExplicitSurfaceRepresentation


COLORS = {"parametric": "#d97706", "surface": "#2563eb", "voxel": "#059669"}
NAMES = {"parametric": "Parametric spline", "surface": "Explicit triangles",
         "voxel": "Material voxels"}
MARKERS = {"parametric": "o", "surface": "s", "voxel": "^"}


def configure_style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.titlesize": 12, "axes.labelsize": 10,
        "legend.fontsize": 9, "figure.titlesize": 16,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.2,
        "svg.fonttype": "none", "savefig.facecolor": "white",
    })


def save_figure(fig, destination):
    destination = Path(destination)
    for suffix in (".svg", ".png"):
        fig.savefig(destination.with_suffix(suffix), dpi=180,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)


def scalar_position(value):
    values = np.asarray(value, dtype=float).ravel()
    finite = values[np.isfinite(values)]
    if not finite.size:
        return float("nan")
    return float(finite[0])


def spacing_label(result):
    """Show supplied settings only, rather than infer precision from a level."""
    settings = result.get("settings", {})
    if not isinstance(settings, dict):
        settings = {}
    if "h_nm" in settings:
        return f"h={float(settings['h_nm']):g} nm"
    if "dy_nm" in settings and "dz_nm" in settings:
        return (f"dY={float(settings['dy_nm']):g} nm, "
                f"dZ={float(settings['dz_nm']):g} nm")
    return ""


def plot_whole_surface(ax, surface):
    # Render the stored material-air triangles.  Buried contact faces are hidden
    # by definition, not removed from or simplified in the saved research data.
    for label, color in ((2, "#a8b2c0"), (1, "#4d8dcc")):
        selected = ((surface.material_pairs[:, 0] == label) &
                    (surface.material_pairs[:, 1] == 0))
        triangles = surface.vertices[surface.faces[selected]][:, :, [0, 2, 1]] / 1000
        collection = Poly3DCollection(triangles, facecolor=color,
                                      edgecolor="none", alpha=1.0)
        collection.set_zsort("average")
        ax.add_collection3d(collection)
    ax.set_xlim(surface.xmin / 1000, surface.xmax / 1000)
    ax.set_ylim(surface.zmin / 1000, surface.zmax / 1000)
    ax.set_zlim(-surface.substrate / 1000, surface.height / 1000)
    ax.set_box_aspect((surface.width_x, surface.length_z,
                       10 * (surface.height + surface.substrate)))
    ax.set_xlabel("X (um)", labelpad=7)
    ax.set_ylabel("Z (um)", labelpad=7)
    ax.set_zlabel("Y (um)", labelpad=6)
    ax.set_title("A  Shared material surfaces", pad=13, loc="left")
    ax.view_init(elev=25, azim=-56)
    ax.set_proj_type("ortho")
    ax.text2D(0.03, 0.02, "Vertical display scale: 10x\nBlue: ridge; gray: substrate",
              transform=ax.transAxes, fontsize=9)


def plot_actual_sidewall_triangles(ax, surface):
    # Draw a genuine subset of the saved right-wall triangles, with no
    # reconstruction or new geometry samples.  The displayed patch spans the
    # full height and approximately 600 nm in the line direction.
    ids = surface.side_vertex_ids[0, 1]
    central = (surface.z_nodes[:-1] >= -300) & (surface.z_nodes[1:] <= 300)
    columns = np.flatnonzero(central)
    if not len(columns):
        middle = max(0, (len(surface.z_nodes) - 2) // 2)
        columns = np.asarray([middle])
    rows = np.arange(len(surface.y_nodes) - 1)
    ii, jj = np.meshgrid(rows, columns, indexing="ij")
    a, b = ids[ii, jj].ravel(), ids[ii + 1, jj].ravel()
    c, d = ids[ii + 1, jj + 1].ravel(), ids[ii, jj + 1].ravel()
    faces = np.concatenate((np.column_stack((a, b, c)),
                            np.column_stack((a, c, d))))
    points = surface.vertices[faces].copy()
    points[:, :, 0] -= float(surface.centers[0])
    # In this plot, the graph axes are Z, Y, and right-wall X relative to center.
    points = points[:, :, [2, 1, 0]]
    collection = Poly3DCollection(points, facecolor="#c2d9ef", edgecolor="#244c73",
                                  linewidth=0.45, alpha=0.92)
    ax.add_collection3d(collection)
    flat = points.reshape(-1, 3)
    lo, hi = flat.min(axis=0), flat.max(axis=0)
    span = np.maximum(hi - lo, 1.0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2] - 0.05 * span[2], hi[2] + 0.05 * span[2])
    displayed_span = span.copy()
    displayed_span[2] *= 1.1
    ax.set_box_aspect(displayed_span)
    ax.set_xlabel("Z (nm)", labelpad=6)
    ax.set_ylabel("Y (nm)", labelpad=6)
    ax.set_zlabel("X - line center (nm)", labelpad=7)
    ax.set_title("B  Actual triangles on one sidewall", pad=13, loc="left")
    ax.view_init(elev=45, azim=55)
    ax.set_proj_type("ortho")
    ax.text2D(0.02, 0.94, "Equal coordinate scale; all triangle edges shown",
              transform=ax.transAxes, fontsize=9)


def representation_views(results, surface, destination):
    fine = {r["method"]: r for r in results
            if r["case"] == "local" and r["level"] == "fine"}
    missing = set(NAMES) - fine.keys()
    if missing:
        raise ValueError(f"Missing fine local profiles for {sorted(missing)}")

    fig = plt.figure(figsize=(14.8, 10.4), layout="constrained")
    grid = fig.add_gridspec(2, 2, height_ratios=(1.15, 1))
    ax_a = fig.add_subplot(grid[0, 0], projection="3d")
    ax_b = fig.add_subplot(grid[0, 1], projection="3d")
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])
    plot_whole_surface(ax_a, surface)
    plot_actual_sidewall_triangles(ax_b, surface)

    reference = fine["surface"]["profiles"]
    cross = reference["cross_section"]
    along = reference["along_length"]
    ax_c.plot(cross["reference_right_nm"], cross["y_nm"], color="#111827",
              linewidth=2.4, alpha=0.8, label="Reference boundary")
    styles = {"parametric": "--", "surface": "-", "voxel": ":"}
    for method in NAMES:
        profile = fine[method]["profiles"]["cross_section"]
        ax_c.plot(profile["right_nm"], profile["y_nm"], color=COLORS[method],
                  linestyle=styles[method], linewidth=1.65, label=NAMES[method])
        profile = fine[method]["profiles"]["along_length"]
        error = (np.asarray(profile["right_nm"], dtype=float) -
                 np.asarray(profile["reference_right_nm"], dtype=float))
        ax_d.plot(np.asarray(profile["z_nm"]) / 1000, error,
                  color=COLORS[method], linestyle=styles[method],
                  linewidth=1.4, label=NAMES[method])
    ax_c.set_title(f"C  Cross-section at Z={scalar_position(cross['z_nm']):g} nm",
                    loc="left")
    ax_c.set_xlabel("Right boundary X (nm)")
    ax_c.set_ylabel("Height Y (nm)")
    ax_c.legend(loc="best", framealpha=0.95)
    ax_c.margins(x=0.08)
    ax_d.axhline(0, color="#64748b", linewidth=0.8, zorder=0)
    ax_d.set_title(f"D  Right-wall error at Y={scalar_position(along['y_nm']):g} nm",
                    loc="left")
    ax_d.set_xlabel("Position along line Z (um)")
    ax_d.set_ylabel("X error: represented - reference (nm)")
    ax_d.legend(loc="best", framealpha=0.95)
    fig.suptitle("Three representations of one asymmetric 3D Mark geometry", y=1.02)
    fig.supxlabel("Controlled synthetic geometry. A: vertical scale exaggerated 10x. "
                  "B: saved triangular surface. C and D: numerical profiles.",
                  fontsize=9)
    save_figure(fig, destination)


def error_vs_size(results, destination):
    local = [r for r in results if r["case"] == "local"]
    if not local:
        raise ValueError("No local results found")
    positive_errors = [float(r["boundary_error_nm"]["p95_abs"]) for r in local
                       if float(r["boundary_error_nm"]["p95_abs"]) > 0]
    zero_floor = min(positive_errors) / 3 if positive_errors else 1e-6
    fig, ax = plt.subplots(figsize=(10.5, 6.7), layout="constrained")
    for method in NAMES:
        selected = sorted((r for r in local if r["method"] == method),
                          key=lambda r: r["payload_bytes"])
        if not selected:
            continue
        x = np.asarray([r["payload_bytes"] / 1e6 for r in selected])
        measured = np.asarray([r["boundary_error_nm"]["p95_abs"] for r in selected])
        if np.any(x <= 0) or np.any(measured < 0) or not np.isfinite(measured).all():
            raise ValueError("Payloads and P95 errors must be finite and nonnegative")
        plotted = np.maximum(measured, zero_floor)
        ax.plot(x, plotted, color=COLORS[method], marker=MARKERS[method],
                markersize=8, linewidth=1.4, label=NAMES[method])
        for index, r in enumerate(selected):
            label = str(r["level"])
            spacing = spacing_label(r)
            if spacing:
                label += "\n" + spacing
            if measured[index] == 0:
                label += f"\nzero, displayed at {zero_floor:g} nm"
            # Keep the first point's text below/right, and second above/right.
            offset = (11, -24) if index == 0 else (11, 10)
            horizontal_alignment = "left"
            if method == "voxel":
                offset = (-10, 14) if index == 0 else (-10, -27)
                horizontal_alignment = "right"
            elif method == "surface":
                offset = (-12, 18) if index == 0 else (12, -18)
                horizontal_alignment = "right" if index == 0 else "left"
            ax.annotate(label, (x[index], plotted[index]), xytext=offset,
                        textcoords="offset points", fontsize=8.5,
                        ha=horizontal_alignment,
                        va="bottom" if offset[1] > 0 else "top",
                        color=COLORS[method])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Representation payload (decimal MB)")
    ax.set_ylabel("P95 absolute sidewall X error (nm)")
    ax.set_title("Boundary error versus stored geometric detail", loc="left", pad=14)
    ax.grid(True, which="both", alpha=0.2)
    ax.legend(loc="upper left", framealpha=0.95)
    ax.margins(x=0.32, y=0.4)
    fig.supxlabel("Local synthetic case; each method uses its stated settings. "
                  "These points do not constitute an equal-fidelity ranking.\n"
                  "Payload is representation data, not peak process memory.",
                  fontsize=9)
    save_figure(fig, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    args = parser.parse_args()
    summary = args.results / "summary.json"
    model = args.results / "local_surface_fine.npz"
    if not summary.is_file() or not model.is_file():
        raise SystemExit("Run the benchmark first: summary.json and local_surface_fine.npz "
                         "must already exist")
    results = json.loads(summary.read_text(encoding="utf-8"))["results"]
    surface = ExplicitSurfaceRepresentation.load(model)
    configure_style()
    representation_views(results, surface, args.results / "representation_views")
    error_vs_size(results, args.results / "error_vs_size")
    print(json.dumps({"figures": [str(args.results / name) for name in
                                  ("representation_views.svg", "representation_views.png",
                                   "error_vs_size.svg", "error_vs_size.png")]}, indent=2))


if __name__ == "__main__":
    main()
