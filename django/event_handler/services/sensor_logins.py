"""Sensor logins: adds and removes each sensor's login on the broker's sensors door.

WHY THIS FILE EXISTS: online, a sensor at home connects to its school's broker through
the sensors door (wss://<school>/sensors), and nobody gets in there without a login.
Each sensor has its own: its ID as the username, and its sensor token, a long random
secret the server made for it, as the password. A sensor may send only under its own
`edgeathlete/node/<its id>/`, so it can never pose as another sensor (spec 14).

The broker keeps those logins itself, in its "dynamic security" plugin, so they work
the moment they are added and stop the moment they are removed, with no restart.
Django is that plugin's administrator: it sends the plugin's commands as messages on
the sensors door, logged in as "django", and reads the answers.

Only this file talks to the plugin. The claim route (Phase 2) decides WHEN a sensor
gets a login; this file only makes it so on the broker. Remote only: a local install
has no sensors door, and its sensors use the gym's own Wi-Fi.
"""
import json
import re
import threading
import uuid

import paho.mqtt.client as mqtt
from django.conf import settings

ADMIN_USERNAME = "django"
CONTROL_TOPIC = "$CONTROL/dynamic-security/v1"
ANSWER_TOPIC = f"{CONTROL_TOPIC}/response"
WAIT_SECONDS = 5

# A sensor ID becomes part of a topic, so it may hold no topic characters (/ + #).
# 64 is the message contract's limit for a node ID.
SENSOR_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class SensorDoorError(Exception):
    """The sensors door couldn't do what was asked; the message says why."""


def add(sensor_id, token):
    """Give this sensor a login with this token. Replaces any login it had, so its
    old token stops working and, if it is connected with it, it is disconnected."""
    role = _role(sensor_id)
    _send([
        {"command": "deleteClient", "username": sensor_id},
        {"command": "deleteRole", "rolename": role},
        {"command": "createRole", "rolename": role, "acls": [
            # What this one sensor may do: send under its own topics. Nothing else
            # is allowed, so it can't send as another sensor, or listen at all.
            {"acltype": "publishClientSend", "topic": f"edgeathlete/node/{sensor_id}/#",
             "allow": True},
        ]},
        {"command": "createClient", "username": sensor_id, "password": token,
         "roles": [{"rolename": role}]},
    ], may_be_missing={"deleteClient", "deleteRole"})


def remove(sensor_id):
    """Take this sensor's login away. It is disconnected at once and can't get back in.
    Removing a sensor that has no login is fine."""
    _send([
        {"command": "deleteClient", "username": sensor_id},
        {"command": "deleteRole", "rolename": _role(sensor_id)},
    ], may_be_missing={"deleteClient", "deleteRole"})


# ───────────────────────────── helpers ─────────────────────────────

def _role(sensor_id):
    if not SENSOR_ID.match(str(sensor_id or '')):
        raise SensorDoorError(f"Not a usable sensor ID: {sensor_id!r}")
    return f"sensor-{sensor_id}"


def _send(commands, may_be_missing=()):
    """Send the plugin these commands, in order, and wait for every answer.

    A command in `may_be_missing` may fail with "not found" (removing what isn't
    there); any other failure raises SensorDoorError.
    """
    password = settings.MQTT_SENSORS_ADMIN_PASSWORD
    if not password:
        raise SensorDoorError("The sensors door isn't set up on this server "
                              "(no broker-admin secret).")
    for n, command in enumerate(commands):
        command["correlationData"] = str(n)

    connected, subscribed, answered = threading.Event(), threading.Event(), threading.Event()
    result = {}
    answers = {}

    def on_connect(client, userdata, flags, rc):
        result["rc"] = rc
        connected.set()

    def on_subscribe(client, userdata, mid, granted):
        subscribed.set()

    def on_message(client, userdata, message):
        for answer in json.loads(message.payload).get("responses", []):
            answers[answer.get("correlationData")] = answer
        if len(answers) >= len(commands):
            answered.set()

    client = mqtt.Client(client_id=f"django-admin-{uuid.uuid4().hex[:8]}",
                         transport="websockets")
    client.username_pw_set(ADMIN_USERNAME, password)
    client.on_connect, client.on_subscribe, client.on_message = on_connect, on_subscribe, on_message
    try:
        client.connect(settings.MQTT_HOST, settings.MQTT_SENSORS_PORT, keepalive=30)
    except OSError as exc:
        raise SensorDoorError(f"Couldn't reach the sensors door: {exc}") from exc
    client.loop_start()
    try:
        if not connected.wait(WAIT_SECONDS):
            raise SensorDoorError("The sensors door didn't answer.")
        if result["rc"] != 0:
            raise SensorDoorError("The sensors door refused django's administrator login.")
        client.subscribe(ANSWER_TOPIC, qos=1)
        if not subscribed.wait(WAIT_SECONDS):
            raise SensorDoorError("The sensors door didn't answer.")
        client.publish(CONTROL_TOPIC, json.dumps({"commands": commands}), qos=1)
        if not answered.wait(WAIT_SECONDS):
            raise SensorDoorError("The sensors door didn't answer every command.")
    finally:
        client.disconnect()
        client.loop_stop()

    for command in commands:
        error = answers[command["correlationData"]].get("error")
        if error and not (command["command"] in may_be_missing and "not found" in error.lower()):
            raise SensorDoorError(f"{command['command']} failed: {error}")
