#!/usr/bin/env bash
# tests/update-clone.sh — check update-clone.sh against a fake GitHub.
#
#   scripts/remote/tests/update-clone.sh
#
# Why this exists: update-clone.sh runs as root, once an hour, on the server. It must
# move the server's copy to the newest RELEASED version only: not a tag still waiting
# on SprintBranch, not a test tag, and not at all while the server is following a
# branch for testing. This builds a fake origin and a shallow copy (like bootstrap.sh
# makes) in a temporary folder and checks each case. Needs only git.

set -euo pipefail

HERE="$(cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd -P)"
SCRIPT="$HERE/../update-clone.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# The fake GitHub: main has v0.1.0 then v0.2.0; SprintBranch is ahead with v0.3.0
# (tagged, not on main yet) and a test tag.
git init -q -b main "$WORK/src"
cd "$WORK/src"
git config user.email test@example.invalid; git config user.name test
c() { git commit -q --allow-empty -m "$1"; }
c A; git tag v0.1.0
c B; git tag v0.2.0; git tag v0.2.1-test.1
git switch -q -c SprintBranch
c C; git tag v0.3.0
git switch -q main
git clone -q --bare "$WORK/src" "$WORK/origin.git"

# The server's copy, as bootstrap.sh makes it: shallow, on main.
git clone -q --depth 1 --branch main "file://$WORK/origin.git" "$WORK/copy"
export EDGE_PROJECT_DIR="$WORK/copy" EDGE_CLONE_SETTINGS="$WORK/clone.env"

failures=0
at() { git -C "$WORK/copy" describe --tags --exact-match HEAD 2>/dev/null || echo "(no tag)"; }
check() {
    if [ "$2" = "$3" ]; then echo "  ok    $1"; else echo "  FAIL  $1: expected [$2], got [$3]"; failures=$((failures + 1)); fi
}

printf 'EDGE_BRANCH=main\n' > "$WORK/clone.env"
"$SCRIPT" >/dev/null
check "a shallow copy moves to the newest release on main" "v0.2.0" "$(at)"
check "it fetched the history it needed"                   "false"  "$(git -C "$WORK/copy" rev-parse --is-shallow-repository)"
check "running again says so and stays"                    "already at v0.2.0" "$("$SCRIPT")"

# v0.3.0 reaches main (the 3-day job moves main forward).
git -C "$WORK/origin.git" update-ref refs/heads/main refs/heads/SprintBranch
"$SCRIPT" >/dev/null
check "once v0.3.0 is on main, the copy follows"           "v0.3.0" "$(at)"

# A new tag placed on SprintBranch, not on main yet: not followed.
git -C "$WORK/src" switch -q SprintBranch
git -C "$WORK/src" commit -q --allow-empty -m D; git -C "$WORK/src" tag v0.4.0
git -C "$WORK/src" push -q "$WORK/origin.git" SprintBranch refs/tags/v0.4.0
"$SCRIPT" >/dev/null
check "a tag still waiting on SprintBranch is not followed" "v0.3.0" "$(at)"

# The server follows a test branch: the copy is left alone.
printf 'EDGE_BRANCH=feature-test\n' > "$WORK/clone.env"
git -C "$WORK/origin.git" update-ref refs/heads/main refs/heads/SprintBranch
check "following a test branch: leaves the copy alone" \
    "following branch 'feature-test' (set by bootstrap.sh): not moving the copy" "$("$SCRIPT")"
check "…and it really didn't move"                         "v0.3.0" "$(at)"

if [ "$failures" -gt 0 ]; then echo "$failures failed"; exit 1; fi
echo "all passed"
