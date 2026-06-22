#ifndef AMH_BATTERY_H
#define AMH_BATTERY_H

void battery_init();

// Accounts for one active wake cycle. Under the virtual model this advances
// depletion; on real hardware it is a no-op.
void battery_on_active_cycle();

float battery_voltage();

#endif // AMH_BATTERY_H
