RCWA -> CB-mark scan: scalar pupil-FFT post-processing example

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
  320 x 320 samples, 80 um field of view, dx=0.25 um.
  Scan -25..25 um in 0.1 um steps. The w=12 um beam is well
  contained within the 80 um window. Sharp masks are sampled on this grid;
  their moving edges can cause small staircase ripple. For quantitative
  accuracy refine the grid (e.g. --n 640), use fractional-cell mask coverage,
  and compare convergence. The existing validation checks normalization and
  analytic limits, not numerical convergence of a physical patent model.
  This coherent, monochromatic, in-focus scalar demonstration omits measured
  aberrations, partial coherence, polarization leakage, roughness, detector
  noise and scan jitter. Those require explicit measured/model parameters.

Validation from the current run
parseval_absolute_error: 0.0
incident_gaussian_power: 0.9999999999473212
infinite_X_plus_normalized_at_0_025_05_075_1_um: [0.9999999999919965, 0.4999999999952183, 9.746832211925585e-14, 0.5000000000008775, 1.0]
infinite_X_expected: [1.0, 0.5, 0.0, 0.4999999999999999, 1.0]
infinite_X_fringe_max_error: 8.003486762220291e-12
infinite_Y_xscan_peak_to_peak: 0.0
max_complementary_output_identity_absolute_error: 4.163336342344337e-17
minimum_detected_power: 6.725263063629096e-34
