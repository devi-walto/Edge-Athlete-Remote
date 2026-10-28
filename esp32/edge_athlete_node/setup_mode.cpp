// setup_mode.cpp — the setup Wi-Fi, the name answering that pops the page open, and
// what the page asks the sensor to do (see setup_mode.h for why).
#include "setup_mode.h"

#include <DNSServer.h>
#include <WebServer.h>
#include <WiFi.h>
#include <algorithm>

#include "connection.h"
#include "settings.h"
#include "setup_page.h"
#include "shared.h"
#include "site.h"

#ifndef SCHOOL_DOMAIN
#error "site.h must define SCHOOL_DOMAIN (copy site.h.example)"
#endif

namespace {

constexpr int PIN_SETUP_BUTTON = 9;          // the board's BOOT button
constexpr uint32_t SETUP_HOLD_MS = 3000;     // held this long: open setup
constexpr uint32_t SETUP_IDLE_LIMIT_MS = 10UL * 60 * 1000;  // untouched setup gives up
// The setup Wi-Fi's own address. Not 192.168.4.x: that's the base station's network,
// and the sensor is on both at once while it tries the gym's Wi-Fi.
const IPAddress SETUP_ADDRESS(10, 71, 0, 1);
const IPAddress SETUP_MASK(255, 255, 255, 0);

bool inSetup = false;
char setupName[32];  // the setup Wi-Fi: "EdgeAthlete-" + the end of the sensor's ID
DNSServer dns;
WebServer web(80);
uint32_t setupTouchedAt = 0;
uint32_t restartAt = 0;
uint32_t buttonDownAt = 0;
String scanJson;
String trySsid;
String tryPassword;
bool setupLocal = false;
String setupHost;

enum class Trying { Nothing, Connecting, Connected, WrongPassword, NotFound, Failed };
volatile Trying trying = Trying::Nothing;
uint32_t tryStartedAt = 0;

const char *tryingName() {
  switch (trying) {
    case Trying::Connecting: return "connecting";
    case Trying::Connected: return "connected";
    case Trying::WrongPassword: return "wrong_password";
    case Trying::NotFound: return "not_found";
    case Trying::Failed: return "failed";
    default: return "idle";
  }
}

// Why the Wi-Fi turned the sensor away, so the page can say so on the spot.
void onWifiEvent(arduino_event_id_t event, arduino_event_info_t info) {
  if (!inSetup) return;
  if (event == ARDUINO_EVENT_WIFI_STA_GOT_IP) {
    trying = Trying::Connected;
  } else if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED && trying == Trying::Connecting) {
    switch (info.wifi_sta_disconnected.reason) {
      case WIFI_REASON_AUTH_FAIL:
      case WIFI_REASON_AUTH_EXPIRE:
      case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
      case WIFI_REASON_HANDSHAKE_TIMEOUT:
        trying = Trying::WrongPassword;
        break;
      case WIFI_REASON_NO_AP_FOUND:
      case WIFI_REASON_NO_AP_FOUND_W_COMPATIBLE_SECURITY:
      case WIFI_REASON_NO_AP_FOUND_IN_AUTHMODE_THRESHOLD:
      case WIFI_REASON_NO_AP_FOUND_IN_RSSI_THRESHOLD:
        trying = Trying::NotFound;
        break;
      default:
        break;  // anything else: keep waiting until the time runs out
    }
  }
}

String jsonText(const String &text) {
  String out = "\"";
  for (size_t i = 0; i < text.length(); ++i) {
    const char c = text[i];
    if (c == '"' || c == '\\') {
      out += '\\';
      out += c;
    } else if (static_cast<uint8_t>(c) >= 0x20) {
      out += c;
    }
  }
  return out + "\"";
}

void touch() { setupTouchedAt = millis(); }

void sendJson(const String &body) {
  web.sendHeader("Cache-Control", "no-store");
  web.send(200, "application/json", body);
}

void refuse(const String &detail) { sendJson("{\"ok\":false,\"detail\":" + jsonText(detail) + "}"); }

// The phone's "am I online?" checks, and every other address, are sent to the page,
// which is what makes the phone pop it open.
void toPage() {
  web.sendHeader("Location", "http://" + SETUP_ADDRESS.toString() + "/", true);
  web.send(302, "text/plain", "");
}

void handlePage() {
  touch();
  web.sendHeader("Cache-Control", "no-store");
  web.send(200, "text/html", SETUP_PAGE);
}

void handleInfo() {
  touch();
  sendJson("{\"id\":" + jsonText(sensorId) + ",\"domain\":" + jsonText(SCHOOL_DOMAIN) +
           ",\"linked\":" + jsonText(linkedSchool()) + "}");
}

// The networks in range, strongest first, each name once, the setup Wi-Fi left out.
void handleScan() {
  touch();
  if (web.hasArg("again")) {
    scanJson = "";
    WiFi.scanDelete();
  }
  if (!scanJson.isEmpty()) {
    sendJson(scanJson);
    return;
  }
  const int found = WiFi.scanComplete();
  if (found == WIFI_SCAN_FAILED) WiFi.scanNetworks(true);
  if (found < 0) {
    sendJson("{\"scanning\":true}");
    return;
  }
  int order[40];
  const int count = min(found, 40);
  for (int i = 0; i < count; ++i) order[i] = i;
  std::sort(order, order + count, [](int a, int b) { return WiFi.RSSI(a) > WiFi.RSSI(b); });
  String list;
  for (int k = 0; k < count; ++k) {
    const int i = order[k];
    const String name = WiFi.SSID(i);
    if (name.isEmpty() || name == setupName || list.indexOf(jsonText(name) + ",") >= 0) continue;
    if (!list.isEmpty()) list += ",";
    list += "{\"ssid\":" + jsonText(name) + ",\"rssi\":" + String(WiFi.RSSI(i)) +
            ",\"lock\":" + (WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "false" : "true") + "}";
  }
  WiFi.scanDelete();
  scanJson = "{\"nets\":[" + list + "]}";
  sendJson(scanJson);
}

void handleWifiTry() {
  touch();
  trySsid = web.arg("ssid");
  tryPassword = web.arg("password");
  // Answer first: joining moves the sensor's channel, which drops the phone for a moment.
  sendJson("{\"ok\":true}");
  delay(50);
  WiFi.disconnect();
  trying = Trying::Connecting;
  tryStartedAt = millis();
  Serial.printf("trying %s...\n", trySsid.c_str());
  WiFi.begin(trySsid.c_str(), tryPassword.c_str());
}

void handleWifiState() {
  touch();
  if (trying == Trying::Connecting && millis() - tryStartedAt > 20000) trying = Trying::Failed;
  const String gateway = trying == Trying::Connected ? WiFi.gatewayIP().toString() : "";
  sendJson(String("{\"state\":\"") + tryingName() + "\",\"gateway\":" + jsonText(gateway) + "}");
}

// Where reps go: a school by its subdomain, or the base station of this Wi-Fi.
void handleServer() {
  touch();
  if (WiFi.status() != WL_CONNECTED) {
    refuse("The sensor lost the Wi-Fi. Go back and connect again.");
    return;
  }
  setupLocal = web.arg("kind") == "local";
  String host;
  if (setupLocal) {
    // The base station is the router of its own Wi-Fi, and handed the sensor its
    // address when it joined: no one types it (Devin, 2026-10-27).
    host = WiFi.gatewayIP().toString();
  } else {
    String sub = web.arg("sub");
    sub.trim();
    sub.toLowerCase();
    bool usable = sub.length() > 0 && sub.length() <= 63 && sub[0] != '-';
    for (size_t i = 0; i < sub.length(); ++i) usable = usable && (isalnum(sub[i]) || sub[i] == '-');
    if (!usable) {
      refuse("Type only letters, numbers and dashes, like test.");
      return;
    }
    host = sub + "." + SCHOOL_DOMAIN;
    // Checking a school's certificate needs the date: ask the internet first.
    if (!clockIsSet()) {
      configTime(0, 0, "pool.ntp.org");
      for (int i = 0; i < 80 && !clockIsSet(); ++i) delay(100);
      if (!clockIsSet()) {
        refuse("The sensor couldn't get the time from the internet. Does this Wi-Fi have internet?");
        return;
      }
    }
  }
  if (!serverAnswers(setupLocal, host)) {
    refuse(setupLocal ? String("No base station answered on this Wi-Fi. Pick the gym's base station Wi-Fi.")
                      : "Can't find a school at " + host + ". Check the spelling, and that this Wi-Fi has internet.");
    return;
  }
  setupHost = host;
  remote = !setupLocal;
  strlcpy(serverHost, host.c_str(), sizeof(serverHost));
  const bool linked = !setupLocal && loadLogin();
  sendJson("{\"ok\":true,\"host\":" + jsonText(host) + ",\"linked\":" + (linked ? "true" : "false") + "}");
}

// Only the letters a code can have, so nothing else reaches the school.
String cleanCode(String code) {
  code.toUpperCase();
  String out;
  for (size_t i = 0; i < code.length() && out.length() < 16; ++i) {
    if (isalnum(code[i]) || code[i] == '-') out += code[i];
  }
  return out;
}

void handleClaim() {
  touch();
  String detail;
  if (setupHost.isEmpty() || setupLocal) {
    refuse("Pick your school first.");
  } else if (claim(cleanCode(web.arg("code")).c_str(), detail)) {
    sendJson("{\"ok\":true}");
  } else {
    refuse(detail);
  }
}

void handleFinish() {
  touch();
  if (trying != Trying::Connected || setupHost.isEmpty()) {
    refuse("Setup isn't finished yet.");
    return;
  }
  saveNetwork({trySsid, tryPassword, setupLocal, setupHost});
  requestSetup(false);
  Serial.printf("saved: %s -> %s; restarting\n", trySsid.c_str(), setupHost.c_str());
  sendJson("{\"ok\":true}");
  restartAt = millis() + 2000;  // time for the page to show "done" first
}

}  // namespace

void startSetup() {
  inSetup = true;
  WiFi.onEvent(onWifiEvent);
  snprintf(setupName, sizeof(setupName), "EdgeAthlete-%s", sensorId + 3);
  WiFi.mode(WIFI_AP_STA);
  WiFi.setAutoReconnect(false);
  WiFi.softAPConfig(SETUP_ADDRESS, SETUP_ADDRESS, SETUP_MASK);
  WiFi.softAP(setupName);  // open, no password (Devin, 2026-10-27)
  // The phone is right beside the sensor during setup: a quieter radio is plenty, and
  // draws smaller bursts of current from a weak charger or cable.
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  dns.setErrorReplyCode(DNSReplyCode::NoError);
  dns.start(53, "*", SETUP_ADDRESS);
  web.on("/", HTTP_GET, handlePage);
  web.on("/api/info", HTTP_GET, handleInfo);
  web.on("/api/scan", HTTP_GET, handleScan);
  web.on("/api/wifi", HTTP_POST, handleWifiTry);
  web.on("/api/wifi", HTTP_GET, handleWifiState);
  web.on("/api/server", HTTP_POST, handleServer);
  web.on("/api/claim", HTTP_POST, handleClaim);
  web.on("/api/finish", HTTP_POST, handleFinish);
  web.onNotFound(toPage);
  web.begin();
  WiFi.scanNetworks(true);
  pinMode(LED_BUILTIN, OUTPUT);
  touch();
  Serial.printf("setup is open: on a phone, join the Wi-Fi %s\n", setupName);
}

void maintainSetup(uint32_t now) {
  dns.processNextRequest();
  web.handleClient();
  digitalWrite(LED_BUILTIN, (now / 500) % 2);  // the light blinks while setup is open
  if (restartAt != 0 && static_cast<int32_t>(now - restartAt) >= 0) ESP.restart();
  // Left untouched with settings already saved: go back to them, unchanged. millis()
  // again, not `now`: the page just answered may have touched it after `now` was read,
  // and `now - setupTouchedAt` then wrapped round to "4 billion ms untouched" and
  // restarted the sensor the moment a phone opened the page (seen 2026-10-27).
  if (networkCount > 0 && millis() - setupTouchedAt >= SETUP_IDLE_LIMIT_MS) {
    Serial.println("setup untouched for 10 minutes; back to the saved settings");
    requestSetup(false);
    ESP.restart();
  }
}

bool setupIsOpen() { return inSetup; }

void watchSetupButton(uint32_t now) {
  static bool ready = false;
  if (!ready) {
    pinMode(PIN_SETUP_BUTTON, INPUT_PULLUP);
    ready = true;
    return;
  }
  if (digitalRead(PIN_SETUP_BUTTON) != LOW) {
    buttonDownAt = 0;
    return;
  }
  if (buttonDownAt == 0) {
    buttonDownAt = now == 0 ? 1 : now;
  } else if (now - buttonDownAt >= SETUP_HOLD_MS) {
    Serial.println("button held: opening setup");
    requestSetup(true);
    delay(200);
    ESP.restart();
  }
}
