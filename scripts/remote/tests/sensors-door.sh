#!/usr/bin/env bash
# tests/sensors-door.sh — check the step that gets the broker's sensors door ready.
#
#   scripts/remote/tests/sensors-door.sh [image with python + paho]   (default ea-django:ci)
#
# Why this exists: sensors-door-init.sh runs every time a school's broker starts
# (k8s/app/base/sensors-door-init.sh). It must make the sensors door's login file
# once, lock it while the school has no broker-admin secret, open it when the secret
# arrives, and never wipe the sensors' logins on a restart or a changed password.
# This runs it the way a school's broker does (start-remote-broker.sh: the real
# settings, the broker's user, a Docker volume) and checks each case with a real
# MQTT client. Needs Docker. CI runs it in the remote backend check.

set -euo pipefail

HERE="$(cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd -P)"
BASE="$HERE/../../../k8s/app/base"
PROBE_IMAGE="${1:-ea-django:ci}"
NAME="sensors-door-test-$$" NET="sensors-door-test-$$"
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; docker volume rm "$NAME-data" >/dev/null 2>&1 || true
            docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker network create "$NET" >/dev/null

failures=0
check() {
    if [ "$2" = "$3" ]; then echo "  ok    $1"; else echo "  FAIL  $1: expected [$2], got [$3]"; failures=$((failures + 1)); fi
}

# probe <what> [args]: a real MQTT client on the sensors door.
#   admin <password>                 -> "in" if the administrator gets in, else "out"
#   add <password> <id> <token>      -> "added" (as the administrator)
#   sensor <id> <token>              -> "in" or "out"
probe() {
    docker run --rm --network "$NET" -e H="$NAME" "$PROBE_IMAGE" python -c '
import json, sys, time, paho.mqtt.client as mqtt
what, args = sys.argv[1], sys.argv[2:]
def login(user, pw):
    c = mqtt.Client(transport="websockets"); c.username_pw_set(user, pw)
    rc = []; c.on_connect = lambda *a: rc.append(a[3])
    c.connect(__import__("os").environ["H"], 9002); c.loop_start()
    for _ in range(50):
        if rc: break
        time.sleep(0.1)
    return c, (rc[0] if rc else None)
if what == "admin": print("in" if login("django", args[0])[1] == 0 else "out")
elif what == "sensor": print("in" if login(args[0], args[1])[1] == 0 else "out")
elif what == "add":
    c, _ = login("django", args[0]); got = []
    c.on_message = lambda cl, u, m: got.append(m.payload); c.subscribe("$CONTROL/dynamic-security/v1/response"); time.sleep(0.5)
    c.publish("$CONTROL/dynamic-security/v1", json.dumps({"commands": [
        {"command": "createClient", "username": args[1], "password": args[2]}]})); time.sleep(1)
    print("added" if got and "error" not in json.loads(got[0])["responses"][0] else "not added")
' "$@"
}

# restart [password]: what a pod restart does — the step before the broker runs
# again, then the broker. Prints what the step said.
restart() {
    docker rm -f "$NAME" >/dev/null
    docker run --rm --user 1883:1883 -e SENSORS_ADMIN_PASSWORD="${1:-}" \
        -v "$NAME-data:/mosquitto/data" \
        -v "$BASE/sensors-door-init.sh:/mosquitto/config/sensors-door-init.sh:ro" \
        eclipse-mosquitto:2.0.22 sh /mosquitto/config/sensors-door-init.sh
    docker run -d --name "$NAME" --network "$NET" \
        -v "$BASE/mosquitto-remote.conf:/mosquitto/config/mosquitto.conf:ro" \
        -v "$BASE/browser.acl:/mosquitto/config/browser.acl:ro" \
        -v "$NAME-data:/mosquitto/data" eclipse-mosquitto:2.0.22 >/dev/null
    sleep 2
}

echo "a school without its broker-admin secret"
said="$("$HERE/start-remote-broker.sh" "$NAME" "$NET")"
check "the door is made locked" "sensors door: made (locked until the broker-admin secret exists)" "$said"
check "nobody gets in as the administrator" out "$(probe admin anything)"

echo "the secret arrives"
said="$(restart first-admin-pw-0123)"
check "the locked door is replaced" yes "$(grep -q 'replacing the locked door' <<<"$said" && echo yes || echo no)"
check "django gets in" in "$(probe admin first-admin-pw-0123)"
check "a sensor login can be added" added "$(probe add first-admin-pw-0123 ea-test1 sensor-token-0123)"
check "the sensor gets in" in "$(probe sensor ea-test1 sensor-token-0123)"

echo "a restart"
said="$(restart first-admin-pw-0123)"
check "the file is left as it is" "sensors door: ready (open to sensor logins)" "$said"
check "the sensor still gets in" in "$(probe sensor ea-test1 sensor-token-0123)"

echo "the administrator password is changed"
said="$(restart second-admin-pw-0123)"
check "it warns and keeps the file" yes "$(grep -q 'Keeping it as it is' <<<"$said" && echo yes || echo no)"
check "the sensor still gets in" in "$(probe sensor ea-test1 sensor-token-0123)"

echo "the file's permissions"
check "only the broker's user can read it" "600 mosquitto" \
    "$(docker exec "$NAME" stat -c '%a %U' /mosquitto/data/dynamic-security.json)"

if [ "$failures" -gt 0 ]; then echo "$failures check(s) failed"; exit 1; fi
echo "all checks passed"
