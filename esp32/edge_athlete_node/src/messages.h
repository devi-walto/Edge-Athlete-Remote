// messages.h — what the sensor tells the server: a pulse every 5 seconds ("I'm here"),
// the bar's live speed 10 times a second, and each finished rep.
//
// Why it's on its own: these are the sensor's half of the MQTT contract the server
// reads (sensor_messages.py on the server side). Keeping their exact shape in one
// file makes it easy to check against the server.
#pragma once

#include <Arduino.h>

void publishRep(float meanVelocityMps, float peakVelocityMps, uint32_t durationMs);
void sendRegularMessages(uint32_t now);  // the pulse and the live speed, when they're due
