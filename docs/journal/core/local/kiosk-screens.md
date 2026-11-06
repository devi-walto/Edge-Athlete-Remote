<!--
this page — how the local install's screens run as locked browsers on a closed
network, and the five decisions that came from the local install being served
over plain HTTP.

Moved here from the Rack screen page: none of this applies to the remote server,
which is HTTPS. Two of these bugs were live for months without anyone noticing,
because they looked exactly like normal operation. Read the tip at the bottom.
-->

# Kiosk screens

On a local install, every screen (rack, coach, wall) is a browser running full-screen on a tablet or PC, talking to the base station over plain HTTP. This page is the decisions that came from that.

## Tool changes at a glance

| Job | First | Now | Where it lives |
|---|---|---|---|
| A missing browser feature (`crypto.randomUUID`) | crashed the rack screen | **a small local replacement** | `react/src/polyfills.js` |
| Secure-context features (offline cache, tag scanning) | silently off | **the kiosk browser marks the base station's address as trusted** | `scripts/rack-screen/kiosk.sh` |
| Kiosk browser mode | private (incognito) | **a normal on-disk profile** | `kiosk.sh` |
| Browser profiles | one for everything | **one per role** | `kiosk.sh` |
| Installable app versions | three that were secretly one | **three manifests with their own identity** | `react/public/manifest.*.json` |
| Coach tablet | the same locked kiosk | **starts full-screen, isn't locked**, with a tappable icon | `rack-kiosk-setup.sh` |

## The problem

The base station serves plain HTTP, which browsers treat as a **non-secure context**. A handful of browser features are switched off there. And a rack screen runs unattended: it boots into a locked browser nobody's watching, so when something quietly breaks, nobody sees it.

## Try 1: replace the one missing function

The browser's built-in unique-ID generator doesn't exist in a non-secure context. It crashed the rack screen on first load in the gym while working perfectly on a laptop, because `localhost` counts as secure and `http://basestation` doesn't.

**What worked:** a small local replacement for that one function.

**Why I moved on:** it fixed the symptom and left the cause. The address itself is untrusted, so *everything* that needs a secure context stayed off. The offline cache had never once worked on a rack screen, and never said so: the code checked whether the browser *supported* the feature, which it does, then threw away the error when the browser refused to use it. It looked healthy and did nothing.

## Try 2: switch the local install to HTTPS

**Why I passed on it:** a secure page refuses the plain `ws://` connection the live rep feed depends on, so HTTPS would trade a crash for a dead sensor feed ({doc}`../real-time`). A self-signed certificate warns on every phone that joins the gym's network, and a real certificate needs a public domain the base station doesn't have. (The remote server is HTTPS, with TLS in front of the broker at Traefik. That doesn't help a closed gym network.)

## Where I landed: tell the browser to trust the address

The kiosk browser is launched with the base station's address explicitly marked as trusted. It's a *local* declaration, one screen's statement about one address on a closed network, not a certificate anyone else honours. It turned on the offline cache and tag scanning in one move.

The failed offline-cache registration now **logs a warning that names the cause** (`main.jsx`). A screen with no offline cache that says so is a known state; one that pretends otherwise is a debugging trap.

**What it cost:** it only applies to the browser launched with it. A coach opening the site on their own phone is still in a non-secure context with no offline cache. The gym's screens are covered; visiting devices aren't.

## A kiosk is the opposite of incognito

The kiosk launcher ran the browser in private mode. It sounds like a sensible default for an unattended screen, and it was quietly destroying the two things the rack screen is built on:

- **The screen's identity** (the ID that tells the server which screen this is, and its rack number) lives in browser storage, and private mode throws it away when the browser closes. The launcher relaunches the browser after any crash, so a screen came back **as a device the server had never seen**, without its rack.
- **The rep buffer**, the whole reason a Wi-Fi drop mid-set loses nothing ({doc}`../rack-screen`), is held in memory in private mode instead of on disk.

**Where I landed:** private mode removed, with the reason written into the script so nobody puts it back. It cost nothing to run. The uncomfortable part is that it was in place for months and nothing failed loudly enough to catch it, because a screen that reinvents itself looks exactly like a new screen.

## One browser profile per role

Browser storage is scoped to *(profile, site)*, and everything the app uses to know what it is (device ID, role, rack number) lives there. So two roles in one profile aren't two devices sharing a machine; they're one device overwriting its own identity. That blocked running the rack screen, the coach tablet and the wall display on one machine for a demo.

**Where I landed:** each role gets its own profile directory, named for the role and the user running it. One machine can show up as several independent devices, each registering separately.

**What it cost:** three copies of the browser's cache and state, and "clear the browser data" no longer means anything specific; you have to say which role. Worth it: the alternative was three tablets.

## Three manifests, three identities

The app ships three installable versions (rack, coach, wall), each with its own name and icon, and the page swaps between them by role. Installing more than one never worked.

A browser identifies an installed web app by an identity string, and falls back to its start address when none is given. All three had the same start address and no identity, so **all three were the same app**. Installing the coach version after the rack version didn't add a second icon; it renamed the first one.

**Where I landed:** each version declares its own identity. Coach and wall also got their own start addresses, so an installed app lands on the right screen. The rack version kept the shared start address, since a rack's number isn't known at install time.

**The bug it uncovered:** the code that points the page at the right version only ran when a device *changed* role. None of that happens on a reboot, so a wall display that restarted still advertised itself as the rack app. It now updates on every navigation (`App.jsx`, with `roleFromPath()` in `device.js`).

**What to know before changing a manifest:** changing an installed app's identity or start address **orphans existing installs**; the browser treats it as a different app. It was free this time only because the offline cache had never worked, so nothing was installed anywhere yet. It won't be free next time.

## The coach tablet is not a kiosk

The coach tablet needs the offline copy for the same reasons, and it needs the app properly *installed*, which a browser refuses outside a trusted context. So it gets the same launcher.

But a coach isn't an unattended screen. A locked kiosk hides the browser menu, and the menu is where "install this app" lives, so the thing delivering the fix would block what it was for. A coach also navigates, signs in, and puts the tablet down.

**"Full-screen" was two ideas.** One is a *lock*: no toolbar, no window buttons, no way out, no menu. Right for a rack screen an athlete mustn't leave. The other just *starts* full-screen as an ordinary window: hover the top edge and the toolbar comes back. Once those were separated, the coach didn't have to give up full-screen to stay installable.

**Where I landed:** the same launcher with the *lock* removed, not the full-screen. Trusted address and on-disk profile kept; the cage and the relaunch loop dropped. A coach tablet gets a **tappable icon** instead of something that grabs the screen at every login. It's a one-time door: once the coach installs the app from the browser menu, the browser writes its own launcher.

**What I didn't build:** offline *writing*. The offline cache keeps the app loading without a network; it doesn't make a coach's edits survive being made while disconnected. That needs a queue and a conflict story, and pretending a cache solves it would look like it worked right up until it lost something.

## Where these live in the code

| File | What changed |
|---|---|
| `scripts/rack-screen/kiosk.sh` | Takes a **role** instead of a URL; private mode removed; a profile per role; marks the address trusted; three launch modes, only one of them locked |
| `scripts/rack-screen/rack-kiosk-setup.sh` | Autostart is system-wide; no hard-coded user; creates the shared profile directory; a coach gets a tappable icon instead of an autostart |
| `react/public/manifest.*.json` | Each declares its own identity; coach and wall get their own start addresses |
| `react/src/device.js` | `roleFromPath()` works out a screen's role from the address |
| `react/src/App.jsx` | Applies the role's identity on **every** navigation |
| `react/src/main.jsx` | A failed offline-cache registration logs why instead of vanishing |
| `react/src/polyfills.js` | The replacement for the missing unique-ID function |

:::{admonition} If you only remember one thing
:class: tip
Two of these bugs, the thrown-away identity and the silently failed offline cache, were live for months without anyone noticing, because **both looked exactly like normal operation.** A screen that reinvents itself looks like a new screen. A cache that never installed looks like a cache that's working. When a feature has no visible failure state, that's the feature to go and check by hand.
:::
