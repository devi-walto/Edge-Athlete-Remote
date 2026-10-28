// shared.h — the few facts every part of the sensor needs: which sensor this is, which
// firmware it runs, and where its reps are going right now.
//
// Why it's its own file: settings, the connection, the setup page and the USB console
// all read these, and each is in its own file. They're kept here, in one place, so no
// part keeps its own copy that could drift.
#pragma once

#include <Arduino.h>

constexpr char FIRMWARE_VERSION[] = "2.2.2";

extern char sensorId[16];    // "ea-" + the last 3 bytes of the chip's Wi-Fi address
extern bool remote;          // true: a school over the internet; false: a local install
extern char serverHost[96];  // the school ("<sub>.<domain>") or the base station's address
