WiCAN Pro BLE standby wake test
Version: 6.0.0-beta.7-blewake.1

This replaces the dual-bus CAN Monitor UI with the original CAN Monitor.
The new test lives under Power Saving > BLE wake test.
This is an experimental build, not a verified stable release.

What it tests
An explicitly armed 3-minute standby. The WiCAN stops WiFi, CAN, loggers,
USB accessories and normal OBD functions while retaining its BLE peripheral.
It requests Bluetooth modem sleep and driver-coordinated automatic light sleep.
It returns to normal operation by a planned reboot after an authenticated
reconnection from an already bonded phone, or after the 3-minute timer.
The result survives that restart and is shown on the Power Saving page.

This is not automatic phone-proximity detection yet. There is no BLE scanning
or RSSI unlock threshold. No CAN unlock or other vehicle command is added.
Power-management configuration success is reported, not measured current or
proof that the CPU slept. Current consumption and BLE behaviour need testing
on the actual WiCAN Pro.

Install
Back up settings first. Upload the .bin through System > Firmware update.
Keep power connected until the restart completes. Check About shows the
blewake.1 version. V6-to-V6 settings should be retained; V4-to-V6 resets them.
The application .bin is not a full-flash image and must not go at address zero.

Prepare the phone
1. Power Saving > BLE wake test > Enable BLE (stage settings).
2. Submit Changes and restart. This preserves the existing passkey and enables
   bonding, Secure Connections, Lean RAM profile and legacy advertising.
3. Open pairing window. Use your Android BLE app (for example nRF Connect)
   to find WiC_<device id>. For the unit observed in this chat: WiC_28848555f511.
4. Bond/pair using the BLE passkey configured in Settings. Access a protected
   GATT value, such as Device Information > Manufacturer Name, to establish
   encrypted, authenticated security. Check the web UI reports secured.
5. Disconnect the phone in the app. The start button requires a fresh link.

Run
1. Start 3-minute BLE standby. WiFi will disconnect as standby starts.
2. Reconnect the already bonded phone in the BLE app. If security does not
   resume automatically, read a protected GATT value. New pairing is refused
   during standby; merely establishing an unsecured connection is not a wake.
3. WiCAN should reboot and return to its WiFi network. Reload Power Saving.
4. Expected result: ble_authenticated. The timer alone gives timeout; that
   confirms timer recovery but does not establish BLE wake success.
5. Check modem_sleep_configured and automatic_light_sleep_configured.
   Accepted configuration does not establish actual standby current.

Safeguards and recovery
Arming requires a valid supply reading >=12.1 V, BLE enabled/applied, bonding
and Secure Connections enabled, and the phone disconnected. Tests do not
re-arm after a reboot. The interval is bounded to 180 seconds. During the
test, voltage is checked every 200 ms. Below 12.0 V or on ADC failure the
WiCAN closes BLE and falls back to normal radio-off sleep, retaining the
stock voltage-wake/battery protection. In that case WiFi may stay off until
the normal wake voltage is reached; the 3-minute timer does not override the
battery cutoff. An unexpected reset produces interrupted rather than success.

Unlock investigation
The Ford DBC in the user's RangerScan source maps a lock-related frame to
HS1_CAN. It includes status/requestor/count/rolling-code signals, so seeing
it does not prove that replaying it would unlock this Ranger. No unlock
request has been validated or transmitted. Next evidence needed is a
listen-only HS-CAN1 capture covering actual remote lock/unlock operations.

Validation
Wake-decision policy tests passed, including voltage/ADC priority and NaN.
UI tests passed: no implicit arming, configuration staging, pairing/start
controls, active guard and removal of the dual-bus tab.
The minified firmware Power Saving page rendered in headless Edge without
browser errors. Physical BLE wake, timer recovery and current are untested.
See BUILD.txt for the full firmware build and image provenance.
