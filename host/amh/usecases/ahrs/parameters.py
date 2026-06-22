from amh.core.parameters import Parameter

PARAMETERS = [
    Parameter("IMU_POLL_RATE_MS", "int", 10, 200, 20,
              "IMU sampling interval in milliseconds; higher reduces active duty"),
    Parameter("FILTER_ALPHA", "float", 0.80, 0.99, 0.96,
              "Complementary filter gyroscope weight"),
    Parameter("BLE_TX_POWER", "int", -40, 8, 0,
              "BLE transmit power in dBm",
              allowed=(-40, -20, -16, -12, -8, -4, 0, 2, 3, 4, 5, 6, 7, 8)),
]
