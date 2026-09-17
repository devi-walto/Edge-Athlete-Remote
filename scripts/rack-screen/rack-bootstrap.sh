#!/usr/bin/env bash
# rack-bootstrap.sh — turn a blank machine into a rack screen with one command.
#
# FIRST INSTALL — copy this file over from your laptop, then run it ON the screen:
#
#   scp scripts/rack-screen/rack-bootstrap.sh pi@<screen>:/tmp/
#   ssh -t pi@<screen> 'sudo bash /tmp/rack-bootstrap.sh'
#
# (Use whatever account the screen was imaged with in place of `pi`.) The first run
# prints this screen's public key and waits while you add it on GitHub as a
# read-only deploy key — the same flow as the base station, for the same reasons:
# the repo is private, so the old `curl ... | sudo bash` one-liner gets a 404, and a
# key per device can be revoked without touching any other device. See the header
# of scripts/basestation/bootstrap.sh for the full story.
#
# AFTER THAT, just `ea-update`. Like the base station's bootstrap.sh, nothing here
# is one-shot — re-running this file is also a full update.
#
# ── WHY THIS EXISTS ─────────────────────────────────────────────────────────────
# The base station had a one-command install and a rack screen did not. Provisioning
# a rack meant "install git, clone the repo, cd into it, run this script with these
# arguments" — four chances to get it wrong, on the device you have the most of. This
# is the same shape as bootstrap.sh so the two are learned once, not twice.
#
# ── WHY IT TAKES NO ROLE ARGUMENT ───────────────────────────────────────────────
# A rack screen is a rack screen. It hardcodes the role deliberately: this is the
# path you run on a dozen identical devices, and a role argument on that path is a
# way to end up with a wall display bolted to a squat rack. The other roles are
# deliberate, one-off acts and go through rack-kiosk-setup.sh directly:
#
#   sudo scripts/rack-screen/rack-kiosk-setup.sh coach
#
# The base station is different again — it defaults to the wall display and can open
# any role for debugging. See scripts/basestation/basestation-kiosk.sh.
#
# ── WHAT IT DOES NOT INSTALL ────────────────────────────────────────────────────
# No Docker, no Python, no database, no server. A rack screen is a CLIENT: it joins
# the base station's WiFi and shows a web page. The repo is cloned only because the
# kiosk scripts live in it — nothing in it runs but two shell scripts.
#
# Override these if you need to. ⚠️ The assignments go AFTER `sudo` — sudo scrubs the
# environment, so anything set before it never reaches this script:
#   sudo EDGE_BRANCH=some-branch AP_PASSWORD='hunter2' bash /tmp/rack-bootstrap.sh

set -euo pipefail

REPO_URL="${EDGE_REPO_URL:-git@github.com:devi-walto/Edge-Athlete-Remote.git}"
EDGE_HOME="${EDGE_HOME:-/srv/edge-athlete}"
EDGE_BRANCH="${EDGE_BRANCH:-main}"
PROJECT_DIR="$EDGE_HOME/Edge-Athlete"

if [ "$(id -u)" -ne 0 ]; then
    echo "[!] needs root — run it with sudo"
    exit 1
fi

echo "[1] installing git..."
if ! command -v git >/dev/null 2>&1 || ! command -v ssh-keygen >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq git ca-certificates openssh-client
fi

# >>> repo access — keep IDENTICAL in bootstrap.sh and rack-bootstrap.sh (a test checks)
#
# Only for SSH remotes. A file:// or https:// URL (the tests, or a public fork) needs
# no key, and generating one there would just be clutter a human later wonders about.
EDGE_KEY_DIR="${EDGE_KEY_DIR:-/etc/edgeathlete/deploy-keys}"
EDGE_KNOWN_HOSTS="${EDGE_KNOWN_HOSTS:-/etc/edgeathlete/github_known_hosts}"

repo_uses_ssh() {
    case "$REPO_URL" in git@*|ssh://*) return 0 ;; *) return 1 ;; esac
}

if repo_uses_ssh; then
    repo_name="$(basename "${REPO_URL%.git}")"
    key="$EDGE_KEY_DIR/$repo_name"
    mkdir -p "$EDGE_KEY_DIR"
    chmod 700 "$EDGE_KEY_DIR"
    if [ ! -f "$key" ]; then
        echo "    generating this machine's deploy key for $repo_name..."
        ssh-keygen -q -t ed25519 -N '' -C "$repo_name@$(hostname)" -f "$key"
    fi
    chmod 600 "$key"

    # GitHub's host keys, PINNED. Trusting whatever answers on first connect is the
    # one moment a fake github.com could hand a base station its own code. These
    # match both https://api.github.com/meta and GitHub's published fingerprints
    # (checked 2026-09-17). If GitHub ever rotates them, clones fail loudly with a
    # host key error — update the lines below from those two sources.
    cat > "$EDGE_KNOWN_HOSTS" <<'EOF'
github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=
github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=
EOF
    chmod 644 "$EDGE_KNOWN_HOSTS"

    # BatchMode: never stop and ask for a password or passphrase. On an unattended
    # box a hidden prompt is a hang, not a question.
    export GIT_SSH_COMMAND="ssh -i $key -o IdentitiesOnly=yes -o UserKnownHostsFile=$EDGE_KNOWN_HOSTS -o StrictHostKeyChecking=yes -o BatchMode=yes"

    # Ask GitHub before cloning, so the answer is a clear sentence instead of a
    # clone failing halfway through. "Not added yet" and "no internet" are different
    # problems with different fixes, and they must not print the same advice — the
    # first time someone pastes a key into GitHub to fix a dead network cable is the
    # last time they trust this script.
    while ! access_error="$(git ls-remote "$REPO_URL" 2>&1 >/dev/null)"; do
        case "$access_error" in
            *"Could not resolve hostname"*|*"timed out"*|*"Network is unreachable"*|*"Connection refused"*)
                echo "[!] cannot reach GitHub from this machine:"
                echo "    $access_error"
                echo "    This is a network problem, not a key problem. Get it online and re-run."
                exit 1
                ;;
        esac
        echo
        echo "=================================================================="
        echo " This machine is not allowed to read $repo_name yet."
        echo
        echo " On GitHub: the repo → Settings → Deploy keys → Add deploy key"
        echo "   Title:  $(hostname)"
        echo "   Key:    the line below"
        echo "   Leave 'Allow write access' UNCHECKED — this machine only reads."
        echo
        cat "$key.pub"
        echo "=================================================================="
        if [ -t 0 ]; then
            read -r -p "Press Enter once the key is added (Ctrl+C to stop)... " _
        else
            echo "No terminal to wait on — add the key, then run this again."
            exit 1
        fi
    done
    echo "    GitHub accepts this machine's key"
fi
# <<< repo access

echo "[2] fetching Edge Athlete into $PROJECT_DIR (branch: $EDGE_BRANCH)..."
mkdir -p "$EDGE_HOME"

# Same location as the base station, and for the same reason: /srv belongs to the
# machine, not to whoever is logged in. A rack screen that was set up by one account
# must keep working after that account is renamed or replaced.
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "    already installed, updating..."
    # set-url is also what MOVES a screen between repos — one installed from the team
    # repo switches here the first time this file runs on it.
    git -C "$PROJECT_DIR" remote set-url origin "$REPO_URL"
    # The refspec is spelled out for the same reason bootstrap.sh spells it out: the
    # first clone is --single-branch, so the remote maps only that one branch and a
    # later `git fetch origin main` never creates refs/remotes/origin/main. Naming
    # the destination forces it into existence, so switching branches works.
    git -C "$PROJECT_DIR" fetch --depth 1 origin \
        "+refs/heads/$EDGE_BRANCH:refs/remotes/origin/$EDGE_BRANCH"
    # -f because a screen is a deployment target, not a working copy. Untracked
    # files are left alone.
    git -C "$PROJECT_DIR" checkout -f -B "$EDGE_BRANCH" "origin/$EDGE_BRANCH"
else
    git clone --depth 1 --branch "$EDGE_BRANCH" "$REPO_URL" "$PROJECT_DIR"
fi

# Remember how to authenticate, IN the clone, so a later `ea-update` — plain `git
# fetch`, long after this environment is gone — still reaches GitHub with the key.
# Cleared for non-SSH remotes. Same as bootstrap.sh.
if repo_uses_ssh; then
    git -C "$PROJECT_DIR" config core.sshCommand "$GIT_SSH_COMMAND"
else
    git -C "$PROJECT_DIR" config --unset core.sshCommand 2>/dev/null || true
fi

echo "[3] handing off to rack-kiosk-setup.sh..."
chmod +x "$PROJECT_DIR/scripts/rack-screen/rack-kiosk-setup.sh"
exec "$PROJECT_DIR/scripts/rack-screen/rack-kiosk-setup.sh" rack
