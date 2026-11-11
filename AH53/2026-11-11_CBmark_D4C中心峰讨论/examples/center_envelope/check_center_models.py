"""Controlled geometry checks; no D4C data or RCWA coefficients are fitted.

Run: uv run --with numpy --with scipy --with matplotlib check_center_models.py
All lengths are in micrometres. Plot labels use English for portability.
"""
from pathlib import Path
import csv
import json
import math
import numpy as np
from scipy.special import erf, erfc
from scipy.signal import find_peaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
H = 1.0  # p/2 for p = 2 um
NODES, WEIGHTS = np.polynomial.legendre.leggauss(256)


def finite_qt(s, size, waist):
    """Continuous quadrature of Gaussian-weighted 2D binary CB X region.

    q: single-mask power. t: overlap with its 180-degree self-image.
    The y integral is analytic; split x domains avoid |x| discontinuities.
    """
    s = np.abs(np.asarray(s, dtype=float))
    half = size / 2
    x = half * (NODES + 1) / 2
    weights = half * WEIGHTS / 2
    density = lambda z: np.sqrt(2 / np.pi) / waist * np.exp(-2 * z*z / waist**2)
    ymass = erf(np.sqrt(2)*half/waist) - erf(np.sqrt(2)*x/waist)
    q = np.sum((density(x[None, :] - s[:, None]) +
                density(-x[None, :] - s[:, None])) * ymass * weights, axis=1)
    bound = np.maximum(half - s, 0)
    u = bound[:, None] * (NODES + 1) / 2
    weights_t = bound[:, None] * WEIGHTS / 2
    ymass_t = erf(np.sqrt(2)*half/waist) - erf(np.sqrt(2)*(u+s[:, None])/waist)
    t = 2 * np.sum(density(u) * np.maximum(ymass_t, 0) * weights_t, axis=1)
    return q, t


def metrics(name, values, **params):
    p = np.asarray(values, dtype=float)
    p = p / p[0]
    d = p[:-1] - p[1:]
    side = d[1:4]
    result = dict(model=name, **params,
                  P0=float(p[0]), P1=float(p[1]), P2=float(p[2]),
                  P3=float(p[3]), P4=float(p[4]),
                  D0=float(d[0]), D1=float(d[1]), D2=float(d[2]), D3=float(d[3]),
                  R01=float(d[0]/d[1]) if abs(d[1]) > 1e-15 else None,
                  side_cv=float(np.std(side)/np.mean(side)) if np.all(side > 1e-12) else None)
    return result


def main():
    s = np.arange(5) * H
    rows = []
    for size in (10., 20., 40., 80.):
        length = np.maximum(size - 2*s, 0)
        rows.append(metrics("line_length", length, L_um=size, w_um=None))
        rows.append(metrics("uniform_two_mask_overlap", length**2, L_um=size, w_um=None))
    for waist in (1., 1.67, 2., 3., 6., 10., 12., 20.):
        q, t = finite_qt(s, 40., waist)
        for name, p in (("single_mask_q", q), ("self_overlap_t", t),
                        ("constructive_envelope_q_plus_t", q+t)):
            rows.append(metrics(name, p, L_um=40., w_um=waist))
    with (OUT / "model_comparison.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # Scale sweep: can a model match R01~2 while later decrements stay equal?
    sweep = []
    for size in (10., 20., 40., 80.):
        for waist in np.geomspace(0.8, 40., 160):
            q, t = finite_qt(s, size, float(waist))
            for name, p in (("q", q), ("t", t), ("q+t", q+t)):
                sweep.append(metrics(name, p, L_um=size, w_um=float(waist)))
    close_ratio = [r for r in sweep if r["R01"] is not None and 1.8 <= r["R01"] <= 2.2]
    both = [r for r in close_ratio if r["side_cv"] is not None and r["side_cv"] <= .10]
    best = sorted(close_ratio, key=lambda r: r["side_cv"] if r["side_cv"] is not None else 1e9)[:8]

    # Independent analytic limit and quadrature convergence.
    test_s = np.linspace(0, 4, 41)
    q_num, t_num = finite_qt(test_s, 120., 12.)
    q_exact = .5 * (1-erf(test_s/12.)**2)
    t_exact = .5 * erfc(test_s/12.)**2
    max_q_error = float(np.max(np.abs(q_num-q_exact)))
    max_t_error = float(np.max(np.abs(t_num-t_exact)))
    assert max_q_error < 1e-10 and max_t_error < 1e-10
    q0, t0 = finite_qt(np.array([0.]), 40., 12.)
    assert abs(q0[0]-t0[0]) < 1e-12
    q, t = finite_qt(test_s, 40., 12.)
    assert np.all(t <= q+1e-12) and np.all(t >= 0)
    phase = 2*np.pi*test_s
    plus = q+t*np.cos(phase)
    minus = q-t*np.cos(phase)
    complementary_error = float(np.max(np.abs(plus+minus-2*q)))
    assert complementary_error < 1e-12

    # Check actual maxima as well: a steep envelope moves maxima away from nh,
    # and may remove the outer carrier maxima entirely.
    actual_maxima = []
    fine_s = np.linspace(0, 5, 50001)
    for waist in (12., 3., 1.67):
        q_fine = .5 * (1-erf(fine_s/waist)**2)
        t_fine = .5 * erfc(fine_s/waist)**2
        signal = q_fine + t_fine*np.cos(2*np.pi*fine_s)
        indices = np.r_[0, find_peaks(signal)[0]]
        actual_maxima.append(dict(w_um=waist,
                                  s_um=fine_s[indices].tolist(),
                                  power=signal[indices].tolist()))
    summary = dict(pitch_um=2., peak_spacing_um=H,
                   data_source="Synthetic controlled model; no D4C or fitted R",
                   sweep_cases=len(sweep), cases_R01_between_1p8_and_2p2=len(close_ratio),
                   cases_also_side_cv_below_10_percent=len(both),
                   best_side_consistency_near_ratio2=best,
                   q_analytic_max_error=max_q_error, t_analytic_max_error=max_t_error,
                   complementary_identity_max_error=complementary_error,
                   actual_maxima_in_0_to_5_um_infinite_wedge_model=actual_maxima)
    (OUT / "model_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plt.rcParams.update({"font.size":10, "figure.dpi":150})
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8), constrained_layout=True)
    dense = np.linspace(-5, 5, 1001)
    q, t = finite_qt(dense, 40., 12.)
    for label, vals in (("Illuminated power q", q), ("Self-image overlap t", t),
                        ("Constructive envelope q+t", q+t)):
        axes[0, 0].plot(dense, vals/vals[len(dense)//2], label=label)
    axes[0, 0].set(title="Broad spot: L=40, w=12 um", xlabel="Scan s (um)", ylabel="Envelope / center")
    for waist in (12., 3., 1.67):
        vals = erfc(np.abs(dense)/waist)
        axes[0, 1].plot(dense, vals, label=f"w={waist:g} um")
        axes[0, 1].plot(s, erfc(s/waist), "o", ms=4)
    axes[0, 1].set(title="A ratio near 2 needs a narrow scale", xlabel="Scan s (um)", ylabel="Constructive envelope")
    for waist in (12., 3., 1.67):
        vals = erfc(s/waist)
        drops = vals[:-1]-vals[1:]
        axes[1, 0].plot(np.arange(4), drops/drops[1], "o-", label=f"w={waist:g} um")
    axes[1, 0].plot([0, 1, 2, 3], [2, 1, 1, 1], "k--", label="Reported approximate pattern")
    axes[1, 0].set(title="Matching first ratio does not match all drops", xlabel="Drop index n", ylabel="(P[n]-P[n+1]) / D1", xticks=[0, 1, 2, 3])
    phase = 2*np.pi*dense
    axes[1, 1].plot(dense, q+t*np.cos(phase), label="Plus port", lw=.9)
    axes[1, 1].plot(dense, q-t*np.cos(phase), label="Minus port", lw=.9)
    axes[1, 1].plot(dense, 2*q, "k", label="Plus + minus")
    axes[1, 1].set(title="Ideal port sum cancels self-image cross term", xlabel="Scan s (um)", ylabel="Scalar signal")
    for ax in axes.flat:
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
    fig.suptitle("CB center-envelope checks | p=2 um | Synthetic scalar models, no D4C fit")
    fig.savefig(OUT / "center_envelope_checks.png")
    plt.close(fig)
    print(json.dumps(summary, indent=2))
    print("Selected broad-spot results:")
    for row in rows:
        if row["w_um"] in (12., 1.67) or (row["model"] == "line_length" and row["L_um"] == 40.):
            print(row)


if __name__ == "__main__":
    main()
