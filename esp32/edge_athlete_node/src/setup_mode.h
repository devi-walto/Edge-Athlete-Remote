// setup_mode.h — the sensor's own phone setup (spec 14 Phase 8).
//
// Why: a sensor with nothing saved, or one whose BOOT button is held 3 seconds, opens
// its own open Wi-Fi, EdgeAthlete-<id>. Joining it pops a page open on the phone
// (setup_page.h): pick the Wi-Fi, where reps go, the code. The settings are saved on
// the sensor; the setup Wi-Fi then switches off and costs nothing. Until something new
// is saved, nothing old is erased.
#pragma once

#include <Arduino.h>

void startSetup();
void maintainSetup(uint32_t now);  // call every loop while setup is open
bool setupIsOpen();
void printSetupStatus();  // for USB `status`: is the setup Wi-Fi up, and who's on it
void watchSetupButton(uint32_t now);  // in normal running: a 3-second hold opens setup
