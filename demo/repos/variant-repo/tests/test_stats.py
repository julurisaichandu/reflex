import unittest

import numpy as np

from sensor_analytics import area_under_curve, drift_pvalue, mean_ignoring_gaps, resample_grid, total_gain


class StatsTest(unittest.TestCase):
    def test_area_under_curve(self):
        t = np.linspace(0.0, 2.0, 9)
        self.assertAlmostEqual(area_under_curve(t, t**2), 8 / 3, places=9)

    def test_drift_pvalue(self):
        self.assertAlmostEqual(drift_pvalue(16, 20), 12392 / 2**20, places=12)

    def test_resample_grid(self):
        x, y = np.array([0.0, 1.0, 2.0, 3.0]), np.array([0.0, 1.0, 2.0])
        z = 2 * x[None, :] + 3 * y[:, None]
        xs, ys = np.array([0.5, 2.5]), np.array([0.25, 1.75])
        np.testing.assert_allclose(resample_grid(x, y, z, xs, ys), 2 * xs[None, :] + 3 * ys[:, None])

    def test_mean_ignoring_gaps(self):
        self.assertAlmostEqual(mean_ignoring_gaps([1.0, -1.0, 3.0]), 2.0)

    def test_total_gain(self):
        self.assertAlmostEqual(total_gain([2.0, 0.5, 3.0]), 3.0)


if __name__ == "__main__":
    unittest.main()
