#include <bluefruit.h>
#include "amh_ble.h"

static uint8_t SERVICE_UUID[16] = {
  0x66,0x66,0x55,0x55,0x44,0x44,0x33,0x33,
  0x22,0x22,0x11,0x11,0x01,0x00,0x00,0xf0
};
static uint8_t CHAR_UUID[16] = {
  0x66,0x66,0x55,0x55,0x44,0x44,0x33,0x33,
  0x22,0x22,0x11,0x11,0x02,0x00,0x00,0xf0
};

static BLEService amhService(SERVICE_UUID);
static BLECharacteristic amhTelemetry(CHAR_UUID);

void ble_init() {
  Bluefruit.begin();
  Bluefruit.setTxPower(0);   // fixed 0 dBm; no longer a tuned parameter
  Bluefruit.setName("AMH-Node");

  amhService.begin();
  amhTelemetry.setProperties(CHR_PROPS_NOTIFY);
  amhTelemetry.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  amhTelemetry.setFixedLen(8);
  amhTelemetry.begin();

  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(amhService);
  Bluefruit.Advertising.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);
}

void ble_notify(float drift_variance, float battery) {
  if (!Bluefruit.connected()) return;
  float payload[2] = { drift_variance, battery };
  amhTelemetry.notify((uint8_t *)payload, sizeof(payload));
}

bool ble_connected() { return Bluefruit.connected(); }
