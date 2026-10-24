"""Meaningful geometry-metric checks independent of the AH53 generator."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import numpy as np
from ah53.evaluate import SegmentSet,stats,top_intersections


def test_distance_is_to_segments_not_vertices_and_pruning_is_exact():
    # The long segment has distant endpoints and midpoint: a nearest-vertex or
    # fixed-k midpoint shortcut would incorrectly return one of the tiny segments.
    a=np.vstack([[0,0],np.c_[np.arange(30)+8,np.full(30,3)]])
    b=np.vstack([[1000,0],np.c_[np.arange(30)+8.1,np.full(30,3)]])
    result=SegmentSet(a,b).distances(np.array([[10.,1.],[500.,2.]]))
    np.testing.assert_allclose(result,[1.,2.],atol=1e-12)


def test_arc_length_weighting_does_not_count_dense_vertices_as_area():
    result=stats(np.array([0.,10.]),np.array([99.,1.]))
    assert result["rms_nm"]==1.
    assert result["p95_nm"]==0.


def test_top_query_intersects_real_segments_at_common_physical_x():
    contour=np.array([[-2,0],[-2,1],[0,3],[2,1],[2,0],[-2,0]])
    np.testing.assert_allclose(top_intersections(contour,[-1.,0.,1.]),[2.,3.,2.])
