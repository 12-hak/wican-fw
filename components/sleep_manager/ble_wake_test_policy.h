#pragma once
#include <stdbool.h>
#include <stdint.h>
/* Codes are also retained across the recovery reboot and exposed by HTTP. */
int ble_wake_test_decide(uint32_t elapsed_ms, uint32_t duration_ms,
                         bool voltage_valid, float volts, bool secured);
