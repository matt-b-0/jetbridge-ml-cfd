import numpy as np
import pytest
from jetbridge_ml.report_evidence import hull_area_fraction


def test_area_fraction_is_physical_area_not_target_count():
    points=np.array([[.25,.5],[.75,.5],[.25,1.5],[.75,1.5]])
    assert hull_area_fraction(points,1.,2.)==pytest.approx(.25)
    # Adding a target inside the hull does not change physical support area.
    assert hull_area_fraction(np.vstack([points,[.5,1.]]),1.,2.)==pytest.approx(.25)


def test_hull_area_is_translation_invariant_for_sloped_floor_offset():
    points=np.array([[0.,0.],[2.,0.],[0.,4.],[2.,4.]])
    assert hull_area_fraction(points+[0.,1.343025],2.,4.)==pytest.approx(1.)
