"""Independent checks for hole retention, material interfaces and saved mesh audit."""
from pathlib import Path

import numpy as np

from ah53.voxel_reconstruction_metrics import (
    LabelGrid, clip_segments_above, mesh_topology, rasterize_section, section_pair_distance,
    section_topology, voxel_section_segments,
)


def square(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]], float)


def test_scanline_retains_holes_disconnected_components_and_cell_centers():
    rings = [square(0, 0, 5, 5), square(1, 1, 4, 4), square(6, 1, 8, 3)]
    mask, diagnostics = rasterize_section(rings, (5, 8), (0, 0), (1, 1))
    expected = np.zeros((5, 8), bool)
    expected[:, :5] = True
    expected[1:4, 1:4] = False
    expected[1:3, 6:8] = True
    np.testing.assert_array_equal(mask, expected)
    assert diagnostics["odd_intersection_rows"] == 0
    report = section_topology(rings)
    assert report["hole_count_2d"] == 1
    assert report["material_components_2d"] == 2
    assert report["signed_material_area_nm2"] == 20


def test_voxel_boundary_uses_labels_and_does_not_fill_internal_hole():
    labels = np.zeros((2, 5, 5), np.uint8)
    labels[:, 0] = 2
    labels[:, 1:4, 1:4] = 1
    labels[:, 2, 2] = 0
    grid = LabelGrid(labels, np.zeros(3), np.ones(3), Path("unused"), {})
    full_a, full_b = voxel_section_segments(grid, .5, free_only=False)
    free_a, free_b = voxel_section_segments(grid, .5, free_only=True)
    assert len(full_a) == 16  # 12 external unit edges + four edges of the hole.
    assert len(free_a) == 13  # Three material-1/material-2 bottom edges removed.
    assert np.linalg.norm(full_b - full_a, axis=1).sum() == 16
    assert not np.any((free_a[:, 1] == 1) & (free_b[:, 1] == 1))


def test_distance_reports_both_directions_without_vertex_density_bias():
    first = (np.array([[0., 0.]]), np.array([[10., 0.]]))
    second = (np.array([[0., 2.], [1., 2.], [3., 2.]]),
              np.array([[1., 2.], [3., 2.], [10., 2.]]))
    result, _ = section_pair_distance(first, second, .7)
    assert result["all"]["rms_nm"] == 2
    assert result["all"]["max_nm"] == 2


def test_saved_mesh_audit_detects_missing_face_and_reversed_winding():
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    report = mesh_topology(vertices, faces)
    assert report["closed_edge_manifold"]
    assert report["connected_components"] == 1
    assert report["euler_characteristic"] == 2
    assert report["inconsistently_oriented_two_face_edges"] == 0
    assert abs(report["signed_volume_nm3"] - 1 / 6) < 1e-12
    assert mesh_topology(vertices, faces[:-1])["boundary_edges"] == 3
    flipped = faces.copy(); flipped[0] = flipped[0, ::-1]
    assert mesh_topology(vertices, flipped)["inconsistently_oriented_two_face_edges"] == 3


def test_self_crossing_ring_is_reported_not_silently_repaired():
    bowtie = np.array([[0., 0.], [2., 2.], [0., 2.], [2., 0.], [0., 0.]])
    assert not section_topology([bowtie])["all_simple_valid"]
    overlap = section_topology([square(0, 0, 2, 2), square(1, 1, 3, 3)])
    assert overlap["ring_boundary_intersections"] == 1
    assert not overlap["all_simple_valid"]


def test_common_height_band_clips_crossing_segments_and_drops_low_bottom():
    a = np.array([[0., -1.], [10., 10.], [20., -.1], [30., 5.]])
    b = np.array([[10., 9.], [20., 0.], [30., .1], [40., 5.]])
    aa, bb = clip_segments_above((a, b), 2.)
    np.testing.assert_allclose(aa, [[3., 2.], [10., 10.], [30., 5.]])
    np.testing.assert_allclose(bb, [[10., 9.], [18., 2.], [40., 5.]])
