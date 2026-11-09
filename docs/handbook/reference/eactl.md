<!--
this page — every eactl command on one page, for looking things up.

eactl is how the remote server is run: SSH in, type eactl. Each command prints the
kubectl it runs before running it, so you can see (and learn) what it did. For the
step-by-step version, see the Remote server guide.
-->

# eactl

The remote server's commands. **It runs on the server:** SSH in, then type `eactl`. `eactl help` prints this list. Every command prints the `kubectl` it runs before running it.

A school is named by its **name** (`"Demo U"`) or its **short name** (`demo-u-u3fyig`, made once from the name and never changed). Tab completion fills in both.

For the step-by-step version, see {doc}`../guides/remote-server`.

## Set up the server (once per server)

| Command | What it does | Changes anything? |
|---|---|---|
| `eactl init` | Asks this server's settings (domain, email, subdomains) and saves them to `/etc/edgeathlete/eactl.env`. Puts the `eactl` shortcut in `/usr/local/bin` | settings only |
| `eactl check` | Is this server's cluster answering? | no |
| `eactl apply-cluster` | Puts the server-wide add-ons on (`k8s/cluster`: cert-manager, Let's Encrypt issuers, Traefik settings, the hairpin DNS rule, the DNS updater, the deploy login). **Shows a preview first** | yes, server-wide |
| `eactl apply-db` | Puts the shared Postgres on (`k8s/db`). Applied on its own, with its own preview, because if it goes wrong every school is affected | yes, every school |

## Schools

| Command | What it does | Changes anything? |
|---|---|---|
| `eactl new "Name"` | Makes a school: its namespace, its database and database login in the shared Postgres, its settings and secrets, and the app. Public over HTTPS straight away; nobody can do anything there until it's claimed with its setup code | yes |
| | `--version v0.8.2` a different release than the other schools · `--address x.y.com` a different address · `--canary` updated first on every deploy (the demo) | |
| `eactl list` | Every school: name, short name, status, release, address | no |
| `eactl status "Name"` | One school's health: each part, its release, its certificate | no |
| `eactl remove "Name"` | Deletes a school: app, settings, database and database login. **Takes a safety copy first**, and only goes ahead once you type its short name | **deletes** |

## Releases

| Command | What it does | Changes anything? |
|---|---|---|
| `eactl update "Name"` | Brings one school up to date with the template, at its current release | yes |
| `eactl update "Name" v0.8.1` | Moves one school to a release, forward or back. Before it changes release, its database changes are checked against that release; going back offers to undo them behind a safety copy, and **holds the school** | yes |
| `eactl update --all` | Every school. Schools marked `ea/canary=true` (the demo) go first; **if one fails, no other school is touched**. Held schools are skipped | yes |
| | `--version 0.8.2` same as typing the version · `--yes` no questions (what the automatic deploy uses) | |
| `eactl hold "Name"` | Keeps a school at its release. Automatic deploys and `update --all` skip it; updating it by name still works | label only |
| `eactl unhold "Name"` | Lets it follow releases again | label only |

## Logins

| Command | What it does | Changes anything? |
|---|---|---|
| `eactl setup-code "Name"` | Issues the one-time code that claims a new school's first administrator. Send it to the school's coach. Running it again replaces the old code, which is also how to cancel one | yes |
| `eactl make-admin "Name" USER` | Makes an existing login an administrator again, for a school whose only administrator is locked out. Never makes a login or sets a password. `--reactivate` if that login was switched off | yes |

## Demo data

Only ever adds. It recognizes its own rows and never touches real ones.

| Command | What it does | Changes anything? |
|---|---|---|
| `eactl seed "Name"` | Four invented athletes, each with a simulated sensor, a plan, a live session and a few finished sets. Refuses on a school with no coach yet, with another session running, or with a real athlete under a demo name. Asks for the short name. `--reset` removes its earlier demo rows first | adds rows |
| | `--guest-logins` (remote only) adds three guest seats for a live demo, Taylor Grant, Morgan Hayes and Sam Ortiz, each with a rack waiting in the room before anyone signs in. They and Jordan Lee get demo logins: first name / first name + `pass123` (`jordan` / `jordanpass123`). Someone who already has a login keeps it. A guest is never a phantom, so a seat nobody takes stays an empty rack | adds rows and logins |
| `eactl sim "Name"` | Wakes the demo athletes' sensors for 2 hours. Each sends reps while its athlete's set is running | adds rows |
| | `--phantom` the athletes also lift on their own, set after set (except the hands-on demo athlete) · `--hours N` · `--stop` ends it early | |

## Safety copies

| Command | What it does | Changes anything? |
|---|---|---|
| `eactl backup "Name"` | A safety copy of one school's database, now | no |
| `eactl restore "Name"` | Lists the school's safety copies (newest first, with why each was taken), asks which, and replaces the database with it. **Takes a fresh safety copy first**, so a restore can be undone too | **replaces the database** |

Safety copies are `pg_dump` files in `/var/lib/edgeathlete/snapshots/<short name>/`, root only. The last 5 per school are kept, none older than 30 days. `remove` and `restore` take one by themselves. **They're on the same Dell as the schools**, so they don't survive losing the machine. Nightly copies off the server aren't built yet.

## Looking inside a school

| Command | What it does | Changes anything? |
|---|---|---|
| `eactl get-session-link "Name"` | The link athletes use to join: the running session, plus any set up but not started | no |
| `eactl logs "Name" PART` | The last 100 lines a part printed. PART is `django`, `react`, `mosquitto`, `mqtt-listener`, `monitoring-publisher`, `setup` (Django's start-up step: migrations, rack recovery) or `sim`. `-f` keeps following | no |
| `eactl shell "Name"` | A command line inside the school's Django, for `manage.py` commands by hand. `exit` to leave | whatever you type |

## eactl itself

| Command | What it does |
|---|---|
| `eactl version` | eactl's release, the newest release, and each school's |
| `eactl self-update` | Brings eactl to the newest release now instead of waiting for the hourly timer. Asks for your password. Never touches a school; that's `eactl update` |
| `eactl help` | The command list |

## Where things live

| What | Where | Why there |
|---|---|---|
| The code and YAML eactl uses | `/srv/edge-athlete/Edge-Athlete-Remote` (root) | Belongs to the machine, not whoever's logged in. Replaced on update, never edited in place |
| The settings | `/etc/edgeathlete/eactl.env` | The machine's settings. They survive every code update |
| The server's read-only repo key | `/etc/edgeathlete/deploy-keys/` | Same place a local install keeps its own |
| The `eactl` shortcut | `/usr/local/bin/eactl` | Typeable from any folder |
| Your cluster login | `~/.kube/config` | It *is* your access, so it stays personal |
| Safety copies | `/var/lib/edgeathlete/snapshots/` | Root only |

The script itself is `scripts/remote/eactl.sh`. Each command's block opens with a comment saying what it does and why.
