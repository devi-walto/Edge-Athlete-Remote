# cert-manager

*Remote server*

**Why I picked it.** Certificates that renew themselves. Anything that needs a person to log in every few months to renew it will eventually lapse, and certificate lifetimes keep getting shorter.

**What it is.** It asks Let's Encrypt for each school's HTTPS certificate, proves the address is mine, stores the certificate where Traefik uses it, and renews it well before it expires.

**How we use it.**

```
new school's Ingress ──► cert-manager ──► Let's Encrypt asks for a file over port 80
                                     ◄── the file, served through Traefik
                         certificate stored ──► Traefik serves HTTPS on 443
```

Two issuers: `letsencrypt-staging` for testing (not trusted by browsers, but no rate limits) and `letsencrypt-prod` for real schools. Both use the HTTP-01 check through Traefik.

**Where it lives.** `k8s/cluster/cert-manager/` (pinned to v1.21.2, the version on the Dell) and `k8s/cluster/letsencrypt-issuers.yaml`. Applied by `eactl apply-cluster`.

**Worth knowing.**

- ⚠️ **That's why port 80 is forwarded**, even though the site itself redirects to HTTPS. If port 80 ever can't be opened, the same proof can be done through Porkbun's DNS API.
- ⚠️ **It needs the hairpin fix.** Before issuing, cert-manager checks the address itself, from inside the cluster. A request to my own public address goes out to the home router, which won't send it back in. `k8s/cluster/coredns-hairpin.yaml` makes the cluster answer my public names with Traefik, so the check never leaves the cluster.
- **Sensors trust Let's Encrypt's root, never the certificate itself**, or every sensor would go dark at the first renewal ({doc}`../core/remote/sensors`).

**More:** {doc}`../core/remote/hosting` · {doc}`traefik`
