// bringup_check.ino — a first test of a freshly wired sensor, before any real firmware.
//
// Why this exists: before writing the real firmware, prove the parts are alive and
// wired right. Every 3 seconds it:
//   - blinks the XIAO's own LED (flashing works, the program runs);
//   - prints the ID this chip would get (one firmware, each chip its own ID);
//   - scans the I2C bus (SDA D4, SCL D5) and names what answers. A BNO08x answers at
//     0x4A (Adafruit's default) or 0x4B (SparkFun's). Nothing at all usually means a
//     swapped SDA/SCL, no power, or missing pull-up resistors;
//   - reads INT (D2). The BNO08x pulls it low when it has something to say.
// At start it pulses RST (D1) low, which restarts the BNO08x: if it then answers, RST
// is wired too.
#include <Wire.h>
#include <esp_mac.h>

const int PIN_INT = D2;   // INT on D2, RST on D1 (as wired, 2026-10-21)
const int PIN_RST = D1;

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_INT, INPUT_PULLUP);
  pinMode(PIN_RST, OUTPUT);
  digitalWrite(PIN_RST, LOW);   // hold the BNO08x in reset...
  delay(20);
  digitalWrite(PIN_RST, HIGH);  // ...then let it start
  delay(300);                   // it needs a moment before it answers
  Wire.begin(SDA, SCL, 100000); // 100 kHz: slow and forgiving for a first check
}

void loop() {
  static int round_ = 0;
  digitalWrite(LED_BUILTIN, round_ % 2);

  Serial.printf("\n--- check %d ---\n", ++round_);
  // The ID: "ea-" and the last 3 bytes of the chip's own Wi-Fi address, so every chip
  // gets its own with no setting. (ESP.getEfuseMac() doesn't work for this on the C6:
  // it returns a longer, padded address whose middle is the same filler on every chip.)
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  Serial.printf("chip: %s, sensor ID would be ea-%02x%02x%02x\n", ESP.getChipModel(), mac[3], mac[4], mac[5]);

  // A voltmeter on D0: a spare wire from the sensor board's VCC pin to D0 shows whether
  // the sensor is getting power. About 3300 mV = powered; near 0 = not.
  Serial.printf("voltage on D0 (wire it to the sensor's VCC): %d mV\n", analogReadMilliVolts(A0));
  // Self-check of the voltmeter: pull D0 up, then down, inside the chip. With nothing
  // connected it follows (about 3300 then about 0); a wire to a real 3.3 V keeps it high.
  pinMode(A0, INPUT_PULLUP);   delay(5); int up = analogReadMilliVolts(A0);
  pinMode(A0, INPUT_PULLDOWN); delay(5); int down = analogReadMilliVolts(A0);
  pinMode(A0, INPUT);
  Serial.printf("voltmeter self-check: pulled up %d mV, pulled down %d mV\n", up, down);

  // The wires themselves. Each one is pulled gently toward 0 V by the chip. If something
  // on the sensor board pulls it up harder (its pull-up resistors, or the BNO08x driving
  // it), it reads HIGH; if it reads LOW, the sensor side isn't powered, has no pull-up,
  // or the wire doesn't reach it.
  Wire.end();
  const int lines[] = {SDA, SCL, PIN_INT};
  const char *names[] = {"SDA (D4)", "SCL (D5)", "INT (D2)"};
  for (int i = 0; i < 3; i++) {
    pinMode(lines[i], INPUT_PULLDOWN);
    delay(5);
    Serial.printf("line %s: %s\n", names[i], digitalRead(lines[i])
      ? "HIGH: something on the sensor board holds it up (good)"
      : "LOW: nothing holds it up (no power, no pull-up, or not connected)");
  }
  pinMode(PIN_INT, INPUT_PULLUP);
  // Restart the BNO08x every round, in case it missed its start-up.
  digitalWrite(PIN_RST, LOW); delay(20); digitalWrite(PIN_RST, HIGH); delay(300);

  int found = 0;
  // Every other round, try the two data wires the other way round, in case SDA and
  // SCL are swapped on the board.
  bool swapped = round_ % 2 == 0;
  Wire.end();
  Wire.begin(swapped ? SCL : SDA, swapped ? SDA : SCL, 100000);
  Serial.printf("I2C scan with %s\n", swapped ? "SDA/SCL SWAPPED (D5 as data, D4 as clock)"
                                                : "SDA on D4, SCL on D5 (as wired)");
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      found++;
      const char *what = address == 0x4A ? " <- BNO08x (Adafruit default address)"
                       : address == 0x4B ? " <- BNO08x (SparkFun default address)" : "";
      Serial.printf("I2C: something answers at 0x%02X%s\n", address, what);
    }
  }
  if (!found) Serial.println("I2C: nothing answers. Check power, SDA/SCL swapped, pull-ups.");
  Serial.printf("INT (D2): %s\n", digitalRead(PIN_INT) ? "high (idle)" : "low (the BNO08x has data waiting)");
  delay(3000);
}
