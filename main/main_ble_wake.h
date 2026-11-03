#pragma once
#include <stdbool.h>
#include "esp_err.h"
esp_err_t main_ble_wake_register_http(void);
void main_ble_wake_prepare(void);
void main_ble_wake_normal_power(void);
bool main_ble_wake_secured(void);
