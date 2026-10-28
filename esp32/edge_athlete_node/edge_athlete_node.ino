// edge_athlete_node.ino — the sensor on the bar: measures each rep and sends it to the
// school (or to a local install) over Wi-Fi. Start reading here.
//
// Why this exists: an athlete clips this to the bar, switches it on, and every rep's
// speed shows up on their rack screen. One firmware for every sensor (spec 14
// decision 6); what it does follows the network it finds: a remote school over the
// internet, encrypted, with the sensor's own login; or a local install on the gym's
// Wi-Fi, plain, with no login.
//
// The parts, each in its own file in src/ (Arduino builds everything in a folder
// named src; any other name it would skip):
//   shared.h          which sensor this is, and where its reps go right now
//   settings.*        what it remembers in flash: Wi-Fi networks, its login
//   measuring.*       the BNO085, and what counts as a rep
//   messages.*        the pulse, live speed and rep messages it sends
//   connection.*      joining Wi-Fi, the clock, the server connection, the claim
//   setup_mode.*      the phone setup (its own Wi-Fi and page, setup_page.h)
//   usb_console.*     commands typed over USB, for development
//   roots.h           the certificate roots it trusts
//
// Build: the board's "Huge APP" layout (sketch.yaml). site.h (ignored by git, copy
// site.h.example) names the schools' base domain, so it stays out of this repo.
#include <WiFi.h>
#include <esp_mac.h>
#include <esp_system.h>

#include "src/connection.h"
#include "src/measuring.h"
#include "src/messages.h"
#include "src/settings.h"
#include "src/setup_mode.h"
#include "src/shared.h"
#include "src/usb_console.h"

char sensorId[16];
bool remote = false;
char serverHost[96];

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
  loadNetworks();
  // Nothing saved, or setup asked for (the button, or USB `setup`): the phone setup.
  if (networkCount == 0 || setupRequested()) {
    startSetup();  // nothing measured during setup, so the BNO085 waits
    return;
  }
  startImu();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  Serial.printf("%d saved Wi-Fi network%s\n", networkCount, networkCount == 1 ? "" : "s");
}

void loop() {
  const uint32_t now = millis();
  runUsbConsole(now);
  if (setupIsOpen()) {
    maintainSetup(now);
    return;
  }
  watchSetupButton(now);
  readImu(now);
  maintainConnection(now);
  sendRegularMessages(now);
}
