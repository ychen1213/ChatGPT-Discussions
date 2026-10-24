"""Meaningful boundary reconstruction checks without analytic-reference access."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


# Loading the standalone worker must not import ah53.__init__ or its reference.
spec = importlib.util.spec_from_file_location("blind_reconstruction", Path(__file__).parents[1] / "src" / "ah53" / "voxel_reconstruction.py")
vr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vr)


def input_case(tmp_path, labels, spacing=2., origin=(-20., -8., 10.)):
    path = tmp_path / "input"
    path.mkdir()
    np.save(path / "labels.npy", labels)
    (path / "grid.json").write_text(json.dumps({"origin_xyz_nm": list(origin), "spacing_nm": spacing,
        "axis_order": "ZYX", "units": "nm", "materials": {"0": "air", "1": "stripe", "2": "substrate"}}))
    return path


def test_saved_models_recover_components_and_obey_coordinate_origin(tmp_path):
    labels = np.zeros((13, 18, 38), np.uint8)
    labels[:, :4] = 2
    labels[:, 4:12, 4:12] = 1
    labels[:, 4:14, 23:33] = 1
    source = input_case(tmp_path, labels)
    result = vr.reconstruct_from_voxels(source, tmp_path / "out")
    assert result["P"]["status"] == "ok"
    assert result["P"]["n_components"] == 2
    assert result["P"]["diagnostics"]["checked_slice_count"] == 13
    for kind in ("P", "T"):
        model = vr.load_reconstruction(tmp_path / "out", kind)
        rings = model.section(23., step_nm=.2)
        assert len(rings) == 2
        combined = np.concatenate(rings)
        assert combined[:, 0].min() == pytest.approx(-12., abs=.5)
        assert combined[:, 0].max() == pytest.approx(46., abs=.5)
        assert combined[:, 1].min() == pytest.approx(0., abs=.5)
        assert model.contains(np.array([[-4., 6., 23.], [35., 10., 23.], [15., 10., 23.], [0., -5., 23.]])).tolist() == [True, True, False, False]
        assert model.section(100.) == []


def test_hole_is_preserved_by_t_and_explicitly_rejected_by_p(tmp_path):
    labels = np.zeros((9, 20, 24), np.uint8)
    labels[:, 3:17, 3:21] = 1
    labels[:, 7:13, 8:16] = 0
    source = input_case(tmp_path, labels, spacing=1., origin=(0., 0., 0.))
    result = vr.reconstruct_from_voxels(source, tmp_path / "out")
    assert result["P"]["status"] == "unsupported_topology"
    assert "hole" in result["P"]["reason"]
    assert not (tmp_path / "out/P/coefficients.npz").exists()
    mesh = vr.load_reconstruction(tmp_path / "out", "T")
    assert len(mesh.section(4.5)) == 2
    assert mesh.contains(np.array([[5., 10., 4.5], [10., 10., 4.5]])).tolist() == [True, False]


def test_component_split_is_detected_on_unsampled_slice(tmp_path):
    labels = np.zeros((9, 15, 24), np.uint8)
    labels[:, 3:12, 3:21] = 1
    labels[2, :, 11:13] = 0
    source = input_case(tmp_path, labels, spacing=1., origin=(0., 0., 0.))
    result = vr.reconstruct_from_voxels(source, tmp_path / "out", kinds=("P",), z_step_nm=4.)
    assert result["P"]["status"] == "unsupported_topology"
    assert "slice 2" in result["P"]["reason"]
    assert "count changed" in result["P"]["reason"]


def test_binary_label_conversion_does_not_include_substrate(tmp_path):
    labels = np.zeros((5, 12, 20), np.uint8)
    labels[:, :7, :] = 2
    labels[:, 7:10, 8:12] = 1
    source = input_case(tmp_path, labels, spacing=1., origin=(0., 0., 0.))
    result = vr.reconstruct_from_voxels(source, tmp_path / "out", kinds="T")
    assert "P" not in result
    mesh = vr.load_reconstruction(tmp_path / "out", "T")
    assert mesh.vertices[:, 1].min() == pytest.approx(7.)
    assert mesh.vertices[:, 0].min() == pytest.approx(8.)
    assert mesh.vertices[:, 0].max() == pytest.approx(12.)
    triangles = mesh.vertices[mesh.faces].astype(float)
    volume = np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6.
    assert volume > 0
    assert volume == pytest.approx(mesh.metadata["signed_volume_nm3"])


def test_input_contract_rejects_hidden_recipe_metadata(tmp_path):
    source = input_case(tmp_path, np.zeros((3, 3, 3), np.uint8))
    grid = json.loads((source / "grid.json").read_text())
    grid["centers_nm"] = [0.]
    (source / "grid.json").write_text(json.dumps(grid))
    with pytest.raises(ValueError, match="exactly"):
        vr.reconstruct_from_voxels(source, tmp_path / "out")


def test_gaussian_is_applied_in_z_before_subsampling(tmp_path):
    labels = np.zeros((9, 16, 30), np.uint8)
    labels[:, 3:12, 5:20] = 1
    labels[4] = 0
    labels[4, 3:12, 8:23] = 1
    source = input_case(tmp_path, labels, spacing=1., origin=(0., 0., 0.))
    centres = []
    for sigma in (0., 1.):
        out = tmp_path / f"sigma_{sigma}"
        status = vr.reconstruct_from_voxels(source, out, kind="P", smoothing_nm=sigma)
        assert status["P"]["status"] == "ok"
        ring = vr.load_reconstruction(out).section(4.5, step_nm=.1)[0]
        centres.append(.5 * (ring[:, 0].min() + ring[:, 0].max()))
    assert centres[0] > centres[1] + 1.
    assert centres[1] > 12.5
