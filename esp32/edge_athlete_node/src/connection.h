// connection.h — getting the sensor's messages to its server: joining a saved Wi-Fi,
// setting the clock, the MQTT connection, and claiming a school login.
//
// Why it's on its own: everything here is about reaching the server, whichever kind
// it is. A remote school is reached over the internet, encrypted, as
// wss://<school>/sensors with the sensor's own login, its certificate checked against
// the two roots in roots.h. A local install is plain MQTT on 1883 on the gym's Wi-Fi,
// with no login.
#pragma once

#include <Arduino.h>

void maintainConnection(uint32_t now);  // call every loop in normal running

// What became of a message handed to publish().
enum class Sent { Now, Kept, Dropped };
// Reps (mustArrive) are kept and sent again until the server has them, also across a
// short drop; pulses and live speed are only worth sending now.
Sent publish(const char *kind, const char *payload, bool mustArrive);
bool serverConnected();
void startMqtt();
void stopMqtt();

bool clockIsSet();
// Asks a server whether it's an Edge Athlete server (GET /api/health/), over HTTPS for a
// school. On a local install its answer also sets the clock.
bool serverAnswers(bool local, const String &host);
// Trades a one-time code for this sensor's login at serverHost. Returns true when
// claimed; otherwise `detail` says why, in words the athlete can act on.
bool claim(const char *code, String &detail);
