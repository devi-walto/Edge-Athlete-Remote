# Local only

Decisions that only apply to the local install: a base station in the gym, serving its own Wi-Fi, with nothing reaching it from outside. Everything else it does is in {doc}`Core <../index>`.

**{doc}`base-station`**
: The machine itself: why it isn't a Raspberry Pi any more, its own Wi-Fi, the installer, the kiosk screens, and the everyday commands.

**{doc}`kiosk-screens`**
: How every screen runs as a locked browser on plain HTTP: why the local install isn't HTTPS, the trusted address, kiosk vs incognito, a browser profile per role, and three app manifests.

```{toctree}
:maxdepth: 1
:hidden:

base-station
kiosk-screens
```
