# sensor-analytics

Shared analytics for sensor traces: signal energy, drift tests, calibration-grid resampling.
Python 3.11, pip. Someone bumped scipy to 1.16 for a security fix and the build has been red since.

    pip install -r requirements.txt
    python -m unittest discover -s tests

Keep scipy on 1.16.
