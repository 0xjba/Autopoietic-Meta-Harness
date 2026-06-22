#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "LSM6DS3.h"
#include "imu.h"
#include "config.h"

static LSM6DS3 imu(I2C_MODE, 0x6A);

static float pitch = 0.0f, roll = 0.0f;   // complementary filter output
static float gyroPitch = 0.0f;            // gyro-only reference

static unsigned long resCount = 0;        // Welford state over the residual
static float resMean = 0.0f, resM2 = 0.0f;

static const float RAD2DEG = 57.29578f;

bool imu_init() {
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);
  digitalWrite(PIN_LSM6DS3TR_C_POWER, HIGH);
  delay(20);
  return imu.begin() == 0;
}

void imu_update(float dt_s) {
  float ax = imu.readFloatAccelX();
  float ay = imu.readFloatAccelY();
  float az = imu.readFloatAccelZ();
  float gx = imu.readFloatGyroX();   // deg/s
  float gy = imu.readFloatGyroY();

  float accelPitch = atan2f(-ax, sqrtf(ay * ay + az * az)) * RAD2DEG;
  float accelRoll  = atan2f(ay, az) * RAD2DEG;

  pitch = FILTER_ALPHA * (pitch + gx * dt_s) + (1.0f - FILTER_ALPHA) * accelPitch;
  roll  = FILTER_ALPHA * (roll  + gy * dt_s) + (1.0f - FILTER_ALPHA) * accelRoll;

  gyroPitch += gx * dt_s;
  float residual = gyroPitch - accelPitch;

  resCount += 1;
  float delta = residual - resMean;
  resMean += delta / (float)resCount;
  resM2 += delta * (residual - resMean);
}

Orientation imu_orientation() {
  Orientation o;
  o.pitch = pitch;
  o.roll = roll;
  return o;
}

float imu_drift_variance_reset() {
  float variance = (resCount > 1) ? (resM2 / (float)(resCount - 1)) : 0.0f;
  resCount = 0;
  resMean = 0.0f;
  resM2 = 0.0f;
  gyroPitch = pitch;   // re-anchor the reference to bound unbounded growth
  return variance;
}
