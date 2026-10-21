#!/bin/sh
# sensors-door-init.sh — gets the broker's sensors door ready, before the broker starts.
#
# Why this file exists: on the sensors door, nobody gets in without a login, and the
# logins live in one file the broker keeps on its own disk (the "dynamic security"
# file). Django adds a login there for each sensor, and removes it again, while the
# broker runs. To do that, Django needs an administrator login in that file. This
# step makes the file the first time, with that administrator, and then leaves it
# alone, so restarts and updates keep every sensor's login.
#
# The administrator's password comes from the school's broker-admin secret, which
# eactl makes. A school that doesn't have it yet still starts normally: its door is
# made LOCKED (an administrator nobody knows), so no sensor can get in until the
# secret exists. Once it does, the locked file is replaced. Nothing is lost, because
# a locked door can't have had any sensor logins.
#
# Runs in the broker's image, as the broker's user, in a step before the broker
# (mosquitto.yaml). The CI test runs this same file: scripts/remote/tests/sensors-door.sh.

set -eu

DATA="${SENSORS_DOOR_DATA:-/mosquitto/data}"
FILE="$DATA/dynamic-security.json"
# Which administrator password the file was made with: a fingerprint of it (never
# the password itself), or "locked". Lets a restart tell "same as before" apart
# from "the secret just arrived".
MARK="$DATA/dynamic-security.made-with"

if [ -n "${SENSORS_ADMIN_PASSWORD:-}" ]; then
    want="$(printf '%s' "$SENSORS_ADMIN_PASSWORD" | sha256sum | cut -d' ' -f1)"
else
    want=locked
fi
have="$(cat "$MARK" 2>/dev/null || echo none)"

if [ -f "$FILE" ]; then
    if [ "$have" = "$want" ]; then
        echo "sensors door: ready ($( [ "$want" = locked ] && echo locked || echo open to sensor logins ))"
        exit 0
    fi
    if [ "$have" != locked ]; then
        # Made with a different password (it was changed), or nobody knows what with.
        # Don't touch it: that would delete every sensor's login. The broker still
        # starts and sensors keep working; only adding or removing one fails until
        # the old password is put back.
        echo "sensors door: [!] the administrator password differs from the one this"
        echo "              door was made with. Keeping it as it is (sensor logins kept)."
        exit 0
    fi
    echo "sensors door: the administrator password has arrived; replacing the locked door"
    rm -f "$FILE"
fi

if [ "$want" = locked ]; then
    password="$(head -c 24 /dev/urandom | base64)"   # known to nobody
else
    password="$SENSORS_ADMIN_PASSWORD"
fi
mosquitto_ctrl dynsec init "$FILE" django "$password" >/dev/null
chmod 600 "$FILE"
printf '%s\n' "$want" > "$MARK"
echo "sensors door: made ($( [ "$want" = locked ] && echo "locked until the broker-admin secret exists" || echo "open to sensor logins" ))"
