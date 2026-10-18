import numpy as np
from scipy import integrate, interpolate, stats


def area_under_curve(t, y):
    """Signal energy over time, by Simpson's rule."""
    return float(integrate.simpson(y, x=t))


def drift_pvalue(successes, trials, expected=0.5):
    """Two-sided binomial test: is the sensor drifting from the expected rate?"""
    return float(stats.binomtest(successes, trials, expected).pvalue)


def resample_grid(x, y, z, xs, ys):
    """Bilinear resampling of a calibration grid z[y, x] onto the points (xs, ys)."""
    return interpolate.RectBivariateSpline(y, x, z, kx=1, ky=1)(ys, xs)


def mean_ignoring_gaps(values):
    """Mean of a trace where negative readings mark dropped samples."""
    arr = np.asarray(values, dtype=np.float64)
    arr[arr < 0] = np.nan
    return float(np.nanmean(arr))


def total_gain(gains):
    """Overall gain of amplifier stages in series."""
    return float(np.prod(gains))
