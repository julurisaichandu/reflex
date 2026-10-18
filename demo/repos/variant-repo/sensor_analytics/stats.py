import numpy as np
from scipy import integrate, interpolate, stats


def area_under_curve(t, y):
    """Signal energy over time, by Simpson's rule."""
    return float(integrate.simps(y, t))


def drift_pvalue(successes, trials, expected=0.5):
    """Two-sided binomial test: is the sensor drifting from the expected rate?"""
    return float(stats.binom_test(successes, trials, expected))


def resample_grid(x, y, z, xs, ys):
    """Bilinear resampling of a calibration grid z[y, x] onto the points (xs, ys)."""
    f = interpolate.interp2d(x, y, z, kind="linear")
    return f(xs, ys)


def mean_ignoring_gaps(values):
    """Mean of a trace where negative readings mark dropped samples."""
    arr = np.asarray(values, dtype=np.float_)
    arr[arr < 0] = np.NaN
    return float(np.nanmean(arr))


def total_gain(gains):
    """Overall gain of amplifier stages in series."""
    return float(np.product(gains))
