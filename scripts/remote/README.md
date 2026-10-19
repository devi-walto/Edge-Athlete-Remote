# scripts/remote/ — the remote server

Everything for running Edge Athlete as a remote service: one server (a PC at home, or
a machine on Azure or AWS) running Kubernetes (k3s), with many schools on it. The gym
box's scripts are in `../basestation/` and `../rack-screen/`; nothing here touches them.

| File | What it is |
|---|---|
| `bootstrap.sh` | copied to a new server and run once; gets the code there and hands off to `eactl init`. Re-running it is the update |
| `eactl.sh` | the server's commands (`eactl new`, `eactl list`, …). Runs **on** the server: SSH in, then type `eactl` |
| `update-clone.sh` + `systemd/` | an hourly timer (installed by `bootstrap.sh`) that moves the server's copy of the code to the newest released version, so the `eactl` you type matches what the schools run. Re-running `bootstrap.sh` is only needed for a new machine or new settings. `sudo edgeathlete-update-clone` updates now |

## Before you start: the machine

Scripts start from a machine that already works. Prepare it by hand, once:

1. Linux (Ubuntu Server) installed, with your user.
2. Tailscale joined, so the server is reachable privately.
3. Your laptop's SSH key added (`ssh-copy-id user@server`) and SSH passwords turned
   off. AWS and Azure ask for the key when the machine is made.
4. k3s installed.
5. **Your domain and its DNS records**, at your domain provider (Porkbun today). Do all
   of these; none is done for you:
   1. The domain uses the provider's own nameservers.
   2. **Create an API key pair** in the provider's account settings.
   3. **Turn on API access for the domain** (a per-domain switch, off by default).
   4. **Add an A record for each subdomain** (e.g. `test`, `demo`) pointing at the
      server's public IP. Find the IP with `curl -4 ifconfig.me` on the server.
   5. **Store the API keys on the server** as the Secret `porkbun-api`, typed by hand,
      never saved in a file:

      ```bash
      kubectl create namespace ddns
      read -rs PORKBUN_API_KEY; read -rs PORKBUN_SECRET_KEY
      kubectl -n ddns create secret generic porkbun-api \
        --from-literal=PORKBUN_API_KEY="$PORKBUN_API_KEY" \
        --from-literal=PORKBUN_SECRET_KEY="$PORKBUN_SECRET_KEY"
      unset PORKBUN_API_KEY PORKBUN_SECRET_KEY
      ```

   From then on, the DNS updater (`eactl apply-cluster`) keeps every record pointed at
   the server when the home IP changes, and adds the record for any new subdomain you
   give `eactl init`.
6. **The server's two other secrets**, in the shared namespace `edge-athlete`. Both are
   typed on the server and never saved in a file:

   ```bash
   kubectl create namespace edge-athlete
   ```

   - **The image pull key**, so the server can download the app's private images. A
     GitHub token with only `read:packages`; it expires, so renew it before then.

     ```bash
     read -rs GHCR_TOKEN
     kubectl -n edge-athlete create secret docker-registry ghcr-pull \
       --docker-server=ghcr.io --docker-username=<github user> \
       --docker-password="$GHCR_TOKEN"
     unset GHCR_TOKEN
     ```

   - **The database's administrator password**: long and random, made and stored in
     one step, so it is never shown. Nobody types it again; `eactl` reads it from here.

     ```bash
     kubectl -n edge-athlete create secret generic postgres-admin \
       --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 32)"
     ```

## From a new server to a running school

```text
YOUR LAPTOP                          THE SERVER (a home PC, Azure, AWS…)
───────────                          ───────────────────────────────────
scp scripts/remote/bootstrap.sh ──▶  /tmp/bootstrap.sh
ssh -t user@server 'sudo bash /tmp/bootstrap.sh'
                                     │
                                     ▼
              ┌─ bootstrap.sh (root; once, and re-run = update) ────────┐
              │ 1. repo access: this server's deploy key                │
              │ 2. clone/update → /srv/edge-athlete/Edge-Athlete-Remote │
              │ 3. hand off to eactl init                               │
              └─────────────────────────────────────────────────────────┘
                                     │
                                     ▼
              ┌─ eactl init (asks questions; once per server) ──────────┐
              │ • asks domain, email, subdomains                        │
              │   → /etc/edgeathlete/eactl.env                          │
              │ • checks kubectl, envsubst, your copy of the key        │
              │ • shortcut /usr/local/bin/eactl                         │
              │ • ✓ finished + command list                             │
              └─────────────────────────────────────────────────────────┘
                                     │
                                     ▼  from then on, SSH in and type:
              ┌─ eactl <command> (you, from any folder) ────────────────┐
              │ check          is the cluster answering?                │
              │ apply-cluster  server add-ons, k8s/cluster (preview 1st)│
              │ apply-db       the shared database, k8s/db (preview 1st)│
              │ new <school>   a school: its database, namespace, app   │
              │ list           every school, address, version, status   │
              └─────────────────────────────────────────────────────────┘
                                     │ reads
                                     ▼
              /srv/edge-athlete/Edge-Athlete-Remote/k8s/   the YAML
              /etc/edgeathlete/eactl.env                   the settings
```

## Where things live, and why

| What | Where | Owner | Why there |
|---|---|---|---|
| The code and YAML | `/srv/edge-athlete/Edge-Athlete-Remote` | root | belongs to the machine, not to whoever logs in; replaced on update, never edited in place |
| The settings | `/etc/edgeathlete/eactl.env` | root, readable by the operator | the machine's settings; survive every code update |
| The deploy key | `/etc/edgeathlete/deploy-keys/` | root | the same place a local install keeps its own |
| The `eactl` shortcut | `/usr/local/bin/eactl` | root | typeable from any folder, like the local install's `ea-*` |
| Your copy of the cluster key | `~/.kube/config` | you | it *is* your access, so it stays personal |

The settings live apart from the code on purpose: the code can be replaced, moved or
upgraded without losing them.

## The deploy runner (automatic deploys on a version tag)

Once set up, a version releases when its tag is on `main`: tag the merge on
`SprintBranch`, and when "Move main forward" brings it to `main` (every 3 days, or the
button) its images are built on GitHub's machines, then a **runner on this server**
moves every school to it (`eactl update --all --version <tag> --yes`), the demo school
first. A tag on a commit already on `main` releases straight away. The runner reaches out to GitHub for its jobs;
nothing is opened inward. It runs as its own user, with a cluster login that can
update schools and nothing else (`k8s/cluster/deployer.yaml`, applied by
`eactl apply-cluster`). Set up once per server:

1. **A user for the runner**, with no password and no sudo:

   ```bash
   sudo useradd --create-home --shell /bin/bash ea-deploy
   ```

2. **Its cluster login**: a kubeconfig made from the deploy login's key, readable by
   that user only.

   ```bash
   TOKEN=$(kubectl -n edge-athlete get secret ea-deployer-token -o jsonpath='{.data.token}' | base64 -d)
   CA=$(kubectl -n edge-athlete get secret ea-deployer-token -o jsonpath='{.data.ca\.crt}')
   sudo -u ea-deploy mkdir -p /home/ea-deploy/.kube
   sudo -u ea-deploy tee /home/ea-deploy/.kube/config >/dev/null <<EOF
   apiVersion: v1
   kind: Config
   clusters:
     - name: local
       cluster: { server: https://127.0.0.1:6443, certificate-authority-data: $CA }
   users:
     - name: ea-deployer
       user: { token: $TOKEN }
   contexts:
     - name: deploy
       context: { cluster: local, user: ea-deployer }
   current-context: deploy
   EOF
   sudo chmod 600 /home/ea-deploy/.kube/config
   unset TOKEN CA
   ```

   Check it can see schools but not their secrets (the second line should say
   `Forbidden`):

   ```bash
   sudo -u ea-deploy kubectl get namespaces -l ea/school
   sudo -u ea-deploy kubectl -n <a school's namespace> get secrets
   ```

3. **The runner itself** (GitHub's own program). On GitHub: the repo → Settings →
   Actions → Runners → **New self-hosted runner** → Linux. It shows a one-time
   registration token: use it in the `config.sh` line below, never save it anywhere.

   ```bash
   sudo -u ea-deploy bash -c 'mkdir -p ~/actions-runner && cd ~/actions-runner \
     && curl -fsSLo runner.tar.gz https://github.com/actions/runner/releases/download/v2.337.0/actions-runner-linux-x64-2.337.0.tar.gz \
     && echo "70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613  runner.tar.gz" | sha256sum -c \
     && tar xzf runner.tar.gz && rm runner.tar.gz'
   sudo -u ea-deploy bash -c 'cd ~/actions-runner && ./config.sh --unattended \
     --url https://github.com/devi-walto/Edge-Athlete-Remote \
     --token <the registration token> --name "$(hostname)-deploy" --labels ea-deploy'
   sudo bash -c 'cd /home/ea-deploy/actions-runner && ./svc.sh install ea-deploy && ./svc.sh start'
   ```

   (Run as root: the runner user's home folder is private, so your own user can't
   go into it. The checksum line refuses a download that isn't the real file; the
   number is the one GitHub publishes for that version.)

   On GitHub, the runner then shows as **Idle** with the label `ea-deploy`. It
   runs as a service: it survives logouts and starts again after a reboot.

4. **Mark the demo school to go first** on every deploy (a new one can use
   `eactl new "Name" --canary` instead):

   ```bash
   kubectl label namespace ea-<demo short name> ea/canary=true --overwrite
   ```

5. **Keep strangers' code off it.** On GitHub: Settings → Actions → General →
   **"Require approval for all outside collaborators"**, and a tag rule so only you
   can push `v*` tags. The deploy job only runs on tags.

## Only the 3-day job can move `main`

`main` is what gets released, and it only ever moves forward to `SprintBranch`
(`.github/workflows/promote-main.yml`). A pull request merged straight into `main`
would skip `SprintBranch`'s checks and stop that job. So the "protect main" ruleset
lets only one key update `main`: a **deploy key** the job pushes with. Set up once:

1. **Make the key, on your laptop** (no passphrase; the job can't type one):
   `ssh-keygen -t ed25519 -N "" -C "promote-main" -f ~/promote-main-key`
2. **Give GitHub the public half:** the repo → Settings → Deploy keys → Add deploy key →
   title `promote-main`, paste `~/promote-main-key.pub`, tick **Allow write access**.
3. **Give the job the private half:** Settings → Secrets and variables → Actions →
   New repository secret → name `PROMOTE_MAIN_KEY`, paste `~/promote-main-key`.
   Then delete both files from your laptop: GitHub now holds the only copies.
4. **Check the job works with the key** while nothing is blocked yet: Actions → Move main
   forward → Run workflow, at a time when `main` is behind `SprintBranch`.
5. **Turn the rule on:** Settings → Rules → Rulesets → protect main → Add rule →
   **Restrict updates**; under Bypass list → Add bypass → **Deploy keys** → Always. Save.
6. **Check both sides:** a pull request into `main` now can't be merged, and the next
   Move main forward still moves it.

## Later: from a clone to a release bundle

While the code changes daily, the server holds a git clone. Once it settles, each
version tag also publishes `eactl-<version>.tar.gz` (this folder and `k8s/`, nothing
else), and `bootstrap.sh` unpacks that instead of cloning:

```text
/srv/edge-athlete/
├── releases/
│   ├── v0.4.0/                    eactl.sh + k8s/
│   └── v0.5.0/                    the next version, unpacked beside it
└── current → releases/v0.5.0      the shortcut points through this
/etc/edgeathlete/eactl.env         untouched by updates
```

Updating is unpacking the new version and pointing `current` at it; rolling back is
pointing it back. A server's commands then always match the version of the app it
runs. A real Linux package (`apt install`) would follow the same rule: code in one
place, settings in `/etc`, which `apt` never overwrites once edited.
