#!/usr/bin/env bash
# self-update.sh — keep eactl (the server's copy of the code) at the newest release.
#
# Why this file exists: the eactl you type on the server, and the templates it reads,
# come from a copy of the repo at /srv/edge-athlete/Edge-Athlete-Remote. Releases
# reach the schools automatically, but that copy only moved when someone re-ran
# bootstrap.sh by hand. So a timer runs this once an hour (systemd, installed by
# bootstrap.sh) and moves the copy to the newest released version: the newest plain
# version tag (v1.2.3) that is on main, the same rule the release follows. So the
# commands you type always match what the schools are running.
#
# Safe by design:
#   - it only READS from GitHub, with the server's own read-only deploy key;
#   - the deploy runner (the robot that releases) has no part in it and gets no new
#     access: this runs as root from a copy bootstrap.sh installed in /usr/local/sbin,
#     not from the repo copy it updates;
#   - if bootstrap.sh was run for a branch other than main (testing one), it leaves
#     the copy alone, so a test isn't undone an hour later.
#
# Run by hand to update now:   eactl self-update   (it runs this as root:
#                               sudo edgeathlete-self-update)
#
# Named update-clone.sh until v0.7.2, when it took the name of the command you type
# (eactl self-update). bootstrap.sh replaces the old timer and file.

set -euo pipefail

PROJECT_DIR="${EDGE_PROJECT_DIR:-/srv/edge-athlete/Edge-Athlete-Remote}"
SETTINGS="${EDGE_SELF_UPDATE_SETTINGS:-/etc/edgeathlete/self-update.env}"
# A server set up before v0.7.2 has the same setting under its old name.
[ -r "$SETTINGS" ] || [ ! -r /etc/edgeathlete/clone.env ] || [ -n "${EDGE_SELF_UPDATE_SETTINGS:-}" ] \
    || SETTINGS=/etc/edgeathlete/clone.env
PLAIN='^v[0-9]+\.[0-9]+\.[0-9]+$'

# Which branch bootstrap.sh was run for (written by bootstrap.sh). Default: main.
EDGE_BRANCH=main
# shellcheck source=/dev/null
[ -r "$SETTINGS" ] && . "$SETTINGS"
if [ "$EDGE_BRANCH" != main ]; then
    echo "following branch '$EDGE_BRANCH' (set by bootstrap.sh): not moving the copy"
    exit 0
fi

git_() { git -C "$PROJECT_DIR" "$@"; }

# bootstrap.sh makes a shallow copy (only the newest commit). Working out which tags
# are on main needs the history, so fetch it once; afterwards only new commits come.
if [ "$(git_ rev-parse --is-shallow-repository)" = true ]; then
    git_ fetch --quiet --unshallow origin
fi
git_ fetch --quiet --force --tags origin "+refs/heads/main:refs/remotes/origin/main"

newest="$(git_ tag --merged origin/main --list 'v*' | { grep -E "$PLAIN" || true; } | sort -V | tail -n 1)"
if [ -z "$newest" ]; then
    echo "no release on main yet: leaving the copy where it is"
    exit 0
fi

current="$(git_ describe --tags --exact-match HEAD 2>/dev/null || true)"
if [ "$current" = "$newest" ]; then
    echo "already at $newest"
    exit 0
fi
git_ checkout --quiet --force --detach "refs/tags/$newest"
echo "moved the copy to $newest (was ${current:-$(git_ rev-parse --short HEAD@{1} 2>/dev/null || echo 'a branch')})"
