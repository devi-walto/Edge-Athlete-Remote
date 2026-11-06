# Docker

*Both installs*

**Why I picked it.** I wanted to learn containers for my DevOps career. And it turned out to be what makes pivoting easy: keep every service modular, and swapping the architecture is a change of orchestration, not a rewrite.

**What it is.** How the server side runs. Each service is a container; Compose
starts them together with one file.

**How we use it.** One stack on the base station, started at boot by systemd:

```
docker compose up -d   ──►  postgres · mosquitto · django · mqtt-listener
                            monitoring-publisher · react · nginx
```

Two services are profile-gated and only run when asked — `seed` (demo data) and
`simulator` (a fake sensor).

**Where it lives.** `docker-compose.yml` at the repo root. Rack screens run **no Docker at all**: they're browsers.

**Online, the same images run on {doc}`k3s`** instead of Compose. GitHub Actions builds them from the same Dockerfiles and stores them privately in GitHub's container registry (`ghcr.io/devi-walto/edge-athlete-django`, `…-react`); the Dell pulls them with a read-only token.

**Worth knowing.** ⚠️ `docker compose build` **skips profile-gated services**. The
simulator image sat months out of date behind a "successful" rebuild because of it.
`ea-seed` and `ea-sim` now build their own image first.

⚠️ A rebuilt image does not restart a running container. That is what `ea-reset` is
for; `ea-update` alone leaves the old container serving.

**More:** {doc}`../../handbook/guides/local-install`
