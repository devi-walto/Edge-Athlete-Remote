#!/usr/bin/env bash
# Exercises bootstrap.sh — the one-command install — against a REAL git remote
# (a local bare repo holding the working tree), so the clone/update logic is the
# genuine article rather than a stub.
set -uo pipefail

STUBS=/tmp/stubs; mkdir -p "$STUBS"
for c in apt-get systemctl hostnamectl; do
  printf '#!/bin/sh\nexit 0\n' > "$STUBS/$c"
done
printf '#!/bin/sh\necho "$*" >> /tmp/docker-calls\nexit 0\n' > "$STUBS/docker"
# We run as root already; sudo just has to pass VAR=value assignments through.
printf '#!/bin/sh\nexec env "$@"\n' > "$STUBS/sudo"
cat > "$STUBS/nmcli" <<'EOF'
#!/bin/sh
case "$*" in *"-f DEVICE,TYPE device"*) echo "wlp2s0:wifi"; exit 0 ;; esac
exit 0
EOF
printf '#!/bin/sh\necho "$*" >> /tmp/curl-calls\nexit 0\n' > "$STUBS/curl"

# ── a fake `ssh`, standing in for GitHub ──────────────────────────────────────
# The private-repo path goes over SSH, and a test cannot use the real GitHub. git
# runs this with the remote command as its LAST argument (git-upload-pack '<path>'),
# so the fake runs that command against a local bare repo — a real clone, over the
# real code path, offline. /tmp/fake-ssh-mode makes it refuse the key or act like
# there is no network instead.
cat > "$STUBS/ssh" <<'EOF'
#!/bin/sh
echo "$*" >> /tmp/ssh-calls
for a; do cmd="$a"; done
case "$(cat /tmp/fake-ssh-mode 2>/dev/null)" in
  denied)  echo "git@github.com: Permission denied (publickey)." >&2; exit 255 ;;
  offline) echo "ssh: Could not resolve hostname github.com: Temporary failure in name resolution" >&2; exit 255 ;;
esac
exec "${cmd%% *}" "$(cat /tmp/fake-ssh-repo)"
EOF
chmod +x "$STUBS"/*
export PATH="$STUBS:$PATH"
export GIT_CONFIG_GLOBAL=/tmp/gitconfig
git config --global user.email t@t.t; git config --global user.name t
git config --global init.defaultBranch main

pass=0; fail=0
check() {
  if printf '%s' "$3" | grep -qF -- "$2"; then echo "  ok    $1"; pass=$((pass+1))
  else echo "  FAIL  $1"; echo "        wanted: $2"; echo "        got:    $3"; fail=$((fail+1)); fi
}

# ── a fake origin holding the real working tree ─────────────────────────────
echo "=== building a local remote on branch main ==="
mkdir -p /tmp/src && cp -r /src/scripts /tmp/src/ \
  && cp /src/docker-compose.yml /src/.env.example /tmp/src/
cd /tmp/src
git init -q && git checkout -qb main && git add -A && git commit -qm "base"
git clone -q --bare /tmp/src /tmp/origin.git
# /tmp/src was init'd, not cloned, so it has no `origin` to push back to. Without
# this the "upstream moved on" step below silently does nothing and the update
# test passes for the wrong reason.
git remote add origin /tmp/origin.git
echo "    origin has: $(git --git-dir=/tmp/origin.git branch --format='%(refname:short)' | tr '\n' ' ')"

export EDGE_REPO_URL=file:///tmp/origin.git
export EDGE_HOME=/srv/edge-athlete

echo
echo "=== run 1: fresh machine, one command ==="
out1=$(bash /tmp/src/scripts/basestation/bootstrap.sh 2>&1); rc1=$?
echo "$out1" | sed 's/^/    /'
echo
echo "--- assertions ---"
check "exits 0" "0" "$rc1"
check "lands at the documented path" "found the repo at /srv/edge-athlete/Edge-Athlete" "$out1"
check "keeps the repo's own name (Edge-Athlete, not edge-athlete)" "Edge-Athlete" \
      "$(ls /srv/edge-athlete)"
check "does NOT create a lowercase twin" "1" "$(ls /srv/edge-athlete | wc -l | tr -d ' ')"
check "checks out the default branch (main)" "main" \
      "$(git -C /srv/edge-athlete/Edge-Athlete rev-parse --abbrev-ref HEAD)"
check "hands off to setup, which provisions" "setup complete" "$out1"
check "boot service points into the install" \
      "ExecStart=/srv/edge-athlete/Edge-Athlete/scripts/basestation/startup.sh" \
      "$(cat /etc/systemd/system/edgeathlete.service)"
check "a non-SSH remote makes NO deploy key" "no key" \
      "$(ls /etc/edgeathlete/deploy-keys 2>/dev/null | grep -q . && echo has key || echo no key)"
check "a non-SSH remote stores no ssh command" "unset" \
      "$(git -C /srv/edge-athlete/Edge-Athlete config core.sshCommand || echo unset)"

echo
echo "=== run 2: same command again = update in place ==="
# New commit upstream, and someone has poked a tracked file on the base station.
cd /tmp/src && echo "# upstream change" >> docker-compose.yml \
  && git commit -qam "upstream moves on" \
  && git push -q origin main \
  || { echo "    [test setup] PUSH FAILED — the update test would be meaningless"; exit 1; }
echo "LOCAL EDIT" >> /srv/edge-athlete/Edge-Athlete/docker-compose.yml
echo "KEEP=1" >> /srv/edge-athlete/Edge-Athlete/.env

out2=$(bash /tmp/src/scripts/basestation/bootstrap.sh 2>&1); rc2=$?
echo "$out2" | sed 's/^/    /'
echo
echo "--- assertions ---"
check "exits 0" "0" "$rc2"
check "recognises an existing install" "already installed, updating" "$out2"
check "picks up the upstream change" "upstream change" \
      "$(cat /srv/edge-athlete/Edge-Athlete/docker-compose.yml)"
# The reason this is `fetch + reset --hard` and not `git pull`: a stray local
# edit on an unattended box must never turn an update into a merge conflict.
check "discards local edits to TRACKED files rather than conflicting" "0" \
      "$(grep -c 'LOCAL EDIT' /srv/edge-athlete/Edge-Athlete/docker-compose.yml)"
check "leaves .env alone — it is untracked, and it is the machine's own" "KEEP=1" \
      "$(cat /srv/edge-athlete/Edge-Athlete/.env)"
check "leaves the machine config alone" "wlp2s0" "$(cat /etc/edgeathlete/basestation.conf)"

SSH_URL=git@github.com:devi-walto/Edge-Athlete-Remote.git
KEY=/etc/edgeathlete/deploy-keys/Edge-Athlete-Remote
echo /tmp/origin.git > /tmp/fake-ssh-repo

echo
echo "=== run 3: private repo, key NOT added on GitHub yet, no terminal ==="
echo denied > /tmp/fake-ssh-mode
out3=$(EDGE_REPO_URL=$SSH_URL EDGE_HOME=/srv/ssh-test bash /tmp/src/scripts/basestation/bootstrap.sh </dev/null 2>&1); rc3=$?
echo "$out3" | sed 's/^/    /'
echo
echo "--- assertions ---"
check "stops (non-zero) rather than cloning half a repo" "nonzero" "$([ "$rc3" -ne 0 ] && echo nonzero || echo zero)"
check "says plainly this machine is not allowed yet" "not allowed to read Edge-Athlete-Remote" "$out3"
check "prints the public key to paste into GitHub" "ssh-ed25519 " "$out3"
check "tells you to leave write access off" "UNCHECKED" "$out3"
check "explains why it did not wait" "No terminal to wait on" "$out3"
check "the key is named after the repo (GitHub allows one repo per deploy key)" "exists" \
      "$([ -f "$KEY" ] && [ -f "$KEY.pub" ] && echo exists || echo missing)"
check "the private key is readable by root only" "600" "$(stat -c %a "$KEY")"
check "GitHub's ed25519 host key is PINNED, not trusted on first use" \
      "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl" \
      "$(cat /etc/edgeathlete/github_known_hosts)"
check "nothing was cloned" "no clone" "$([ -d /srv/ssh-test/Edge-Athlete ] && echo cloned || echo no clone)"
first_key="$(ssh-keygen -lf "$KEY.pub")"

echo
echo "=== run 4: no internet must NOT be blamed on the key ==="
echo offline > /tmp/fake-ssh-mode
out4=$(EDGE_REPO_URL=$SSH_URL EDGE_HOME=/srv/ssh-test bash /tmp/src/scripts/basestation/bootstrap.sh </dev/null 2>&1); rc4=$?
echo "$out4" | sed 's/^/    /'
echo
echo "--- assertions ---"
check "stops (non-zero)" "nonzero" "$([ "$rc4" -ne 0 ] && echo nonzero || echo zero)"
check "calls it a network problem" "network problem, not a key problem" "$out4"
check "does NOT blame the key for a dead network" "no key advice" \
      "$(printf '%s' "$out4" | grep -q 'not allowed to read' && echo blamed the key || echo no key advice)"
# A base station in AP mode has no uplink, so "offline" is the NORMAL first run. It
# must still hand over the key, or enrolling means a second trip to the machine.
check "still prints the key so it can be enrolled offline" "ssh-ed25519 " "$out4"
check "and says where to put it" "Deploy keys (write access OFF)" "$out4"

echo
echo "=== run 5: key added — the real SSH clone path ==="
echo ok > /tmp/fake-ssh-mode; : > /tmp/ssh-calls
out5=$(EDGE_REPO_URL=$SSH_URL EDGE_HOME=/srv/ssh-test bash /tmp/src/scripts/basestation/bootstrap.sh </dev/null 2>&1); rc5=$?
echo "$out5" | sed 's/^/    /'
echo
echo "--- assertions ---"
check "exits 0" "0" "$rc5"
check "confirms GitHub accepted the key" "GitHub accepts this machine's key" "$out5"
check "clones over SSH into the install" "main" \
      "$(git -C /srv/ssh-test/Edge-Athlete rev-parse --abbrev-ref HEAD 2>&1)"
check "ssh was given THIS repo's key" "-i $KEY" "$(cat /tmp/ssh-calls)"
check "ssh refuses unknown host keys" "StrictHostKeyChecking=yes" "$(cat /tmp/ssh-calls)"
check "the key is REMEMBERED in the clone, for ea-update later" "-i $KEY" \
      "$(git -C /srv/ssh-test/Edge-Athlete config core.sshCommand)"
check "the remembered command uses the pinned host keys" "UserKnownHostsFile=/etc/edgeathlete/github_known_hosts" \
      "$(git -C /srv/ssh-test/Edge-Athlete config core.sshCommand)"
check "re-running does NOT replace the key already added on GitHub" "$first_key" "$(ssh-keygen -lf "$KEY.pub")"

echo
echo "=== run 6: a machine installed from ANOTHER repo moves to this one ==="
# /srv/edge-athlete was installed from a file:// remote in run 1 — the shape of a
# base station that came from the team repo. Running the new bootstrap on it must
# repoint it, not leave it quietly updating from the old place.
out6=$(EDGE_REPO_URL=$SSH_URL bash /tmp/src/scripts/basestation/bootstrap.sh </dev/null 2>&1); rc6=$?
echo "--- assertions ---"
check "exits 0" "0" "$rc6"
check "origin now points at the private repo" "$SSH_URL" \
      "$(git -C /srv/edge-athlete/Edge-Athlete remote get-url origin)"
check "and remembers the key for future updates" "-i $KEY" \
      "$(git -C /srv/edge-athlete/Edge-Athlete config core.sshCommand)"

echo
echo "=== run 7: ea-update pulls through the clone, with NO download ==="
cd /tmp/src && echo "# second upstream change" >> docker-compose.yml \
  && git commit -qam "upstream moves again" && git push -q origin main \
  || { echo "    [test setup] PUSH FAILED"; exit 1; }
: > /tmp/curl-calls; : > /tmp/ssh-calls
# No GIT_SSH_COMMAND in this environment: the only way this fetch can authenticate
# is the core.sshCommand the bootstrap saved. That is exactly what has to work.
out7=$(env -u GIT_SSH_COMMAND EDGE_DIR=/srv/edge-athlete/Edge-Athlete \
       bash /tmp/src/scripts/basestation/ea.sh update main </dev/null 2>&1); rc7=$?
echo "$out7" | tail -6 | sed 's/^/    /'
echo "--- assertions ---"
check "exits 0" "0" "$rc7"
check "picks up the new upstream change" "second upstream change" \
      "$(cat /srv/edge-athlete/Edge-Athlete/docker-compose.yml)"
check "authenticated with the saved key" "-i $KEY" "$(cat /tmp/ssh-calls)"
check "ran the branch's bootstrap" "already installed, updating" "$out7"
check "downloaded nothing from raw.githubusercontent.com" "no downloads" \
      "$(grep -q raw.githubusercontent /tmp/curl-calls && echo DOWNLOADED || echo no downloads)"

echo
echo "=== run 8: a failed update must not leave the gym with no app ==="
: > /tmp/docker-calls
out8=$(EDGE_DIR=/srv/edge-athlete/Edge-Athlete bash /tmp/src/scripts/basestation/ea.sh reset no-such-branch </dev/null 2>&1); rc8=$?
echo "$out8" | tail -6 | sed 's/^/    /'
echo "--- assertions ---"
check "says the fetch failed and why it might have" "could not fetch 'no-such-branch'" "$out8"
check "says it is restarting what it already had" "restarting the code already on this machine" "$out8"
check "still brings the stack back up" "compose up -d" "$(cat /tmp/docker-calls)"

echo
echo "=== the two bootstraps share ONE access block ==="
check "repo-access block is identical in bootstrap.sh and rack-bootstrap.sh" "identical" \
      "$(diff <(sed -n '/^# >>> repo access/,/^# <<< repo access/p' /src/scripts/basestation/bootstrap.sh) \
              <(sed -n '/^# >>> repo access/,/^# <<< repo access/p' /src/scripts/rack-screen/rack-bootstrap.sh) \
         >/dev/null && echo identical || echo DIFFERENT)"

echo
echo "=== rack screen: the same private-repo clone, end to end ==="
# The real rack-kiosk-setup.sh installs a browser; that is not what is under test
# here. A copy of the repo whose kiosk setup just reports how it was called.
rm -rf /tmp/rack-src && cp -r /tmp/src /tmp/rack-src && cd /tmp/rack-src
printf '#!/bin/sh\necho "kiosk setup ran as: $*"\n' > scripts/rack-screen/rack-kiosk-setup.sh
git add -A && git commit -qm "stub kiosk" && git clone -q --bare /tmp/rack-src /tmp/rack-origin.git
echo /tmp/rack-origin.git > /tmp/fake-ssh-repo
out9=$(EDGE_REPO_URL=$SSH_URL EDGE_HOME=/srv/rack-test bash /tmp/src/scripts/rack-screen/rack-bootstrap.sh </dev/null 2>&1); rc9=$?
echo "$out9" | sed 's/^/    /'
echo "--- assertions ---"
check "exits 0" "0" "$rc9"
check "clones over SSH" "main" "$(git -C /srv/rack-test/Edge-Athlete rev-parse --abbrev-ref HEAD 2>&1)"
check "remembers the key for ea-update" "-i $KEY" "$(git -C /srv/rack-test/Edge-Athlete config core.sshCommand)"
check "hands off to kiosk setup as a rack" "kiosk setup ran as: rack" "$out9"

echo
echo "============================================"
echo "  passed: $pass    failed: $fail"
echo "============================================"
[ "$fail" -eq 0 ]
