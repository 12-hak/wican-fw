# Dual-bus TSR discovery capture (WiCAN Pro V6 candidate)

Target wiring: Ranger pre-gateway HS-CAN1 on WiCAN 6/14 and pre-gateway
HS-CAN2 on WiCAN 3/11. The two vehicle networks must remain separate.
The MS label on 3/11 does not make the rerouted vehicle bus 125 kbit/s:
this test sets both interfaces to 500 kbit/s.

The existing candidate firmware already exposes the independent native CAN
controller and OBD interpreter. No additional always-on firmware task is
needed for this first test. The Python tool configures the chip's second
interface and captures both streams concurrently, with bus-labelled CSV
and raw input files. This does NOT yet decode traffic sign recognition.

Maintainer's pin selection and bitrate instructions:
https://github.com/meatpiHQ/wican-fw/issues/708

## Firmware setup

Back up configuration before the V4-to-V6 migration (it resets settings).
Use the V6 stability candidate, with external power through OBD 16/4/5.
In its settings, enable native CAN, set baud 500, silent true; disable
AutoPID, scripts, diagnostic jobs and transmit rules for this capture.
Restart to apply the configuration. Close other OBD clients.

In Connections, enable TCP slcan0 port 3333 with the connection
`a=can, b=slcan0, translator=slcan`. Keep the default TCP obd0 port 35000
and its raw connection to `obd`. Native GVRET/SavvyCAN can also remain
connected; the SLCAN socket supplies this tool's native capture.

The capture preflight requires /api/can running, configured silent and
500 kbit/s, plus /api/autopid stats.running=false. It does not reconfigure
persistent settings. During chip setup, every command must return OK:
ATM0 precedes VTP251, VT PBR 500000 selects the bit rate, ATCSM1 requests
silent monitoring, ATCFC0 disables automatic ISO-TP flow control, ATH1,
ATS1, ATL0, ATD0 and ATCAF0 select raw frames. Only then is ATMA started.
There are no diagnostic request payloads or CAN transmit frames in the tool.
If ATCSM1 or another command is unsupported, the tool aborts. Actual silent
operation and simultaneous reception still need validation on your chip.
The chip is occupied by monitoring until the test ends; AutoPID cannot
poll through it at the same time. Stopping sends SPACE, not CR (repeat).

## Run

Python 3.10 or newer, no extra packages:

    python tools/dualcan/capture.py 192.168.0.10 --seconds 120 --output captures/run01

Use a new output directory each time. Output: frames.csv, both raw streams,
setup.json and summary.json. A zero-frame bus, unexpected chip output or a
socket disconnect makes the run fail. Inspect native RX/drop/error counter
changes in summary.json; the interpreter's UART timestamps and loss cannot
be inferred from the CSV. These are PC reception timestamps, not precisely
synchronised CAN-wire timestamps. The parser accepts standard and extended
CAN frames; unparsed chip output fails the test rather than vanishing.

First test with the vehicle stationary: confirm frames on BOTH labelled
buses. Then capture known displayed speed-limit transitions, with a
passenger operating the PC, recording the displayed limits and approximate
times. Compare changing IDs/bytes on HS-CAN2 against HS-CAN1. TSR's presence,
ID, bit layout and speed units are unverified until real captures establish
them. No guessed CAN ID or speed-limit decoder is included.

## Software validation

    python tools/dualcan/test_capture.py

Tests cover standard/extended/RTR parsing, malformed lines, fragmented
concurrent fake-device streams, bus labels, passive command ordering,
unknown native silent state, and unsupported chip-command refusal. They
are simulations, not WiCAN/vehicle validation.
