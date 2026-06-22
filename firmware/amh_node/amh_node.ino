#include <Arduino.h>
#include "config.h"
#include "imu.h"
#include "battery.h"
#include "amh_ble.h"

static unsigned long lastNotifyMs = 0;

void setup() {
  imu_init();
  battery_init();
  ble_init(BLE_TX_POWER);
}

void loop() {
  const float dt = IMU_POLL_RATE_MS / 1000.0f;

  imu_update(dt);
  battery_on_active_cycle();

  unsigned long now = millis();
  if (now - lastNotifyMs >= 1000) {
    lastNotifyMs = now;
    ble_notify(imu_drift_variance_reset(), battery_voltage());
  }

  delay(IMU_POLL_RATE_MS);
}
