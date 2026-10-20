"""sensor_messages.py — the messages a sensor sends, in the shape everything else expects.

Why this file exists: two stand-ins for a real sensor send these messages. The
simulator (management/commands/simulate_node.py) runs beside the server, and the fake
sensor (scripts/sensor/fake_sensor.py) runs anywhere, like a sensor at someone's home.
Both build their messages here, so they can't drift apart, or away from what the
message contract says (docs/reference/message-contract.md).

Plain Python on purpose: no Django, so the fake sensor can use it without a server.
"""
import random
from datetime import datetime, timezone


def build_pulse_payload(node_id):
    """One fake heartbeat, battery/signal jitter within a realistic range."""
    return {
        "node_id": node_id,
        "event_type": "pulse",
        "battery_level": random.randint(80, 100),
        "signal_strength": random.randint(-70, -40),
        "firmware_version": "sim-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_rep_payload(node_id, rep_number):
    """One fake rep, peak velocity is always a bit above mean, like a real lift."""
    mean_velocity = round(random.uniform(0.4, 1.1), 3)
    peak_velocity = round(mean_velocity + random.uniform(0.1, 0.3), 3)
    duration_ms = random.randint(600, 1100)

    return {
        "node_id": node_id,
        "rep_number": rep_number,
        "mean_velocity": mean_velocity,
        "peak_velocity": peak_velocity,
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
