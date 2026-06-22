#ifndef AMH_BLE_H
#define AMH_BLE_H

void ble_init();

// Notifies an 8-byte payload: float32 drift_variance, float32 battery (LE).
void ble_notify(float drift_variance, float battery);

bool ble_connected();

#endif // AMH_BLE_H
