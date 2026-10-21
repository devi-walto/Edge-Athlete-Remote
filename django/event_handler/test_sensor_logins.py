"""Tests for sensor logins on the broker's sensors door (spec 14, Phase 1).

WHY THESE EXIST: on the internet, the sensors door is the only thing between anyone
and the reps in a school's sessions. A sensor must get in only with its own token,
send only its own messages, and be shut out the moment it is removed. The rest of the
broker must be unchanged: the screens door listen-only, the programs door working.

The broker tests need a real broker with the remote settings (CI's remote run starts
one, made by the same sensors-door-init.sh as a school's). Without one they are
skipped; the checks that need no broker always run.
"""
import json
import time
import uuid
from unittest import skipUnless

import paho.mqtt.client as mqtt
from django.conf import settings
from django.test import SimpleTestCase, override_settings

from .services import sensor_logins
from .services.sensor_logins import SensorDoorError

HAS_DOOR = bool(settings.MQTT_SENSORS_ADMIN_PASSWORD)
SETTLE = 1.0   # long enough for a message to go through the broker


def connect(port, username=None, password=None, transport="tcp"):
    """A client on one of the broker's doors. Returns (client, answer code, events)."""
    client = mqtt.Client(client_id=f"test-{uuid.uuid4().hex[:8]}", transport=transport)
    if username:
        client.username_pw_set(username, password)
    events = {"rc": None, "disconnected": False}
    client.on_connect = lambda c, u, f, rc: events.update(rc=rc)
    client.on_disconnect = lambda c, u, rc: events.update(disconnected=True)
    client.connect(settings.MQTT_HOST, port)
    client.loop_start()
    for _ in range(50):
        if events["rc"] is not None:
            break
        time.sleep(0.1)
    return client, events["rc"], events


def sensor(sensor_id, token):
    return connect(settings.MQTT_SENSORS_PORT, sensor_id, token, transport="websockets")


@skipUnless(HAS_DOOR, "needs a broker with the sensors door (CI's remote run)")
class SensorsDoorTests(SimpleTestCase):
    def setUp(self):
        # What arrives on the programs door, where django listens.
        self.arrived = []
        self.watcher, rc, _ = connect(settings.MQTT_PORT)
        self.assertEqual(rc, 0)
        self.watcher.on_message = lambda c, u, m: self.arrived.append((m.topic, m.payload.decode()))
        self.watcher.subscribe("edgeathlete/#", qos=1)
        self.id = f"ci-{uuid.uuid4().hex[:8]}"
        self.clients = [self.watcher]
        time.sleep(0.3)

    def tearDown(self):
        sensor_logins.remove(self.id)
        for client in self.clients:
            client.disconnect()
            client.loop_stop()

    def open_sensor(self, sensor_id, token):
        client, rc, events = sensor(sensor_id, token)
        self.clients.append(client)
        return client, rc, events

    def test_a_sensor_sends_its_own_messages_and_nobody_elses(self):
        sensor_logins.add(self.id, "token-one-0123456789")
        client, rc, _ = self.open_sensor(self.id, "token-one-0123456789")
        self.assertEqual(rc, 0)
        client.publish(f"edgeathlete/node/{self.id}/rep", "mine", qos=1)
        client.publish("edgeathlete/node/someone-else/rep", "posing", qos=1)
        time.sleep(SETTLE)
        self.assertIn((f"edgeathlete/node/{self.id}/rep", "mine"), self.arrived)
        self.assertNotIn("posing", [payload for _, payload in self.arrived])

    def test_only_its_own_token_gets_in(self):
        sensor_logins.add(self.id, "token-one-0123456789")
        self.assertNotEqual(self.open_sensor(self.id, "wrong-token")[1], 0)
        self.assertNotEqual(self.open_sensor(None, None)[1], 0)

    def test_a_new_token_replaces_the_old(self):
        sensor_logins.add(self.id, "token-one-0123456789")
        old, rc, events = self.open_sensor(self.id, "token-one-0123456789")
        self.assertEqual(rc, 0)
        sensor_logins.add(self.id, "token-two-0123456789")
        time.sleep(SETTLE)
        self.assertTrue(events["disconnected"])
        self.assertNotEqual(self.open_sensor(self.id, "token-one-0123456789")[1], 0)
        self.assertEqual(self.open_sensor(self.id, "token-two-0123456789")[1], 0)

    def test_a_removed_sensor_is_shut_out_at_once(self):
        sensor_logins.add(self.id, "token-one-0123456789")
        client, rc, events = self.open_sensor(self.id, "token-one-0123456789")
        sensor_logins.remove(self.id)
        time.sleep(SETTLE)
        self.assertTrue(events["disconnected"])
        client.publish(f"edgeathlete/node/{self.id}/rep", "after", qos=1)
        time.sleep(SETTLE)
        self.assertNotIn("after", [payload for _, payload in self.arrived])
        self.assertNotEqual(self.open_sensor(self.id, "token-one-0123456789")[1], 0)
        sensor_logins.remove(self.id)   # removing again is fine

    def test_the_programs_door_cannot_make_a_login(self):
        sneak, rc, _ = connect(settings.MQTT_PORT)
        self.clients.append(sneak)
        sneak.publish(sensor_logins.CONTROL_TOPIC, json.dumps({"commands": [
            {"command": "createClient", "username": self.id, "password": "sneaky-0123456789"}]}))
        time.sleep(SETTLE)
        self.assertNotEqual(self.open_sensor(self.id, "sneaky-0123456789")[1], 0)

    def test_the_screens_door_is_still_listen_only(self):
        screen, rc, _ = connect(9001, transport="websockets")
        self.clients.append(screen)
        self.assertEqual(rc, 0)
        screen.publish(f"edgeathlete/node/{self.id}/rep", "from-a-browser", qos=1)
        time.sleep(SETTLE)
        self.assertNotIn("from-a-browser", [payload for _, payload in self.arrived])

    def test_a_wrong_administrator_password_is_refused(self):
        with override_settings(MQTT_SENSORS_ADMIN_PASSWORD="not-it"):
            with self.assertRaisesMessage(SensorDoorError, "refused"):
                sensor_logins.add(self.id, "token-one-0123456789")


class WithoutABrokerTests(SimpleTestCase):
    @override_settings(MQTT_SENSORS_ADMIN_PASSWORD="")
    def test_a_server_without_the_door_says_so(self):
        with self.assertRaisesMessage(SensorDoorError, "isn't set up"):
            sensor_logins.add("ea-3f9c", "token-one-0123456789")

    @override_settings(MQTT_SENSORS_ADMIN_PASSWORD="anything")
    def test_an_id_with_topic_characters_is_refused_before_anything_is_sent(self):
        for bad in ("a/b", "a+", "#", "", "x" * 65, None):
            with self.assertRaises(SensorDoorError):
                sensor_logins.add(bad, "token-one-0123456789")
