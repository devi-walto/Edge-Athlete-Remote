# Nginx

*Local install (as the proxy) · both (inside the React image)*

**Why I picked it.** A small, standard reverse proxy that does exactly one job on one box.

**What it is.** The reverse proxy on the local install: one address for the whole app, so a browser never needs to know which service answers what.

**How we use it.** It splits on the path:

```
http://basestation/          ──► the built React files (static)
http://basestation/api/…     ──► django
```

Live data does **not** pass through it — browsers talk to Mosquitto directly on
9001. Nginx is out of the real-time path entirely.

**Where it lives.** Container `edgeathlete-nginx`, image `nginx:alpine`, the only
service publishing a port (**80**). Config in `nginx/`.

**Worth knowing.** It serves plain HTTP, and that's deliberate: an offline gym has no way to get a trusted certificate. The cost is that `http://basestation` is a **non-secure origin**, which switches off service workers and app install. `localhost` is exempt, which is why things work on the base station's own screen and not on a rack ({doc}`../core/local/kiosk-screens`).

It also limits sign-in tries (10 a minute) and tells browsers not to keep sign-in replies. **Online, {doc}`traefik` is the proxy instead, and Django does those two jobs itself.** nginx still runs online in one place: inside the React image, handing out the built pages as plain files.

**More:** {doc}`../core/local/base-station` · {doc}`traefik` · {doc}`chromium`
