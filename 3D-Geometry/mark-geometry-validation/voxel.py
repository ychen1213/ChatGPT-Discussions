"""Dense, cell-centred uint8 material labels for the geometry experiment.

Coordinates are nm. Array order is [Y, Z, X]. Sidewall coordinates are
recovered from the actual label transitions, never by rounding the source
geometry. There is no post-extraction surface smoothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class VoxelRepresentation:
    def __init__(self, ref, h=10.0):
        if h <= 0:
            raise ValueError("h must be positive")
        for name in ("width_x", "length_z", "height", "substrate",
                     "xmin", "xmax", "zmin", "zmax", "n_lines"):
            setattr(self, name, getattr(ref, name))
        self.centers = np.asarray(ref.centers, np.float64).copy()
        self.ymin, self.ymax = -self.substrate, self.height
        self.h_requested = float(h)
        self.nx = int(np.ceil(self.width_x / h))
        self.ny = int(np.ceil((self.height + self.substrate) / h))
        self.nz = int(np.ceil(self.length_z / h))
        self.hx = self.width_x / self.nx
        self.hy = (self.height + self.substrate) / self.ny
        self.hz = self.length_z / self.nz
        n_cells = self.nx * self.ny * self.nz
        if n_cells > 1_200_000_000:
            raise MemoryError("This demonstration limits dense labels to 1.2 GB; increase h.")
        self.labels = np.empty((self.ny, self.nz, self.nx), dtype=np.uint8)
        x = self.xmin + (np.arange(self.nx) + 0.5) * self.hx
        z = self.zmin + (np.arange(self.nz) + 0.5) * self.hz
        zi = np.arange(self.nz)
        self._material_counts = np.zeros(3, dtype=np.int64)
        for iy in range(self.ny):
            y = self.ymin + (iy + 0.5) * self.hy
            target = self.labels[iy]
            if y < 0:
                target.fill(2)
            else:
                # Signed interval events avoid an X*Z temporary per ridge.
                changes = np.zeros((self.nz, self.nx + 1), dtype=np.int16)
                previous_right = None
                for line in range(self.n_lines):
                    left, right = ref.boundaries(line, y, z)
                    if np.any(right <= left):
                        raise ValueError("A source ridge has non-positive width")
                    if previous_right is not None and np.any(left <= previous_right):
                        raise ValueError("This experiment assumes separated ordered ridges")
                    previous_right = right
                    start = np.searchsorted(x, left, side="left")
                    stop = np.searchsorted(x, right, side="right")
                    np.add.at(changes, (zi, start), 1)
                    np.add.at(changes, (zi, stop), -1)
                active = changes[:, :-1]
                np.cumsum(active, axis=1, dtype=np.int16, out=active)
                target[:] = active > 0
                del active, changes
            # Count the generated array, not analytic interval widths.
            ridge = int(np.count_nonzero(target == 1))
            substrate = int(np.count_nonzero(target == 2))
            self._material_counts += (target.size - ridge - substrate, ridge, substrate)
        self._geometry_values = np.array([
            self.xmin, self.xmax, self.ymin, self.ymax, self.zmin, self.zmax,
            self.hx, self.hy, self.hz, self.h_requested,
        ], dtype=np.float64)
        self._grid_shape = np.array(self.labels.shape, dtype=np.int64)

    @property
    def payload_bytes(self):
        return int(sum(a.nbytes for a in (
            self.labels, self.centers, self._geometry_values,
            self._grid_shape, self._material_counts,
        )))

    @property
    def surface_counts(self):
        return {"array_shape_yzx": list(self.labels.shape),
                "voxel_count": int(self.labels.size), "dtype": str(self.labels.dtype)}

    def boundaries_all(self, y, z):
        """Return [line, side, query] X positions from real label intervals.

        Rows are deduplicated only inside this call. Its temporary interval
        table is not a retained alternative representation.
        """
        yy, zz = np.broadcast_arrays(np.asarray(y, float), np.asarray(z, float))
        if np.any((yy < 0) | (yy > self.height)):
            raise ValueError("Sidewall queries must be within ridge height")
        iy = np.clip(np.floor((yy.ravel() - self.ymin) / self.hy).astype(int),
                     0, self.ny - 1)
        iz = np.clip(np.floor((zz.ravel() - self.zmin) / self.hz).astype(int),
                     0, self.nz - 1)
        rows, inverse = np.unique(iy * self.nz + iz, return_inverse=True)
        endpoints = np.empty((len(rows), self.n_lines, 2), dtype=np.float64)
        for k, row in enumerate(rows):
            a, b = divmod(int(row), self.nz)
            padded = np.zeros(self.nx + 2, dtype=np.int8)
            padded[1:-1] = self.labels[a, b] == 1
            delta = np.diff(padded)
            starts = np.flatnonzero(delta == 1)
            stops = np.flatnonzero(delta == -1)
            if len(starts) != self.n_lines or len(stops) != self.n_lines:
                raise ValueError("Voxel row lost/merged a ridge; cannot silently match intervals")
            endpoints[k, :, 0] = self.xmin + starts * self.hx
            endpoints[k, :, 1] = self.xmin + stops * self.hx
        answer = endpoints[inverse].transpose(1, 2, 0)
        return answer.reshape((self.n_lines, 2) + yy.shape)

    def boundaries(self, line, y, z):
        result = self.boundaries_all(y, z)[int(line)]
        return result[0], result[1]

    def material_at(self, x, y, z):
        xx, yy, zz = np.broadcast_arrays(np.asarray(x, float),
                                         np.asarray(y, float), np.asarray(z, float))
        result = np.zeros(xx.shape, dtype=np.uint8)
        inside = ((xx >= self.xmin) & (xx <= self.xmax) &
                  (yy >= self.ymin) & (yy <= self.ymax) &
                  (zz >= self.zmin) & (zz <= self.zmax))
        if np.any(inside):
            ix = np.clip(np.floor((xx[inside] - self.xmin) / self.hx).astype(int),
                         0, self.nx - 1)
            iy = np.clip(np.floor((yy[inside] - self.ymin) / self.hy).astype(int),
                         0, self.ny - 1)
            iz = np.clip(np.floor((zz[inside] - self.zmin) / self.hz).astype(int),
                         0, self.nz - 1)
            result[inside] = self.labels[iy, iz, ix]
        return result

    def volume(self, material=None):
        cell_volume = self.hx * self.hy * self.hz
        result = {str(i): float(n * cell_volume)
                  for i, n in enumerate(self._material_counts)}
        result["domain"] = float(self.labels.size * cell_volume)
        return result if material is None else result[str(int(material))]

    def save(self, path):
        path = Path(path)
        np.savez(path, labels=self.labels, centers=self.centers,
                 geometry_values=self._geometry_values, grid_shape=self._grid_shape,
                 material_counts=self._material_counts,
                 metadata_json=np.array(json.dumps({
                     "unit": "nm", "order": "YZX", "sample": "cell_center",
                     "labels": {"0": "air", "1": "ridge", "2": "substrate"},
                 })))
        return str(path)
