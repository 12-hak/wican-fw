#include <math.h>
#include "ble_wake_test_policy.h"
int ble_wake_test_decide(uint32_t elapsed_ms, uint32_t duration_ms,
                         bool voltage_valid, float volts, bool secured)
{
    if (!voltage_valid || !isfinite(volts)) return 6;
    if (volts < 12.0f) return 5;
    if (secured) return 3;
    if (elapsed_ms >= duration_ms) return 4;
    return 0;
}
