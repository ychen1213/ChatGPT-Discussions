# Controlled finite-pupil CB-mask test

This is a synthetic scalar experiment to test one candidate explanation. It is not a D4C fit and does not use measured RCWA coefficients.

The isolated-order experiment fixes equal real ±1 coefficients and uses only the slowly varying X-order envelope. The CB X-region is the binary set `|y| >= |x|` inside a 40 µm square. Illumination amplitude is `sqrt(2/(pi*w^2))*exp(-(u^2+v^2)/w^2)` with intensity 1/e² radius `w=12 µm`. Pitch is 2 µm, so constructive carrier positions are separated by 1 µm. The illuminated envelope is Fourier transformed and collected through a circular disk centered on an isolated order, with local radius 0.05, 0.1, 0.2 or 0.4 cycles/µm. These correspond to local angular/NA radii 0.03165, 0.0633, 0.1266, 0.2532 at wavelength 0.633 µm; they are not the absolute objective NA.

At each scan position, `q=sum(|f(q)|²)` and `t=Re sum(f(q)*conj(f(-q)))`, including fixed integration factors. The complementary ports are `q ± t*cos(4*pi*s/p)`, their raw sum is `2q`, and the constructive-position envelope is `q+t`. A full-collection reference computes exact real-space overlap integrals by adaptive quadrature. No scan-by-scan normalization is applied in any calculation. Plotting normalizes each entire curve by its own s=0 value only for comparison.

The 0–5 µm scan step is 0.05 µm. Domain is 80 µm. The finite-pupil experiment is repeated at 512² and 1024² samples. Each pixel uses the exact area fraction of the binary triangular region, so diagonal step boundaries do not jump between sampling points. This is quadrature of a step geometry, not an assumed physical soft edge. The maximum difference between the two `q+t` curves is below 0.033% of the 1024-grid central value for every radius.

Define `R=(P(0)-P(1))/(P(1)-P(2))`, with distances in µm. Results at 1024²:

| Collection | Constructive envelope q+t | Modulation t | Raw complementary sum 2q |
|---|---:|---:|---:|
| Full collection | 1.01397 | 1.12383 | 0.33955 |
| Local disk 0.05 /µm | 0.35067 | 0.35422 | 0.34009 |
| Local disk 0.10 /µm | 0.38037 | 0.38813 | 0.33972 |
| Local disk 0.20 /µm | 0.49524 | 0.51671 | 0.33964 |
| Local disk 0.40 /µm | 0.83883 | 0.91867 | 0.33959 |

For these parameters, finite bandwidth smooths the center cusp and makes the first drop smaller relative to the second. It does not create a ratio near 2. This is a parameter-bounded counterexample to the claim that the 2D CB mask or finite NA by itself must produce that ratio. Different mark and illumination widths, detection modes or apertures remain possible explanations.

An additional 512² full-field experiment adds symmetric X and Y ±1 carriers, without a zero order, and compares coherent X+Y power against the sum of separate X and Y powers. The physical annular pupil uses wavelength 0.633 µm, absolute NA 0.45, and inner radius 0.7 times the first-order spatial frequency. X-only half-wedge and local-disk ROIs are also checked. None produces the proposed center-drop ratio of 2. The all-annulus raw sum is nearly constant, with a small increase away from center rather than a monotone decrease. Detailed numbers are in results.json and full_xy_*.csv. This full-field extension is illustrative and was not separately refined to 1024².

Run:

```powershell
uv run --with numpy --with scipy --with matplotlib python check_finite_pupil.py
```

`envelopes.png` shows normalized envelope curves. All raw powers, positions, parameters, drop sequences and convergence errors are retained in the CSV and JSON outputs.
