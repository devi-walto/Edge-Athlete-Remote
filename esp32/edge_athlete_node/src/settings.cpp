// settings.cpp — the sensor's saved Wi-Fi networks, its school login, and its record of
// bad restarts, all in its own flash (see settings.h for why).
#include "settings.h"

#include <Preferences.h>

#include "shared.h"

SavedNetwork networks[MAX_NETWORKS];
int networkCount = 0;
char loginUser[40];
char loginToken[128];
char loginPath[32];

namespace {
Preferences saved;
}  // namespace

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

// The saved login belongs to one school; a different school means claiming again.
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

void saveLogin() {
  saved.begin("edgeathlete", false);
  saved.putString("server", serverHost);
  saved.putString("user", loginUser);
  saved.putString("token", loginToken);
  saved.putString("path", loginPath);
  saved.end();
}

void forgetLogin() {
  saved.begin("edgeathlete", false);
  saved.clear();  // only the login lives here; the networks are in "ea-networks"
  saved.end();
  loginToken[0] = '\0';
}

String linkedSchool() {
  saved.begin("edgeathlete", true);
  const String school = saved.getString("token", "").isEmpty() ? "" : saved.getString("server", "");
  saved.end();
  return school;
}

// A sensor that drops off on one charger but not another shows "power dipped" here
// (USB `status`).
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
