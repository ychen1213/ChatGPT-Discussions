"""Deterministic synthetic Mark used only as a geometric reference.

All lengths are in nm. X is transverse, Y is height, and Z runs along
the ridges. This is a smooth, topology-fixed synthetic shape, not a
reconstruction of a measured device. It intentionally tests asymmetric
cross-sections and height/length-dependent sidewalls only.
"""

from __future__ import annotations

import numpy as np


class ReferenceGeometry:
    """Two local ridges or a 50 by 50 um full domain with 15 ridges."""

    def __init__(self, case: str = "local", seed: int = 20261024):
        if case not in {"local", "full"}:
            raise ValueError("case must be 'local' or 'full'")
        self.case = case
        self.seed = int(seed)
        self.width_x = 6400.0 if case == "local" else 50000.0
        self.length_z = 6400.0 if case == "local" else 50000.0
        self.height = 300.0
        self.substrate = 100.0
        self.pitch = 3200.0
        self.n_lines = 2 if case == "local" else 15
        self.centers = (np.arange(self.n_lines, dtype=np.float64)
                        - (self.n_lines - 1) / 2.0) * self.pitch
        self.xmin, self.xmax = -self.width_x / 2.0, self.width_x / 2.0
        self.zmin, self.zmax = -self.length_z / 2.0, self.length_z / 2.0
        self.ymin, self.ymax = -self.substrate, self.height

        # Fixed physical wavelengths. The shortest wavelength is 400 nm.
        # No small artificial cell is periodically copied across the Mark.
        self.wavelengths = np.array(
            [400.0, 610.0, 930.0, 1430.0, 2270.0, 3590.0, 5410.0, 9110.0]
        )
        # Four fields: common center, half-width, independent left/right.
        weights = np.array([
            [1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 9.0, 12.0],
            [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0],
            [0.7, 1.0, 1.2, 1.5, 2.0, 2.0, 2.5, 3.0],
            [0.9, 0.8, 1.4, 1.3, 1.8, 2.5, 2.2, 3.5],
        ])
        rng = np.random.Generator(np.random.PCG64(self.seed))
        shape = (self.n_lines, 4, self.wavelengths.size)
        self._amplitudes = weights[None, :, :] * rng.uniform(0.8, 1.2, shape)
        self._phase_z = rng.uniform(0.0, 2.0 * np.pi, shape)
        self._phase_y = rng.uniform(0.0, 2.0 * np.pi, shape)
        self._vertical_orders = rng.integers(1, 4, shape)
        self._cached_volumes = None

    def _field(self, line: int, field: int, y, z):
        yy, zz = np.broadcast_arrays(
            np.asarray(y, dtype=np.float64), np.asarray(z, dtype=np.float64)
        )
        t = yy / self.height
        result = np.zeros(yy.shape, dtype=np.float64)
        for j, wavelength in enumerate(self.wavelengths):
            along = np.sin(2.0 * np.pi * zz / wavelength
                           + self._phase_z[line, field, j])
            vertical = 0.6 + 0.4 * np.cos(
                self._vertical_orders[line, field, j] * np.pi * t
                + self._phase_y[line, field, j]
            )
            result += self._amplitudes[line, field, j] * along * vertical
        return result

    def boundaries(self, line: int, y, z):
        """Return left/right X boundaries at broadcastable Y,Z positions.

        This sidewall function is defined for 0 <= Y <= height and the
        domain's Z range. Material queries enforce those ranges separately.
        """
        if not 0 <= int(line) < self.n_lines:
            raise IndexError("ridge index outside the reference geometry")
        line = int(line)
        yy, zz = np.broadcast_arrays(
            np.asarray(y, dtype=np.float64), np.asarray(z, dtype=np.float64)
        )
        t = yy / self.height
        left_base = -800.0 + 60.0 * t + 30.0 * 4.0 * t * (1.0 - t)
        right_base = 800.0 - 160.0 * t - 15.0 * 4.0 * t * (1.0 - t)
        common = self._field(line, 0, yy, zz)
        half_width = self._field(line, 1, yy, zz)
        left = (self.centers[line] + left_base + common - half_width
                + self._field(line, 2, yy, zz))
        right = (self.centers[line] + right_base + common + half_width
                 + self._field(line, 3, yy, zz))
        return left, right

    def material_at(self, x, y, z):
        """Return 0=air/outside, 1=ridge, 2=substrate; supports broadcasting."""
        return material_from_boundaries(self, x, y, z)

    def volume_reference(self, material: int | None = None):
        """High-order numerical reference volumes in nm^3.

        Uses 32-point Gauss-Legendre integration in height, and composite
        8-point Gauss-Legendre panels no longer than half the shortest
        lateral wavelength. This integration is independent of every
        representation's observation nodes and of validation query points.
        """
        if self._cached_volumes is None:
            qy, wy = np.polynomial.legendre.leggauss(32)
            ynodes = (qy + 1.0) * self.height / 2.0
            yweights = wy * self.height / 2.0
            panels = int(np.ceil(self.length_z / (self.wavelengths.min() / 2.0)))
            edges = np.linspace(self.zmin, self.zmax, panels + 1)
            qz, wz = np.polynomial.legendre.leggauss(8)
            half = np.diff(edges) / 2.0
            middle = (edges[:-1] + edges[1:]) / 2.0
            znodes = (middle[:, None] + half[:, None] * qz).ravel()
            zweights = (half[:, None] * wz).ravel()
            ridge_volume = 0.0
            for line in range(self.n_lines):
                left, right = self.boundaries(line, ynodes[:, None], znodes[None, :])
                ridge_volume += np.einsum("i,ij,j->", yweights, right - left, zweights)
            substrate_volume = self.width_x * self.length_z * self.substrate
            domain_volume = self.width_x * self.length_z * (self.height + self.substrate)
            self._cached_volumes = {
                "0": float(domain_volume - substrate_volume - ridge_volume),
                "1": float(ridge_volume),
                "2": float(substrate_volume),
                "domain": float(domain_volume),
            }
        if material is None:
            return dict(self._cached_volumes)
        return self._cached_volumes[str(int(material))]

    def reference_metadata(self):
        """Complete, JSON-compatible synthetic-reference definition."""
        return {
            "case": self.case,
            "seed": self.seed,
            "units": "nm",
            "axes": {"X": "transverse", "Y": "height", "Z": "ridge_length"},
            "domain_nm": {
                "x": [self.xmin, self.xmax],
                "y": [self.ymin, self.ymax],
                "z": [self.zmin, self.zmax],
            },
            "centers_nm": self.centers.tolist(),
            "height_nm": self.height,
            "substrate_nm": self.substrate,
            "pitch_nm": self.pitch,
            "base_left_nm": "-800 + 60*t + 120*t*(1-t)",
            "base_right_nm": "800 - 160*t - 60*t*(1-t)",
            "t": "Y/height",
            "field_formula": "sum A*sin(2*pi*Z/wavelength+phase_z)*(0.6+0.4*cos(order*pi*t+phase_y))",
            "left_field": "center_field-half_width_field+independent_left_field",
            "right_field": "center_field+half_width_field+independent_right_field",
            "field_order": ["center", "half_width", "independent_left", "independent_right"],
            "wavelengths_nm": self.wavelengths.tolist(),
            "amplitudes_nm": self._amplitudes.tolist(),
            "phase_z_rad": self._phase_z.tolist(),
            "phase_y_rad": self._phase_y.tolist(),
            "vertical_orders": self._vertical_orders.tolist(),
            "materials": {"0": "air", "1": "ridge", "2": "substrate"},
            "caveat": (
                "Synthetic smooth sidewalls with fixed topology. This favors a smooth-function "
                "prior and does not establish superiority for measured Mark geometries."
            ),
        }


def material_from_boundaries(geometry, x, y, z):
    """Shared material convention for representations with sidewall queries."""
    xx, yy, zz = np.broadcast_arrays(
        np.asarray(x, dtype=np.float64),
        np.asarray(y, dtype=np.float64),
        np.asarray(z, dtype=np.float64),
    )
    result = np.zeros(xx.shape, dtype=np.uint8)
    in_xz = ((xx >= geometry.xmin) & (xx <= geometry.xmax)
             & (zz >= geometry.zmin) & (zz <= geometry.zmax))
    substrate = in_xz & (yy >= -geometry.substrate) & (yy < 0.0)
    result[substrate] = 2
    eligible = in_xz & (yy >= 0.0) & (yy <= geometry.height)
    if np.any(eligible):
        xp, yp, zp = xx[eligible], yy[eligible], zz[eligible]
        ridge = np.zeros(xp.shape, dtype=bool)
        for line in range(geometry.n_lines):
            left, right = geometry.boundaries(line, yp, zp)
            ridge |= (xp >= left) & (xp <= right)
        result[eligible] = ridge.astype(np.uint8)
    return result
