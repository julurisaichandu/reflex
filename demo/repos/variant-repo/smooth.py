import numpy as np
from scipy.signal import savgol_filter


def smooth(samples: list[float], window: int = 5) -> list[float]:
    return [round(float(v), 3) for v in savgol_filter(np.asarray(samples, dtype=float), window, 2)]


if __name__ == "__main__":
    print(smooth([1.0, 2.1, 2.9, 4.2, 5.0, 5.8, 7.1, 8.0]))
