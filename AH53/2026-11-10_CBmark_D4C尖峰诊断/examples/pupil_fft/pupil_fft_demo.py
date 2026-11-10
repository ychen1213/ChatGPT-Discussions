"""RCWA-to-CB-mark post-processing scaffold; no RCWA solver is used here.

Run with:
    uv run --with numpy --with matplotlib pupil_fft_demo.py

All lengths are in micrometres.  The supplied symmetric scalar amplitudes are
illustrative placeholders, NOT measured values or a fit to WO2022258371A1.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Parameters:
    pitch: float = 2.0
    mark_size: float = 40.0
    waist: float = 12.0  # Gaussian intensity 1/e^2 radius
    wavelength: float = 0.633
    na: float = 0.45
    domain: float = 80.0
    n: int = 320
    stop_fraction: float = 0.7  # central stop radius, in units of G
    delta: float = 0.0
    # Use X/Y coefficients expressed in one consistent global polarization
    # basis. Their defaults match only to isolate geometric/optical effects.
    r_x_minus: complex = complex(np.sqrt(0.08))
    r_x_zero: complex = 0.3 + 0j
    r_x_plus: complex = complex(np.sqrt(0.08))
    r_y_minus: complex = complex(np.sqrt(0.08))
    r_y_zero: complex = 0.3 + 0j
    r_y_plus: complex = complex(np.sqrt(0.08))
    r_background: complex = 0.3 + 0j


class Postprocessor:
    def __init__(self, p: Parameters):
        self.p = p
        self.dx = p.domain / p.n
        self.g = 2 * np.pi / p.pitch
        self.k0 = 2 * np.pi / p.wavelength
        coordinate = (np.arange(p.n) - p.n // 2) * self.dx
        self.u, self.v = np.meshgrid(coordinate, coordinate, indexing="xy")
        self.amplitude = np.sqrt(2 / (np.pi * p.waist**2)) * np.exp(
            -(self.u**2 + self.v**2) / p.waist**2
        )
        frequency = 2 * np.pi * np.fft.fftfreq(p.n, d=self.dx)
        self.kx, self.ky = np.meshgrid(frequency, frequency, indexing="xy")
        kr = np.hypot(self.kx, self.ky)
        self.pupil = (kr <= self.k0 * p.na) & (kr >= p.stop_fraction * self.g)
        # D1 collects the X-minus and Y-plus lobes. D2 collects the other two.
        self.d1 = self.pupil & ((self.ky - 0.5 * self.kx) > 0)
        self.d2 = self.pupil & ~self.d1
        # Positive half-ROIs each select one member of an antipodal order pair.
        self.roi_x = self.pupil & (self.kx > 0) & (np.abs(self.kx) > np.abs(self.ky))
        self.roi_y = self.pupil & (self.ky > 0) & (np.abs(self.ky) > np.abs(self.kx))
        # In unshifted FFT storage, index -i modulo N is exact k -> -k.
        # np.flip would introduce a one-bin frequency error.
        self.negative_index = (-np.arange(p.n)) % p.n

    def field(self, sx: float, sy: float = 0.0, geometry: str = "cb"):
        # Sensor/beam coordinates u,v stay fixed. The mark coordinates move.
        # Do not add a second translation phase to the resulting FFT.
        x, y = self.u + sx, self.v + sy
        if geometry == "cb":
            square = (np.abs(x) <= self.p.mark_size / 2) & (
                np.abs(y) <= self.p.mark_size / 2
            )
            wx = square & (np.abs(y) >= np.abs(x))
            wy = square & ~wx
        elif geometry == "infinite_x":
            square = np.ones_like(x, dtype=bool)
            wx, wy = square, np.zeros_like(square)
        elif geometry == "infinite_y":
            square = np.ones_like(x, dtype=bool)
            wx, wy = np.zeros_like(square), square
        else:
            raise ValueError(geometry)
        grating_x = (
            self.p.r_x_minus * np.exp(-1j * self.g * x)
            + self.p.r_x_zero
            + self.p.r_x_plus * np.exp(1j * self.g * x)
        )
        grating_y = (
            self.p.r_y_minus * np.exp(-1j * self.g * y)
            + self.p.r_y_zero
            + self.p.r_y_plus * np.exp(1j * self.g * y)
        )
        e = self.amplitude * (
            wx * grating_x + wy * grating_y + self.p.r_background * ~square
        )
        return e, wx, wy

    def pupil_field(self, e):
        # ifftshift puts the physical sensor origin at FFT index zero.
        # Unitary FFT permits equal dx^2 weights in the input/output power sums.
        u = np.fft.fft2(np.fft.ifftshift(e), norm="ortho")
        return u, self.pupil * u

    def channels(self, f):
        # A 180-degree pupil mapping is a spatial inversion, not conjugation.
        f2 = f[np.ix_(self.negative_index, self.negative_index)]
        phase = np.exp(1j * self.p.delta)
        plus, minus = 0.5 * np.abs(f + phase * f2) ** 2, 0.5 * np.abs(f - phase * f2) ** 2
        intensity = np.abs(f) ** 2
        result = {
            "mix_D1": float(np.sum(intensity[self.d1]) * self.dx**2),
            "mix_D2": float(np.sum(intensity[self.d2]) * self.dx**2),
            "S_X_plus": float(np.sum(plus[self.roi_x]) * self.dx**2),
            "S_X_minus": float(np.sum(minus[self.roi_x]) * self.dx**2),
            "S_Y_plus": float(np.sum(plus[self.roi_y]) * self.dx**2),
            "S_Y_minus": float(np.sum(minus[self.roi_y]) * self.dx**2),
        }
        identity_error = 0.0
        for roi, label in [(self.roi_x, "X"), (self.roi_y, "Y")]:
            expected = np.sum((np.abs(f) ** 2 + np.abs(f2) ** 2)[roi]) * self.dx**2
            actual = result[f"S_{label}_plus"] + result[f"S_{label}_minus"]
            identity_error = max(identity_error, abs(actual - expected))
        return result, identity_error


def validate(model: Postprocessor):
    checks = {}
    e, _, _ = model.field(3.125)
    u, _ = model.pupil_field(e)
    power_in = np.sum(np.abs(e) ** 2) * model.dx**2
    power_fft = np.sum(np.abs(u) ** 2) * model.dx**2
    checks["parseval_absolute_error"] = float(abs(power_in - power_fft))
    checks["incident_gaussian_power"] = float(np.sum(model.amplitude**2) * model.dx**2)
    assert checks["parseval_absolute_error"] < 1e-12
    assert abs(checks["incident_gaussian_power"] - 1) < 1e-8

    positions = np.array([0, 0.25, 0.5, 0.75, 1.0])
    phase_values = []
    y_values = []
    for sx in positions:
        ex, _, _ = model.field(float(sx), geometry="infinite_x")
        _, f = model.pupil_field(ex)
        channels, _ = model.channels(f)
        phase_values.append(channels["S_X_plus"])
        ey, _, _ = model.field(float(sx), geometry="infinite_y")
        _, fy = model.pupil_field(ey)
        ychannels, _ = model.channels(fy)
        y_values.append(ychannels["S_Y_plus"])
    normalized = np.array(phase_values) / max(phase_values)
    expected = 0.5 * (1 + np.cos(2 * model.g * positions + model.p.delta))
    expected /= max(expected)
    checks["infinite_X_plus_normalized_at_0_025_05_075_1_um"] = normalized.tolist()
    checks["infinite_X_expected"] = expected.tolist()
    checks["infinite_X_fringe_max_error"] = float(np.max(np.abs(normalized - expected)))
    checks["infinite_Y_xscan_peak_to_peak"] = float(np.ptp(y_values))
    assert checks["infinite_X_fringe_max_error"] < 1e-8
    assert checks["infinite_Y_xscan_peak_to_peak"] < 1e-12
    return checks


def save_plots(model, scan, channels, output):
    plt.rcParams.update({"font.size": 10, "figure.dpi": 140})
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.2), constrained_layout=True)
    e, _, _ = model.field(0)
    _, f = model.pupil_field(e)
    intensity = np.fft.fftshift(np.abs(f) ** 2)
    kk = np.fft.fftshift(model.kx[0]) / model.g
    extent = [kk[0], kk[-1], kk[0], kk[-1]]
    log_intensity = np.log10(np.maximum(intensity / intensity.max(), 1e-8))
    im = axes[0, 0].imshow(log_intensity, origin="lower", extent=extent, cmap="magma", vmin=-6, vmax=0)
    axes[0, 0].plot([-1.5, 1.5], [-0.75, 0.75], "c--", lw=1, label="D1/D2 boundary")
    axes[0, 0].set(xlim=(-1.5, 1.5), ylim=(-1.5, 1.5), xlabel=r"$k_x/G$", ylabel=r"$k_y/G$", title="CB pupil at scan x = 0; zero order stopped")
    fig.colorbar(im, ax=axes[0, 0], label=r"$\log_{10}(I/I_{max})$")
    axes[0, 0].legend(loc="upper right", fontsize=8)
    plot_items = [
        (axes[0, 1], "mix_D1", "mix_D2", "Pupil power: X-/Y+ versus X+/Y-"),
        (axes[1, 0], "S_X_plus", "S_X_minus", "X self-reference: geometric envelope + 1 um fringes"),
        (axes[1, 1], "S_Y_plus", "S_Y_minus", "Y self-reference during a pure x scan"),
    ]
    for ax, a, b, title in plot_items:
        ax.plot(scan, channels[a], label=a, lw=1.15)
        ax.plot(scan, channels[b], label=b, lw=1.15, alpha=0.8)
        ax.set(xlabel="Mark coordinate offset sx (um)", ylabel="Scalar signal / unit input norm", title=title)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("Illustrative scalar RCWA post-processing scaffold | p=2 um, L=40 um, w=12 um\nSymmetric placeholder amplitudes; no patent fit", fontsize=12)
    fig.savefig(output / "cb_scan_curves.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.6), constrained_layout=True)
    for key in ["S_X_plus", "S_X_minus"]:
        ax.plot(scan, channels[key], label=key)
    ax.set(xlim=(-3, 3), xlabel="Mark coordinate offset sx (um)", ylabel="Scalar signal / unit input norm", title="X channel detail: 2 um pitch gives 1 um self-reference period")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.savefig(output / "cb_x_fringe_detail.png")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--n", type=int, default=320)
    parser.add_argument("--scan-step", type=float, default=0.1)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    p = Parameters(n=args.n)
    model = Postprocessor(p)
    checks = validate(model)
    scan = np.linspace(-25, 25, round(50 / args.scan_step) + 1)
    records = []
    max_identity_error = 0.0
    min_channel = float("inf")
    for sx in scan:
        e, wx, wy = model.field(float(sx))
        _, f = model.pupil_field(e)
        channels, error = model.channels(f)
        max_identity_error = max(max_identity_error, error)
        min_channel = min(min_channel, *channels.values())
        # The fractions below are diagnostics only: never multiply them into f
        # or a detected power again; the mask/spot overlap is already in e.
        power_density = model.amplitude**2 * model.dx**2
        records.append({"sx_um": float(sx), **channels, "q_X_diagnostic": float(np.sum(power_density * wx)), "q_Y_diagnostic": float(np.sum(power_density * wy))})
    checks["max_complementary_output_identity_absolute_error"] = max_identity_error
    checks["minimum_detected_power"] = min_channel
    assert max_identity_error < 1e-12
    assert min_channel >= 0
    with (args.outdir / "cb_scan_curves.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    channels = {key: np.array([row[key] for row in records]) for key in records[0] if key != "sx_um"}
    save_plots(model, scan, channels, args.outdir)
    results = "\n".join(f"{key}: {value}" for key, value in checks.items()) + "\n"
    (args.outdir / "validation.txt").write_text(results, encoding="utf-8")
    readme = f"""RCWA -> CB-mark scan: scalar pupil-FFT post-processing example

Run (Python plus NumPy and Matplotlib):
  uv run --with numpy --with matplotlib pupil_fft_demo.py

Outputs: cb_scan_curves.png, cb_x_fringe_detail.png, cb_scan_curves.csv,
validation.txt. This program solves no Maxwell/RCWA problem. It shows a
physically explicit post-processing route for supplied complex order fields.

Geometry and coordinates
  Pitch 2 um; illustrative square mark L=40 um. Within the square,
  X-grating regions satisfy |y| >= |x|; Y-grating regions fill the remainder.
  Beam waist w=12 um is the 1/e^2 intensity radius. The field amplitude
  sqrt(2/(pi*w^2))*exp(-(u^2+v^2)/w^2) has unit incident power.
  The sensor coordinates u,v and its FFT grid remain fixed. Mark coordinates
  are x=u+sx, y=v+sy, with sy=0. The sign of mechanical scan can be reversed
  by changing this coordinate convention. No extra translation phase or
  overlap factor is multiplied in after constructing the field.

Equivalent-field approximation
  E=A*[WX*sum_m rXm exp(i*m*G*x) + WY*sum_m rYm exp(i*m*G*y)
       + rbg*(1-square)], m=-1,0,+1 and G=2*pi/p.
  rX+ = rX- = rY+ = rY- = sqrt(0.08), rX0=rY0=rbg=0.3 are scalar electric-field
  amplitudes chosen only to illustrate behavior. They are NOT actual RCWA
  data, NOT a complete energy-conserving scattering solution, and NOT a fit
  to the patent. The four first orders have equal angles in this example.
  Parameters.r_x_minus/zero/plus and r_y_minus/zero/plus are independent
  inputs, so the two orientations can use their own RCWA complex fields.
  To use real RCWA outputs, insert complex amplitudes including phase and
  polarization; for X/Y gratings rotate the polarization basis consistently.
  RCWA diffraction efficiencies are powers, not field amplitudes: recover
  fields using the solver's flux/admittance normalization, rather than simply
  sqrt(efficiency), especially across different angles/media or vector modes.
  In particular sqrt(0.08) is just an electric-field placeholder here; this
  program does not claim a physical diffraction efficiency of 0.08.
  A scalar mask times a local infinite-grating field is an approximation to
  finite mark boundaries. It does not model boundary EM coupling/near fields.

Optical and detection model
  Lambda=0.633 um; NA=0.45 in air; central stop |k|<0.7*G.
  Unitary FFT and dx^2 integration give Parseval-consistent scalar norms.
  Treating raw electric-field |FFT(E)|^2 as power uses a common-admittance /
  paraxial approximation. The plotted normalized scalar signal is not a
  calibrated absolute power in watts, nor a strict flux-normalized fraction
  for arbitrary real RCWA orders. Real use requires a consistent vector-field,
  modal-flux and optical pupil-apodization mapping before power detection.
  Pupil D1: ky-0.5*kx>0 (X-minus + Y-plus), D2 its complement.
  Mix power is integrated intensity, not an arbitrary X/Y field sum.
  Self-reference uses F1=P*FFT(E), F2=F1(-kx,-ky) and
    S+/- = 0.5*integral_ROI |F1 +/- exp(i*delta)*F2|^2.
  delta=0. X ROI: kx>0 and |kx|>|ky|; Y ROI: ky>0 and |ky|>|kx|.
  The negative-frequency map is (-index) modulo N, NOT array reversal.
  These ROIs and the diagonal pupil split are explicit illustrative detector
  choices. Actual apparatus may have other ports/masks, beam-splitter factors,
  relay magnification, polarization transformations, and coherence matrices.
  The finite beam, triangular regions and stop are included in the same
  complex field. Thus finite spot/window overlap and order cross-overlap
  emerge automatically. q_X/Y columns are diagnostics only.

Reading the curves
  X-channel interference contains the relative phase 2*G*sx, hence period
  p/2=1 um. Along a pure x scan the ideal infinite Y grating has no carrier;
  finite CB geometry can still change the Y-channel envelope and visibility.
  A vanishing Y-minus signal for a symmetric infinite Y grating is valid for
  this illustrative delta=0 optical model. Other phase biases change it.

Numerical grid and limitations
  {p.n} x {p.n} samples, {p.domain:g} um field of view, dx={model.dx:g} um.
  Scan -25..25 um in {scan[1]-scan[0]:g} um steps. The w=12 um beam is well
  contained within the 80 um window. Sharp masks are sampled on this grid;
  their moving edges can cause small staircase ripple. For quantitative
  accuracy refine the grid (e.g. --n 640), use fractional-cell mask coverage,
  and compare convergence. The existing validation checks normalization and
  analytic limits, not numerical convergence of a physical patent model.
  This coherent, monochromatic, in-focus scalar demonstration omits measured
  aberrations, partial coherence, polarization leakage, roughness, detector
  noise and scan jitter. Those require explicit measured/model parameters.

Validation from the current run
{results}
"""
    (args.outdir / "README.txt").write_text(readme, encoding="utf-8")
    print(results)
    print(f"Wrote plots, curve CSV, README and validation to: {args.outdir.resolve()}")


if __name__ == "__main__":
    main()
