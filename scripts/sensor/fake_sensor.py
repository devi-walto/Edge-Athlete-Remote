#!/usr/bin/env python3
"""fake_sensor.py — a pretend sensor at someone's home, for trying the online flow without hardware.

Why this file exists: a real sensor at an athlete's home knows only three things: its
own ID, the school's address, and (once) the one-time code the athlete gave it. It
can't see the school's database. This does exactly what the firmware will do with
those (spec 14, Phase 3), so the whole online path can be proven before the hardware
is on the desk:

  1. claim:   send the code and its ID to the school (POST /api/sensors/claim/) and
              get back its own sensor token. Saved in a small file, the way a real
              sensor keeps it in its memory; the code is used up.
  2. connect: to the school's sensors door, wss://<school>/sensors (ws:// for a plain
              http address, like the review copy on a laptop), with its ID and token.
  3. send:    a pulse every 5 seconds (so the athlete's page shows it connected) and
              reps on a steady rhythm. A real sensor sends a rep when the bar moves; the
              rack screen only records the ones that arrive while a set is running.

  python3 scripts/sensor/fake_sensor.py --server https://<school address> --id ea-fake-01 --claim K7MQ-2XPR
  python3 scripts/sensor/fake_sensor.py --server https://<school address> --id ea-fake-01    (later: reuses the token)

Needs only Python and paho-mqtt (the django image has both). It never sends anything
under another sensor's topic unless asked to (--pose-as), which the school must refuse.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import paho.mqtt.client as mqtt

# The message shapes, shared with the server-side simulator (plain Python, no Django).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "django"))
from event_handler.sensor_messages import build_pulse_payload, build_rep_payload  # noqa: E402

PULSE_SECONDS = 5
SAVED = Path(os.environ.get("FAKE_SENSOR_DIR", Path.home() / ".edgeathlete" / "fake-sensors"))


def claim(server, sensor_id, code):
    """Trade the code for this sensor's login. Returns {"username", "token", "path"}."""
    request = urllib.request.Request(
        server.rstrip("/") + "/api/sensors/claim/", method="POST",
        data=json.dumps({"code": code, "node_id": sensor_id}).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as reply:
            return json.load(reply)
    except urllib.error.HTTPError as refused:
        body = json.loads(refused.read() or b"{}")
        sys.exit(f"The school refused the claim ({refused.code}): {body.get('detail', body)}")
    except urllib.error.URLError as exc:
        sys.exit(f"Couldn't reach {server}: {exc.reason}")


def door_address(server, path):
    """(host, port, use TLS) for the sensors door, from the school's own address."""
    parts = urlsplit(server)
    secure = parts.scheme == "https"
    return parts.hostname, parts.port or (443 if secure else 80), secure


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--server", required=True, help="the school's address, e.g. https://demo-u-k7m2qx.<domain>")
    parser.add_argument("--id", required=True, help="this sensor's ID, e.g. ea-fake-01")
    parser.add_argument("--claim", metavar="CODE", help="a one-time code from the athlete's page")
    parser.add_argument("--rep-every", type=float, default=3.0, help="seconds between reps (default 3)")
    parser.add_argument("--reps-per-set", type=int, default=5, help="reps before a rest (default 5)")
    parser.add_argument("--rest", type=float, default=20.0, help="seconds of rest between sets (default 20)")
    parser.add_argument("--pose-as", metavar="OTHER_ID", help="also send reps as another sensor (the school must drop them)")
    parser.add_argument("--send-twice", action="store_true",
                        help="send every rep twice, as happens now and then when a 'got it' is lost "
                             "(the rack screen must count it once)")
    args = parser.parse_args()

    saved = SAVED / f"{args.id}.json"
    if args.claim:
        login = claim(args.server, args.id, args.claim)
        SAVED.mkdir(parents=True, exist_ok=True)
        saved.write_text(json.dumps({"server": args.server, **login}))
        saved.chmod(0o600)
        print(f"claimed: {args.id} now belongs to the athlete whose code that was")
    elif saved.exists():
        login = json.loads(saved.read_text())
    else:
        sys.exit(f"{args.id} has no login yet. Get a code on the athlete's page and pass --claim CODE.")

    host, port, secure = door_address(args.server, login["path"])
    client = mqtt.Client(client_id=args.id, transport="websockets")
    client.username_pw_set(login["username"], login["token"])
    client.ws_set_options(path=login["path"])
    if secure:
        client.tls_set()   # checks the school's certificate against the trusted roots
    answers = {0: "connected", 4: "refused: wrong token", 5: "refused: not allowed (removed? claim again)"}
    state = {"stop": None}

    def on_connect(c, userdata, flags, rc):
        print(f"{'wss' if secure else 'ws'}://{host}{login['path']}: {answers.get(rc, f'refused ({rc})')}")
        if rc != 0:
            state["stop"] = rc

    def on_disconnect(c, userdata, rc):
        if rc != 0:
            print("disconnected by the school")

    client.on_connect, client.on_disconnect = on_connect, on_disconnect
    client.connect(host, port, keepalive=30)
    client.loop_start()

    topic = f"edgeathlete/node/{args.id}"
    next_pulse, rep, next_rep = 0.0, 0, time.monotonic() + 2
    try:
        while state["stop"] is None:
            now = time.monotonic()
            if now >= next_pulse:
                client.publish(f"{topic}/pulse", json.dumps(build_pulse_payload(args.id)))
                next_pulse = now + PULSE_SECONDS
            if now >= next_rep:
                rep += 1
                message = json.dumps(build_rep_payload(args.id, rep))
                client.publish(f"{topic}/rep", message, qos=1)
                if args.send_twice:
                    client.publish(f"{topic}/rep", message, qos=1)
                if args.pose_as:
                    client.publish(f"edgeathlete/node/{args.pose_as}/rep",
                                   json.dumps(build_rep_payload(args.pose_as, rep)), qos=1)
                print(f"rep {rep}" + (" (sent twice)" if args.send_twice else ""))
                if rep >= args.reps_per_set:
                    rep, next_rep = 0, now + args.rest
                    print(f"resting {args.rest:g}s")
                else:
                    next_rep = now + args.rep_every
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
    sys.exit(1 if state["stop"] else 0)


if __name__ == "__main__":
    main()
