// edge_athlete_node.ino — the sensor on the bar: measures each rep and sends it to the
// school (or to a local install) over Wi-Fi.
//
// Why this exists: an athlete clips this to the bar, switches it on, and every rep's
// speed shows up on their rack screen. One firmware for every sensor (spec 14
// decision 6); what it does follows the network it finds:
//   - a remote server: it claimed itself once with a one-time code from the athlete's
//     page, keeps the token the school answered with, and connects to the school's
//     sensors door, wss://<school>/sensors, checking the school's certificate against
//     the two roots in roots.h. It may only send under its own ID.
//   - a local install: plain MQTT on port 1883 on the gym's Wi-Fi, no login.
//
// Setting it up (spec 14 Phase 8): a sensor with nothing saved, or one whose BOOT
// button is held 3 seconds, opens its own open Wi-Fi, EdgeAthlete-<id>. Joining it pops
// a page open on the phone (setup_page.h): pick the Wi-Fi, where reps go, the code.
// The settings are saved here, on the sensor; the setup Wi-Fi then switches off and
// costs nothing. Until something new is saved, nothing old is erased.
//
// Measuring (spec 14 Phase 6): the BNO085 gives movement with gravity already taken
// out, and which way it is pointing. Turning the movement the "up" way of the room
// means a tilted bar measures the same speed. Speed is added up while the bar moves;
// a movement that ends with the bar still, or slowed right down, is one rep.
//
// Build: the board's "Huge APP" layout (sketch.yaml). site.h (ignored by git, copy
// site.h.example) names the schools' base domain, so it stays out of this repo.
//
// Typed over USB (115200), for development:
//   claim K7MQ-2XPR   trade a code for this sensor's login (the setup page does this)
//   forget            throw the saved login away
//   setup             open the setup Wi-Fi now, same as holding the button
//   status            what the sensor is doing
//   watch             print the movement 5 times a second (again to stop), for tuning
#include <Arduino.h>
#include <DNSServer.h>
#include <algorithm>
#include <HTTPClient.h>
#include <NetworkClientSecure.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_mac.h>
#include <esp_system.h>
#include <math.h>
#include <mqtt_client.h>
#include <time.h>

#include "SparkFun_BNO08x_Arduino_Library.h"
#include "roots.h"
#include "setup_page.h"
#include "site.h"

#ifndef SCHOOL_DOMAIN
#error "site.h must define SCHOOL_DOMAIN (copy site.h.example)"
#endif

namespace {

constexpr char FIRMWARE_VERSION[] = "2.1.2";
constexpr uint8_t BNO_ADDRESS = 0x4B;  // this board's address (found by bringup_check)
constexpr int PIN_RST = D1;            // restart line: pulsed once at start (see startImu)
constexpr uint16_t REPORT_INTERVAL_MS = 10;  // 100 readings a second
constexpr float REPORT_SECONDS = REPORT_INTERVAL_MS / 1000.0F;
constexpr uint32_t STILLNESS_DURATION_MS = 500;  // still this long = the rep is over
constexpr uint32_t PULSE_INTERVAL_MS = 5000;
constexpr uint32_t MOTION_INTERVAL_MS = 100;
constexpr uint32_t WATCH_INTERVAL_MS = 200;
constexpr uint32_t READING_GAP_MS = 100;  // longer than this between readings: the rep is lost
// Movement with gravity taken out, in m/s^2, smoothed over about 50 ms. Lying still the
// BNO085 reads about 0.03; held in a hand (or at the top of a lift) it shakes to about
// 0.3, which has to count as still or one rep never ends (seen 2026-10-27).
constexpr float SMOOTHING = 0.2F;  // each reading moves the smoothed value 20% of the way
constexpr float MOVEMENT_THRESHOLD_MPS2 = 0.8F;
constexpr float STILLNESS_THRESHOLD_MPS2 = 0.4F;
constexpr uint32_t MIN_REP_DURATION_MS = 250;
constexpr uint32_t MAX_REP_DURATION_MS = 15000;
constexpr float MIN_REP_PEAK_VELOCITY_MPS = 0.15F;
// A rep also ends once the bar has slowed right down, even if it isn't quite still yet:
// a hand (or a lifter) settling after a rep shakes at 0.4 to 2 m/s^2 for a couple of
// seconds, and the next rep often starts before that, so waiting for stillness joined
// reps together (seen 2026-10-27). Slowed = under a quarter of the rep's top speed,
// moving under 1.5 m/s^2, for a quarter of a second. At the bottom of a squat the bar
// turns round hard, well over 1.5, so a rep isn't cut in two there.
constexpr float SETTLED_SPEED_FRACTION = 0.25F;
constexpr float SETTLED_THRESHOLD_MPS2 = 1.5F;
constexpr uint32_t SETTLED_DURATION_MS = 250;
constexpr float MAX_CONTRACT_VELOCITY_MPS = 10.0F;
constexpr int BATTERY_LEVEL_PERCENT = 100;  // USB-powered for now.

constexpr int PIN_SETUP_BUTTON = 9;          // the board's BOOT button
constexpr uint32_t SETUP_HOLD_MS = 3000;     // held this long: open setup
constexpr uint32_t SETUP_IDLE_LIMIT_MS = 10UL * 60 * 1000;  // untouched setup gives up
constexpr int MAX_NETWORKS = 4;
constexpr uint32_t NETWORK_SCAN_INTERVAL_MS = 15000;  // none of ours in range: look again
constexpr uint32_t LOST_NETWORK_MS = 30000;   // gone this long: look for another of ours
constexpr uint32_t CLOCK_RETRY_MS = 10000;
constexpr uint32_t LOCAL_CLOCK_REFRESH_MS = 60UL * 60 * 1000;
// The setup Wi-Fi's own address. Not 192.168.4.x: that's the base station's network,
// and the sensor is on both at once while it tries the gym's Wi-Fi.
const IPAddress SETUP_ADDRESS(10, 71, 0, 1);
const IPAddress SETUP_MASK(255, 255, 255, 0);

BNO08x imu;
Preferences saved;
esp_mqtt_client_handle_t mqtt = nullptr;
volatile bool mqttConnected = false;

char sensorId[16];  // "ea-" + the last 3 bytes of the chip's Wi-Fi address
bool remote = false;
char serverHost[96];
char loginUser[40];
char loginToken[128];
char loginPath[32];
char brokerUri[160];

// The newest orientation (game rotation vector: ignores the compass, which a steel
// bar and rack make useless) and movement.
float qi = 0.0F, qj = 0.0F, qk = 0.0F, qr = 1.0F;
float movementMps2 = 0.0F;
float verticalMps2 = 0.0F;

bool repActive = false;
uint32_t repStartedAt = 0;
uint32_t stillnessStartedAt = 0;
uint32_t settledStartedAt = 0;
uint32_t previousReadingAt = 0;
uint8_t repNumber = 0;
float velocityMps = 0.0F;
float velocityTotal = 0.0F;
float peakVelocityMps = 0.0F;
uint32_t velocitySamples = 0;

uint32_t lastPulseAt = 0;
uint32_t lastMotionAt = 0;
uint32_t lastWatchAt = 0;
bool watching = false;
char usbLine[64];
size_t usbLineLength = 0;

// ─────────────────────────── settings and login ───────────────────────────

// The saved Wi-Fi networks, each with where its reps go (spec 14 decision 6): a remote
// school (host = "<sub>.<domain>") or a local base station (host = its address). Kept in
// their own place in flash, apart from the login, so forgetting one leaves the other.
struct SavedNetwork {
  String ssid;
  String password;
  bool local;
  String host;
};
SavedNetwork networks[MAX_NETWORKS];
int networkCount = 0;

void loadNetworks() {
  saved.begin("ea-networks", true);
  networkCount = min(static_cast<int>(saved.getUChar("count", 0)), MAX_NETWORKS);
  for (int i = 0; i < networkCount; ++i) {
    const String n(i);
    networks[i] = {saved.getString(("s" + n).c_str(), ""), saved.getString(("p" + n).c_str(), ""),
                   saved.getBool(("l" + n).c_str(), false), saved.getString(("h" + n).c_str(), "")};
  }
  saved.end();
}

// The newest goes first; one with the same Wi-Fi name is replaced.
void saveNetwork(const SavedNetwork &network) {
  SavedNetwork kept[MAX_NETWORKS];
  int count = 0;
  kept[count++] = network;
  for (int i = 0; i < networkCount && count < MAX_NETWORKS; ++i) {
    if (networks[i].ssid != network.ssid) kept[count++] = networks[i];
  }
  saved.begin("ea-networks", false);
  saved.clear();
  saved.putUChar("count", count);
  for (int i = 0; i < count; ++i) {
    const String n(i);
    saved.putString(("s" + n).c_str(), kept[i].ssid);
    saved.putString(("p" + n).c_str(), kept[i].password);
    saved.putBool(("l" + n).c_str(), kept[i].local);
    saved.putString(("h" + n).c_str(), kept[i].host);
  }
  saved.end();
  loadNetworks();
}

// Why the sensor last restarted badly (power dip, crash, hang), kept across unplugging
// so it can be read later over USB (`status`): a sensor that drops off on one charger
// but not another shows "power dipped" here.
const char *resetName(esp_reset_reason_t why) {
  switch (why) {
    case ESP_RST_POWERON: return "switched on";
    case ESP_RST_SW: return "restarted itself";
    case ESP_RST_BROWNOUT: return "power dipped too low";
    case ESP_RST_PANIC: return "crashed";
    case ESP_RST_INT_WDT:
    case ESP_RST_TASK_WDT:
    case ESP_RST_WDT: return "hung, and the watchdog restarted it";
    case ESP_RST_DEEPSLEEP: return "woke up";
    default: return "restarted";
  }
}

void recordStart(esp_reset_reason_t why) {
  const bool trouble = why == ESP_RST_BROWNOUT || why == ESP_RST_PANIC || why == ESP_RST_INT_WDT ||
                       why == ESP_RST_TASK_WDT || why == ESP_RST_WDT;
  if (!trouble) return;
  saved.begin("ea-diag", false);
  saved.putUChar("last", static_cast<uint8_t>(why));
  saved.putUShort("count", saved.getUShort("count", 0) + 1);
  saved.end();
}

void printTrouble() {
  saved.begin("ea-diag", true);
  const uint16_t count = saved.getUShort("count", 0);
  const auto last = static_cast<esp_reset_reason_t>(saved.getUChar("last", 0));
  saved.end();
  if (count == 0) {
    Serial.println("restarts after trouble: none");
  } else {
    Serial.printf("restarts after trouble: %u, the last because it %s\n", count, resetName(last));
  }
}

// "Open setup" survives the restart it takes to get there.
void requestSetup(bool open) {
  saved.begin("ea-networks", false);
  saved.putBool("setup", open);
  saved.end();
}

bool setupRequested() {
  saved.begin("ea-networks", true);
  const bool open = saved.getBool("setup", false);
  saved.end();
  return open;
}

// The saved login belongs to one school; a different SERVER means claiming again.
bool loadLogin() {
  saved.begin("edgeathlete", true);
  String forServer = saved.getString("server", "");
  String user = saved.getString("user", "");
  String token = saved.getString("token", "");
  String path = saved.getString("path", "/sensors");
  saved.end();
  if (forServer != serverHost || user.isEmpty() || token.isEmpty()) {
    return false;
  }
  strlcpy(loginUser, user.c_str(), sizeof(loginUser));
  strlcpy(loginToken, token.c_str(), sizeof(loginToken));
  strlcpy(loginPath, path.c_str(), sizeof(loginPath));
  return true;
}

void forgetLogin() {
  saved.begin("edgeathlete", false);
  saved.clear();  // only the login lives here; the networks are in "ea-networks"
  saved.end();
  loginToken[0] = '\0';
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

// ─────────────────────────── the connection ───────────────────────────

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

void startMqtt() {
  if (mqtt != nullptr) {
    esp_mqtt_client_stop(mqtt);
    esp_mqtt_client_destroy(mqtt);
    mqtt = nullptr;
    mqttConnected = false;
  }
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

bool clockIsSet() {
  return time(nullptr) > 1704067200;  // 2024-01-01; before that, the boot clock
}

// Trades a one-time code for this sensor's login at serverHost. Returns true when
// claimed; otherwise `detail` says why, in words the athlete can act on.
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
  saved.begin("edgeathlete", false);
  saved.putString("server", serverHost);
  saved.putString("user", loginUser);
  saved.putString("token", loginToken);
  saved.putString("path", loginPath);
  saved.end();
  Serial.println("claimed: this sensor now belongs to the athlete whose code that was");
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

// Asks a server whether it's an Edge Athlete server (GET /api/health/), over HTTPS for a
// school. On a local install its answer also sets the clock.
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

// ─────────────────────────── messages ───────────────────────────

bool formatUtcTimestamp(char *output, size_t outputSize) {
  if (!clockIsSet()) return false;
  const time_t now = time(nullptr);
  tm utcTime;
  gmtime_r(&now, &utcTime);
  return strftime(output, outputSize, "%Y-%m-%dT%H:%M:%SZ", &utcTime) > 0;
}

// Reps are kept and sent again until the school says it has them (QoS 1), also across
// a short drop of the connection. Pulses and live movement are only worth sending now.
// Online, a rep goes out at once; queued, it waited up to a second for the connection's
// next turn, so only a rep with no connection to go out on waits in the queue.
void send(const char *kind, const char *payload, bool mustArrive) {
  if (mqtt == nullptr) return;
  char topic[96];
  snprintf(topic, sizeof(topic), "edgeathlete/node/%s/%s", sensorId, kind);
  if (mustArrive) {
    const bool now = mqttConnected && esp_mqtt_client_publish(mqtt, topic, payload, 0, 1, 0) >= 0;
    if (!now) esp_mqtt_client_enqueue(mqtt, topic, payload, 0, 1, 0, true);
    Serial.printf("rep %u sent%s\n", repNumber, now ? "" : " (kept until reconnected)");
  } else if (mqttConnected) {
    esp_mqtt_client_publish(mqtt, topic, payload, 0, 0, 0);
  }
}

void publishPulse() {
  char timestamp[25];
  if (!formatUtcTimestamp(timestamp, sizeof(timestamp))) return;
  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"node_id\":\"%s\",\"event_type\":\"pulse\",\"battery_level\":%d,"
           "\"signal_strength\":%d,\"firmware_version\":\"%s\",\"timestamp\":\"%s\"}",
           sensorId, BATTERY_LEVEL_PERCENT, constrain(WiFi.RSSI(), -120, 0), FIRMWARE_VERSION, timestamp);
  send("pulse", payload, false);
}

void publishMotion() {
  char timestamp[25];
  if (!formatUtcTimestamp(timestamp, sizeof(timestamp))) return;
  float speed = repActive ? fabsf(velocityMps) : 0.0F;
  if (!isfinite(speed)) speed = 0.0F;
  speed = constrain(speed, 0.0F, MAX_CONTRACT_VELOCITY_MPS);
  char payload[192];
  snprintf(payload, sizeof(payload),
           "{\"node_id\":\"%s\",\"event_type\":\"motion\",\"velocity\":%.3f,\"timestamp\":\"%s\"}",
           sensorId, speed, timestamp);
  send("motion", payload, false);
}

void publishRep(uint32_t durationMs) {
  if (velocitySamples == 0 || !isfinite(peakVelocityMps) ||
      peakVelocityMps < MIN_REP_PEAK_VELOCITY_MPS || peakVelocityMps > MAX_CONTRACT_VELOCITY_MPS) {
    Serial.println("movement too small or too fast for a rep; not sent");
    return;
  }
  char timestamp[25];
  if (!formatUtcTimestamp(timestamp, sizeof(timestamp))) {
    Serial.println("the time isn't set yet; rep not sent");
    return;
  }
  const float meanVelocityMps = velocityTotal / static_cast<float>(velocitySamples);
  if (!isfinite(meanVelocityMps) || meanVelocityMps > peakVelocityMps) return;
  repNumber = (repNumber % 100) + 1;
  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"node_id\":\"%s\",\"rep_number\":%u,\"mean_velocity\":%.3f,"
           "\"peak_velocity\":%.3f,\"duration_ms\":%lu,\"timestamp\":\"%s\"}",
           sensorId, static_cast<unsigned int>(repNumber), meanVelocityMps, peakVelocityMps,
           static_cast<unsigned long>(durationMs), timestamp);
  Serial.printf("rep: mean %.2f m/s, peak %.2f m/s, %lu ms\n", meanVelocityMps, peakVelocityMps,
                static_cast<unsigned long>(durationMs));
  send("rep", payload, true);
}

// ─────────────────────────── measuring ───────────────────────────

void resetRep() {
  repActive = false;
  stillnessStartedAt = 0;
  settledStartedAt = 0;
  velocityMps = 0.0F;
  velocityTotal = 0.0F;
  peakVelocityMps = 0.0F;
  velocitySamples = 0;
}

// Turns the sensor's own x/y/z movement into the room's "up", using its orientation
// (the third row of the rotation the quaternion describes). A tilted bar then measures
// the same as a level one.
float upwardPart(float x, float y, float z) {
  return 2.0F * (qi * qk - qr * qj) * x +
         2.0F * (qj * qk + qr * qi) * y +
         (1.0F - 2.0F * (qi * qi + qj * qj)) * z;
}

// One movement reading, 100 a second.
void processReading(float x, float y, float z, uint32_t at) {
  movementMps2 += SMOOTHING * (sqrtf(x * x + y * y + z * z) - movementMps2);
  verticalMps2 = upwardPart(x, y, z);
  const uint32_t gap = at - previousReadingAt;
  previousReadingAt = at;

  if (!repActive) {
    if (movementMps2 >= MOVEMENT_THRESHOLD_MPS2) {
      resetRep();
      repActive = true;
      repStartedAt = at;
    }
    return;
  }
  if (gap > READING_GAP_MS) {
    Serial.println("readings stopped for a moment; that movement is lost");
    resetRep();
    return;
  }
  // The sensor sends a reading every 10 ms, so each one adds 10 ms of speed.
  velocityMps += verticalMps2 * REPORT_SECONDS;
  const float speed = fabsf(velocityMps);
  velocityTotal += speed;
  peakVelocityMps = fmaxf(peakVelocityMps, speed);
  ++velocitySamples;

  if (movementMps2 < STILLNESS_THRESHOLD_MPS2) {
    if (stillnessStartedAt == 0) stillnessStartedAt = at;
  } else {
    stillnessStartedAt = 0;
  }
  const uint32_t durationMs = at - repStartedAt;
  const bool stillLongEnough = stillnessStartedAt != 0 && at - stillnessStartedAt >= STILLNESS_DURATION_MS;
  const bool slowed = peakVelocityMps >= MIN_REP_PEAK_VELOCITY_MPS &&
                      speed < peakVelocityMps * SETTLED_SPEED_FRACTION &&
                      movementMps2 < SETTLED_THRESHOLD_MPS2;
  if (slowed) {
    if (settledStartedAt == 0) settledStartedAt = at;
  } else {
    settledStartedAt = 0;
  }
  const bool settledLongEnough = settledStartedAt != 0 && at - settledStartedAt >= SETTLED_DURATION_MS;
  if ((stillLongEnough || settledLongEnough) && durationMs >= MIN_REP_DURATION_MS) {
    publishRep(durationMs);
    resetRep();
  } else if (durationMs >= MAX_REP_DURATION_MS) {
    Serial.println("moved for 15 s without stopping; not a rep");
    resetRep();
  }
}

void turnOnReadings() {
  const bool ok = imu.enableLinearAccelerometer(REPORT_INTERVAL_MS) &&
                  imu.enableGameRotationVector(REPORT_INTERVAL_MS);
  Serial.println(ok ? "readings on: movement + orientation, 100 a second"
                    : "[!] the BNO085 refused a reading");
}

// Same start as motion_test.ino, which settled what works on this board (2026-10-21):
// one clean restart done here, RST then held high, and the library given neither INT
// nor RST (handed either, no reading got through).
void startImu() {
  pinMode(PIN_RST, OUTPUT);
  digitalWrite(PIN_RST, LOW);
  delay(20);
  digitalWrite(PIN_RST, HIGH);
  delay(300);
  Wire.begin(SDA, SCL, 100000);
  Wire.setTimeOut(1000);
  for (int attempt = 1; attempt <= 3; ++attempt) {
    if (imu.begin(BNO_ADDRESS, Wire)) {
      Serial.println("BNO085 found");
      delay(200);
      turnOnReadings();
      return;
    }
    Serial.printf("BNO085 start attempt %d: no answer\n", attempt);
    delay(500);
  }
  Serial.println("[!] the BNO085 didn't start. Check the wires; bringup_check helps. Restarting.");
  delay(2000);
  ESP.restart();
}

void readImu(uint32_t now) {
  if (imu.wasReset()) {
    Serial.println("the BNO085 restarted; turning the readings back on");
    turnOnReadings();
  }
  while (imu.getSensorEvent()) {
    switch (imu.getSensorEventID()) {
      case SENSOR_REPORTID_GAME_ROTATION_VECTOR:
        qi = imu.getGameQuatI();
        qj = imu.getGameQuatJ();
        qk = imu.getGameQuatK();
        qr = imu.getGameQuatReal();
        break;
      case SENSOR_REPORTID_LINEAR_ACCELERATION:
        processReading(imu.getLinAccelX(), imu.getLinAccelY(), imu.getLinAccelZ(), now);
        break;
    }
  }
}

// ─────────────────────────── USB commands ───────────────────────────

void printStatus() {
  Serial.printf("sensor %s, firmware %s\n", sensorId, FIRMWARE_VERSION);
  for (int i = 0; i < networkCount; ++i) {
    Serial.printf("saved wi-fi %d: %s -> %s (%s)\n", i + 1, networks[i].ssid.c_str(), networks[i].host.c_str(),
                  networks[i].local ? "local install" : "remote server");
  }
  if (networkCount == 0) Serial.println("saved wi-fi: none (setup is open)");
  printTrouble();
  Serial.printf("server: %s (%s)\n", serverHost[0] ? serverHost : "none yet", remote ? "remote, encrypted" : "local install, plain");
  Serial.printf("wi-fi: %s, time: %s\n",
                WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "not connected",
                clockIsSet() ? "set" : "not set yet");
  if (remote) Serial.printf("login: %s\n", loginToken[0] ? "saved" : "none yet: type  claim CODE");
  Serial.printf("connection: %s\n", mqttConnected ? "connected" : "not connected");
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
    if (mqtt != nullptr) {
      esp_mqtt_client_stop(mqtt);
      esp_mqtt_client_destroy(mqtt);
      mqtt = nullptr;
      mqttConnected = false;
    }
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

void readUsb() {
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
}

// ─────────────────────────── normal running ───────────────────────────

int current = -1;        // which saved network the sensor is on (or joining); -1 = none yet
bool started = false;    // the connection to the server, once online with the time
bool timeAsked = false;  // the internet's time servers asked (remote)
uint32_t lastScanAt = 0;
uint32_t offlineSince = 0;
uint32_t clockTriedAt = 0;
uint32_t clockSetAt = 0;
uint32_t buttonDownAt = 0;

void stopMqtt() {
  if (mqtt == nullptr) return;
  esp_mqtt_client_stop(mqtt);
  esp_mqtt_client_destroy(mqtt);
  mqtt = nullptr;
  mqttConnected = false;
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

void maintainConnection(uint32_t now) {
  if (current < 0) {
    if (lastScanAt == 0 || now - lastScanAt >= NETWORK_SCAN_INTERVAL_MS) joinSavedNetwork(now);
    return;
  }
  if (WiFi.status() != WL_CONNECTED) {
    if (offlineSince == 0) offlineSince = now;
    // Gone a while: maybe the sensor moved (home to gym); look for any saved network.
    if (now - offlineSince >= LOST_NETWORK_MS && now - lastScanAt >= NETWORK_SCAN_INTERVAL_MS && !repActive) {
      Serial.println("lost the Wi-Fi; looking for any saved one");
      WiFi.disconnect();
      joinSavedNetwork(now);
    }
    return;
  }
  offlineSince = 0;
  // The time: a school's from the internet; a base station's from its own answers, again
  // every hour (not mid-rep: asking takes a moment).
  if (remote && !timeAsked) {
    configTime(0, 0, "pool.ntp.org");
    timeAsked = true;
  } else if (!remote && !repActive &&
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

void watchSetupButton(uint32_t now) {
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

// ─────────────────────────── setup ───────────────────────────

bool inSetup = false;
char setupName[32];  // the setup Wi-Fi: "EdgeAthlete-" + the end of the sensor's ID
DNSServer dns;
WebServer web(80);
uint32_t setupTouchedAt = 0;
uint32_t restartAt = 0;
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
  saved.begin("edgeathlete", true);
  const String linked = saved.getString("token", "").isEmpty() ? "" : saved.getString("server", "");
  saved.end();
  sendJson("{\"id\":" + jsonText(sensorId) + ",\"domain\":" + jsonText(SCHOOL_DOMAIN) +
           ",\"linked\":" + jsonText(linked) + "}");
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

// Where reps go: a school by its subdomain, or a local base station by its address.
void handleServer() {
  touch();
  if (WiFi.status() != WL_CONNECTED) {
    refuse("The sensor lost the Wi-Fi. Go back and connect again.");
    return;
  }
  setupLocal = web.arg("kind") == "local";
  String host;
  if (setupLocal) {
    host = web.arg("host");
    host.trim();
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
    refuse(setupLocal ? "No base station answered at " + host + "."
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

void startSetup() {
  inSetup = true;
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

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1500);  // give the computer a moment to start listening
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  snprintf(sensorId, sizeof(sensorId), "ea-%02x%02x%02x", mac[3], mac[4], mac[5]);
  Serial.printf("\nEdge Athlete sensor %s, firmware %s\n", sensorId, FIRMWARE_VERSION);
  const esp_reset_reason_t why = esp_reset_reason();
  recordStart(why);
  Serial.printf("started because it %s\n", resetName(why));
  pinMode(PIN_SETUP_BUTTON, INPUT_PULLUP);
  WiFi.onEvent(onWifiEvent);
  loadNetworks();
  if (networkCount == 0 || setupRequested()) {
    startSetup();  // nothing measured during setup, so the BNO085 waits
    return;
  }
  startImu();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  Serial.printf("%d saved Wi-Fi network%s\n", networkCount, networkCount == 1 ? "" : "s");
  previousReadingAt = millis();
}

void loop() {
  const uint32_t now = millis();
  readUsb();
  if (inSetup) {
    maintainSetup(now);
    return;
  }
  watchSetupButton(now);
  readImu(now);
  maintainConnection(now);

  if (now - lastPulseAt >= PULSE_INTERVAL_MS) {
    lastPulseAt = now;
    publishPulse();
  }
  if (now - lastMotionAt >= MOTION_INTERVAL_MS) {
    lastMotionAt = now;
    publishMotion();
  }
  if (watching && now - lastWatchAt >= WATCH_INTERVAL_MS) {
    lastWatchAt = now;
    Serial.printf("movement %5.2f m/s2, up %5.2f m/s2, speed %5.2f m/s%s\n", movementMps2, verticalMps2,
                  fabsf(velocityMps), repActive ? " (moving)" : "");
  }
}
