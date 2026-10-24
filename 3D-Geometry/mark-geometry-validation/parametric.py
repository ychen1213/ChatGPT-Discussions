"""Tensor-product cubic sidewall interpolation from shared observation nodes.

The representation retains knots and coefficients, not the reference object
or its analytic functions. Payload figures count stored numeric model data,
not Python object overhead, transient fitting memory, or compressed file size.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.interpolate import RectBivariateSpline

from reference import material_from_boundaries


class ParametricRepresentation:
    def __init__(self, ref, dy: float = 25.0, dz: float = 100.0):
        if dy <= 0.0 or dz <= 0.0:
            raise ValueError("dy and dz must be positive")
        for name in ("width_x", "length_z", "height", "substrate", "pitch",
                     "n_lines", "xmin", "xmax", "zmin", "zmax", "ymin", "ymax"):
            setattr(self, name, getattr(ref, name))
        self.centers = np.asarray(ref.centers, dtype=np.float64).copy()
        self.dy_requested, self.dz_requested = float(dy), float(dz)
        ny = max(4, int(np.ceil(self.height / dy)) + 1)
        nz = max(4, int(np.ceil(self.length_z / dz)) + 1)
        self.y_nodes = np.linspace(0.0, self.height, ny)
        self.z_nodes = np.linspace(self.zmin, self.zmax, nz)
        self.dy_actual = float(self.y_nodes[1] - self.y_nodes[0])
        self.dz_actual = float(self.z_nodes[1] - self.z_nodes[0])
        self._metadata_values = np.array([
            self.xmin, self.xmax, self.zmin, self.zmax, self.height,
            self.substrate, self.pitch, self.dy_requested, self.dz_requested,
        ], dtype=np.float64)
        self._grid_shape_and_degrees = np.array([ny, nz, 3, 3], dtype=np.int64)
        self.splines = []
        for line in range(self.n_lines):
            left, right = ref.boundaries(line, self.y_nodes[:, None], self.z_nodes[None, :])
            self.splines.append((
                RectBivariateSpline(self.y_nodes, self.z_nodes, left, kx=3, ky=3, s=0),
                RectBivariateSpline(self.y_nodes, self.z_nodes, right, kx=3, ky=3, s=0),
            ))

    def boundaries(self, line: int, y, z):
        if not 0 <= int(line) < self.n_lines:
            raise IndexError("ridge index outside the parametric geometry")
        yy, zz = np.broadcast_arrays(
            np.asarray(y, dtype=np.float64), np.asarray(z, dtype=np.float64)
        )
        left, right = self.splines[int(line)]
        return (
            left.ev(yy.ravel(), zz.ravel()).reshape(yy.shape),
            right.ev(yy.ravel(), zz.ravel()).reshape(yy.shape),
        )

    def material_at(self, x, y, z):
        return material_from_boundaries(self, x, y, z)

    @property
    def sample_grid_shape(self):
        return (self.y_nodes.size, self.z_nodes.size)

    @property
    def control_point_count(self):
        return int(sum(s.get_coeffs().size for pair in self.splines for s in pair))

    @property
    def knot_value_count(self):
        return int(sum(sum(a.size for a in s.get_knots())
                       for pair in self.splines for s in pair))

    @property
    def payload_bytes(self):
        # Knots are actually retained separately by each FITPACK spline.
        spline_bytes = sum(
            s.get_coeffs().nbytes + sum(a.nbytes for a in s.get_knots())
            for pair in self.splines for s in pair
        )
        metadata_bytes = sum(a.nbytes for a in (
            self.centers, self.y_nodes, self.z_nodes,
            self._metadata_values, self._grid_shape_and_degrees,
        ))
        return int(spline_bytes + metadata_bytes)

    @property
    def surface_counts(self):
        return {
            "sidewall_surfaces": 2 * self.n_lines,
            "sample_grid_shape": list(self.sample_grid_shape),
            "input_sidewall_values": 2 * self.n_lines * int(np.prod(self.sample_grid_shape)),
            "control_coefficients": self.control_point_count,
            "stored_knot_values": self.knot_value_count,
        }

    def metadata(self):
        return {
            "representation": "tensor_product_cubic_spline_sidewalls",
            "units": "nm",
            "dy_requested_nm": self.dy_requested,
            "dz_requested_nm": self.dz_requested,
            "dy_actual_nm": self.dy_actual,
            "dz_actual_nm": self.dz_actual,
            "counts": self.surface_counts,
            "payload_bytes": self.payload_bytes,
            "payload_scope": "stored numeric knots, coefficients, observation axes, centers and geometry metadata; excludes runtime objects and temporary fitting arrays",
            "source": "interpolation of reference boundary observations; analytic truth is not retained",
            "caveat": "smooth synthetic shape and fixed topology favor the interpolation prior; validate with measured sidewalls before selecting a production representation",
        }

    def volume(self, material: int | None = None):
        ridge_volume = sum(
            right.integral(0.0, self.height, self.zmin, self.zmax)
            - left.integral(0.0, self.height, self.zmin, self.zmax)
            for left, right in self.splines
        )
        substrate_volume = self.width_x * self.length_z * self.substrate
        domain_volume = self.width_x * self.length_z * (self.height + self.substrate)
        result = {
            "0": float(domain_volume - substrate_volume - ridge_volume),
            "1": float(ridge_volume),
            "2": float(substrate_volume),
            "domain": float(domain_volume),
        }
        return result if material is None else result[str(int(material))]

    def save(self, path):
        """Save independent numeric spline data without pickled Python objects."""
        arrays = {
            "centers_nm": self.centers,
            "observation_y_nm": self.y_nodes,
            "observation_z_nm": self.z_nodes,
            "geometry_metadata": self._metadata_values,
            "grid_shape_and_degrees": self._grid_shape_and_degrees,
            "metadata_json": np.array(json.dumps(self.metadata(), ensure_ascii=False)),
        }
        for line, pair in enumerate(self.splines):
            for side_name, spline in zip(("left", "right"), pair):
                ty, tz = spline.get_knots()
                prefix = f"line_{line:03d}_{side_name}"
                arrays[f"{prefix}_knots_y"] = ty
                arrays[f"{prefix}_knots_z"] = tz
                arrays[f"{prefix}_coefficients"] = spline.get_coeffs()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **arrays)
        return str(path if path.suffix == ".npz" else Path(str(path) + ".npz"))
