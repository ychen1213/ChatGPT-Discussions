"""Shared multi-material triangular interfaces for the Mark geometry experiment.

All coordinates are in nm.  A face normal points from material_pairs[:, 0]
to material_pairs[:, 1].  Labels: 0 air, 1 ridge, 2 substrate.  The ridge /
substrate contact is stored once, and is used with reverse orientation when
considering the substrate boundary.  This is a shape representation, not an
electromagnetic calculation mesh.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class ExplicitSurfaceRepresentation:
    """Piecewise planar sidewalls with closed, shared material interfaces."""

    def __init__(self, ref, dy=25.0, dz=100.0):
        if dy <= 0 or dz <= 0:
            raise ValueError("dy and dz must be positive")
        for name in ("width_x", "length_z", "height", "substrate", "xmin",
                     "xmax", "zmin", "zmax"):
            setattr(self, name, float(getattr(ref, name)))
        self.centers = np.asarray(ref.centers, dtype=np.float64).copy()
        self.n_lines = len(self.centers)
        self.dy_requested, self.dz_requested = float(dy), float(dz)
        self.y_nodes = np.linspace(0.0, self.height,
                                   int(np.ceil(self.height / dy)) + 1)
        self.z_nodes = np.linspace(self.zmin, self.zmax,
                                   int(np.ceil(self.length_z / dz)) + 1)
        ny, nz = len(self.y_nodes), len(self.z_nodes)
        yy, zz = np.meshgrid(self.y_nodes, self.z_nodes, indexing="ij")
        patches, face_parts, pair_parts = [], [], []
        total_vertices = 0
        side_ids = np.empty((self.n_lines, 2, ny, nz), dtype=np.uint32)

        def add_patch(points, pair, reverse=False):
            """Use the same lower-left to upper-right diagonal in each cell."""
            nonlocal total_vertices
            points = np.asarray(points, dtype=np.float64)
            nr, nc, _ = points.shape
            ids = np.arange(total_vertices, total_vertices + nr * nc,
                            dtype=np.uint32).reshape(nr, nc)
            a, b = ids[:-1, :-1].ravel(), ids[1:, :-1].ravel()
            c, d = ids[1:, 1:].ravel(), ids[:-1, 1:].ravel()
            faces = np.concatenate((np.column_stack((a, b, c)),
                                    np.column_stack((a, c, d))))
            if reverse:
                faces = faces[:, [0, 2, 1]]
            patches.append(points.reshape(-1, 3))
            face_parts.append(faces)
            pair_parts.append(np.tile(np.asarray(pair, np.uint8),
                                      (len(faces), 1)))
            total_vertices += nr * nc
            return ids

        # Values at the observed knots are used only during construction.
        # The original reference object is deliberately not retained.
        bottom_left, bottom_right = [], []
        previous_right = None
        for line in range(self.n_lines):
            left, right = ref.boundaries(line, yy, zz)
            left = np.broadcast_to(np.asarray(left, dtype=float), yy.shape)
            right = np.broadcast_to(np.asarray(right, dtype=float), yy.shape)
            if not np.all(left < right):
                raise ValueError("A ridge must have strictly positive width")
            if np.any(left <= self.xmin) or np.any(right >= self.xmax):
                raise ValueError("This prototype requires uncropped ridges in X")
            if previous_right is not None and np.any(previous_right >= left):
                raise ValueError("Ridges must remain separate and ordered in X")
            previous_right = right
            lp = np.stack((left, yy, zz), axis=-1)
            rp = np.stack((right, yy, zz), axis=-1)
            side_ids[line, 0] = add_patch(lp, (1, 0), reverse=True)
            side_ids[line, 1] = add_patch(rp, (1, 0))
            add_patch(np.stack((lp[-1], rp[-1])), (1, 0), reverse=True)
            # The bottom contact normal points out of ridge into substrate.
            add_patch(np.stack((lp[0], rp[0])), (1, 2))
            add_patch(np.stack((lp[:, 0], rp[:, 0]), axis=1), (1, 0))
            add_patch(np.stack((lp[:, -1], rp[:, -1]), axis=1),
                      (1, 0), reverse=True)
            bottom_left.append(left[0].copy())
            bottom_right.append(right[0].copy())

        # Complete the substrate top with gap ribbons, sharing all contact edges.
        gap_left = [np.full(nz, self.xmin)] + bottom_right
        gap_right = bottom_left + [np.full(nz, self.xmax)]
        for left, right in zip(gap_left, gap_right):
            if not np.all(left < right):
                raise ValueError("Ridges must remain separate and ordered in X")
            lp = np.column_stack((left, np.zeros(nz), self.z_nodes))
            rp = np.column_stack((right, np.zeros(nz), self.z_nodes))
            add_patch(np.stack((lp, rp)), (2, 0), reverse=True)

        # Perimeter vertices must match the top contact/gap tessellation.
        front_x = [self.xmin]
        back_x = [self.xmin]
        for left, right in zip(bottom_left, bottom_right):
            front_x.extend((float(left[0]), float(right[0])))
            back_x.extend((float(left[-1]), float(right[-1])))
        front_x.append(self.xmax)
        back_x.append(self.xmax)
        ring = [(x, 0.0, self.zmin) for x in front_x]
        ring += [(self.xmax, 0.0, z) for z in self.z_nodes[1:]]
        ring += [(x, 0.0, self.zmax) for x in back_x[-2::-1]]
        ring += [(self.xmin, 0.0, z) for z in self.z_nodes[-2:0:-1]]
        ring = np.asarray(ring, dtype=np.float64)
        bottom_ring = ring.copy()
        bottom_ring[:, 1] = -self.substrate
        count = len(ring)
        # Two rows and a repeated endpoint close the vertical perimeter strip.
        wall = np.stack((np.vstack((bottom_ring, bottom_ring[:1])),
                         np.vstack((ring, ring[:1]))))
        add_patch(wall, (2, 0))

        # A planar fan closes the substrate bottom.  Long triangles here are
        # intentional: a flat surface needs no uniform fine subdivision.
        center = np.array([[(self.xmin + self.xmax) / 2,
                            -self.substrate,
                            (self.zmin + self.zmax) / 2]])
        bottom_points = np.vstack((center, bottom_ring))
        base = total_vertices
        idx = np.arange(count, dtype=np.uint32)
        bottom_faces = np.column_stack((np.full(count, base, np.uint32),
                                        base + 1 + idx,
                                        base + 1 + (idx + 1) % count))
        patches.append(bottom_points)
        face_parts.append(bottom_faces)
        pair_parts.append(np.tile(np.array((2, 0), np.uint8), (count, 1)))

        # Exact coordinate deduplication provides shared interfaces/vertices.
        # No geometric rounding, smoothing, or topology repair is performed.
        vertices, inverse = np.unique(np.concatenate(patches), axis=0,
                                      return_inverse=True)
        self.vertices = np.ascontiguousarray(vertices, dtype=np.float64)
        self.faces = np.ascontiguousarray(
            inverse[np.concatenate(face_parts)].astype(np.uint32))
        self.material_pairs = np.ascontiguousarray(np.concatenate(pair_parts))
        self.side_vertex_ids = inverse[side_ids].astype(np.uint32)
        self.metadata = {
            "representation": "shared_explicit_triangular_interfaces",
            "version": 1, "unit": "nm", "width_x": self.width_x,
            "length_z": self.length_z, "height": self.height,
            "substrate": self.substrate, "xmin": self.xmin,
            "xmax": self.xmax, "zmin": self.zmin, "zmax": self.zmax,
            "n_lines": self.n_lines, "dy_requested": self.dy_requested,
            "dz_requested": self.dz_requested,
            "normal_convention": "material_pairs_first_to_second",
            "labels": {"0": "air", "1": "ridge", "2": "substrate"},
            "query": "piecewise_linear_interpolation_on_saved_sidewall_triangles",
            "domain_assumption": "ordered_separate_single_interval_ridges",
        }

    def boundaries(self, line, y, z):
        """Evaluate the actual planar triangles at arbitrary Y,Z positions.

        Values outside the sidewall coordinate range are clamped to its edge.
        material_at separately applies the finite three-dimensional domain.
        """
        y, z = np.broadcast_arrays(np.asarray(y, float), np.asarray(z, float))
        yc = np.clip(y, self.y_nodes[0], self.y_nodes[-1])
        zc = np.clip(z, self.z_nodes[0], self.z_nodes[-1])
        iy = np.clip(np.searchsorted(self.y_nodes, yc, side="right") - 1,
                     0, len(self.y_nodes) - 2)
        iz = np.clip(np.searchsorted(self.z_nodes, zc, side="right") - 1,
                     0, len(self.z_nodes) - 2)
        u = (yc - self.y_nodes[iy]) / (self.y_nodes[iy + 1] - self.y_nodes[iy])
        v = (zc - self.z_nodes[iz]) / (self.z_nodes[iz + 1] - self.z_nodes[iz])
        result = []
        for side in range(2):
            ids = self.side_vertex_ids[int(line), side]
            f00 = self.vertices[ids[iy, iz], 0]
            f10 = self.vertices[ids[iy + 1, iz], 0]
            f11 = self.vertices[ids[iy + 1, iz + 1], 0]
            f01 = self.vertices[ids[iy, iz + 1], 0]
            result.append(np.where(
                u >= v,
                (1 - u) * f00 + (u - v) * f10 + v * f11,
                (1 - v) * f00 + u * f11 + (v - u) * f01))
        return tuple(result)

    def material_at(self, x, y, z):
        x, y, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float),
                                      np.asarray(z, float))
        result = np.zeros(x.shape, dtype=np.uint8)
        lateral = ((x >= self.xmin) & (x <= self.xmax) &
                   (z >= self.zmin) & (z <= self.zmax))
        result[lateral & (y >= -self.substrate) & (y < 0)] = 2
        candidate = lateral & (y >= 0) & (y <= self.height)
        for line in range(self.n_lines):
            left, right = self.boundaries(line, y, z)
            result[candidate & (x >= left) & (x <= right)] = 1
        return result

    @property
    def payload_bytes(self):
        """Array payload plus serialized metadata; excludes Python overhead."""
        arrays = (self.vertices, self.faces, self.material_pairs,
                  self.side_vertex_ids, self.y_nodes, self.z_nodes, self.centers)
        return int(sum(a.nbytes for a in arrays) +
                   len(json.dumps(self.metadata, sort_keys=True).encode("utf-8")))

    @property
    def surface_counts(self):
        return {"vertices": len(self.vertices), "triangles": len(self.faces),
                "sidewall_y_nodes": len(self.y_nodes),
                "sidewall_z_nodes": len(self.z_nodes),
                "shared_ridge_substrate_triangles": int(np.sum(
                    (self.material_pairs[:, 0] == 1) &
                    (self.material_pairs[:, 1] == 2)))}

    def material_volumes_nm3(self):
        volumes = {1: 0.0, 2: 0.0}
        for start in range(0, len(self.faces), 100_000):
            face = self.faces[start:start + 100_000]
            v = self.vertices[face]
            signed = np.einsum("ij,ij->i", v[:, 0],
                               np.cross(v[:, 1], v[:, 2])) / 6.0
            pair = self.material_pairs[start:start + 100_000]
            for label in volumes:
                volumes[label] += float(np.sum(signed[pair[:, 0] == label]) -
                                        np.sum(signed[pair[:, 1] == label]))
        return volumes

    def check_geometry(self, local=True):
        report = {"finite_vertices": bool(np.isfinite(self.vertices).all()),
                  "valid_face_indices": bool(len(self.faces) and
                                              self.faces.max() < len(self.vertices)),
                  "nonzero_faces": True, "topology_checked": bool(local),
                  "material_volumes_nm3": self.material_volumes_nm3()}
        min_area = float("inf")
        for start in range(0, len(self.faces), 100_000):
            v = self.vertices[self.faces[start:start + 100_000]]
            area2 = np.linalg.norm(np.cross(v[:, 1] - v[:, 0],
                                            v[:, 2] - v[:, 0]), axis=1)
            min_area = min(min_area, float(area2.min()))
            report["nonzero_faces"] &= bool(np.all(area2 > 1e-12))
        report["min_triangle_area_nm2"] = min_area / 2
        if local:
            for label in (1, 2):
                selected = np.any(self.material_pairs == label, axis=1)
                face = self.faces[selected].copy()
                pair = self.material_pairs[selected]
                reverse = pair[:, 1] == label
                face[reverse] = face[reverse][:, [0, 2, 1]]
                edges = np.concatenate((face[:, [0, 1]], face[:, [1, 2]],
                                        face[:, [2, 0]]))
                lo, hi = edges.min(axis=1), edges.max(axis=1)
                keys = (lo.astype(np.uint64) << np.uint64(32)) | hi.astype(np.uint64)
                _, inverse, counts = np.unique(keys, return_inverse=True,
                                                return_counts=True)
                direction = np.where(edges[:, 0] < edges[:, 1], 1, -1)
                balance = np.bincount(inverse, weights=direction)
                report[f"material_{label}"] = {
                    "edge_closed": bool(np.all(counts == 2)),
                    "consistent_orientation": bool(np.all(balance == 0)),
                    "non_two_sided_edges": int(np.sum(counts != 2)),
                }
        return report

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, vertices=self.vertices, faces=self.faces,
                 material_pairs=self.material_pairs,
                 side_vertex_ids=self.side_vertex_ids, y_nodes=self.y_nodes,
                 z_nodes=self.z_nodes, centers=self.centers,
                 metadata=np.asarray(json.dumps(self.metadata, sort_keys=True)))
        return str(path)

    @classmethod
    def load(cls, path):
        obj = cls.__new__(cls)
        with np.load(path, allow_pickle=False) as saved:
            for name in ("vertices", "faces", "material_pairs", "side_vertex_ids",
                         "y_nodes", "z_nodes", "centers"):
                setattr(obj, name, saved[name].copy())
            obj.metadata = json.loads(str(saved["metadata"]))
        for name in ("width_x", "length_z", "height", "substrate", "xmin", "xmax",
                     "zmin", "zmax", "n_lines", "dy_requested", "dz_requested"):
            setattr(obj, name, obj.metadata[name])
        return obj
