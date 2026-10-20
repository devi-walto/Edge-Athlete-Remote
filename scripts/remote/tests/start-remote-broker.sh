#!/usr/bin/env bash
# tests/start-remote-broker.sh — start a broker set up exactly like a school's.
#
#   scripts/remote/tests/start-remote-broker.sh <container name> <docker network> [admin password]
#
# Why this exists: the sensors door only works with a school's own broker settings
# (k8s/app/base/mosquitto-remote.conf), its listen-only rules (browser.acl) and the
# step that makes the door's login file before the broker starts
# (sensors-door-init.sh). CI's remote test run, and sensors-door.sh, start the broker
# this way, so what they test is what a school runs, not a copy of it.
#
# The broker's disk is a Docker volume, not a folder on this machine: a Mac's shared
# folders ignore file permissions, which is how v0.5.0's broker crash got past a
# test. Without a password, the sensors door is made locked, like a school without
# its broker-admin secret.

set -euo pipefail

NAME="$1" NETWORK="$2" PASSWORD="${3:-}"
BASE="$(cd -- "$(dirname -- "$0")/../../../k8s/app/base" >/dev/null 2>&1 && pwd -P)"
IMAGE=eclipse-mosquitto:2.0.22   # the same as mosquitto.yaml

docker volume create "$NAME-data" >/dev/null
# The step before the broker, as mosquitto.yaml runs it: the broker's user, the data disk.
docker run --rm --user 1883:1883 -e SENSORS_ADMIN_PASSWORD="$PASSWORD" \
    -v "$NAME-data:/mosquitto/data" \
    -v "$BASE/sensors-door-init.sh:/mosquitto/config/sensors-door-init.sh:ro" \
    "$IMAGE" sh /mosquitto/config/sensors-door-init.sh
docker run -d --name "$NAME" --network "$NETWORK" --network-alias mosquitto \
    -v "$BASE/mosquitto-remote.conf:/mosquitto/config/mosquitto.conf:ro" \
    -v "$BASE/browser.acl:/mosquitto/config/browser.acl:ro" \
    -v "$NAME-data:/mosquitto/data" \
    "$IMAGE" >/dev/null
# Wait until it answers on the programs door.
for _ in $(seq 1 30); do
    docker exec "$NAME" mosquitto_sub -h localhost -t probe -W 1 -E >/dev/null 2>&1 && exit 0
    sleep 1
done
echo "[!] the broker didn't start:"; docker logs "$NAME"; exit 1
