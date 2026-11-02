# Fork-local web UI override

Copied from meatpi-components 2a8dbea8662fc2e018324e5cb62546256ada330e,
with original copyright and license headers retained. ESP-IDF project
components override EXTRA_COMPONENT_DIRS, so this UI is embedded in this
fork without changing the pinned shared component checkout.

Changes: index.html adds the Dual bus test tab; monitor.js adds two
independent receive-only panels using existing /ws/can and /ws/obd routes.
There are no new backend tasks or CAN transmitter paths. Native capture
requires enabled native CAN with silent=true, baud=500 and the existing
CAN-to-ws_can slcan bridge. Chip capture requires AutoPID disabled and the
default raw obd-to-ws_obd bridge, a ready chip, and every setup command OK.

Stopping a view does not power down either CAN controller. Native Stop
unsubscribes the browser. Chip Stop sends SPACE to end ATMA and closes its
socket. A network failure cannot guarantee delivery of that stop byte;
the chip may remain in passive monitor mode until stopped or restarted.
