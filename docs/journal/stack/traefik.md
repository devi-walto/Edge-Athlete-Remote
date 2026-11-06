# Traefik

*Remote server*

**Why I picked it.** It ships with k3s, and it already routes by address inside the cluster. Running nginx alongside it would have meant two reverse proxies to keep in step.

**What it is.** The reverse proxy on the remote server: the one entry point on ports 80 and 443. It looks at each request's address and path and sends it to the right school and the right part of that school.

**How we use it.**

```
https://<school>/api/…      ──► that school's django
https://<school>/mqtt       ──► that school's mosquitto, screens listener (listen only)
https://<school>/sensors    ──► that school's mosquitto, sensors listener (a token each)
https://<school>/           ──► that school's react
```

Each school's routing is one Ingress file (`k8s/app/base/ingress.yaml`), the same job `nginx/nginx.conf` does on a local install. TLS is handled here, with each school's certificate from {doc}`cert-manager`.

**Where it lives.** k3s installs it from a Helm chart in `kube-system`. Our changes to that chart are `k8s/cluster/traefik-keep-visitor-address.yaml`: Traefik holds the Dell's ports 80 and 443 itself, instead of k3s's built-in load balancer (ServiceLB), which hid every visitor's real address.

**Worth knowing.**

- ⚠️ **Read the installed chart version's `values.yaml` before changing a setting.** A misspelled setting is silently ignored. One wrong name took the practice site down for about four minutes.
- **Only one Traefik per machine**, because it holds the ports itself. An update stops the old one before starting the new one: a few seconds offline.
- **Two jobs nginx did aren't done here:** the wrong-password limit and "don't cache sign-in replies." Online, Django does both.

**More:** {doc}`../core/remote/hosting` · {doc}`nginx`
