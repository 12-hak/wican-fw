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
