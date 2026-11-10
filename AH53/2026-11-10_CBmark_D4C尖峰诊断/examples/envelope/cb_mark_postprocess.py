"""Illustrative CB-mark postprocessing, not a calibrated RCWA prediction.

Requires Python 3, numpy, matplotlib. Run:
    uv run --with numpy --with matplotlib cb_mark_postprocess.py

All lateral lengths are micrometres. Complex a are POWER-normalized isolated
diffraction-order amplitudes, so |a|**2 is incident-power efficiency.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Circle


@dataclass
class Parameters:
    pitch_um: float = 2.0
    duty: float = 0.5  # Geometric illustration only; amplitudes are supplied.
    side_um: float = 40.0
    waist_um: float = 12.0  # 1/e^2 INTENSITY radius, not FWHM.
    y_offset_um: float = 0.0
    extra_visibility: float = 0.9
    a_x_plus: complex = complex(math.sqrt(0.08))
    a_x_minus: complex = complex(math.sqrt(0.08))
    a_y_plus: complex = complex(math.sqrt(0.08))
    a_y_minus: complex = complex(math.sqrt(0.08))
    # Additional sensor arm phase after RCWA amplitude phases, radians.
    delta_x: float = 0.35
    delta_y: float = 0.35


def erf_array(value):
    a = np.asarray(value, dtype=float)
    return np.fromiter((math.erf(float(v)) for v in a.flat),
                       dtype=float, count=a.size).reshape(a.shape)


def gaussian_mass(low, high, waist):
    """Integral of normalized 1D Gaussian over [low,high], zero if empty."""
    lo, hi = np.broadcast_arrays(low, high)
    c = math.sqrt(2.0) / waist
    return np.where(hi > lo, 0.5 * (erf_array(c * hi) - erf_array(c * lo)), 0.0)


def gaussian_density(value, waist):
    return math.sqrt(2.0 / math.pi) / waist * np.exp(-2.0 * np.asarray(value)**2 / waist**2)


def window_powers(sx, sy, p):
    """q_j = integral G(u) W_j(u+r_s) du, using 1D analytic y masses."""
    h = p.side_um / 2.0
    node, weight = np.polynomial.legendre.leggauss(128)
    x = h * (node + 1.0) / 2.0
    wx = h * weight / 2.0
    sx, sy = np.asarray(sx), np.asarray(sy)
    # Integrate positive and negative mark x; y range for WX is |y|>=|x|.
    gx = (gaussian_density(x[None, :] - sx[:, None], p.waist_um)
          + gaussian_density(-x[None, :] - sx[:, None], p.waist_um))
    my = gaussian_mass(-h - sy[:, None], h - sy[:, None], p.waist_um)
    middle = gaussian_mass(-x[None, :] - sy[:, None],
                           x[None, :] - sy[:, None], p.waist_um)
    qx = np.sum(gx * (my - middle) * wx, axis=1)
    qy = np.sum(gx * middle * wx, axis=1)
    q_square = (gaussian_mass(-h - sx, h - sx, p.waist_um)
                * gaussian_mass(-h - sy, h - sy, p.waist_um))
    return qx, qy, q_square


def overlap_segments(sx, sy, ax, ay):
    """Break x integral wherever any clipped y-interval endpoint switches.

    With u=(x,y), both square windows require |x|<=ax, |y|<=ay.
    X windows exclude intervals [-sy-|x+sx|,-sy+|x+sx|] and
    [sy-|sx-x|,sy+|sx-x|]. Y windows require membership of both intervals.
    Endpoint crossing splits make the quadrature smooth within each segment.
    """
    corners = sorted(set([-ax, ax] + [v for v in (-sx, sx) if -ax < v < ax]))
    result = []
    for left, right in zip(corners[:-1], corners[1:]):
        mid = (left + right) / 2.0
        s1 = 1.0 if mid + sx >= 0 else -1.0
        s2 = 1.0 if sx - mid >= 0 else -1.0
        # Endpoint functions m*x+b.
        funcs = [(0.0, -ay), (0.0, ay),
                 (-s1, -sy - s1 * sx), (s1, -sy + s1 * sx),
                 (s2, sy - s2 * sx), (-s2, sy + s2 * sx)]
        points = [left, right]
        for i, (m1, b1) in enumerate(funcs):
            for m2, b2 in funcs[i + 1:]:
                if abs(m1 - m2) > 1e-14:
                    cross = (b2 - b1) / (m1 - m2)
                    if left + 1e-12 < cross < right - 1e-12:
                        points.append(cross)
        points = sorted(set(points))
        result.extend(zip(points[:-1], points[1:]))
    return result


def window_overlaps(sx_values, sy_values, p):
    """t_j = integral G(u) W_j(u+r_s) W_j(-u+r_s) du.

    This is geometric field overlap for an ideal 180-degree self-image.
    It is not a finite-NA diffraction or rigorous finite-grating calculation.
    """
    node, weight = np.polynomial.legendre.leggauss(16)
    tx, ty = np.zeros_like(sx_values), np.zeros_like(sx_values)
    h = p.side_um / 2.0
    for k, (sx, sy) in enumerate(zip(sx_values, sy_values)):
        ax, ay = h - abs(sx), h - abs(sy)
        if ax <= 0.0 or ay <= 0.0:
            continue
        seg = overlap_segments(float(sx), float(sy), ax, ay)
        starts = np.array([v[0] for v in seg])
        stops = np.array([v[1] for v in seg])
        half = (stops - starts) / 2.0
        x = ((starts + stops)[:, None] / 2.0 + half[:, None] * node).ravel()
        weights = (half[:, None] * weight).ravel()
        b1, b2 = np.abs(x + sx), np.abs(sx - x)
        low1, high1 = np.maximum(-ay, -sy - b1), np.minimum(ay, -sy + b1)
        low2, high2 = np.maximum(-ay, sy - b2), np.minimum(ay, sy + b2)
        intersection = gaussian_mass(np.maximum(low1, low2),
                                     np.minimum(high1, high2), p.waist_um)
        mass1 = gaussian_mass(low1, high1, p.waist_um)
        mass2 = gaussian_mass(low2, high2, p.waist_um)
        outside = gaussian_mass(-ay, ay, p.waist_um) - mass1 - mass2 + intersection
        gw = gaussian_density(x, p.waist_um) * weights
        tx[k], ty[k] = np.dot(gw, outside), np.dot(gw, intersection)
    return tx, ty


def simulate(scan, alpha_deg, p):
    """Return ideal isolated-order and self-reference detector intensities."""
    angle = math.radians(alpha_deg)
    sx = scan * math.cos(angle)
    sy = p.y_offset_um + scan * math.sin(angle)
    qx, qy, qsquare = window_powers(sx, sy, p)
    tx, ty = window_overlaps(sx, sy, p)
    if not 0 <= p.extra_visibility <= 1:
        raise ValueError("extra_visibility must be between 0 and 1")
    g = 2 * math.pi / p.pitch_um
    data = {"scan_um": scan, "x_um": sx, "y_um": sy,
            "q_x": qx, "q_y": qy, "q_square": qsquare, "t_x": tx, "t_y": ty}
    for name, q, t, a_plus, a_minus, coord, delta in [
        ("x", qx, tx, p.a_x_plus, p.a_x_minus, sx, p.delta_x),
        ("y", qy, ty, p.a_y_plus, p.a_y_minus, sy, p.delta_y),
    ]:
        i_plus, i_minus = abs(a_plus)**2 * q, abs(a_minus)**2 * q
        phase = 2 * g * coord + np.angle(a_plus * np.conj(a_minus)) + delta
        cross = 2 * p.extra_visibility * abs(a_plus * a_minus) * t * np.cos(phase)
        data[f"I_{name}_plus"] = i_plus
        data[f"I_{name}_minus"] = i_minus
        data[f"S_{name}_plus"] = 0.5 * (i_plus + i_minus + cross)
        data[f"S_{name}_minus"] = 0.5 * (i_plus + i_minus - cross)
        data[f"carrier_{name}"] = np.cos(phase)
    # Patent-like composite INTENSITY channels: orthogonal orders are summed.
    # A physical coherent combiner would need a different complex-field model.
    data["mix_1"] = data["I_x_minus"] + data["I_y_plus"]
    data["mix_2"] = data["I_x_plus"] + data["I_y_minus"]
    return data


def validate(data, p, alpha_deg):
    tol = 5e-11
    assert np.max(np.abs(data["q_x"] + data["q_y"] - data["q_square"])) < tol
    for name in ("x", "y"):
        q, t = data[f"q_{name}"], data[f"t_{name}"]
        assert q.min() >= -tol and q.max() <= 1 + tol
        assert t.min() >= -tol and np.max(t - q) < tol
        plus, minus = data[f"S_{name}_plus"], data[f"S_{name}_minus"]
        isum = data[f"I_{name}_plus"] + data[f"I_{name}_minus"]
        assert min(plus.min(), minus.min()) >= -tol
        assert np.max(np.abs(plus + minus - isum)) < tol
    if alpha_deg == 0:
        assert np.ptp(data["carrier_y"]) < tol
        # Scan step is 0.025 um, so one 1 um carrier period is 40 samples.
        offset = int(round((p.pitch_um / 2) / (data["scan_um"][1] - data["scan_um"][0])))
        assert np.max(np.abs(data["carrier_x"][offset:] - data["carrier_x"][:-offset])) < tol
    return {"max_q_partition_error": float(np.max(np.abs(data["q_x"] + data["q_y"] - data["q_square"]))),
            "min_detector_power": min(float(data[f"S_{j}_{a}"].min()) for j in ("x", "y") for a in ("plus", "minus")),
            "max_t_minus_q": max(float(np.max(data[f"t_{j}"] - data[f"q_{j}"])) for j in ("x", "y"))}


def export_csv(path, data):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(data.keys())
        writer.writerows(zip(*data.values()))


def make_figure(path, data, p):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150})
    fig, axs = plt.subplots(2, 2, figsize=(13.8, 9.4))
    ax = axs[0, 0]
    h = p.side_um / 2.0
    spot_x = 0.35 * h
    view = max(1.3 * h, abs(spot_x) + 1.1 * p.waist_um)
    grid = np.linspace(-h, h, 1000)
    xx, yy = np.meshgrid(grid, grid)
    window_x = np.abs(yy) >= np.abs(xx)
    grating_x = np.mod(xx + p.pitch_um * p.duty / 2, p.pitch_um) < p.pitch_um * p.duty
    grating_y = np.mod(yy + p.pitch_um * p.duty / 2, p.pitch_um) < p.pitch_um * p.duty
    raster = np.where(window_x, grating_x.astype(int), 2 + grating_y.astype(int))
    cmap = ListedColormap(["#d7efea", "#348b85", "#ffe5c7", "#d7883e"])
    ax.imshow(raster, extent=(-h, h, -h, h), origin="lower", cmap=cmap, interpolation="nearest")
    for radius, style in [(p.waist_um, "--"), (p.waist_um / 2, ":")]:
        ax.add_patch(Circle((spot_x, 0), radius, fill=False, color="#a82782", linewidth=1.6, linestyle=style))
    ax.plot(spot_x, 0, "+", color="#a82782", markersize=10)
    ax.text(0, .85 * h, r"$W_X$: lines vary in $x$", ha="center", fontsize=9,
            bbox={"facecolor": "white", "alpha": .88, "edgecolor": "none"})
    ax.text(-.7 * h, 0, "$W_Y$", ha="center", fontsize=10,
            bbox={"facecolor": "white", "alpha": .88, "edgecolor": "none"})
    ax.annotate("scan +x", xy=(.9 * h, -1.2 * h), xytext=(-.8 * h, -1.2 * h), ha="center",
                arrowprops={"arrowstyle": "->", "lw": 1.4})
    ax.text(spot_x, -1.25 * p.waist_um, rf"Gaussian $w={p.waist_um:g}$ $\mu$m", color="#a82782", ha="center", fontsize=9)
    ax.set(xlim=(-view, view), ylim=(-view * 1.04, view), xlabel=r"$x$ ($\mu$m)", ylabel=r"$y$ ($\mu$m)",
           title=f"(a) Illustrative {p.side_um:g} um CB aperture; pitch = {p.pitch_um:g} um")
    ax.set_aspect("equal")

    scan = data["scan_um"]
    ax = axs[0, 1]
    ax.plot(scan, data["q_x"], color="#237f84", lw=2, label=r"$q_X$: power in X region")
    ax.plot(scan, data["q_y"], color="#c87b30", lw=2, label=r"$q_Y$: power in Y region")
    ax.plot(scan, data["q_square"], color="#43484d", lw=1.5, label=r"$q_X+q_Y$: square overlap")
    ax.plot(scan, data["t_x"], color="#237f84", ls="--", label=r"$t_X$: 180-deg field overlap")
    ax.plot(scan, data["t_y"], color="#c87b30", ls="--", label=r"$t_Y$: 180-deg field overlap")
    ax.set(xlabel=r"Scan position $s=x$ ($\mu$m)", ylabel="Fraction of incident beam power",
           title="(b) Illumination and geometric self-overlap", ylim=(-.02, 1.04))
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=.18)

    ax = axs[1, 0]
    ax.plot(scan, data["mix_1"], color="#5268af", lw=2.6, label=r"$M_1=I_{X,-1}+I_{Y,+1}$")
    ax.plot(scan, data["mix_2"], color="#ce536b", lw=1.7, ls=":", label=r"$M_2=I_{X,+1}+I_{Y,-1}$")
    ax.text(.5, .13, "The two traces coincide for symmetric dummy coefficients.",
            ha="center", transform=ax.transAxes, fontsize=8.7)
    ax.set(xlabel=r"Scan position $s=x$ ($\mu$m)", ylabel="Detector power / incident power",
           title="(c) Composite intensity channels: smooth envelope", ylim=(0, .09))
    ax.legend(fontsize=9)
    ax.grid(alpha=.18)

    ax = axs[1, 1]
    zoom = np.abs(scan) <= 8.0
    ax.plot(scan[zoom], data["S_x_plus"][zoom], color="#237f84", lw=1.3, label=r"$S_{X,+}$")
    ax.plot(scan[zoom], data["S_x_minus"][zoom], color="#b04471", lw=1.3, label=r"$S_{X,-}$")
    ax.plot(scan[zoom], data["S_y_plus"][zoom], color="#c87b30", lw=1.7, ls="--", label=r"$S_{Y,+}$: no x carrier")
    ax.plot(scan[zoom], data["S_y_minus"][zoom], color="#766b58", lw=1.5, ls=":", label=r"$S_{Y,-}$")
    port_max = max(float(data[f"S_{j}_{port}"][zoom].max())
                   for j in ("x", "y") for port in ("plus", "minus"))
    ax.set(xlabel=r"Scan position $s=x$ ($\mu$m)", ylabel="Port power / incident power",
           title=rf"(d) Ideal self-reference ports: $T_X=p/2={p.pitch_um/2:g}$ $\mu$m",
           xlim=(-8, 8), ylim=(0, 1.08 * port_max if port_max > 0 else 1))
    ax.legend(fontsize=8.5, ncol=2, loc="upper center")
    ax.grid(alpha=.18)
    fig.suptitle("RCWA coefficients + macro-window overlap + ideal sensor model", fontsize=15, y=.975)
    fig.text(.5, .024,
             "ILLUSTRATIVE ONLY: all four diffraction efficiencies = 0.08; extra visibility = 0.9. "
             "Full collection, isolated orders, even Gaussian; no finite-NA propagation.",
             ha="center", fontsize=9, color="#4f5255")
    fig.subplots_adjust(left=.075, right=.98, bottom=.092, top=.91, hspace=.31, wspace=.24)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    out = Path(__file__).resolve().parent
    p = Parameters()
    scan = np.linspace(-45.0, 45.0, 3601)
    checks = []
    main_data = None
    for angle, filename in [(0.0, "scan_x_alpha0.csv"), (20.0, "scan_alpha20.csv")]:
        data = simulate(scan, angle, p)
        check = validate(data, p, angle)
        export_csv(out / filename, data)
        checks.append(f"alpha={angle:g} deg: {check}")
        if angle == 0:
            main_data = data
    make_figure(out / "cb_mark_postprocess_demo.png", main_data, p)
    text = "\n".join(checks)
    (out / "validation.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"Outputs: {out}")


if __name__ == "__main__":
    main()
