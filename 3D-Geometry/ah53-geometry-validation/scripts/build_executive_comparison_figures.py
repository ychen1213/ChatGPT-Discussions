"""Build three concise, traceable figures for the October 2026 management review.

Figure 1 is explicitly an illustrative shape, not experimental evidence.
Figures 2 and 3 use persisted result JSON and challenge NPZ inputs, respectively.
No reconstruction or evaluation is rerun. Run with the project virtualenv Python.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.path import Path as MplPath
from matplotlib.patches import Polygon, Rectangle
import numpy as np
from scipy.interpolate import BSpline


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT.parent / "review-20261024"
OUT = REVIEW / "figures"
RUN = ROOT / "results" / "20261024_voxel_reconstruction"
OLD = ROOT / "results" / "20261024_v2"
INK = "#173047"
MUTED = "#62758a"
V = "#6b999b"
T = "#287bb8"
P = "#d47828"
P_COLORS = ["#ebb57f", "#d98b43", "#bc641b"]
LIGHT = "#f3f7fa"
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
    "font.size": 20,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "axes.unicode_minus": False,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "svg.fonttype": "path",
    "figure.dpi": 120,
    "savefig.dpi": 180,
})


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(path: Path):
    return path.relative_to(ROOT.parent).as_posix()


def fact(path: Path, key: str, value, unit: str = "dimensionless", **notes):
    return {"source_path": relative(path), "actual_key": key,
            "value": value, "unit": unit, **notes}


def scalar(path: Path, key: str, unit: str = "dimensionless"):
    value = read(path)
    for part in key.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return fact(path, key, value, unit)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for extension in ("png", "svg"):
        path = OUT / f"{name}.{extension}"
        # Preserve the agreed 16:7 dimensions; do not crop differently per figure.
        fig.savefig(path, facecolor="white", bbox_inches=None)
        if extension == "svg":
            # Matplotlib path output contains insignificant trailing spaces.
            clean = "\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines())
            path.write_text(clean + "\n", encoding="utf-8", newline="\n")
        paths.append(relative(path))
    plt.close(fig)
    return paths


def illustrative_representation():
    """Same periodic B-spline outline, shown in three different representations."""
    controls = np.array([
        [-1.00, -.82], [-.35, -.82], [.45, -.82], [1.02, -.82],
        [1.10, -.30], [.94, .35], [.60, .90], [.15, .72],
        [-.28, 1.08], [-.78, .86], [-1.15, .38], [-1.15, -.32],
    ])
    n = len(controls)
    coefficients = np.vstack((controls, controls[:3]))
    spline = BSpline(np.arange(n + 7, dtype=float), coefficients, 3)
    curve = spline(np.linspace(3, n + 3, 800))
    shape = MplPath(curve)
    fig = plt.figure(figsize=(16, 7))
    fig.text(.04, .93, "同一形状，三种保存方式", fontsize=26, fontweight="bold")
    fig.text(.96, .93, "原理示意 · 非实验结果", ha="right", fontsize=18, color=MUTED)
    lefts = [.04, .365, .69]
    titles = ["V  体素", "T  三角网格", "P  样条曲面"]
    captions = ["逐格保存材料类别", "保存顶点与三角面连接", "保存样条节点与系数"]
    colors = [V, T, P]
    axes = []
    for left, title, caption, color in zip(lefts, titles, captions, colors):
        fig.text(left + .135, .82, title, ha="center", fontsize=25,
                 fontweight="bold", color=color)
        ax = fig.add_axes([left, .29, .27, .47])
        ax.set_aspect("equal"); ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.1, 1.28)
        ax.set_axis_off(); axes.append(ax)
        fig.text(left + .135, .235, caption, ha="center", fontsize=20)
    ax = axes[0]
    h = .15
    for x in np.arange(-1.35, 1.35, h):
        for y in np.arange(-1.05, 1.2, h):
            occupied = shape.contains_point((x + h / 2, y + h / 2))
            ax.add_patch(Rectangle((x, y), h, h, facecolor=V if occupied else LIGHT,
                                   edgecolor="white", linewidth=.7))
    ax.plot(curve[:, 0], curve[:, 1], color=INK, lw=1.2, alpha=.55)
    ax = axes[1]
    polygon = spline(np.linspace(3, n + 3, 23))
    ax.add_patch(Polygon(polygon, facecolor=T + "13", edgecolor=T, lw=3))
    ax.plot(polygon[:, 0], polygon[:, 1], "o", color=T, ms=5)
    # A small projected strip of the actual polygon's extruded side surface:
    # these are surface triangles, not triangles filling the solid interior.
    start, stop = 2, 10
    shift = np.array([.33, .29])
    for i in range(start, stop):
        a, b = polygon[i], polygon[i + 1]
        for tri in ([a, b, b + shift], [a, b + shift, a + shift]):
            ax.add_patch(Polygon(tri, facecolor=T + "24", edgecolor=T, lw=1.0))
    ax = axes[2]
    ax.add_patch(Polygon(curve, facecolor=P + "12", edgecolor="none"))
    ax.plot(curve[:, 0], curve[:, 1], color=P, lw=4)
    closed_controls = np.vstack((controls, controls[0]))
    ax.plot(closed_controls[:, 0], closed_controls[:, 1], "--", color=MUTED,
            lw=1.3, alpha=.8)
    ax.plot(controls[:, 0], controls[:, 1], "s", mec=P, mfc="white", ms=7, mew=1.7)
    fig.text(.175, .15, "内部也要记录", ha="center", fontsize=19, color=V)
    fig.text(.50, .15, "切开是折线，表面是三角片", ha="center", fontsize=18, color=T)
    fig.text(.825, .15, "控制点通常不在边界上", ha="center", fontsize=19, color=P)
    fig.text(.5, .045, "图示为截面；沿长度 Z 延展并允许截面变化，形成三维物体。",
             ha="center", fontsize=19, color=MUTED)
    return save(fig, "01_representation")


def measured_tradeoff(evidence):
    profiles = ["T_MC", "P_sigma0", "P_sigma05", "P_sigma1"]
    names = ["T · 直接网格", "P · 无额外平滑", "P · 轻度平滑", "P · 较强平滑"]
    colors = [T] + P_COLORS
    rows = []
    for profile in profiles:
        path = RUN / "metrics" / f"local_5nm__{profile}.json"
        build = RUN / "build_records" / f"local_5nm__{profile}.json"
        row = {"profile": profile,
               "p95_nm": scalar(path, "reconstructed_to_reference.all.p95_nm", "nm"),
               "payload_bytes": scalar(build, "payload_bytes", "byte"),
               "material_iou": scalar(path, "material_consistency.iou"),
               "false_negative": scalar(path, "material_consistency.false_negative", "cell"),
               "false_positive": scalar(path, "material_consistency.false_positive", "cell"),
               "core_build_seconds": scalar(build, "build_seconds", "second"),
               "worker_wall_seconds": scalar(build, "worker.wall_seconds", "second")}
        rows.append(row)
    evidence["voxel_reconstruction_5nm"] = rows
    baseline_path = RUN / "metrics" / "local_5nm__voxel_baseline.json"
    baseline = scalar(baseline_path, "input_voxel_to_reference.all.p95_nm", "nm")
    manifest_path = RUN / "input_manifest.json"
    manifest = read(manifest_path)
    input_index = next(i for i, record in enumerate(manifest) if record["name"] == "local_5nm")
    input_data = scalar(manifest_path, f"{input_index}.payload_bytes", "byte")
    evidence["voxel_input_5nm"] = {
        "staircase_p95_nm": baseline,
        "payload_bytes": input_data,
        "array_shape_zyx": scalar(manifest_path, f"{input_index}.array_shape_zyx", "cell"),
        "note": "Dense uint8 labels cover air, stripe and substrate across the full box; P/T payloads store stripe boundaries. This is not equal-semantics storage ranking.",
    }
    p95 = [row["p95_nm"]["value"] for row in rows]
    mb = [row["payload_bytes"]["value"] / 1e6 for row in rows]
    ratio = mb[0] / mb[2]
    evidence["derived"] = {
        "T_to_P05_payload_ratio": {"value": ratio, "unit": "ratio",
            "calculation": "voxel_reconstruction_5nm[T_MC].payload_bytes / voxel_reconstruction_5nm[P_sigma05].payload_bytes"},
    }
    fig = plt.figure(figsize=(16, 7))
    fig.text(.04, .93, "同一份 5 nm 体素输入：精度接近，存储差异明显", fontsize=25, fontweight="bold")
    fig.text(.04, .855, "合成体素重建测试 · 三档 P 均公开；T 未做额外平滑或网格简化", fontsize=19, color=MUTED)
    ax_error = fig.add_axes([.20, .265, .33, .48])
    ax_size = fig.add_axes([.64, .265, .32, .48])
    ypos = np.arange(4)[::-1]
    for ax in (ax_error, ax_size):
        ax.set_ylim(-.6, 3.6); ax.grid(axis="x", color="#e6edf2", zorder=0)
        ax.tick_params(axis="y", length=0, pad=14)
        ax.spines["bottom"].set_color("#d8e2ea")
        ax.set_axisbelow(True)
    ax_error.barh(ypos, p95, height=.52, color=colors, zorder=3)
    ax_error.set_yticks(ypos, names, fontsize=19)
    ax_error.set_xlim(0, 2.85); ax_error.set_xticks([0, 1, 2])
    ax_error.set_title("截面边界 P95 / nm ↓", pad=18, loc="left", fontsize=21)
    base_value = baseline["value"]
    ax_error.axvline(base_value, color=V, ls="--", lw=2, zorder=2)
    for y, value in zip(ypos, p95):
        ax_error.text(value + .055, y, f"{value:.3f}", va="center", fontsize=19, zorder=5,
                      bbox={"facecolor": "white", "edgecolor": "none", "pad": .5})
    ax_size.barh(ypos, mb, height=.52, color=colors, zorder=3)
    ax_size.set_yticks(ypos, [""] * 4); ax_size.set_xlim(0, 88)
    ax_size.set_xticks([0, 40, 80]); ax_size.set_title("几何数据 / MB ↓", pad=18, loc="left", fontsize=21)
    for y, value in zip(ypos, mb):
        ax_size.text(value + 1.6, y, f"{value:.2f}", va="center", fontsize=19)
    fig.text(.04, .15, f"P 数据量约为 T 的 1 / {ratio:.1f}", color=P, fontsize=23, fontweight="bold")
    fig.text(.96, .15, "更平滑不等于更能保留微小缺陷", ha="right", fontsize=21, color=INK)
    fig.text(.04, .065, f"虚线：V 阶梯边界 P95 = {base_value:.3f} nm。输入全域标签为 {input_data['value']/1e6:.0f} MB，含空气和衬底。",
             fontsize=18, color=MUTED)
    return save(fig, "02_measured_tradeoff")


def challenge_figure(evidence):
    cases = ["straight_control", "through_hole", "merging_bridge", "single_voxel_spur"]
    names = ["直条：对照", "贯通孔洞", "中段合并", "单格毛刺"]
    inputs = {}
    challenge_rows = []
    for case in cases:
        path = RUN / "challenge_inputs" / f"{case}.npz"
        with np.load(path) as z:
            inputs[case] = {key: z[key].copy() for key in z.files}
        profiles = ["T_MC", "P_sigma05"] if case in ("through_hole", "merging_bridge") else ["T_MC", "P_sigma0", "P_sigma05", "P_sigma1"]
        row = {"case": case, "input_source_path": relative(path),
               "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "profiles": []}
        for profile in profiles:
            metrics_path = RUN / "metrics" / f"{case}__{profile}.json"
            d = read(metrics_path)
            record = {"profile": profile, "status": fact(metrics_path, "status", d["status"], "status")}
            if d["status"] == "evaluated":
                for key, unit in [("iou", "dimensionless"), ("false_negative", "cell"), ("false_positive", "cell"), ("evaluated_cells", "cell")]:
                    record[key] = scalar(metrics_path, f"material_consistency.{key}", unit)
                for key in ("hole_counts", "material_component_counts"):
                    record[key] = scalar(metrics_path, f"topology.{key}", "count")
            else:
                build_path = RUN / "build_records" / f"{case}__{profile}.json"
                record["reason"] = scalar(build_path, "reason", "text")
            row["profiles"].append(record)
        challenge_rows.append(row)
    evidence["topology_challenges"] = challenge_rows
    straight = inputs["straight_control"]["labels"]
    spur = inputs["single_voxel_spur"]["labels"]
    difference = np.argwhere(spur != straight)
    assert difference.shape == (1, 3), "The spur figure must identify the sole changed input cell"
    iz, iy, ix = map(int, difference[0])
    # Guard the concise claims against the actual saved scoring results.
    for row in challenge_rows:
        t = next(record for record in row["profiles"] if record["profile"] == "T_MC")
        assert t["iou"]["value"] == 1 and t["false_negative"]["value"] == 0 and t["false_positive"]["value"] == 0
        ps = [record for record in row["profiles"] if record["profile"].startswith("P_")]
        if row["case"] in ("through_hole", "merging_bridge"):
            assert ps[0]["status"]["value"] == "unsupported_topology"
        elif row["case"] == "single_voxel_spur":
            assert all(record["false_negative"]["value"] == 1 for record in ps)
        else:
            assert all(record["iou"]["value"] == 1 for record in ps)
    fig = plt.figure(figsize=(16, 7))
    fig.text(.04, .93, "缺陷检查：整体精度相近，并不代表细节保留相同", fontsize=25, fontweight="bold")
    fig.text(.04, .855, "合成挑战样本的实际输入切片 · 每格 10 nm", fontsize=19, color=MUTED)
    cmap = ListedColormap(["#edf3f6", V])
    for i, (case, name) in enumerate(zip(cases, names)):
        left = .04 + i * .24
        ax = fig.add_axes([left, .405, .21, .315])
        labels = inputs[case]["labels"]
        if case == "merging_bridge":
            changes = np.argwhere(labels[labels.shape[0] // 2] != labels[0])
            bridge_y = int(np.median(changes[:, 0]))
            displayed = labels[:, bridge_y, :] == 1
            view = "XZ 切面"
            selection = {"view": "XZ", "y_index": bridge_y}
        elif case == "single_voxel_spur":
            displayed = labels[iz, iy - 5:iy + 7, ix - 6:ix + 7] == 1
            view = "XY 局部放大"
            selection = {"view": "XY", "z_index": iz, "y_indices_half_open": [iy - 5, iy + 7], "x_indices_half_open": [ix - 6, ix + 7], "spur_index_zyx": [iz, iy, ix]}
        else:
            z_index = labels.shape[0] // 2
            displayed = labels[z_index, 6:36, 8:57] == 1
            view = "XY 截面"
            selection = {"view": "XY", "z_index": z_index, "y_indices_half_open": [6, 36], "x_indices_half_open": [8, 57]}
        ax.imshow(displayed, origin="lower", interpolation="nearest", cmap=cmap, vmin=0, vmax=1)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        if case == "single_voxel_spur":
            ax.add_patch(Rectangle((5.5, 4.5), 1, 1, fill=False, edgecolor=P, lw=3))
            ax.annotate("1 格", xy=(6, 5), xytext=(9, 8), color=P, fontsize=18,
                        arrowprops={"arrowstyle": "->", "color": P, "lw": 1.8}, ha="center")
        fig.text(left + .105, .77, name, ha="center", fontsize=22, fontweight="bold")
        fig.text(left + .105, .355, view, ha="center", fontsize=17, color=MUTED)
        p_caption = ["P：三档均一致", "P：当前实现不支持", "P：当前实现不支持", "P：三档均漏 1 格"][i]
        fig.text(left + .105, .275, p_caption, ha="center", fontsize=19, color=P)
        fig.text(left + .105, .205, "T：格中心均一致", ha="center", fontsize=19, color=T)
        challenge_rows[i]["displayed_slice"] = selection
    fig.text(.5, .09, "此处“一致”指全部输入格子中心的材料判断；不是连续表面处处相同的证明。",
             ha="center", fontsize=18, color=MUTED)
    fig.text(.5, .035, "孔洞与合并的限制属于本次 P 实现，不能推广为所有参数曲面都不支持。",
             ha="center", fontsize=18, color=MUTED)
    return save(fig, "03_topology_challenges")


def previous_evidence(evidence):
    csv_path = OLD / "metrics.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream)}
    records = []
    for model_id in ["local_P_fine", "local_T_direct_fine", "local_V_direct_fine", "full_P_fine", "full_T_direct_fine", "full_V_direct_10nm"]:
        records.append({"model_id": model_id, **{
            key: fact(csv_path, f"row[id={model_id}].{key}", float(rows[model_id][key]), unit)
            for key, unit in [("section_p95_nm", "nm"), ("array_payload_bytes", "byte"), ("construction_seconds", "second")]
        }})
    manifest_path = OLD / "manifest.json"
    manifest = read(manifest_path)
    evidence["previous_known_contour_experiment"] = {
        "records": records,
        "full_bounds_nm": scalar(manifest_path, "configuration.scenes.full.bounds_nm", "nm"),
        "full_spacing_nm": scalar(manifest_path, "configuration.sampling.full.voxel_nm", "nm"),
        "full_input_sampling_boundary_step_nm": scalar(manifest_path, "configuration.sampling.full.boundary_step_nm", "nm"),
        "full_input_sampling_z_step_nm": scalar(manifest_path, "configuration.sampling.full.z_step_nm", "nm"),
        "nominal_height_nm": scalar(manifest_path, "configuration.nominal.height_nm", "nm"),
        "notes": [
            "P and T_direct were built from identical ordered contours derived from the synthetic reference.",
            "V_direct used the analytic material oracle; this was not a common measured-input reconstruction ranking.",
            "The full 48 x 48 um box is a validation assumption, not a measured full AH53 mark.",
            "The main score is XY-section distance, not full-3D Hausdorff error; artificial end faces were excluded.",
        ],
    }
    if "limitations" in manifest:
        evidence["previous_known_contour_experiment"]["saved_limitations"] = scalar(manifest_path, "limitations", "text list")


def main():
    evidence = {"schema": 1, "date": "2026-10-24",
        "purpose": "Traceable scalar evidence for the detailed review and three-page executive summary",
        "units": {"MB": "1,000,000 bytes", "nm": "nanometre"},
        "current_metric_scope": "Bidirectional arc-length-weighted XY-section distance at 14 prescribed Z planes; all candidates clipped to Y >= inferred contact + 2h. Not full-3D Hausdorff distance.",
        "current_storage_scope": "P coefficient NPZ or T vertex/face NPY payload file bytes, excluding metadata; V input label-array bytes cover all materials across the box.",
        "current_time_scope": "Detailed-report build times use worker_wall_seconds; core_build_seconds measures the inner builder and excludes worker overhead. Neither time is shown in the executive chart.",
        "figure_01_scope": "Illustrative common periodic cubic B-spline outline; not a measured experimental shape or error comparison.",
    }
    figures = illustrative_representation()
    figures += measured_tradeoff(evidence)
    figures += challenge_figure(evidence)
    previous_evidence(evidence)
    evidence["figure_paths"] = figures
    evidence_path = REVIEW / "comparison_evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"figures": figures, "evidence": relative(evidence_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
