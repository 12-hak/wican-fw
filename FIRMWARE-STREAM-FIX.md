WiCAN Pro BLE wake + TCP stream test, 6.0.0-beta.7-blewake.2

Observed on the live blewake.1 unit: repeated socket_manager gvret0 client drops
with the reason "stalled/dead on send", matching Pace retry reports despite
Wi-Fi remaining associated. Existing code closes the connection whenever one
send() does not return the entire requested chunk, with a 100 ms send timeout.
A TCP short write is valid and requires sending the remaining suffix.

This adds a project-local socket_manager override from the pinned shared
component. It retains byte order across partial writes, retries EINTR and
transient EAGAIN/EWOULDBLOCK within a 500 ms total budget, and uses a 50 ms
per-call socket timeout. Truly closed/failing or persistently stalled clients
are still dropped. A drop logs bytes sent/requested, errno/text and whether
the retry deadline expired. No new queues or dynamic allocations are added.

The existing synchronous socket-manager lock/fan-out design remains: a slow
client can still delay other sends up to the bounded budget. This is not a
claim that every send error is transient or that the vehicle fault is fixed.

Host tests cover ordered partial writes, EINTR, transient backpressure, hard
errors, closed peers, bounded timeout and empty writes. The BLE wake feature
and pinned stability baseline are retained. Firmware has not been flashed or
validated on the head unit by the agent.

Upload the application OTA BIN through WiCAN System / Firmware Update, then
check About reports blewake.2. Preserve settings before updating. Re-test Pace
and RangerScan separately, then together. If drops persist, the new socket log
will identify timeout versus hard socket errors and partial progress.
