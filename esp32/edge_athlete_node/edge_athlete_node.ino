// edge_athlete_node.ino — the sensor on the bar: measures each rep and sends it to the
// school (or to a local install) over Wi-Fi.
//
// Why this exists: an athlete clips this to the bar, switches it on, and every rep's
// speed shows up on their rack screen. One firmware for every sensor; what it does
// follows the SERVER in secrets.h (spec 14 decision 6):
//   - a remote server (https://): it claims itself once with a one-time code from the
//     athlete's page, keeps the token the school answers with, and connects to the
//     school's sensors door, wss://<school>/sensors, checking the school's certificate
//     against the two roots in roots.h. It may only send under its own ID.
//   - a local install (http://): plain MQTT on port 1883 on the gym's Wi-Fi, no login.
//
// Measuring (spec 14 Phase 6): the BNO085 gives movement with gravity already taken
// out, and which way it is pointing. Turning the movement the "up" way of the room
// means a tilted bar measures the same speed. Speed is added up while the bar moves
// and reset when it is still; a movement that ends in stillness is one rep.
//
// Typed over USB (Arduino serial monitor, 115200, "Newline"):
//   claim K7MQ-2XPR   trade a code from the athlete's page for this sensor's login
//   forget            throw the saved login away (to claim again, or for someone else)
//   status            what the sensor is doing
//   watch             print the movement 5 times a second (again to stop), for tuning
//
// Not yet (spec 14 Phase 5): several saved Wi-Fi networks and servers, and the USB
// settings tool. For now the one network and server are built in from secrets.h.
#include <Arduino.h>
#include <HTTPClient.h>
#include <NetworkClientSecure.h>
#include <Preferences.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_mac.h>
#include <math.h>
#include <mqtt_client.h>
#include <time.h>

#include "SparkFun_BNO08x_Arduino_Library.h"
#include "roots.h"
#include "secrets.h"

namespace {

constexpr char FIRMWARE_VERSION[] = "2.0.0";
constexpr uint8_t BNO_ADDRESS = 0x4B;  // this board's address (found by bringup_check)
constexpr int PIN_RST = D1;            // restart line: pulsed once at start (see startImu)
constexpr uint16_t REPORT_INTERVAL_MS = 10;  // 100 readings a second
constexpr float REPORT_SECONDS = REPORT_INTERVAL_MS / 1000.0F;
constexpr uint32_t STILLNESS_DURATION_MS = 500;  // still this long = the rep is over
constexpr uint32_t PULSE_INTERVAL_MS = 5000;
constexpr uint32_t MOTION_INTERVAL_MS = 100;
constexpr uint32_t WATCH_INTERVAL_MS = 200;
constexpr uint32_t WIFI_RECONNECT_INTERVAL_MS = 10000;
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
constexpr float MAX_CONTRACT_VELOCITY_MPS = 10.0F;
constexpr int BATTERY_LEVEL_PERCENT = 100;  // USB-powered for now.

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
uint32_t previousReadingAt = 0;
uint8_t repNumber = 0;
float velocityMps = 0.0F;
float velocityTotal = 0.0F;
float peakVelocityMps = 0.0F;
uint32_t velocitySamples = 0;

uint32_t lastPulseAt = 0;
uint32_t lastMotionAt = 0;
uint32_t lastWatchAt = 0;
uint32_t lastWifiReconnectAt = 0;
bool watching = false;
char usbLine[64];
size_t usbLineLength = 0;

// ─────────────────────────── settings and login ───────────────────────────

// "https://school.example/" → remote, host "school.example"; "http://192.168.4.1" → local.
bool readServer() {
  const char *address = SERVER;
  const char *rest = nullptr;
  if (strncmp(address, "https://", 8) == 0) {
    remote = true;
    rest = address + 8;
  } else if (strncmp(address, "http://", 7) == 0) {
    remote = false;
    rest = address + 7;
  } else {
    return false;
  }
  size_t length = strcspn(rest, "/");
  if (length == 0 || length >= sizeof(serverHost)) {
    return false;
  }
  memcpy(serverHost, rest, length);
  serverHost[length] = '\0';
  return true;
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
  saved.clear();
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

void claim(const char *code) {
  if (!remote) {
    Serial.println("a local install needs no claim: a coach links the sensor to a rack");
    return;
  }
  if (WiFi.status() != WL_CONNECTED || !clockIsSet()) {
    Serial.println("not online yet (Wi-Fi and the time come first); try again in a moment");
    return;
  }
  NetworkClientSecure secure;
  secure.setCACert(TRUSTED_ROOTS);
  HTTPClient http;
  String url = String("https://") + serverHost + "/api/sensors/claim/";
  if (!http.begin(secure, url)) {
    Serial.println("couldn't start the claim");
    return;
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
    return;
  }
  char path[sizeof(loginPath)] = "/sensors";
  if (!jsonField(answer, "username", loginUser, sizeof(loginUser)) ||
      !jsonField(answer, "token", loginToken, sizeof(loginToken))) {
    Serial.println("the school's answer had no login in it");
    return;
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
  startMqtt();
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
  if (stillLongEnough && durationMs >= MIN_REP_DURATION_MS) {
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
  Serial.printf("server: %s (%s)\n", serverHost, remote ? "remote, encrypted" : "local install, plain");
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
    claim(code);
  } else if (strcmp(line, "forget") == 0) {
    forgetLogin();
    if (mqtt != nullptr) {
      esp_mqtt_client_stop(mqtt);
      esp_mqtt_client_destroy(mqtt);
      mqtt = nullptr;
      mqttConnected = false;
    }
    Serial.println("login forgotten; claim again with a new code");
  } else if (strcmp(line, "status") == 0) {
    printStatus();
  } else if (strcmp(line, "watch") == 0) {
    watching = !watching;
  } else if (*line) {
    Serial.println("commands: claim CODE · forget · status · watch");
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

// ─────────────────────────── start and run ───────────────────────────

bool started = false;  // the connection, once Wi-Fi and the time are ready

void maintainConnection(uint32_t now) {
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiReconnectAt >= WIFI_RECONNECT_INTERVAL_MS) {
      lastWifiReconnectAt = now;
      Serial.println("joining Wi-Fi...");
      WiFi.reconnect();
    }
    return;
  }
  // esp-mqtt reconnects on its own; it only needs starting once.
  if (!started && clockIsSet()) {
    started = true;
    Serial.printf("online: %s\n", WiFi.localIP().toString().c_str());
    if (!remote) {
      startMqtt();
    } else if (loadLogin()) {
      startMqtt();
    } else {
      Serial.println("this sensor has no login for this school yet.");
      Serial.println("get a code on the athlete's page (Add my sensor), then type:  claim CODE");
    }
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
  if (!readServer()) {
    Serial.println("[!] SERVER in secrets.h must start with https:// or http://");
    while (true) delay(1000);
  }
  startImu();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  configTime(0, 0, NTP_SERVER);
  previousReadingAt = millis();
  lastWifiReconnectAt = previousReadingAt;
}

void loop() {
  const uint32_t now = millis();
  readUsb();
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
