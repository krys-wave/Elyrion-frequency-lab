#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>
#include "sensors.h"

SensorDrivers sensors;
bool ready = false;
uint64_t epochMs = 0;
uint32_t syncTick = 0;

void setup() {
  Serial.begin(115200); // Native USB CDC; baud does not limit USB throughput.
  ready = sensors.begin();
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    JsonDocument command;
    if (deserializeJson(command, line) == DeserializationError::Ok && command["command"] == "start") {
      epochMs = command["epoch_ms"].as<uint64_t>();
      syncTick = millis();
    }
  }
  if (!ready || !epochMs) { delay(10); return; }
  const uint64_t sampledAt = epochMs + static_cast<uint32_t>(millis() - syncTick);
  JsonDocument frame;
  auto values = frame["values"].to<JsonObject>();
  auto audio = frame["acoustic_samples"].to<JsonArray>();
  if (!sensors.read(values, audio)) { ready = false; return; }
  time_t seconds = sampledAt / 1000;
  tm utc;
  gmtime_r(&seconds, &utc);
  char timestamp[40];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S", &utc);
  char suffix[12];
  snprintf(suffix, sizeof(suffix), ".%03uZ", static_cast<unsigned>(sampledAt % 1000));
  frame["timestamp"] = String(timestamp) + suffix;
  frame["device_id"] = "Sensor Node 01";
  frame["firmware_version"] = "0.1.0-unvalidated";
  frame["sampling_rate"] = 20;
  frame["acoustic_sampling_rate"] = SensorDrivers::AUDIO_RATE;
  frame["calibration"]["status"] = "uncalibrated";
  frame["calibration"]["clock"] = "host sync; USB latency and drift uncharacterized";
  frame["run_id"] = "assigned-by-gateway";
  frame["location_id"] = "Room A";
  frame["source"] = "serial";
  serializeJson(frame, Serial);
  Serial.println();
}
