# WiCAN Pro V6 stability candidate

This branch is a test candidate, not a stable release. Based on upstream
`dev-v6` a5f15f8 with shared components 2a8dbea8662fc2e018324e5cb62546256ada330e.

## Confirmed evidence

- Upstream beta.5 release notice asks all V6 alpha/beta users to revert to stable:
  https://github.com/meatpiHQ/wican-fw/releases/tag/v6.0.0p-beta.5
- Issue 1024 contains the crash report and maintainer reproduction with BLE and
  Tailscale enabled: https://github.com/meatpiHQ/wican-fw/issues/1024
- The component fix 010009e releases failed DERP TLS contexts, backs off retries,
  gates VPN startup on internal RAM and guards the resolver semaphore allocation.
  Later changes move stacks and Bluetooth controller code out of internal RAM.
- Issue 1023 is a separate OBD-interpreter bring-up/recovery problem, not proof
  that the ESP32 itself boot-loops:
  https://github.com/meatpiHQ/wican-fw/issues/1023
- Issue 973's reconnect failure was discussed as lost WiFi configuration during
  the V4-to-V6 partition migration; it is not a confirmed reset-loop trace.

## Fork changes

Pin the complete shared-component revision, check it and tracked cleanliness
at CMake configure, and detach automatic clones at that revision. Otherwise a
firmware branch silently builds a different component snapshot as upstream moves.
Remove the build script's hardcoded developer-local component path. Add an
explicit candidate build workflow with ELF, map, source revisions and SHA-256.
Existing user component checkouts are never reset or modified by the checks.

## Release gates

Build the complete firmware and retain its ELF and checksum. Then validate on
real Pro hardware: cold/warm boots; V4-to-V6 migration with backup; existing V6
settings; BLE plus WiFi plus Tailscale; repeated failed DERP TLS handshakes and
reconnects; long-running internal-heap trend; settings saves and OTA while BLE
is connected; low-voltage sleep/wake; rollback/recovery; OBD-chip bring-up.
Use upstream testing/tspublic.md, testing/ble_ts_soak.md, testing/obdbringup.md
and testing/release.md. The upstream recorded results are upstream evidence,
not tests performed on this fork or this user's device.

No stable firmware has been published or flashed by this change.

## Validation performed on this fork

2026-11-02: GitHub build 41423988796 completed successfully from firmware
commit 56cab34 and pinned shared components 2a8dbea8662fc2e018324e5cb62546256ada330e.
Firmware image: 4,066,640 bytes; ELF and linker map retained with the artifact.
Five upstream lwip_guard host tests passed on local WSL GCC with Unity 2.6.1.
CMake configuration accepted the matching components and rejected a wrong SHA.
Four dual-capture host tests passed, including two concurrent mock TCP streams.
The later tools/dualcan files do not change the compiled firmware source.
No physical device is connected, so no WiCAN or vehicle test has been performed.

The dual-bus capture procedure is in tools/dualcan/README.md. It uses the
firmware's existing native-CAN and OBD-chip interfaces rather than adding
an always-running task. TSR message identities are still unknown.

## On-device dual monitor test build

Version 6.0.0-beta.7-dualbus.1 builds from firmware 1e3364693415c9fe0531539ab073ff6e05cc1005.
Build 41428541495 passed; downloaded BIN SHA256 af110f2035f835ed1c4d5b5a7789181246e9ca083c07d885b939945ab814e0b2.
The new navigation and monitor implementation were verified inside the BIN.
See FIRMWARE-DUAL-MONITOR.md for device setup. Browser/UI checks passed;
no physical WiCAN or vehicle validation has been performed.

## BLE standby wake test

Version 6.0.0-beta.7-blewake.1, source 613eea5bf8c65d94e531bd3a2dae8069dddecf99.
Build 41634670896 passed. BIN SHA256 e9413a51a063a2fca829dfad193748a2b838d6deb797f2ed73c43d9fcd047753.
Original CAN Monitor restored; bounded BLE wake experiment under Power Saving.
See FIRMWARE-BLE-WAKE.md. Software tests and artifact checks passed; live device
was inspected read-only and has not been updated. Hardware BLE wake and
standby current remain unverified. No vehicle unlock request was added.
