#ifndef AMH_IMU_H
#define AMH_IMU_H

struct Orientation {
  float pitch;
  float roll;
};

// Powers and configures the onboard LSM6DS3TR-C. Returns true on success.
bool imu_init();

// Reads one sample and advances both the complementary filter and the
// gyro-only reference integration. dt_s is the elapsed time in seconds.
void imu_update(float dt_s);

Orientation imu_orientation();

// Variance of the (gyro-only minus accelerometer) pitch residual accumulated
// since the previous call. Resets the accumulator.
float imu_drift_variance_reset();

#endif // AMH_IMU_H
