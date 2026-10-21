// motion_test.ino — does the BNO085 measure? A first look at its two readings.
//
// Why this exists: before the real firmware relies on the BNO085, show it working on
// this board (and settle the reported I2C trouble between BNO08x chips and ESP32s).
// It turns on the two readings the sensor will use (docs/remote/sensors.md):
//   - linear acceleration: movement in m/s^2 with gravity already taken out, so a bar
//     lying still reads about 0 whichever way it's tilted;
//   - game rotation vector: which way the board is pointing, ignoring the compass
//     (a steel bar and rack make a compass useless).
// Both 100 times a second. Five times a second it prints the latest of each and how
// many readings arrived, so you can watch the numbers move as you move the board.
#include <Wire.h>
#include "SparkFun_BNO08x_Arduino_Library.h"

const uint8_t ADDRESS = 0x4B;   // this board's address (found by bringup_check)
const int PIN_INT = D2;         // "data ready": wired, not used (see setup)
const int PIN_RST = D1;         // restart: pulsed once by this sketch at start

BNO08x imu;
float ax, ay, az, roll, pitch, yaw;
int accelCount = 0, rotationCount = 0;

void turnOnReadings() {
  // 10 ms between readings = 100 a second.
  bool ok = imu.enableLinearAccelerometer(10) && imu.enableGameRotationVector(10);
  Serial.println(ok ? "readings on: linear acceleration + game rotation vector, 100/s"
                    : "[!] the sensor refused a reading");
}

void setup() {
  Serial.begin(115200);
  delay(1500);   // give the Mac a moment to start listening
  // 100 kHz, as SparkFun's own examples use. The BNO08x holds the clock line while it
  // works ("clock stretching"); a slower bus and a longer timeout give it room.
  // One clean restart of the BNO085, done here rather than by the library, then RST
  // held high so the sensor stays running (left floating, it can sit half-reset).
  pinMode(PIN_RST, OUTPUT);
  digitalWrite(PIN_RST, LOW);
  delay(20);
  digitalWrite(PIN_RST, HIGH);
  delay(300);
  Wire.begin(SDA, SCL, 100000);
  Wire.setTimeOut(1000);
  Serial.println("starting the BNO085...");
  // The library gets neither INT nor RST. Handed either pin, it got no reading through on
  // this board (2026-10-21): with INT it restarted the sensor whenever INT was slow, and
  // with RST it started but sent nothing. This sketch restarts the sensor itself (above)
  // and asks it directly, 100 times a second, which works cleanly. Why the library's pin
  // handling misbehaves is noted in spec 14 to find out later.
  bool started = false;
  for (int attempt = 1; attempt <= 3 && !started; attempt++) {
    started = imu.begin(ADDRESS, Wire);
    if (!started) { Serial.printf("start attempt %d: no answer\n", attempt); delay(500); }
  }
  if (!started) {
    Serial.println("[!] the BNO085 didn't start. Check the wires; bringup_check helps.");
    while (true) delay(1000);
  }
  Serial.println("BNO085 found");
  delay(200);   // let it finish starting before asking for readings
  turnOnReadings();
}

void loop() {
  // The sensor restarts itself now and then (or after a glitch): turn the readings back on.
  if (imu.wasReset()) {
    Serial.println("the BNO085 restarted; turning the readings back on");
    turnOnReadings();
  }
  while (imu.getSensorEvent()) {
    switch (imu.getSensorEventID()) {
      case SENSOR_REPORTID_LINEAR_ACCELERATION:
        ax = imu.getLinAccelX(); ay = imu.getLinAccelY(); az = imu.getLinAccelZ();
        accelCount++;
        break;
      case SENSOR_REPORTID_GAME_ROTATION_VECTOR:
        roll = imu.getRoll() * RAD_TO_DEG; pitch = imu.getPitch() * RAD_TO_DEG;
        yaw = imu.getYaw() * RAD_TO_DEG;
        rotationCount++;
        break;
    }
  }
  static unsigned long last = 0;
  if (millis() - last >= 200) {
    last = millis();
    float moving = sqrt(ax * ax + ay * ay + az * az);
    Serial.printf("movement %5.2f m/s2 (x %5.2f y %5.2f z %5.2f) | roll %6.1f pitch %6.1f yaw %6.1f | readings in 0.2 s: %d + %d\n",
                  moving, ax, ay, az, roll, pitch, yaw, accelCount, rotationCount);
    accelCount = rotationCount = 0;
  }
}
