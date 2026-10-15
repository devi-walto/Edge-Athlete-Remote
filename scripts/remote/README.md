# scripts/remote/ — the hosted server

Everything for running Edge Athlete as a hosted service: one server (a PC at home, or
a machine on Azure or AWS) running Kubernetes (k3s), with many schools on it. The gym
box's scripts are in `../basestation/` and `../rack-screen/`; nothing here touches them.

| File | What it is |
|---|---|
| `bootstrap.sh` | copied to a new server and run once; gets the code there and hands off to `eactl init`. Re-running it is the update |
| `eactl.sh` | the server's commands (`eactl new`, `eactl list`, …). Runs **on** the server: SSH in, then type `eactl` |

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
| The deploy key | `/etc/edgeathlete/deploy-keys/` | root | the same place a gym box keeps its own |
| The `eactl` shortcut | `/usr/local/bin/eactl` | root | typeable from any folder, like the gym box's `ea-*` |
| Your copy of the cluster key | `~/.kube/config` | you | it *is* your access, so it stays personal |

The settings live apart from the code on purpose: the code can be replaced, moved or
upgraded without losing them.

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
