Historical test build: dual-bus UI is removed in blewake.1. See FIRMWARE-BLE-WAKE.md for the current experiment.

WiCAN Pro dual-bus monitor firmware test
Version: 6.0.0-beta.7-dualbus.1

Purpose
Check reception on the two physical interfaces separately, then together.
No external Python capture tool or SavvyCAN is required: use the WiCAN web UI.
This is a test build, not a stable release. No physical WiCAN was connected
for development or validation.

Before installing
Back up configuration. The V4-to-V6 partition migration resets settings.
Use the WiCAN firmware-upload function for the application .bin. This is
not a full-flash image and must not be written at flash address zero.

Settings for this test
1. Native CAN: enabled, fixed 500 kbit/s, silent/listen-only enabled.
2. Native monitor connection: /ws/can WebSocket channel enabled, with
   a=can, b=ws_can, translator=slcan. The existing Monitor page's setup
   action can stage the native monitor wiring if it is absent.
3. OBD monitor connection: /ws/obd channel enabled, with raw obd-to-ws_obd
   bridge (the stock V6 default).
4. AutoPID master switch disabled, configuration applied, restart complete.
   Close other OBD clients and disable scripts/transmit rules/diagnostic jobs.

Test procedure
Open CAN Monitor > Dual bus test. The two panels start stopped.
A. Start only HS-CAN1 / pins 6/14. Confirm the frame count increases.
B. Stop it. Start only HS-CAN2 / pins 3/11. Expand Chip setup commands:
   each setup command must answer OK before ATMA monitoring starts.
   Confirm the second frame count increases.
C. Leave 3/11 running and start 6/14. Confirm BOTH counters increase.
D. Stop either panel: the other should continue receiving.

The 3/11 panel configures VTP251, VT PBR 500000, ATCSM1 (silent),
ATCFC0 (no automatic flow control), headers/spaces/raw formatting, then
ATMA. It does not send diagnostic CAN requests. If a command is rejected,
the panel displays the command and stops. AutoPID must be disabled both
in saved settings and in the running firmware before setup proceeds.

Each panel shows total frames, recent frames/s, time since last frame,
and latest data/count per ID (up to 256 distinct ID/type entries).
Clear resets only that panel's displayed capture. Native Stop closes its
browser subscription; it does not disable the controller. Chip Stop sends
SPACE to stop ATMA, then closes its socket. Leaving the page does the same.
After a WiFi failure, the stop byte may not reach the chip; it can remain
in passive monitoring until explicitly stopped or restarted.

Wiring target
Pre-gateway Ranger HS-CAN1 on WiCAN pins 6/14; pre-gateway HS-CAN2 on
WiCAN pins 3/11. The two vehicle CAN networks remain separate. The 3/11
interface's MS-CAN label does not change the routed HS-CAN2 bitrate.

What this does not establish
TSR message IDs, payload layout and speed units are not decoded yet.
Successful compilation and browser mocks do not prove reception from your
chip or the vehicle; the above test is intended to establish that.

Software checks completed
- JavaScript syntax check.
- UI tests: no automatic capture; independent sockets and frame counts;
  fragmented frames; command order; stop/clear isolation; teardown;
  unsupported command rejection; AutoPID gate; cancelled startup.
- Headless Edge: actual minified firmware UI loads CAN Monitor / Dual bus
  test with two panels and no page errors. Desktop/narrow layout checked.
- Full firmware build and embedded-resource verification: see BUILD.txt.

Source
https://github.com/12-hak/wican-fw/tree/fix/v6-boot-stability
