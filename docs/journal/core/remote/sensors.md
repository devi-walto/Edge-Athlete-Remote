<!--
this page — how a sensor at an athlete's house ended up talking safely to a
server on the internet, and every setup I tried before the one that stuck.

It reads in order on purpose: each try fixed something the last one couldn't.
Keep that order when adding to it, so nobody re-opens a try that's already been
ruled out.
-->

# Sensors

*Oct 8 – Nov 5, 2026 · spec 14 · PRs #15, #17, #18*

## Tool changes at a glance

| Job | Before | Now | Why it changed |
|---|---|---|---|
| MQTT library on the sensor | PubSubClient | **ESP-MQTT** (built into the ESP32) | PubSubClient only sends at QoS 0, can't do WebSockets, and isn't maintained |
| How the sensor reaches the broker | plain MQTT, port 1883 | **MQTT over secure WebSockets, `wss://<school>/sensors` on 443** | Encrypted, no extra router port, gets through hotel and guest Wi-Fi |
| Who may connect | anyone | **each sensor with its own token** (Mosquitto's dynamic security plugin) | An ID is public; a token proves it |
| Setting a sensor up | Wi-Fi compiled into the firmware, then a USB tool | **a setup page the sensor serves to the phone** | An athlete can do it alone |
| Motion sensor | MPU-6050 | **BNO085** | Removes gravity itself, so a tilted bar still reads right |

## The problem

An athlete at home has their own sensor. It has to get on their Wi-Fi, find their school's server on the internet, and send every rep without anyone else being able to read it or fake it. And the athlete has to set it up alone, with just their phone.

## Try 1: the gym sensor, as is

The original firmware was built for the gym's own Wi-Fi. The Wi-Fi password and the base station's address were compiled in. It sent plain MQTT on port 1883, and the broker let anyone connect and send anything.

**What worked:** on a closed network in one room, that's fine. Nobody outside can reach it.

**Why I moved on:** on the internet, every one of those is a way in. Anyone could read every rep, or send reps as any sensor. And with the Wi-Fi compiled in, every athlete would need their own firmware build.

## Try 2: encrypted MQTT on port 8883

The standard answer: MQTT over TLS, on the port made for it.

The firmware used PubSubClient, a popular Arduino MQTT library. It could do encrypted MQTT, but it couldn't do WebSockets without a lot of extra code and memory. So I couldn't put sensors on 443 next to the website. They needed their own port, 8883.

The same library had a bigger problem. **PubSubClient can only send at QoS 0**, which is "send it once and hope." If the Wi-Fi blinked the moment a rep ended, that rep was gone. Every other hop already protected reps: the broker holds them for a screen that drops offline, and the rack screen saves each one before doing anything else. The very first hop, sensor to broker, was the only weak one. And the library's own README says it's no longer maintained, so nothing was going to change.

**What worked:** encrypted, and the usual way to do it.

**Why I moved on (Oct 19):** 8883 meant a second port open on my home router and a second kind of route in Traefik. It's also blocked on a lot of networks an athlete might lift on, like hotels and guest Wi-Fi.

The fix for both was swapping the library. I moved the firmware to **ESP-MQTT**, the MQTT client built into the ESP32 by the people who make the chip. It sends reps at **QoS 1**: it keeps every rep in an outbox and resends it until the broker confirms, even reps that ended while the sensor was offline. QoS 1 means *at least* once, so a rep can now and then show up twice; the rack screen spots a repeat and doesn't count it. And MQTT over secure WebSockets is one setting. So sensors moved to 443, the same port as the website, with their own path (`/sensors`) through Traefik, and the router only keeps 80 and 443 open.

## Try 3: set up over USB, with a one-time code

Firmware 2.0. The athlete presses **Add my sensor** on their page and gets a one-time code. They plug the sensor into a laptop and type in their Wi-Fi and the code. The sensor trades the code for its own token, and from then on it connects with that token.

**What worked:** the security model. The athlete's password never touches the sensor. The code works once, for 15 minutes, and each sensor's token can only send its own reps. That part stayed.

**Why I moved on (Oct 27):** a laptop and a cable is not something an athlete does alone. After the demo review I dropped the USB tool.

## Try 4: a setup page on the phone

Firmware 2.1. Hold the button, and the sensor opens its own Wi-Fi network. The phone pops up a setup page by itself, the same way hotel Wi-Fi does. Pick your network, type the code, done. No app to install.

**What worked:** it worked for me, every time.

**Why I moved on (Nov 4):** I watched a real athlete set one up on her own. She thought the school field was for making up a school name. She missed the small step numbers. She typed the code from memory and got it wrong. Then she hit a sensor that was still linked to someone else.

It was easy to say she's using it wrong. But if she doesn't want to read, other athletes won't either.

## Where I landed: setup v2

v0.8.2 and firmware 2.3.5:

- **Two codes, named the same everywhere:** a *school code* and a *sensor code*, asked for in that order. The athlete's page shows them in that same order.
- **Big green-bar steps:** "Step 2 of 3 · School code", not small grey numbers.
- **Code boxes that catch typos:** 8 boxes with the dash built in, and a letter the codes never use turns amber as it's typed.
- **Takeover:** a sensor linked to someone else can be made yours, but only with the sensor in your hand and an explicit "Make it mine". The old owner keeps their history.

Then the Wi-Fi kept saying wrong password when the password was right. I tried pinning the setup network to one channel (2.3.1), then moving channels when the athlete picked a network (2.3.2). Neither fixed it, and the second one closed the phone's setup page.

The real cause: setup turned the radio down to a whisper (8.5 dBm) for the phone sitting next to it. That one setting covers the whole radio, so the router could barely hear the sensor and turned it away mid sign-in. The fix was full power on every join (2.3.4), and up to 3 quiet tries before showing an error.

It taught me to think outside the error. I knew the connection worked days before, so the error message couldn't be the whole story.

## Things I passed on

- **Wi-Fi setup over Bluetooth from a web page.** Web Bluetooth doesn't work on iPhones.
- **A phone app.** A whole app to build and publish for one job a web page already does.
- **One shared login for every sensor.** One sensor taken apart would speak for all of them.
- **Locking the sensor to the server's exact certificate.** It renews every few months, and every sensor would go dark at once. Sensors trust Let's Encrypt's root instead.

## What it cost

- Each sensor's token lives in its flash. Anyone holding the sensor could pull it out, which is exactly why each sensor has its own, and it unlocks nothing else.
- The setup page can't have a padlock, since the sensor serves it on its own little network. That's why it only ever asks for codes, never a password.
- The ESP32-C6 is 2.4 GHz only. A 5 GHz-only home network can't be joined, and the page says so.
