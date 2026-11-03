/** Bounded BLE standby experiment. Never sends vehicle commands. */
#include <stdio.h>
#include <math.h>
#include "sdkconfig.h"
#include "cJSON.h"
#include "esp_bt.h"
#include "esp_log.h"
#include "esp_pm.h"
#include "esp_http_server.h"
#include "battery_monitor.h"
#include "ble_manager.h"
#include "http_server_manager.h"
#include "settings_manager.h"
#include "sleep_manager.h"
#include "main_ble_wake.h"

static const char *TAG = "ble_wake_test";

void main_ble_wake_normal_power(void)
{
    const esp_pm_config_t cfg = {
        .max_freq_mhz = CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ,
        .min_freq_mhz = CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ,
        .light_sleep_enable = false
    };
    (void)esp_pm_configure(&cfg);
    (void)esp_bt_sleep_disable();
}

void main_ble_wake_prepare(void)
{
    /* Existing bonds can restore encryption; no new pairing in standby. */
    ble_manager_pairing_disable();
    esp_err_t modem = esp_bt_sleep_enable();
    const esp_pm_config_t cfg = {
        .max_freq_mhz = CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ,
        .min_freq_mhz = 80,
        .light_sleep_enable = true
    };
    esp_err_t automatic = esp_pm_configure(&cfg);
    sleep_manager_ble_test_note_power(modem == ESP_OK, automatic == ESP_OK);
    ESP_LOGW(TAG, "standby power config: modem=%s automatic_light_sleep=%s; current unmeasured",
             esp_err_to_name(modem), esp_err_to_name(automatic));
}

bool main_ble_wake_secured(void)
{
    return !ble_manager_pairing_is_enabled() &&
           ble_manager_is_connected() && ble_manager_is_secured();
}

static esp_err_t json_reply(httpd_req_t *req, cJSON *o)
{
    char *body = cJSON_PrintUnformatted(o);
    cJSON_Delete(o);
    if (body == NULL) return ESP_ERR_NO_MEM;
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    esp_err_t err = httpd_resp_sendstr(req, body);
    cJSON_free(body);
    return err;
}

static esp_err_t refuse(httpd_req_t *req, const char *message)
{
    httpd_resp_set_status(req, "409 Conflict");
    cJSON *o = cJSON_CreateObject();
    cJSON_AddStringToObject(o, "error", message);
    return json_reply(req, o);
}

static esp_err_t status_handler(httpd_req_t *req)
{
    static const char *const RESULTS[] = {
        "none", "armed", "standby", "ble_authenticated", "timeout",
        "low_battery", "sensor_failure", "interrupted"
    };
    sleep_manager_ble_test_status_t st;
    sleep_manager_ble_test_status(&st);
    cJSON *o = cJSON_CreateObject();
    cJSON_AddBoolToObject(o, "active", st.active);
    cJSON_AddStringToObject(o, "result", st.result >= 0 && st.result < 8 ? RESULTS[st.result] : "unknown");
    cJSON_AddNumberToObject(o, "trials", st.trials);
    cJSON_AddNumberToObject(o, "elapsed_ms", st.elapsed_ms);
    cJSON_AddNumberToObject(o, "voltage", st.voltage);
    cJSON_AddBoolToObject(o, "modem_sleep_configured", st.modem_sleep);
    cJSON_AddBoolToObject(o, "automatic_light_sleep_configured", st.automatic_light_sleep);
    cJSON_AddBoolToObject(o, "ble_enabled", ble_manager_is_enabled());
    cJSON_AddBoolToObject(o, "connected", ble_manager_is_connected());
    cJSON_AddBoolToObject(o, "secured", ble_manager_is_secured());
    cJSON_AddBoolToObject(o, "pairing_enabled", ble_manager_pairing_is_enabled());
    cJSON_AddNumberToObject(o, "max_seconds", 180);
    cJSON_AddBoolToObject(o, "vehicle_commands_enabled", false);
    return json_reply(req, o);
}

static esp_err_t pairing_handler(httpd_req_t *req)
{
    if (!ble_manager_is_enabled() || settings_manager_is_pending_reboot("ble_manager"))
        return refuse(req, "Enable BLE and restart first");
    if (sleep_manager_ble_test_active()) return refuse(req, "Standby already running");
    sleep_manager_ble_test_status_t st;
    sleep_manager_ble_test_status(&st);
    if (st.active) return refuse(req, "Standby already armed");
    ble_manager_pairing_enable();
    return status_handler(req);
}

static esp_err_t start_handler(httpd_req_t *req)
{
    if (!ble_manager_is_enabled() || settings_manager_is_pending_reboot("ble_manager"))
        return refuse(req, "Enable BLE, bonding and Secure Connections, then restart");
    if (ble_manager_is_connected())
        return refuse(req, "Disconnect the phone first; wake requires a new secured connection");
    cJSON *cfg = NULL;
    bool valid = settings_manager_get("ble_manager", &cfg) == ESP_OK &&
        cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(cfg, "bonding")) &&
        cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(cfg, "sc_only"));
    cJSON_Delete(cfg);
    if (!valid) return refuse(req, "Bonding and Secure Connections must both be enabled");
    float volts;
    if (battery_monitor_read_now(&volts) != ESP_OK || !isfinite(volts) || volts < 12.1f)
        return refuse(req, "A valid supply reading of at least 12.1 V is required");
    if (sleep_manager_ble_test_start(180) != ESP_OK)
        return refuse(req, "Sleep task not ready or another test is running");
    ble_manager_pairing_disable();
    return status_handler(req);
}

esp_err_t main_ble_wake_register_http(void)
{
    static const httpd_uri_t URIS[] = {
        { .uri = "/api/ble_wake_test", .method = HTTP_GET, .handler = status_handler },
        { .uri = "/api/ble_wake_test/start", .method = HTTP_POST, .handler = start_handler },
        { .uri = "/api/ble_wake_test/pairing", .method = HTTP_POST, .handler = pairing_handler }
    };
    return http_server_manager_register_handlers(URIS, sizeof(URIS)/sizeof(URIS[0]));
}
