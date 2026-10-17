#!/usr/bin/env bash
# bootstrap.sh — get Edge Athlete's remote-server tools onto a new server.
#
# Run once on a server that already works (Linux, your user, Tailscale, SSH key,
# k3s; see README.md). It sets up the server's read-only access to the repo, puts
# the code in a fixed place, and hands off to `eactl init`. Re-running it is the
# update.
#
# FIRST INSTALL — copy this file over from your laptop, then run it ON the server:
#
#   scp scripts/remote/bootstrap.sh user@server:/tmp/
#   ssh -t user@server 'sudo bash /tmp/bootstrap.sh'
#
# The first run prints the server's key and waits while you add it on GitHub
# (repo → Settings → Deploy keys, write access OFF). `-t` gives it a terminal to
# wait on.
#
# Modelled on ../basestation/bootstrap.sh, the local install's; its comments explain the
# deploy key and the update steps at length. The code goes in /srv, not a home
# folder, for the reason given there: it belongs to the machine, not to whoever
# is logged in.
#
# Settings to change if you need to. They go AFTER `sudo` (sudo drops anything
# set before it):
#   sudo EDGE_BRANCH=some-branch bash /tmp/bootstrap.sh

set -euo pipefail

REPO_URL="${EDGE_REPO_URL:-git@github.com:devi-walto/Edge-Athlete-Remote.git}"
EDGE_HOME="${EDGE_HOME:-/srv/edge-athlete}"
EDGE_BRANCH="${EDGE_BRANCH:-main}"

PROJECT_DIR="$EDGE_HOME/Edge-Athlete-Remote"

if [ "$(id -u)" -ne 0 ]; then
    echo "[!] needs root — run it with sudo"
    exit 1
fi

echo "[1] installing git..."
if ! command -v git >/dev/null 2>&1 || ! command -v ssh-keygen >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq git ca-certificates openssh-client
fi

# >>> repo access — keep IDENTICAL in all three bootstraps: basestation/, rack-screen/, remote/ (a test checks)
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
                echo
                # The key still gets printed, because making it needed no network and
                # ENROLLING it needs no network either — that part happens on GitHub,
                # in a browser, on whatever device you like. A base station in access
                # point mode has no uplink by design, so the common case is exactly
                # this: add the key now from your phone or laptop, plug in ethernet
                # once, re-run. Exiting without showing it would force a second trip
                # to the machine for information it already had in its hand.
                echo "    This machine's key, for when you can reach GitHub:"
                echo "      $key.pub"
                echo
                echo "   ▼▼▼ copy the WHOLE next line, starting with ssh-ed25519 ▼▼▼"
                cat "$key.pub"
                echo "   ▲▲▲ to the line above ▲▲▲"
                echo
                echo "    Add it under the repo's Settings -> Deploy keys (write access OFF)."
                echo "    Then give this machine internet and run this again."
                exit 1
                ;;
        esac
        echo
        echo "=================================================================="
        echo " This machine is not allowed to read $repo_name yet."
        echo
        echo " On GitHub: the repo → Settings → Deploy keys → Add deploy key"
        echo "   Title:  $(hostname)"
        echo "   Key:    the WHOLE line between the arrows, starting with ssh-ed25519"
        echo "   Leave 'Allow write access' UNCHECKED — this machine only reads."
        echo
        echo "   ▼▼▼ copy from the next line ▼▼▼"
        cat "$key.pub"
        echo "   ▲▲▲ to the line above ▲▲▲"
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

echo "[2] fetching the code into $PROJECT_DIR (branch: $EDGE_BRANCH)..."
mkdir -p "$EDGE_HOME"

if [ -d "$PROJECT_DIR/.git" ]; then
    # Already there: update in place, discarding any local edits (this is an
    # install, not a place to edit code). See the local bootstrap for why the
    # fetch spells out where the branch goes.
    echo "    already installed, updating..."
    git -C "$PROJECT_DIR" remote set-url origin "$REPO_URL"
    git -C "$PROJECT_DIR" fetch --depth 1 origin \
        "+refs/heads/$EDGE_BRANCH:refs/remotes/origin/$EDGE_BRANCH"
    git -C "$PROJECT_DIR" checkout -f -B "$EDGE_BRANCH" "origin/$EDGE_BRANCH"
else
    git clone --depth 1 --branch "$EDGE_BRANCH" "$REPO_URL" "$PROJECT_DIR"
fi

# Remember the key in the clone, so later updates can reach GitHub too.
if repo_uses_ssh; then
    git -C "$PROJECT_DIR" config core.sshCommand "$GIT_SSH_COMMAND"
else
    git -C "$PROJECT_DIR" config --unset core.sshCommand 2>/dev/null || true
fi

# Hand off to `eactl init` as YOU, not root: it uses your copy of the cluster key
# and asks for sudo itself where it needs it. SUDO_USER is who ran `sudo`.
echo "[3] handing off to eactl init..."
EACTL="$PROJECT_DIR/scripts/remote/eactl.sh"
chmod +x "$EACTL"
if [ -z "${SUDO_USER:-}" ] || [ "$SUDO_USER" = root ]; then
    echo "[i] run this next, as your own user (not root):"
    echo "      $EACTL init"
    exit 0
fi
exec sudo -u "$SUDO_USER" "$EACTL" init
