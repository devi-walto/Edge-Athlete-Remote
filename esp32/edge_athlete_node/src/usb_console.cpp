// usb_console.cpp — reads the lines typed over USB and answers them (see usb_console.h).
#include "usb_console.h"

#include <WiFi.h>

#include "connection.h"
#include "measuring.h"
#include "settings.h"
#include "setup_mode.h"
#include "shared.h"

namespace {

constexpr uint32_t WATCH_INTERVAL_MS = 200;

bool watching = false;
uint32_t lastWatchAt = 0;
char usbLine[64];
size_t usbLineLength = 0;

void printStatus() {
  Serial.printf("sensor %s, firmware %s\n", sensorId, FIRMWARE_VERSION);
  for (int i = 0; i < networkCount; ++i) {
    Serial.printf("saved wi-fi %d: %s -> %s (%s)\n", i + 1, networks[i].ssid.c_str(), networks[i].host.c_str(),
                  networks[i].local ? "local install" : "remote server");
  }
  if (networkCount == 0) Serial.println("saved wi-fi: none (setup is open)");
  printTrouble();
  Serial.printf("motion sensor: %s\n", setupIsOpen() ? "not started during setup"
                                     : motionSensorFound() ? "BNO085 found" : "missing, so no reps");
  Serial.printf("server: %s (%s)\n", serverHost[0] ? serverHost : "none yet", remote ? "remote, encrypted" : "local install, plain");
  Serial.printf("wi-fi: %s, time: %s\n",
                WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "not connected",
                clockIsSet() ? "set" : "not set yet");
  if (remote) Serial.printf("login: %s\n", loginToken[0] ? "saved" : "none yet: type  claim CODE");
  Serial.printf("connection: %s\n", serverConnected() ? "connected" : "not connected");
}

void runCommand(char *line) {
  while (*line == ' ') ++line;
  if (strncmp(line, "claim ", 6) == 0) {
    char *code = line + 6;
    while (*code == ' ') ++code;
    String detail;
    if (claim(code, detail)) {
      startMqtt();
    } else {
      Serial.println(detail);
    }
  } else if (strcmp(line, "forget") == 0) {
    forgetLogin();
    stopMqtt();
    Serial.println("login forgotten; claim again with a new code");
  } else if (strcmp(line, "setup") == 0) {
    requestSetup(true);
    Serial.println("opening setup...");
    delay(200);
    ESP.restart();
  } else if (strcmp(line, "status") == 0) {
    printStatus();
  } else if (strcmp(line, "watch") == 0) {
    watching = !watching;
  } else if (*line) {
    Serial.println("commands: claim CODE · forget · setup · status · watch");
  }
}

}  // namespace

void runUsbConsole(uint32_t now) {
  while (Serial.available() > 0) {
    const char next = static_cast<char>(Serial.read());
    if (next == '\n' || next == '\r') {
      usbLine[usbLineLength] = '\0';
      if (usbLineLength) runCommand(usbLine);
      usbLineLength = 0;
    } else if (usbLineLength + 1 < sizeof(usbLine)) {
      usbLine[usbLineLength++] = next;
    }
  }
  if (watching && now - lastWatchAt >= WATCH_INTERVAL_MS) {
    lastWatchAt = now;
    printMovement();
  }
}
