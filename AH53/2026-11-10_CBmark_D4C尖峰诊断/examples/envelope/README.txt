CB mark: RCWA coefficients followed by finite-window and ideal-sensor effects
============================================================================

This is an ILLUSTRATIVE, UNCALIBRATED mathematical model. No actual RCWA data,
measured scan, patent device dimensions, optical NA, wavelength, or layer stack
were supplied. The example coefficients and dimensions are not patent results.

Run (Python 3 + numpy + matplotlib):
  uv run --with numpy --with matplotlib cb_mark_postprocess.py

Files:
  cb_mark_postprocess.py      Reproducible standalone implementation.
  cb_mark_postprocess_demo.png  Four-panel scientific illustration.
  scan_x_alpha0.csv          Pure x scan, s=-45..45 um, step 0.025 um.
  scan_alpha20.csv           Optional oblique scan, alpha=20 degrees.
  validation.txt            Numerical checks generated on each run.

Geometry and illumination:
  L=40 um square, pitch p=2 um, duty=0.5; these are chosen example values.
  WX=1 if inside square AND |y|>=|x| (upper/lower triangles, lines vary in x).
  WY=1 if inside square AND |x|>|y| (left/right triangles, lines vary in y).
  Gaussian intensity G(u)=2/(pi*w^2)*exp(-2*|u|^2/w^2), w=12 um.
  w is a 1/e^2 intensity radius. Integral over the whole plane is 1.
  r_s=(s*cos(alpha), y0+s*sin(alpha)), y0=0 by default.
  q_j=integral G(u) W_j(u+r_s) d^2u.
  t_j=integral G(u) W_j(u+r_s) W_j(-u+r_s) d^2u.
  t_j is overlap after an ideal 180-degree image reversal; it generally differs
  from q_j away from the centered position. It is not a constant visibility.

Replace the four complex amplitudes in Parameters with POWER-NORMALIZED RCWA
amplitudes for the isolated +1/-1 orders of the X/Y-oriented gratings. The
dummy values a=sqrt(0.08) are real and identical for all four orders.
Consequently, each |a|^2 is an 8% diffraction efficiency, and the composite
channels in panel (c) coincide. This is intentional and is not a real RCWA
calculation. If RCWA provides electric field amplitudes, apply its outgoing-
flux/admittance normalization first. Efficiency alone loses diffraction phase.
Do not interpret duty=0.5 as a rigorous guarantee of zero even orders; stack,
polarization, wavelength, and coupling can matter.

Ideal intensity channels:
  I_j,+ = |a_j,+|^2 q_j; I_j,- = |a_j,-|^2 q_j.
  M1=I_X,-+I_Y,+; M2=I_X,++I_Y,-.
These M signals SUM INTENSITIES. They do not include coherent interference
between orthogonal diffraction directions. That requires an explicit sensor
field transformation. They also do not include a background from the wafer
outside the square; add measured/modelled background separately if needed.

Ideal self-reference ports, for one isolated orientation j:
  phi_j=2*G_j dot r_s + arg(a_j,+ conj(a_j,-)) + delta_j,
  S_j,+/- = 0.5 * [(|a_j,+|^2+|a_j,-|^2)*q_j
              +/- 2*V_extra*|a_j,+ a_j,-|*t_j*cos(phi_j)].
  G_X=(2*pi/p,0), G_Y=(0,2*pi/p).
  V_extra=0.9 is extra phenomenological loss AFTER geometric overlap.
  delta_X=delta_Y=0.35 rad are illustrative sensor phase offsets.
  Here +/- on S denote complementary sensor PORTS, whereas +/- on I and a
  denote diffraction ORDERS; those are different labels.

For pure x scanning the X self-reference carrier period is p/2=1 um; the Y
carrier phase is constant (its intensity envelope can still vary). The p/2
period follows the explicitly assumed +/-1 interference and is NOT a universal
claim about every detector signal. For alpha=20 deg, periods along s are
T_X=p/(2*cos(alpha)) and T_Y=p/(2*|sin(alpha)|).

Scope and how to extend:
This model assumes local isolated orders, full collection, identical ideal
sensor paths, a real even Gaussian field, and no finite-NA propagation. It
cannot predict aperture diffraction, order clipping/crosstalk, vector mode
overlap, coherent edge scattering, wavefront aberrations, or an exact device.
For those, propagate windowed complex fields A(r)*W_j(r)*a_j,m*exp(i m G_j.r)
through the actual pupil/relay/detector, then form square-law detector signals.
Do not apply geometric q/t losses a second time if that field propagation
already includes the same windows. Spectral/polarization/source averaging
must act at the appropriate coherent/incoherent stage. Temporal filtering,
sampling, background, drift, and noise can be appended at detector output.

Numerical checks:
qX+qY=qSquare; 0<=t_j<=q_j<=1; all detector powers>=0;
S_j,++S_j,-=I_j,++I_j,-; pure-x carrier has 1 um period and constant Y phase.
q is evaluated by analytic Gaussian y masses and 128-point x quadrature.
t uses analytic y-interval intersections and 16-point x quadrature in each
piecewise-smooth interval. Validation tolerances are 5e-11 for this example.
