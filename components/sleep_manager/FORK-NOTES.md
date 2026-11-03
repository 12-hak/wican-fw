Fork-local sleep manager from meatpi-components 2a8dbea.
Adds an explicitly armed 30..180-second BLE standby experiment on the existing
state task. Ordinary sleep and its radio-off/manual-nap path stay unchanged.
During the experiment the root keeps BLE only, closes pairing, and configures
Bluetooth modem sleep plus driver-coordinated automatic light sleep. Battery
checks run at 200 ms; <12.0 V or invalid ADC switches to normal radio-off sleep.
Authenticated reconnect or timeout recovers by a planned reboot. A retained
RTC_NOINIT result distinguishes these outcomes; a reboot never re-arms a test.
No CAN transmit or unlock code is introduced. Power configuration acceptance
is reported; actual current consumption requires hardware measurement.
