<!--
this page — how a blank machine becomes a working base station in a gym, and
how it stays one.

Nearly every decision here is the same one restated: nothing may depend on who
is logged in, and nothing the machine owns may live in the repository. When you
add something to a base station, that's the question to ask of it. Several of
these failures produced no error at all, so the "what broke" parts matter.
-->

# Base station

How a blank machine becomes a working base station, and how it stays one. A base station runs the whole local install (database, web server, broker, screens) and **broadcasts the gym's own Wi-Fi**. Rack screens join that Wi-Fi and run no server.

:::{admonition} Who built this
:class: note
**All of it**: **Devin**. Base station provisioning, the rack-screen kiosk, and the short commands on both.
:::

## Tool changes at a glance

| Job | First | Now | Where it lives |
|---|---|---|---|
| The machine | Raspberry Pi 3 | **Dell OptiPlex mini PC** | — |
| Installing | `curl … \| sudo bash` from a public repo | **copy `bootstrap.sh` over and run it; each machine gets its own read-only deploy key** | `scripts/basestation/bootstrap.sh` |
| This machine's settings | written into a tracked script | **`/etc/edgeathlete/basestation.conf`**, outside the repo | `setup.sh` |
| The short commands | shell functions loaded at login | **programs on the system path**, linked from the repo | `scripts/basestation/ea.sh` |
| Django's web server | `runserver` | **gunicorn** | the Django image |
| Network managers | systemd-networkd and NetworkManager | **NetworkManager only**; networkd's wait service disabled | `setup.sh` |
| Changing the Wi-Fi from the app | — | **the app drops a request file; a host agent applies it as root** | `scripts/basestation/apply-wifi.sh` |
| The browser | a container, considered | **installed on the machine** | `setup.sh` |
| Looking at the wall display | an admin account logging in by itself, considered | **a locked kiosk account that only shows a web page** | `basestation-kiosk.sh` |

## The problem

A base station sits in a weight room, often with nobody technical nearby. It has to install from nothing, boot straight into a working gym, survive its own updates, and be fixable by whoever's standing in front of it. And every failure that doesn't announce itself becomes a habit people build around.

## The machine

**Try 1: a Raspberry Pi.** The system was designed around one. **Why I moved on:** its Wi-Fi was the weak link, and the whole stack (database, web server, broker, screens) was more than it wanted to carry: hard bottlenecks and library-support problems.

**Where I landed: a Dell OptiPlex mini PC.** Everything else ported unchanged, because broadcasting a Wi-Fi network is the operating system's job on any Linux box, not something Pi-specific. Pi-era docs still say "Pi" in places; it means base station.

## Installing and updating

**Try 1: `curl … | sudo bash`.** One line, from the public repo. **Why I moved on:** the repo went private, and GitHub answers an anonymous download from a private repo with a 404. The one-liner handed `sudo bash` an empty script, which does nothing and says nothing. An HTTPS clone was worse: it asked a headless box in a gym for a GitHub username.

**Where I landed: two commands, and each machine carries its own read-only key.**

```bash
scp scripts/basestation/bootstrap.sh edgeathlete@basestation:/tmp/
ssh -t edgeathlete@basestation 'sudo bash /tmp/bootstrap.sh'
```

The first run makes the machine its own SSH key and waits while you add it on GitHub as a read-only deploy key. Running it again is how you update; it isn't one-shot.

- **A key per machine, not one shared token.** Losing a base station should cost one key, not the fleet. A shared token sits on every device, and revoking it cuts them all off on the day you least want to re-provision a gym.
- **The key is named after the repo**, not `deploy_key`. GitHub allows a deploy key on exactly one repo, so a machine that later needs a second repo gets a second key instead of an error nobody would connect to that rule.
- **GitHub's host keys are pinned.** The first connection is the one moment a fake `github.com` could hand a base station its own code, and "just press yes" is the normal answer to that prompt.
- **"Your key isn't added yet" and "this machine has no internet" get different messages.** The first time someone pastes a key into GitHub to fix a dead ethernet cable is the last time they trust the installer.
- **A rack screen installs the same way** (`scripts/rack-screen/rack-bootstrap.sh`), key and all, so it's learned once. It takes **no role argument** on purpose: it's the path you run on a dozen identical devices, and an argument there is how a wall display ends up bolted to a squat rack.

**The install doesn't live in anyone's home folder.** The first scripts hard-coded a path under one user's home. Rename that account, or log in as someone else, and the boot service pointed at nothing: a base station that silently fails to start. Now the install lives at `/srv/edge-athlete/Edge-Athlete`, and the scripts work out where the project is from their own position on disk.

**This machine's settings aren't in git.** The first setup script edited the *startup script itself* to write in the Wi-Fi interface name. That permanently modified the repo, so the next update hit a merge conflict on a machine with nobody around, and it put **the gym's Wi-Fi password in version control.** Now network name, password and interface live in `/etc/edgeathlete/basestation.conf`, written once and never overwritten. Updates pull cleanly forever because nothing edits a tracked file.

**Set it if it's missing, never correct it if it's present.** The installer runs again on every update, so anything it writes every time silently undoes a deliberate change. Somebody who pointed the machine at the coach screen for a week would find it back on the wall display after the next update. Settings like that are written only if absent.

## The everyday commands

`ea-update`, `ea-seed`, `ea-sim`, `ea-reset`, `ea-kiosk-exit`, `ea-help`. Each wraps a long command that's easy to get subtly wrong; typing them by hand is how a demo ends up running old code.

**Try 1: shell functions, loaded at login.** **Why I moved on:** they only existed in *login* shells. A terminal opened on the desktop, a one-shot command over ssh, anything under `sudo`: none are logins, and in all of them the commands didn't exist. "`ea-update: command not found`" reads as *the update is broken* when only its delivery was. **A command you have to load into your shell before every use isn't a command.**

**Where I landed:** ordinary programs on the system path, one file linked under each name, defined **inside the repo**. Because it's a link and not a copy, updating the base station updates the commands too. A copied helper rots: it keeps wrapping the old behaviour of a script that's since changed.

**The same verb on two devices, from two separate files.** A rack screen's `ea-update` and the base station's mean the same thing (update this device), but the base station rebuilds a server and an access point. Running its version on a rack tablet would install a server it doesn't need **and stand up a second access point competing with the real one.** So each device type has its own `ea.sh`, naming its machine in the first three lines. One shared file with a "which device am I?" check was passed on: the wrong branch of that check is a silent disaster.

**The build has to name the optional pieces.** The demo-data loader and the fake sensor are optional Compose services, so they never start on their own. The **build** skipped them for the same reason, so an update that reported success left them on whatever was last built by hand. Found when a change to the fake sensor didn't appear: the file inside that image was ten days old. Every build now names them, and `ea-seed` and `ea-sim` build before they run. *A tool that excludes things by default will exclude them from operations you didn't have in mind.*

## Booting

**A failed access point must not stop the app.** The startup script first aborted on any error, so if the Wi-Fi didn't come up, nothing did: a base station with no gym Wi-Fi *and* no app, unreachable even over a network cable. Now the access point is attempted, failure is logged loudly, and the app still comes up on the wired network. A reachable broken machine is fixable; an unreachable one needs a monitor and a keyboard carried to it.

**Two minutes of every boot were spent waiting for nothing.** Every boot stalled on `systemd-networkd-wait-online.service (56s / no limit)`. Linux here has *two* network managers, and the setup gives every device to NetworkManager, the only way the Wi-Fi adapter shows up for the tool that builds the access point. So networkd's "wait until the network is up" service waited for an interface it would never be given, until it timed out. The proof was two lines apart in the boot log: NetworkManager's own wait service had already finished. **Fix:** keep NetworkManager's enabled, disable the orphan. This is only safe *because* NetworkManager owns the devices; undo that and it silently removes a real safety check, which the script says at both ends.

**The radio isn't allowed to nap.** Wi-Fi power saving adds delay to exactly the traffic that can't absorb it: a live rep on its way to a screen. The standard one-liner returns "Operation not supported," because power saving is for devices *joining* a network and this one *is* the network. It's set in NetworkManager's config instead, plus a driver option for Intel adapters, and survives reboots.

**A real web server.** Django's built-in server is a development tool, single-threaded and not for production. The stack runs **gunicorn** with a small, fixed number of workers. *If pages stall under a handful of tablets while the network looks healthy, the worker count is the first thing to check.*

**A signing key per machine.** The key that signs logins can't be a shared default in the repo, or a token from one gym works at another. Each machine makes its own at setup, stored outside the repo, and the app **refuses to start** without one when debug is off. A base station that won't boot gets fixed today; one that boots with a known-insecure key gets used for a season.

## Changing the Wi-Fi from the app

Coaches need to change the gym's Wi-Fi password from the app. But the app runs in a container, and it's the most exposed service on the box.

**Where I landed: a work order.** The app writes the requested change to a **file** in a shared folder, and that's all it can do. A privileged agent on the host (`apply-wifi.sh`) notices the file and makes the change as root, outside the container. The container never gets network privileges.

*The analogy that made it click:* the front-desk clerk can't rewire the building. They fill out a work order and drop it in a tray, and a maintenance worker who already has the keys does the job.

**What it cost:** the app confirms the request, not the result. Just before the access point restarts, the server warns the rack screens and the room display and shows them the new password (`edgeathlete/system/wifi`, {doc}`../../../handbook/reference/mqtt-topics`).

**The thing everybody hits once:** changing the Wi-Fi password **disconnects every device in the gym**, immediately. A web app can't change a device's Wi-Fi settings, so each one has to rejoin by hand. Do it between sessions, never during one.

## The base station's own screen

**The browser is installed on the machine, not in a container.** Everything else is containerised, so a containerised browser looked consistent. But a container suits a *service*, something on a port with no opinion about the machine. A kiosk browser exists to draw on **this machine's screen** and read **this machine's keyboard**; containerising it means giving that container more access to the host than the rest of the stack combined. Setup doesn't fail if the browser can't install: a headless base station doesn't need one.

**It can be its own screen, and boots into the wall display.** It already has a video output, and demoing meant carrying three tablets. Now it runs any screen itself, each as its own identity ({doc}`kiosk-screens`), with a clickable launcher for every role. Opening a rack screen for a minute to ask "is this broken, or is that tablet?" is a double-click, not a walk to a rack.

- **At `localhost`, everything works.** Browsers treat `localhost` as trusted, so the offline cache and installing the app work here with no flags. **The trap:** only the literal name `localhost`. The machine's own hostname resolves to the same address and still doesn't count, because the browser judges the name you typed. And a bug that reproduces on a rack but not here may be exactly that difference.

**"Full-screen" was three questions.** The launcher had one full-screen setting answering three things at once: does it fill the screen, can you get out, does it reopen if closed. On a rack screen you want all three locked, so nobody noticed they were separate. On the base station, opening a second screen made two locked windows each grabbing focus and reopening when it lost: the display cycled between roles several times a second, with no error logged, because nothing had failed. And the wall display couldn't be closed to reach the desktop; it was back three seconds later.

**Where I landed: three named modes** (`scripts/rack-screen/kiosk.sh`):

| Mode | Window | On close | For |
|---|---|---|---|
| `kiosk` | full-screen, **no way out** | reopens itself | a rack screen in a gym |
| `once` | full-screen, an ordinary window | stays closed | anything a person sits at |
| `windowed` | a normal window | stays closed | when you want the toolbar |

Reopening is for screens **nobody's standing at**. Anywhere a person is at the keyboard, closing has to mean closing. *Two behaviours that always travel together in the case you built for aren't necessarily one behaviour.*

**The rack screens say `kiosk` out loud.** They were locked only because `kiosk` was the launcher's *default*. The two things the gym depends on (an athlete can't leave the screen, a dead screen revives itself) rested on a default any later change would flip across every rack. A default is a convenience, not a place to keep a decision.

**A locked screen still needs a way out for whoever maintains it.** The relaunch loop watches for a flag file. `ea-kiosk-exit`, or **Ctrl+Alt+K**, sets the flag and then closes the browser, in that order; the other order races the relaunch loop and looks intermittent. The shortcut matters because you can't open a terminal from inside a locked window, and the desktop handles it, not the browser. The flag clears at the next start. There's deliberately **no exit button in the app**: an athlete must not find one by accident.

**Kiosk state belongs to the machine, not a user.** The kiosk scripts first wrote the browser's data and the autostart entry into one user's home folder, so logging in as anyone else started nothing. Both moved to machine-owned places. *The same lesson as the install path, made twice: writing a lesson down doesn't spread it to the next script.*

**The screen unlocks itself; the machine doesn't.** Plug in a monitor and you want the wall display, not a login prompt. But the same machine is the server.

- **Passed on: auto-login for a normal admin account.** One setting, same screen, and it leaves a logged-in session that can administer the server in a public room.
- **Where I landed:** a dedicated account that only looks at a web page. It logs in automatically, has no admin rights, and its password is **locked**: stronger than blank, since it can't be authenticated against at all. Physical access gets you a wall display and nothing else.
- **The trap I didn't see coming:** when the desktop dimmed and locked itself, the prompt asked for **that locked password**, which nothing satisfies. The wall display became a password box with no way in except a text console or ssh. Fixed twice: the launcher switches the screen lock off from inside the session, and the account joins the group Linux ships for exactly this, which lets it past the lock prompt. That grants nothing new, since auto-login already means physical access opens this session. *Two settings that are each right can combine into a state with no exit.*
- **An off switch has to switch something off.** The first "don't set up the kiosk login" setting just *skipped* the step, which did nothing on the machines that already had it. Now it removes exactly the lines it added, so later edits survive. The account itself stays: it holds the wall display's browser data.

## A diagnostic worth knowing about

`scripts/netmon.sh` opens three live views on one screen: bandwidth per device, each device's radio health, and how busy the Wi-Fi channel is. Bandwidth alone can't tell **"the app is slow"** from **"the radio can't push the bits,"** and those have completely different fixes.

## Things I passed on

- **The Raspberry Pi.**
- **`curl | sudo bash`**, and one shared token for every device.
- **Settings in the repo**, and an install in someone's home folder.
- **Shell functions** for the everyday commands, and one `ea.sh` for both devices.
- **A containerised browser**, and auto-login for an admin account.

## What it cost

- **A base station can be "up" while useless to tablets** (app running, access point failed). Better than unreachable.
- **A Wi-Fi change is confirmed, not completed,** and disconnects every device.
- **A rack screen clones the whole repo** to get a few scripts, in exchange for one update mechanism.
- **The base station boots to a desktop** to be its own screen, which is heavier than a server needs. It's optional.

## Where these live in the code

| File | What it does |
|---|---|
| `scripts/basestation/bootstrap.sh` | Install **or** update; enrols the machine's deploy key |
| `scripts/basestation/setup.sh` | Docker, the browser, the Wi-Fi config, the boot service, the short commands |
| `scripts/basestation/startup.sh` | Every boot: access point first, then the stack |
| `scripts/basestation/apply-wifi.sh` | The privileged Wi-Fi agent on the host |
| `scripts/basestation/ea.sh` | `ea-update`, `ea-seed`, `ea-sim`, `ea-reset`, `ea-kiosk-exit`… linked onto the system path |
| `scripts/basestation/basestation-kiosk.sh` | Runs a screen on the base station itself, at `localhost` |
| `scripts/basestation/update-via-hotspot.sh` | Updates a box with no wired internet by borrowing a phone's |
| `scripts/rack-screen/rack-bootstrap.sh` | Install **or** update a rack screen |
| `scripts/rack-screen/rack-kiosk-setup.sh` | Provisions a screen; run it directly only for a coach tablet |
| `scripts/rack-screen/ea.sh` | The screen's own short commands. A separate file on purpose |
| `scripts/rack-screen/kiosk.sh` | Launches a screen with a role and a mode: `kiosk`, `once` or `windowed` |
| `scripts/netmon.sh` | The three-pane radio diagnostic |

:::{admonition} The pattern underneath most of these
:class: tip
Nearly every decision here is the same one restated: **nothing may depend on who's logged in, and nothing the machine owns may live in the repo.** The install path, the settings file, the browser profiles, the autostart entry: each was a separate outage waiting to happen, with the same shape.
:::
