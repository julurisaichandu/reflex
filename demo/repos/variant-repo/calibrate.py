import numpy as np

from sensor_analytics import resample_grid

x, y = np.array([0.0, 10.0, 20.0]), np.array([0.0, 5.0])
offsets = np.array([[0.0, 0.4, 0.9], [0.2, 0.7, 1.3]])
print(resample_grid(x, y, offsets, np.array([5.0, 15.0]), np.array([2.5])))
