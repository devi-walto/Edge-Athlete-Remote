# Chromium

*Local install*

**Why I picked it.** So I could download the web app onto a device as a clickable icon and "install" the project like an app. Chromium installs a PWA that way. It also means there's no native app to build: every screen is the same web app.

**What it is.** The browser every screen runs. There is no native app — a rack
screen is a locked browser in full screen.

**How we use it.** Three modes, because "full screen" and "cannot be closed" are
different questions:

| Mode | Behaviour | Used for |
|---|---|---|
| `kiosk` | locked, reopens itself | a gym rack screen, unattended |
| `once` | full screen, stays closed | the base station's own monitor |
| `windowed` | a normal maximised window | when you want the toolbar |

Each role gets its **own browser profile**, so the rack, coach and wall apps do not
overwrite each other's identity.

**Where it lives.** `scripts/rack-screen/kiosk.sh`, launched at login. Profiles in
`/var/lib/edge-athlete/kiosk/`.

**Worth knowing.** ⚠️ Never add `--incognito`. It wipes the device id every launch
and makes the rep buffer memory-only — which is the one thing protecting a set from
a Wi-Fi drop.

**More:** {doc}`../core/local/kiosk-screens` for why · {doc}`../../handbook/guides/rack-screen`
