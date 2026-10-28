// measuring.cpp — reads the BNO085 and turns the bar's movement into reps.
//
// The BNO085 gives movement with gravity already taken out, and which way it is
// pointing. Turning the movement the "up" way of the room means a tilted bar measures
// the same speed. Speed is added up while the bar moves; a movement that ends with the
// bar still, or slowed right down, is one rep (spec 14 Phase 6).
#include "measuring.h"

#include <Wire.h>
#include <math.h>

#include "SparkFun_BNO08x_Arduino_Library.h"
#include "messages.h"

namespace {

constexpr uint8_t BNO_ADDRESS = 0x4B;  // this board's address (found by bringup_check)
constexpr int PIN_RST = D1;            // restart line: pulsed once at start (see startImu)
constexpr uint16_t REPORT_INTERVAL_MS = 10;  // 100 readings a second
constexpr float REPORT_SECONDS = REPORT_INTERVAL_MS / 1000.0F;
constexpr uint32_t STILLNESS_DURATION_MS = 500;  // still this long = the rep is over
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
// A rep also ends once the bar has slowed right down, even if it isn't quite still yet:
// a hand (or a lifter) settling after a rep shakes at 0.4 to 2 m/s^2 for a couple of
// seconds, and the next rep often starts before that, so waiting for stillness joined
// reps together (seen 2026-10-27). Slowed = under a quarter of the rep's top speed,
// moving under 1.5 m/s^2, for a quarter of a second. At the bottom of a squat the bar
// turns round hard, well over 1.5, so a rep isn't cut in two there.
constexpr float SETTLED_SPEED_FRACTION = 0.25F;
constexpr float SETTLED_THRESHOLD_MPS2 = 1.5F;
constexpr uint32_t SETTLED_DURATION_MS = 250;

BNO08x imu;

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
float velocityMps = 0.0F;
float velocityTotal = 0.0F;
float peakVelocityMps = 0.0F;
uint32_t velocitySamples = 0;

void resetRep() {
  repActive = false;
  stillnessStartedAt = 0;
  settledStartedAt = 0;
  velocityMps = 0.0F;
  velocityTotal = 0.0F;
  peakVelocityMps = 0.0F;
  velocitySamples = 0;
}

// A finished movement: sent as a rep if it looks like one.
void finishRep(uint32_t durationMs) {
  if (velocitySamples == 0 || !isfinite(peakVelocityMps) ||
      peakVelocityMps < MIN_REP_PEAK_VELOCITY_MPS || peakVelocityMps > MAX_CONTRACT_VELOCITY_MPS) {
    Serial.println("movement too small or too fast for a rep; not sent");
    return;
  }
  const float meanVelocityMps = velocityTotal / static_cast<float>(velocitySamples);
  if (!isfinite(meanVelocityMps) || meanVelocityMps > peakVelocityMps) return;
  publishRep(meanVelocityMps, peakVelocityMps, durationMs);
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
    finishRep(durationMs);
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

}  // namespace

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
      previousReadingAt = millis();
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

bool repInProgress() { return repActive; }

float barSpeed() {
  float speed = repActive ? fabsf(velocityMps) : 0.0F;
  if (!isfinite(speed)) speed = 0.0F;
  return constrain(speed, 0.0F, MAX_CONTRACT_VELOCITY_MPS);
}

void printMovement() {
  Serial.printf("movement %5.2f m/s2, up %5.2f m/s2, speed %5.2f m/s%s\n", movementMps2, verticalMps2,
                fabsf(velocityMps), repActive ? " (moving)" : "");
}
