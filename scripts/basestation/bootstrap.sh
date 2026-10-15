#!/usr/bin/env bash
# bootstrap.sh — get Edge Athlete Remote onto a bare base station with one command.
#
# Run this on a fresh machine and it does everything: installs git, sets up this
# machine's read-only access to the (private) repo, pulls the code down to a fixed
# location, and hands off to setup.sh, which installs Docker and the boot service.
#
# FIRST INSTALL — copy this file over from your laptop, then run it ON the machine:
#
#   scp scripts/basestation/bootstrap.sh edgeathlete@basestation:/tmp/
#   ssh -t edgeathlete@basestation 'sudo bash /tmp/bootstrap.sh'
#
# The first run prints this machine's public key and waits while you add it on
# GitHub (repo → Settings → Deploy keys → Add deploy key, write access OFF). The
# `-t` matters: without a terminal there is nothing to wait on, so it prints the
# key and stops, and you run the same command again once the key is added.
#
# AFTER THAT, just `ea-update`. It pulls through this machine's own clone. Nothing
# here is one-shot — re-running this file is also a full update.
#
# ── WHY THERE IS NO `curl ... | sudo bash` ONE-LINER ANY MORE ──────────────────────
# There was, and it depended on the repo being public. This one is private, and
# GitHub answers an anonymous download from a private repo with a 404 — so the old
# one-liner would hand `sudo bash` an empty script, which does nothing and says
# nothing. An HTTPS clone fails the same way on a machine that has no GitHub login.
#
# ── WHY A DEPLOY KEY PER MACHINE, AND NOT A TOKEN ─────────────────────────────────
# Each machine makes its own key, and GitHub gives it read access to this one repo
# and nothing else. Lose a base station, delete its key, and every other device is
# untouched. A shared token would sit on every device's disk, and revoking it
# would cut them all off at once.
#
# The key is named after the REPO, not just "deploy_key", because GitHub allows a
# deploy key on exactly one repository. A machine that later needs a second repo
# gets a second key automatically instead of an error it would have to diagnose.
#
# WHERE THINGS GO, AND WHY IT IS NOT YOUR HOME DIRECTORY.
# The install lives at /srv/edge-athlete/Edge-Athlete, owned by root. The old
# Pi script hardcoded /home/pi, which meant the whole system quietly depended on
# WHICH USER was logged in — rename the account, add a second admin, or log in
# as anyone else and the boot service pointed at a directory that no longer
# existed. /srv belongs to the machine, not to a person, so nothing below cares
# who is at the keyboard. The directory keeps its old name on purpose: it is an
# install location, and renaming it would break every machine already using it.
#
# Override any of these if you need to. ⚠️ The assignments go AFTER `sudo` — sudo
# scrubs the environment, so anything set before it never reaches this script:
#   sudo EDGE_HOME=/opt/edge-athlete EDGE_BRANCH=some-branch bash /tmp/bootstrap.sh

set -euo pipefail

REPO_URL="${EDGE_REPO_URL:-git@github.com:devi-walto/Edge-Athlete-Remote.git}"
EDGE_HOME="${EDGE_HOME:-/srv/edge-athlete}"

# Installs from `main`. A branch pin is a claim about the world that rots — if you
# pin this to something else, say WHEN and WHY, so the next person can tell whether
# it still holds.
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
                cat "$key.pub"
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

if [ -d "$PROJECT_DIR/.git" ]; then
    # Already installed — update in place. Deliberately NOT `git pull`: the base
    # station is not a place anyone edits code, and a local change (or the old
    # setup script's habit of rewriting startup.sh in place) would turn a routine
    # update into a merge conflict on a machine with no one to resolve it.
    echo "    already installed, updating..."
    # set-url is also what MOVES a machine between repos — a base station installed
    # from the team repo switches here the first time this file runs on it.
    git -C "$PROJECT_DIR" remote set-url origin "$REPO_URL"

    # The refspec is spelled out on purpose, and it is load-bearing when the branch
    # CHANGES. The first install clones with `--branch X --depth 1`, which implies
    # --single-branch and leaves the remote configured to map only that one branch:
    #
    #     fetch = +refs/heads/X:refs/remotes/origin/X
    #
    # So a later `git fetch origin main` downloads main into FETCH_HEAD and never
    # creates refs/remotes/origin/main — and the checkout below then dies with
    # "'origin/main' is not a commit". Naming the destination ref forces it into
    # existence, so switching branches works the same as staying on one.
    git -C "$PROJECT_DIR" fetch --depth 1 origin \
        "+refs/heads/$EDGE_BRANCH:refs/remotes/origin/$EDGE_BRANCH"
    # `checkout -f`, and the -f is load-bearing. Plain `checkout -B` REFUSES when
    # a tracked file has been edited locally — so on a base station where anyone
    # once poked docker-compose.yml, the update aborted and the box silently sat
    # on old code. Forcing discards those edits, which is right: the install is a
    # deployment target, not a working copy. Untracked files are NOT touched, so
    # .env — the machine's own config — survives.
    git -C "$PROJECT_DIR" checkout -f -B "$EDGE_BRANCH" "origin/$EDGE_BRANCH"
else
    git clone --depth 1 --branch "$EDGE_BRANCH" "$REPO_URL" "$PROJECT_DIR"
fi

# Remember how to authenticate, IN the clone. `ea-update` runs plain `git fetch`
# later, long after this script's environment is gone — without this it would
# reach GitHub with no key and get refused. Cleared for non-SSH remotes so a
# machine moved back to one is not left pointing at a key it no longer uses.
if repo_uses_ssh; then
    git -C "$PROJECT_DIR" config core.sshCommand "$GIT_SSH_COMMAND"
else
    git -C "$PROJECT_DIR" config --unset core.sshCommand 2>/dev/null || true
fi

# The repo keeps its own name. The old script renamed Edge-Athlete to
# edge-athlete on arrival, which meant the directory you cloned was never the
# directory things ran from — a small thing that cost real time every time
# somebody went looking for it.
echo "[3] handing off to setup.sh..."
chmod +x "$PROJECT_DIR/scripts/basestation/setup.sh"
exec "$PROJECT_DIR/scripts/basestation/setup.sh"
