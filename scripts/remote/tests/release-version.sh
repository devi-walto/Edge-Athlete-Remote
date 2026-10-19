#!/usr/bin/env bash
# tests/release-version.sh — check release-version.sh against a throwaway repository.
#
#   scripts/remote/tests/release-version.sh
#
# Why this exists: that script decides what gets released to every school. A
# mistake would release the wrong version, or nothing, or an old one. This builds
# a small fake history (main, a SprintBranch ahead of it, an abandoned branch,
# tags in different places) in a temporary folder, runs each case, and checks the
# answer. It never touches the real repository or its tags. Needs only git.

set -euo pipefail

HERE="$(cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd -P)"
SCRIPT="$HERE/../release-version.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

git init -q -b main .
git config user.email test@example.invalid
git config user.name test
commit() { git commit -q --allow-empty -m "$1"; git rev-parse HEAD; }

# The fake history:
#   main:          A ── B (v0.1.0)
#   SprintBranch:  A ── B ── C (v0.2.0) ── D (v0.2.1, v0.3.0-test.1) ── E (v0.3.0)
#   abandoned:     B ── X (v9.9.9), never merged
A="$(commit A)"
B="$(commit B)"; git tag v0.1.0
git switch -q -c SprintBranch
C="$(commit C)"; git tag v0.2.0
D="$(commit D)"; git tag v0.2.1; git tag v0.3.0-test.1
E="$(commit E)"; git tag v0.3.0
git switch -q -c abandoned "$B"
X="$(commit X)"; git tag v9.9.9
git switch -q main

failures=0
check() {
    local name="$1" expected="$2" actual
    actual="$("$SCRIPT" "${@:3}" | tr '\n' ' ' | sed 's/ $//')"
    if [ "$actual" = "$expected" ]; then
        echo "  ok    $name"
    else
        echo "  FAIL  $name: expected [$expected], got [$actual]"
        failures=$((failures + 1))
    fi
}

echo "a tag is pushed"
check "its commit is on main: release it"          "v0.1.0" tag v0.1.0 "$B"
check "not on main yet: nothing, it waits"         ""       tag v0.2.0 "$B"
check "on an abandoned branch: nothing"            ""       tag v9.9.9 "$E"
check "a test tag on main still releases"          "v0.3.0-test.1" tag v0.3.0-test.1 "$E"

echo "main moves"
check "no new tags came with it"                   ""       moved "$A" "$A"
check "one tag arrived"                            "v0.2.0" moved "$B" "$C"
check "several arrived: all, oldest first"         "v0.2.0 v0.2.1 v0.3.0" moved "$B" "$E"
check "a test tag that arrived is left out"        "v0.2.1" moved "$C" "$D"
check "tags already on main are not repeated"      "v0.3.0" moved "$D" "$E"
check "a brand-new main (all-zero before)"         "v0.1.0" moved 0000000000000000000000000000000000000000 "$B"
check "an abandoned branch's tag never arrives"    "v0.1.0 v0.2.0 v0.2.1 v0.3.0" moved "$A" "$E"

echo "two-digit versions sort as numbers, not text"
git switch -q SprintBranch
F="$(commit F)"; git tag v0.10.0
G="$(commit G)"; git tag v0.9.1
check "v0.9.1 before v0.10.0 when both arrive"    "v0.3.0 v0.9.1 v0.10.0" moved "$D" "$G"

if [ "$failures" -gt 0 ]; then
    echo "$failures failed"
    exit 1
fi
echo "all passed"
