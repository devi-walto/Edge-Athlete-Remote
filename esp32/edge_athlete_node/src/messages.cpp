// messages.cpp — builds the pulse, live-speed and rep messages and hands them to the
// connection to send (see messages.h for why they're kept together).
#include "messages.h"

#include <WiFi.h>
#include <time.h>

#include "connection.h"
#include "measuring.h"
#include "shared.h"

namespace {

constexpr uint32_t PULSE_INTERVAL_MS = 5000;
constexpr uint32_t MOTION_INTERVAL_MS = 100;
constexpr int BATTERY_LEVEL_PERCENT = 100;  // USB-powered for now.

uint8_t repNumber = 0;
uint32_t lastPulseAt = 0;
uint32_t lastMotionAt = 0;

bool formatUtcTimestamp(char *output, size_t outputSize) {
  if (!clockIsSet()) return false;
  const time_t now = time(nullptr);
  tm utcTime;
  gmtime_r(&now, &utcTime);
  return strftime(output, outputSize, "%Y-%m-%dT%H:%M:%SZ", &utcTime) > 0;
}

void publishPulse() {
  char timestamp[25];
  if (!formatUtcTimestamp(timestamp, sizeof(timestamp))) return;
  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"node_id\":\"%s\",\"event_type\":\"pulse\",\"battery_level\":%d,"
           "\"signal_strength\":%d,\"firmware_version\":\"%s\",\"timestamp\":\"%s\"}",
           sensorId, BATTERY_LEVEL_PERCENT, constrain(WiFi.RSSI(), -120, 0), FIRMWARE_VERSION, timestamp);
  publish("pulse", payload, false);
}

void publishMotion() {
  char timestamp[25];
  if (!formatUtcTimestamp(timestamp, sizeof(timestamp))) return;
  char payload[192];
  snprintf(payload, sizeof(payload),
           "{\"node_id\":\"%s\",\"event_type\":\"motion\",\"velocity\":%.3f,\"timestamp\":\"%s\"}",
           sensorId, barSpeed(), timestamp);
  publish("motion", payload, false);
}

}  // namespace

void publishRep(float meanVelocityMps, float peakVelocityMps, uint32_t durationMs) {
  char timestamp[25];
  if (!formatUtcTimestamp(timestamp, sizeof(timestamp))) {
    Serial.println("the time isn't set yet; rep not sent");
    return;
  }
  repNumber = (repNumber % 100) + 1;
  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"node_id\":\"%s\",\"rep_number\":%u,\"mean_velocity\":%.3f,"
           "\"peak_velocity\":%.3f,\"duration_ms\":%lu,\"timestamp\":\"%s\"}",
           sensorId, static_cast<unsigned int>(repNumber), meanVelocityMps, peakVelocityMps,
           static_cast<unsigned long>(durationMs), timestamp);
  Serial.printf("rep: mean %.2f m/s, peak %.2f m/s, %lu ms\n", meanVelocityMps, peakVelocityMps,
                static_cast<unsigned long>(durationMs));
  const Sent sent = publish("rep", payload, true);
  if (sent != Sent::Dropped) {
    Serial.printf("rep %u sent%s\n", repNumber, sent == Sent::Now ? "" : " (kept until reconnected)");
  }
}

void sendRegularMessages(uint32_t now) {
  if (now - lastPulseAt >= PULSE_INTERVAL_MS) {
    lastPulseAt = now;
    publishPulse();
  }
  if (now - lastMotionAt >= MOTION_INTERVAL_MS) {
    lastMotionAt = now;
    publishMotion();
  }
}
