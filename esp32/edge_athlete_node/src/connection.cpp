// connection.cpp — joining a saved Wi-Fi, the clock, the MQTT connection to the
// server, and the claim (see connection.h for why these live together).
#include "connection.h"

#include <HTTPClient.h>
#include <NetworkClientSecure.h>
#include <WiFi.h>
#include <mqtt_client.h>
#include <time.h>

#include "measuring.h"
#include "roots.h"
#include "settings.h"
#include "shared.h"

namespace {

constexpr uint32_t NETWORK_SCAN_INTERVAL_MS = 15000;  // none of ours in range: look again
constexpr uint32_t LOST_NETWORK_MS = 30000;   // gone this long: look for another of ours
constexpr uint32_t CLOCK_RETRY_MS = 10000;
constexpr uint32_t LOCAL_CLOCK_REFRESH_MS = 60UL * 60 * 1000;

esp_mqtt_client_handle_t mqtt = nullptr;
volatile bool mqttConnected = false;
char brokerUri[160];

int current = -1;        // which saved network the sensor is on (or joining); -1 = none yet
bool started = false;    // the connection to the server, once online with the time
bool timeAsked = false;  // the internet's time servers asked (remote)
uint32_t lastScanAt = 0;
uint32_t offlineSince = 0;
uint32_t clockTriedAt = 0;
uint32_t clockSetAt = 0;

void onMqttEvent(void *, esp_event_base_t, int32_t eventId, void *eventData) {
  auto *event = static_cast<esp_mqtt_event_handle_t>(eventData);
  switch (eventId) {
    case MQTT_EVENT_CONNECTED:
      mqttConnected = true;
      Serial.printf("connected to %s\n", brokerUri);
      break;
    case MQTT_EVENT_DISCONNECTED:
      if (mqttConnected) Serial.println("disconnected; trying again");
      mqttConnected = false;
      break;
    case MQTT_EVENT_ERROR:
      if (event->error_handle->error_type == MQTT_ERROR_TYPE_CONNECTION_REFUSED) {
        const int code = event->error_handle->connect_return_code;
        Serial.printf("the school refused the login (%d): %s\n", code,
                      code == MQTT_CONNECTION_REFUSE_BAD_USERNAME ? "wrong token, claim again"
                      : code == MQTT_CONNECTION_REFUSE_NOT_AUTHORIZED ? "not allowed: removed? claim again"
                      : "see the broker's log");
      } else if (event->error_handle->esp_tls_last_esp_err != 0) {
        Serial.printf("couldn't reach the school securely (TLS error 0x%x): check the address and the time\n",
                      event->error_handle->esp_tls_last_esp_err);
      }
      break;
    default:
      break;
  }
}

// The school answers {"username": ..., "token": ..., "path": ...}; these are plain
// letters, digits, - and _, so finding the quotes is enough.
bool jsonField(const String &body, const char *name, char *output, size_t outputSize) {
  String key = String("\"") + name + "\"";
  int at = body.indexOf(key);
  if (at < 0) return false;
  at = body.indexOf('"', body.indexOf(':', at + key.length()) + 1);
  int end = body.indexOf('"', at + 1);
  if (at < 0 || end < 0 || static_cast<size_t>(end - at - 1) >= outputSize) return false;
  strlcpy(output, body.c_str() + at + 1, end - at);
  return true;
}

// The day's date and time from a server's own answer ("Date: Tue, 27 Oct 2026 16:23:30
// GMT"). A local install's Wi-Fi has no internet and the base station runs no time
// server, but every answer it gives carries the time (spec 14 Phase 8).
bool setClockFrom(const String &date) {
  static const char MONTHS[] = "JanFebMarAprMayJunJulAugSepOctNovDec";
  char month[4] = "";
  int day = 0, year = 0, hour = 0, minute = 0, second = 0;
  if (sscanf(date.c_str(), "%*3s, %d %3s %d %d:%d:%d", &day, month, &year, &hour, &minute, &second) != 6) {
    return false;
  }
  const char *found = strstr(MONTHS, month);
  if (found == nullptr || year < 2024) return false;
  int m = (found - MONTHS) / 3 + 1;
  // Days since 1970-01-01 (Howard Hinnant's days_from_civil).
  const int y = year - (m <= 2);
  const int era = y / 400;
  const int yoe = y - era * 400;
  const int doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + day - 1;
  const int doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  const long days = static_cast<long>(era) * 146097 + doe - 719468;
  timeval now = {static_cast<time_t>(days * 86400L + hour * 3600L + minute * 60L + second), 0};
  return settimeofday(&now, nullptr) == 0;
}

// Looks for the saved networks and joins the first one in range, in saved order (the
// newest saved first). Each network says where its reps go.
void joinSavedNetwork(uint32_t now) {
  lastScanAt = now;
  const int found = WiFi.scanNetworks();
  for (int i = 0; i < networkCount; ++i) {
    for (int j = 0; j < found; ++j) {
      if (WiFi.SSID(j) != networks[i].ssid) continue;
      WiFi.scanDelete();
      if (i != current) {
        stopMqtt();
        started = false;
      }
      current = i;
      remote = !networks[i].local;
      strlcpy(serverHost, networks[i].host.c_str(), sizeof(serverHost));
      Serial.printf("joining %s...\n", networks[i].ssid.c_str());
      WiFi.begin(networks[i].ssid.c_str(), networks[i].password.c_str());
      offlineSince = now;
      return;
    }
  }
  WiFi.scanDelete();
  Serial.println("none of the saved Wi-Fi is in range; looking again shortly");
}

}  // namespace

void startMqtt() {
  stopMqtt();
  esp_mqtt_client_config_t config = {};
  if (remote) {
    snprintf(brokerUri, sizeof(brokerUri), "wss://%s:443%s", serverHost, loginPath);
    config.broker.verification.certificate = TRUSTED_ROOTS;
    config.credentials.username = loginUser;
    config.credentials.authentication.password = loginToken;
  } else {
    snprintf(brokerUri, sizeof(brokerUri), "mqtt://%s:1883", serverHost);
  }
  config.broker.address.uri = brokerUri;
  config.credentials.client_id = sensorId;
  config.session.keepalive = 30;
  config.network.reconnect_timeout_ms = 3000;
  mqtt = esp_mqtt_client_init(&config);
  esp_mqtt_client_register_event(mqtt, MQTT_EVENT_ANY, onMqttEvent, nullptr);
  esp_mqtt_client_start(mqtt);
  Serial.printf("connecting to %s as %s\n", brokerUri, sensorId);
}

void stopMqtt() {
  if (mqtt == nullptr) return;
  esp_mqtt_client_stop(mqtt);
  esp_mqtt_client_destroy(mqtt);
  mqtt = nullptr;
  mqttConnected = false;
}

bool serverConnected() { return mqttConnected; }

// Online, a rep goes out at once; queued, it waited up to a second for the connection's
// next turn, so only a rep with no connection to go out on waits in the queue.
Sent publish(const char *kind, const char *payload, bool mustArrive) {
  if (mqtt == nullptr) return Sent::Dropped;
  char topic[96];
  snprintf(topic, sizeof(topic), "edgeathlete/node/%s/%s", sensorId, kind);
  if (mustArrive) {
    if (mqttConnected && esp_mqtt_client_publish(mqtt, topic, payload, 0, 1, 0) >= 0) return Sent::Now;
    esp_mqtt_client_enqueue(mqtt, topic, payload, 0, 1, 0, true);
    return Sent::Kept;
  }
  if (!mqttConnected) return Sent::Dropped;
  esp_mqtt_client_publish(mqtt, topic, payload, 0, 0, 0);
  return Sent::Now;
}

bool clockIsSet() {
  return time(nullptr) > 1704067200;  // 2024-01-01; before that, the boot clock
}

bool serverAnswers(bool local, const String &host) {
  HTTPClient http;
  NetworkClientSecure secure;
  NetworkClient plain;
  const char *keep[] = {"Date"};
  bool begun;
  if (local) {
    begun = http.begin(plain, "http://" + host + "/api/health/");
  } else {
    secure.setCACert(TRUSTED_ROOTS);
    begun = http.begin(secure, "https://" + host + "/api/health/");
  }
  if (!begun) return false;
  http.setTimeout(6000);
  http.collectHeaders(keep, 1);
  const int status = http.GET();
  const String date = http.header("Date");
  http.end();
  if (status != 200) return false;
  if (local) setClockFrom(date);
  return true;
}

bool claim(const char *code, String &detail) {
  if (!remote) {
    detail = "A local install needs no code: the coach links the sensor to a rack.";
    return false;
  }
  if (WiFi.status() != WL_CONNECTED || !clockIsSet()) {
    detail = "The sensor isn't online yet. Try again in a moment.";
    return false;
  }
  NetworkClientSecure secure;
  secure.setCACert(TRUSTED_ROOTS);
  HTTPClient http;
  String url = String("https://") + serverHost + "/api/sensors/claim/";
  if (!http.begin(secure, url)) {
    detail = "The sensor couldn't reach the school.";
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Accept", "application/json");
  String body = String("{\"code\":\"") + code + "\",\"node_id\":\"" + sensorId + "\"}";
  Serial.printf("claiming %s at %s...\n", sensorId, serverHost);
  const int status = http.POST(body);
  String answer = http.getString();
  http.end();
  if (status != 201) {
    Serial.printf("the school refused the claim (%d): %s\n", status, answer.c_str());
    char said[200] = "";
    jsonField(answer, "detail", said, sizeof(said));
    if (status == 409 || status == 503) {
      detail = said;  // another athlete's sensor; or the school can't take sensors now
    } else if (status == 429) {
      detail = "Too many tries. Wait a minute, then try again.";
    } else if (status <= 0) {
      detail = "The sensor couldn't reach the school.";
    } else {
      detail = "That code didn't work. It may be used, out of time or mistyped. Get a new one on your athlete page.";
    }
    return false;
  }
  char path[sizeof(loginPath)] = "/sensors";
  if (!jsonField(answer, "username", loginUser, sizeof(loginUser)) ||
      !jsonField(answer, "token", loginToken, sizeof(loginToken))) {
    detail = "The school's answer had no login in it.";
    return false;
  }
  jsonField(answer, "path", path, sizeof(path));
  strlcpy(loginPath, path, sizeof(loginPath));
  saveLogin();
  Serial.println("claimed: this sensor now belongs to the athlete whose code that was");
  return true;
}

void maintainConnection(uint32_t now) {
  if (current < 0) {
    if (lastScanAt == 0 || now - lastScanAt >= NETWORK_SCAN_INTERVAL_MS) joinSavedNetwork(now);
    return;
  }
  if (WiFi.status() != WL_CONNECTED) {
    if (offlineSince == 0) offlineSince = now;
    // Gone a while: maybe the sensor moved (home to gym); look for any saved network.
    if (now - offlineSince >= LOST_NETWORK_MS && now - lastScanAt >= NETWORK_SCAN_INTERVAL_MS && !repInProgress()) {
      Serial.println("lost the Wi-Fi; looking for any saved one");
      WiFi.disconnect();
      joinSavedNetwork(now);
    }
    return;
  }
  offlineSince = 0;
  // On a local install, the base station is whoever gave this Wi-Fi its addresses: use
  // that, fresh on every join, rather than the address saved at setup, so a base
  // station whose address changes is still found.
  if (!remote && !started) {
    strlcpy(serverHost, WiFi.gatewayIP().toString().c_str(), sizeof(serverHost));
  }
  // The time: a school's from the internet; a base station's from its own answers, again
  // every hour (not mid-rep: asking takes a moment).
  if (remote && !timeAsked) {
    configTime(0, 0, "pool.ntp.org");
    timeAsked = true;
  } else if (!remote && !repInProgress() &&
             ((!clockIsSet() && (clockTriedAt == 0 || now - clockTriedAt >= CLOCK_RETRY_MS)) ||
              (clockSetAt != 0 && now - clockSetAt >= LOCAL_CLOCK_REFRESH_MS))) {
    clockTriedAt = now;
    if (serverAnswers(true, serverHost)) {
      clockSetAt = now;
    } else {
      Serial.printf("the base station at %s didn't answer; trying again\n", serverHost);
    }
  }
  // esp-mqtt reconnects on its own; it only needs starting once per network.
  if (!started && clockIsSet()) {
    started = true;
    Serial.printf("online: %s\n", WiFi.localIP().toString().c_str());
    if (!remote) {
      startMqtt();
    } else if (loadLogin()) {
      startMqtt();
    } else {
      Serial.println("no login for this school; hold the button 3 s to set the sensor up again");
    }
  }
}
