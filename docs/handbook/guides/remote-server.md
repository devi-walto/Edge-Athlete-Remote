<!--
this guide — running the remote server day to day, and setting up a new one.

Day to day is at the top because it's what you'll open most. Setting up a new
server is below it, once per machine. Like the local install guide, the detail
is folded into dropdowns so the page skims in a minute. Add inside a dropdown.
-->

# Remote server

:::{note}
How to run it. For why it's built this way (k3s on the Dell, Traefik, one database per school, demo school first), see {doc}`../../journal/core/remote/hosting` and {doc}`../../journal/core/remote/releases`. Every command is in {doc}`../reference/eactl`.
:::

Everything happens **on the server**, over SSH through Tailscale:

```bash
ssh <you>@<server>
eactl list
```

## Day to day

| I want to… | Run |
|---|---|
| see every school | `eactl list` |
| check one school | `eactl status "Name"` |
| add a school | `eactl new "Name"`, then `eactl setup-code "Name"` |
| ship a release | nothing: it deploys itself once its tag reaches `main` |
| get the athletes' link | `eactl get-session-link "Name"` |
| run a demo | `eactl seed "Demo U"`, then `eactl sim "Demo U" --phantom` |
| take a safety copy | `eactl backup "Name"` |
| read a school's logs | `eactl logs "Name" django -f` |

::::{dropdown} Add a school
1. **Make it:** `eactl new "Lincoln High"`. It's live at its own address over HTTPS within a minute or two (the certificate takes the longest). `eactl status "Lincoln High"` shows when every part is up.
2. **Issue its setup code:** `eactl setup-code "Lincoln High"`. Send the code to the school's coach.
3. **The coach claims it:** they open the school's address, type the code on the first-run screen, and make the first administrator login. Until then, nobody can do anything there.

**A demo school** gets `--canary` so it's updated first on every deploy: `eactl new "Demo U" --canary`.

**A new address** needs its DNS record first (see "Your domain" below), then `eactl init` with the subdomain added, or `--address`.
::::

::::{dropdown} Ship a release
**Normally there's nothing to type.** Pull request into `SprintBranch`, CI green, merge, tag the merge (`v0.8.3`). When "Move main forward" brings the tag to `main`, GitHub builds the images and the runner on the server moves every school to it, demo first. Watch it under the repo's **Actions** tab. The release page publishes itself once every school is on it.

**By hand**, if the runner is down:

```bash
eactl update --all v0.8.3
```

**One school only:** `eactl update "Name" v0.8.3`.

**Roll a school back:** `eactl update "Name" v0.8.2`. It checks which database changes v0.8.2 doesn't know about, offers to undo them behind a safety copy, and **holds** the school so the next deploy doesn't move it forward again. `eactl unhold "Name"` when it's fixed.
::::

::::{dropdown} Run a demo
```bash
eactl seed "Demo U"                 # four invented athletes, a plan, a live session
eactl sim "Demo U" --phantom        # they lift on their own for 2 hours
eactl get-session-link "Demo U"     # the link for a real athlete to join
eactl sim "Demo U" --stop           # end it early
```

`seed` only adds, and refuses if the school has no coach yet or another session is running. `--reset` removes its earlier demo rows first. The hands-on demo athlete is never a phantom; a real person lifts as them.
::::

::::{dropdown} Back up and restore
```bash
eactl backup "Name"       # a safety copy now
eactl restore "Name"      # lists them, newest first, and asks which
```

`restore` replaces the school's database, **after taking a fresh safety copy**, so it can be undone too. `remove` takes one by itself. Copies live in `/var/lib/edgeathlete/snapshots/<short name>/`: the last 5, none older than 30 days.

:::{warning}
**Safety copies are on the same machine as the schools.** If the Dell dies, so do they. Copy anything you can't lose somewhere else.
:::
::::

::::{dropdown} Something's wrong with a school
1. `eactl status "Name"`: which part is down, which release, is the certificate valid.
2. `eactl logs "Name" django`: what it printed. Other parts: `react`, `mosquitto`, `mqtt-listener`, `monitoring-publisher`, `setup` (start-up: migrations, rack recovery), `sim`. Add `-f` to keep following.
3. `eactl shell "Name"`: a command line inside its Django, for `python manage.py …` by hand.

**Every school down at once?** Check the cluster before any one school: `eactl check`, then `kubectl get pods -A` for anything not `Running`. If it started right after a reboot, see the kernel warning under "The machine" below.
::::

::::{dropdown} A coach is locked out
- **The only administrator lost their login:** `eactl make-admin "Name" <username>` makes an existing login an administrator again. Add `--reactivate` if it was switched off. It never makes a login or sets a password.
- **A coach forgot their password:** any administrator resets it from the coach screens.
- **An athlete forgot theirs:** their coach sends a new login link. Nothing to do on the server.
::::

::::{dropdown} Remove a school
```bash
eactl remove "Name"
```

Deletes its app, settings, database and database login. It takes a safety copy first, and only goes ahead once you type the school's short name.
::::

::::{dropdown} eactl itself is out of date
eactl updates itself every hour. `eactl version` shows eactl's release next to each school's. `eactl self-update` updates it now (asks for your password). Neither touches a school.
::::

## Set up a new server

Once per machine. It works the same on a PC at home or a machine on AWS or Azure; only "The router" step is home-only.

::::{dropdown} 1. The machine
1. **Ubuntu Server**, with your user.
2. **Tailscale** joined, so the server is reachable privately.
3. **Your laptop's SSH key** added (`ssh-copy-id <you>@<server>`) and SSH passwords turned off. AWS and Azure ask for the key when the machine is made.
4. **k3s**, with its defaults (Traefik stays on):

   ```bash
   curl -sfL https://get.k3s.io | sh -
   mkdir -p ~/.kube && sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config && sudo chown "$USER" ~/.kube/config
   ```

:::{warning}
**Watch kernel updates.** On Nov 5, 2026, Ubuntu's kernel 7.0.0-42 started applying the host's AppArmor rules inside containers, and every container broke after a reboot (Postgres hung, the brokers crash-looped). The fix was booting the previous kernel and holding updates:

```bash
sudo apt-mark hold linux-generic linux-image-generic linux-headers-generic
```

Until that's properly fixed, test a new kernel with a planned reboot, never a surprise one.
:::
::::

::::{dropdown} 2. The router (home only)
Forward **80 and 443** to the server, and nothing else. Never forward 6443, the cluster's control port.

Check first that the connection has its own public address (no CGNAT): the address the router reports must match what `curl -4 ifconfig.me` prints on the server.
::::

::::{dropdown} 3. Your domain
At your domain provider (Porkbun today). None of this is done for you:

1. The domain uses the provider's own nameservers.
2. Create an API key pair in the provider's account settings.
3. Turn on API access for the domain. It's a per-domain switch, off by default.
4. Add an **A record for each subdomain** (`demo`, `test`, …) pointing at the server's public address.
5. Store the API keys on the server, typed by hand, never saved in a file:

   ```bash
   kubectl create namespace ddns
   read -rs PORKBUN_API_KEY; read -rs PORKBUN_SECRET_KEY
   kubectl -n ddns create secret generic porkbun-api \
     --from-literal=PORKBUN_API_KEY="$PORKBUN_API_KEY" \
     --from-literal=PORKBUN_SECRET_KEY="$PORKBUN_SECRET_KEY"
   unset PORKBUN_API_KEY PORKBUN_SECRET_KEY
   ```

From then on, the DNS updater keeps every record pointed at the server when the home address changes.
::::

::::{dropdown} 4. The server's two secrets
Both go in the shared namespace, typed on the server, never saved in a file.

```bash
kubectl create namespace edge-athlete
```

**The image pull key**, so the server can download the app's private images: a GitHub token with only `read:packages`. It expires, so renew it before then.

```bash
read -rs GHCR_TOKEN
kubectl -n edge-athlete create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io --docker-username=<github user> \
  --docker-password="$GHCR_TOKEN"
unset GHCR_TOKEN
```

**The database's administrator password**, made and stored in one step so it's never shown. Nobody types it again; eactl reads it from here.

```bash
kubectl -n edge-athlete create secret generic postgres-admin \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 32)"
```
::::

::::{dropdown} 5. Get the code there, and eactl
From your laptop:

```bash
scp scripts/remote/bootstrap.sh <you>@<server>:/tmp/
ssh -t <you>@<server> 'sudo bash /tmp/bootstrap.sh'
```

The first run prints **this server's own public key** and waits. Add it on GitHub (the repo → **Settings → Deploy keys → Add deploy key**) with **"Allow write access" unchecked**, then press Enter. It clones the code to `/srv/edge-athlete/Edge-Athlete-Remote`, installs the hourly self-update, and hands off to `eactl init`, which asks for your domain, email and subdomains.

`-t` on the `ssh` matters: without a terminal there's nothing to wait on, so it prints the key and stops.
::::

::::{dropdown} 6. The server-wide pieces
```bash
eactl check            # is the cluster answering?
eactl apply-cluster    # cert-manager, Let's Encrypt, Traefik settings, the hairpin rule, the DNS updater
eactl apply-db         # the shared Postgres
```

Both `apply` commands show a preview and ask before changing anything.
::::

::::{dropdown} 7. The first schools
The demo first, so the template proves itself:

```bash
eactl new "Demo U" --canary
eactl setup-code "Demo U"
```

Then the real school the same way, without `--canary`. See "Add a school" above.
::::

::::{dropdown} 8. Automatic deploys (the runner)
So a version tag deploys itself. Once per server.

**A user for the runner**, with no password and no sudo:

```bash
sudo useradd --create-home --shell /bin/bash ea-deploy
```

**Its cluster login**, which can update schools and nothing else (made by `eactl apply-cluster`):

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

Check it can see schools but not their secrets (the second should say `Forbidden`):

```bash
sudo -u ea-deploy kubectl get namespaces -l ea/school
sudo -u ea-deploy kubectl -n <school namespace> get secrets
```

**The runner.** On GitHub: the repo → **Settings → Actions → Runners → New self-hosted runner** → Linux. It shows a one-time registration token; use it below and never save it.

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

On GitHub it then shows as **Idle** with the label `ea-deploy`. It's a service, so it survives logouts and reboots.

**Keep strangers' code off it:** Settings → Actions → General → **"Require approval for all outside collaborators"**, and a tag rule so only you can push `v*` tags.
::::

::::{dropdown} 9. Only the 3-day job can move main
So a pull request can never be merged straight into `main`. Once per repo, not per server.

1. **Make a key on your laptop**, no passphrase: `ssh-keygen -t ed25519 -N "" -C "promote-main" -f ~/promote-main-key`
2. **Public half to GitHub:** Settings → Deploy keys → Add deploy key, title `promote-main`, paste `~/promote-main-key.pub`, tick **Allow write access**.
3. **Private half to the job:** Settings → Secrets and variables → Actions → New repository secret, name `PROMOTE_MAIN_KEY`, paste `~/promote-main-key`. Then delete both files from your laptop.
4. **Check the job works with the key:** Actions → Move main forward → Run workflow, while `main` is behind `SprintBranch`.
5. **Turn the rule on:** Settings → Rules → Rulesets → protect main → **Restrict updates**, bypass list → **Deploy keys** → Always.
6. **Check both sides:** a pull request into `main` can't be merged, and the next Move main forward still moves it.
::::
