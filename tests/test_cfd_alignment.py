"""Check coordinate alignment before interpreting CFD-to-sensor deltas."""
import numpy as np
import pytest

from jetbridge_ml.cfd_interface.plot_comparison import align_samples


def test_sample_alignment_uses_xyz_not_row_order():
    expected = np.array([[.35, 2.48, 3.05], [1.04, .45, 3.05]])
    sampled = np.array([[1.04, .45, 3.05, 0, 0, -.2],
                        [.35, 2.48, 3.05, 0, 0, -.1]])
    result = align_samples(expected, sampled)
    np.testing.assert_allclose(result[:, :3], expected)
    np.testing.assert_allclose(np.linalg.norm(result[:, 3:], axis=1), [.1, .2])


def test_sample_alignment_rejects_shifted_plane():
    expected = np.array([[.35, 2.48, 3.05]])
    with pytest.raises(ValueError, match="match"):
        align_samples(expected, [[.35, 2.48, 3.048, 0, 0, -.1]])


def test_sample_alignment_rejects_duplicate_and_nonfinite_samples():
    expected = np.array([[.35, 2.48, 3.05], [1.04, .45, 3.05]])
    repeated = np.array([[.35, 2.48, 3.05, 0, 0, -.1]] * 2)
    with pytest.raises(ValueError, match="match"):
        align_samples(expected, repeated)
    with pytest.raises(ValueError, match="finite"):
        align_samples(expected[:1], [[.35, 2.48, 3.05, 0, 0, np.nan]])
