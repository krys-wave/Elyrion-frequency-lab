# Sensor Node 01 / integration status

The Python USB serial gateway and canonical parser are implemented and transport-tested with a mock serial device. Firmware source includes adapters for all four specified devices. **No ESP32, sensors, microphone, or Bose speaker are attached to this cloud machine. Firmware has not been compiled or flashed here. Physical acceptance has not passed.**

Target: ESP32-S3 DevKitC-1, Arduino framework via pinned PlatformIO Espressif32 6.10.0. Install PlatformIO separately, then `pio run -d firmware/sensor-node-01` to compile; flash only after confirming the exact board and wiring. Firmware dependency download requires `registry.platformio.org`, `api.registry.platformio.org`, PlatformIO artifact hosts, and package/GitHub access, which have not been validated in this environment.

Example wiring in `include/pins.h`: I²C SDA 8 / SCL 9, microphone BCLK 14 / LRCLK 15 / DATA 16. These are example pins, not a verified wiring plan. BME280 address 0x76; ISM330DHCX address 0x6A. Confirm actual breakout addresses, supply voltages and pull-ups. Tie the SPH0645 channel-select pin for the left channel, use its required 3.3 V supply, and verify bit alignment and I²S electrical timing with the device datasheet. The SPH adapter samples 32 kHz, 32-bit I²S words; scale and calibration are provisional.

Use the ESP32-S3 **native USB CDC** connector, not a low-throughput external UART bridge. Firmware emits newline-delimited JSON with 20 scalar frames/s and 1600 audio samples per frame at 32 kHz; this payload is too large for a physical 115200-baud UART. In native USB CDC the nominal baud setting does not determine throughput. Validate sustained throughput, frame size and sample-rate accuracy on the actual board. Firmware audio DMA drives the acquisition timing; serialization and scalar reads may create jitter, which the engine will report rather than hide.

On serial connection, the gateway sends `{"command":"start","epoch_ms":<UTC milliseconds>}`. Firmware anchors its monotonic millisecond counter to that host epoch; USB synchronization latency and device drift remain uncharacterized. This supplies UTC labels for local event association, not precision clock synchronization. Missing sensors or microphone initialization stop emission; missing frames are never replaced with simulated values.

Each JSON frame must match `lab.schema.Frame`: timezone-aware timestamp, device ID, firmware version, scalar/acoustic sampling rates, calibration metadata, run/location IDs, source `serial`, all twelve finite canonical values, and finite normalized audio samples. The gateway assigns the active run/location IDs. Port discovery is available in the dashboard. Stop the run to change source.

Before physical acceptance:

1. Compile the pinned PlatformIO target and resolve any board/library compatibility issues.
2. Verify every sensor identity, actual sample rate, timestamps, units, magnetic scale, microphone alignment, clipping and calibration.
3. Characterize serial throughput and timing; implement hardware buffering/resampling if the 10% regularity check reports jitter.
4. Confirm disconnect/reconnect behavior, device-clock wrap and long-run stability. V0.1 requires stopping and restarting a run to reconnect.
5. Confirm browser audio output reaches the wired speaker; measure actual acoustic onset and SPL, rather than relying on software timestamps.
6. Record physical Room A and Room B runs; confirm archival round trip and common downstream processing. Keep simulation available as a test source.
