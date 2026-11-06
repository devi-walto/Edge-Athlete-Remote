# ESP32-C6 + BNO085

*Both installs*

**Why I picked them.** The ESP32 was hardware I had on hand. The BNO085 was the most accurate motion sensor I could find.

**What it is.** The sensor on the bar. A **Seeed XIAO ESP32-C6** (a small board with Wi-Fi) and a **BNO085** motion sensor, which works out the bar's movement with gravity already taken out, however the sensor is mounted.

**How we use it.** One firmware for every sensor, in the gym or at home:

```
BNO085 ──I2C──► ESP32-C6 ──Wi-Fi──► MQTT
                  │                  local:  plain MQTT on 1883 to the base station
                  │                  remote: wss://<school>/sensors with its own token
                  └── its own setup page, served to the athlete's phone
```

It works out each rep's mean and peak speed itself and sends one message per rep, plus a heartbeat every 5 seconds and live speed 10 times a second ({doc}`../../handbook/reference/mqtt-topics`).

**Where it lives.** `esp32/edge_athlete_node/`: the `.ino` and `sketch.yaml` at the top, the parts in `src/` (Arduino only builds `src/`). Settings that never go in git are in `secrets.h` and `site.h`, both gitignored. Firmware 2.3.5 as of Nov 5.

**Worth knowing.**

- ⚠️ **2.4 GHz only.** A 5 GHz-only home network can't be joined, and the setup page says so.
- ⚠️ **Joins at full transmit power.** Setup turned the radio down to a whisper for the phone beside it, and the router turned the sensor away while "wrong password" showed on screen ({doc}`../core/remote/sensors`).
- **It needs the right time before TLS works**, because a certificate is only valid between two dates. A rep is dropped rather than sent without a time.
- **It replaced the MPU-6050**, which only measured gravity once, at rest, so any tilt leaked into the speed. And the **WT901** Bluetooth sensor was dropped on Oct 27: MQTT sensors everywhere.

**More:** {doc}`../core/remote/sensors` · {doc}`mosquitto`
