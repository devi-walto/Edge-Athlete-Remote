// settings.h — what the sensor remembers in its own flash, across switching off.
//
// Why: one firmware for every sensor (spec 14 decision 6), so nothing about a network,
// a school or an athlete is built in. The setup page writes these; the rest of the
// sensor reads them. Kept in three separate places in flash, so clearing one (the
// login, say) never touches another.
#pragma once

#include <Arduino.h>
#include <esp_system.h>

constexpr int MAX_NETWORKS = 4;

// A saved Wi-Fi network and where its reps go: a remote school (host = "<sub>.<domain>")
// or a local base station (host = the address it had at setup; see connection.cpp).
struct SavedNetwork {
  String ssid;
  String password;
  bool local;
  String host;
};
extern SavedNetwork networks[MAX_NETWORKS];
extern int networkCount;

void loadNetworks();
void saveNetwork(const SavedNetwork &network);  // the newest goes first

// "Open setup" survives the restart it takes to get there.
void requestSetup(bool open);
bool setupRequested();

// The school login from a claim: the sensor's ID, its token, and the door's path.
extern char loginUser[40];
extern char loginToken[128];
extern char loginPath[32];
bool loadLogin();        // true if there's a login for serverHost
void saveLogin();        // keeps loginUser/Token/Path for serverHost
void forgetLogin();
String linkedSchool();   // the school this sensor has a login for, or ""

// Why the sensor last restarted badly (power dip, crash, hang), kept across unplugging.
const char *resetName(esp_reset_reason_t why);
void recordStart(esp_reset_reason_t why);
void printTrouble();
