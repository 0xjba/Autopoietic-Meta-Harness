#include <Arduino.h>
#include "battery.h"

#ifndef AMH_VIRTUAL_BATTERY
#define AMH_VIRTUAL_BATTERY 1
#endif

#if AMH_VIRTUAL_BATTERY

static const float V_FULL = 4.20f;
static const float V_FLOOR = 3.00f;
static const float ACTIVE_COST_V = 0.00008f;   // volts lost per wake cycle

static float v = V_FULL;

void battery_init() { v = V_FULL; }

void battery_on_active_cycle() {
  v -= ACTIVE_COST_V;
  if (v < V_FLOOR) v = V_FLOOR;
}

float battery_voltage() { return v; }

#else

void battery_init() {
  pinMode(VBAT_ENABLE, OUTPUT);
  digitalWrite(VBAT_ENABLE, HIGH);   // reading disabled by default
}

void battery_on_active_cycle() {}

float battery_voltage() {
  digitalWrite(VBAT_ENABLE, LOW);    // enable the divider
  delay(1);
  int raw = analogRead(PIN_VBAT);
  digitalWrite(VBAT_ENABLE, HIGH);
  float v_adc = raw * (3.6f / 1023.0f);
  return v_adc * 2.961f;             // divider ratio; calibrate in Section 9
}

#endif
