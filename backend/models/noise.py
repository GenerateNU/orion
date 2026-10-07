"""
Noise settings for the Kalman filter, kept in one place.

Two kinds of noise, and the balance between them decides how much the filter trusts physics vs sensors:
  - SENSOR_STDDEV (R): how noisy each sensor is. Bigger = trust that sensor less.
  - PROCESS_NOISE_STDDEV (Q): how far the real car can drift from CTRA's physics each tick. Bigger = trust physics less.

Values are standard deviations in the filter's units (meters, m/s, rad, rad/s, m/s^2), i.e. AFTER unit conversion.
Where they're used, they become matrices: R = diag(stddev^2), Q = diag(stddev^2).

TODO(noise-config ticket): make these configurable instead of hardcoded, and replace the placeholders with values
from sensor datasheets / calibration runs (e.g. the spread of readings while the car is parked).
"""

# Measurement noise per sensor -- feeds the UKF's R matrix in update().
# A property of each sensor, so it lives here instead of on every reading.
SENSOR_STDDEV: dict[str, float] = {
    "gps_location": 2.5,     # meters -- typical GPS accuracy is 1-5 m (placeholder)
    "vcu_speed": 0.2,        # m/s, about 0.45 mph (placeholder)
    "vcu_imu_gyro": 0.02,    # rad/s, about 1 deg/s -- parked readings showed ~0.7 deg/s offsets (placeholder)
    "vcu_imu_accel": 0.3,    # m/s^2, about 30 mg (placeholder)
}

# Process noise per state variable, per 10 ms tick -- feeds Q in the UKF's predict() and URTS.
# The UKF and URTS must use the same values. Assumes dt = 0.01 s; rescale if the tick rate changes.
PROCESS_NOISE_STDDEV: dict[str, float] = {
    "x": 0.01,          # meters
    "y": 0.01,          # meters
    "speed": 0.1,       # m/s
    "heading": 0.003,   # rad
    "turn_rate": 0.01,  # rad/s -- the driver moving the steering wheel
    "accel": 0.1,       # m/s^2 -- the driver moving the pedal
}
