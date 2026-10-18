import numpy as np
from scipy import stats


def summarize(samples: list[float]) -> dict:
    xs = np.asarray(samples, dtype=float)
    ci = stats.t.interval(0.95, len(xs) - 1, loc=xs.mean(), scale=stats.sem(xs))
    return {"mean": round(float(xs.mean()), 3), "ci95": [round(float(c), 3) for c in ci]}


if __name__ == "__main__":
    print(summarize([9.8, 10.1, 10.0, 9.9, 10.3, 10.2]))
