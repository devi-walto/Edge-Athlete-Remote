# k3s

*Remote server*

**Why I picked it.** I wanted to learn Kubernetes for my DevOps career. k3s is a small Kubernetes that installs as one program and runs fine on a single machine, so it fits one PC at my house.

**What it is.** It runs the containers on the remote server, keeps them running, and restarts anything that dies. If Kubernetes is a football team: the cluster is the team, I'm the head coach, a YAML file is a play card, `kubectl apply` is handing it in, a pod is a skill player, a deployment is a position group, and each school is its own squad (a namespace).

**How we use it.** One node, the Dell. Every school is one copy of the same stack, stamped from one template:

```
namespace edge-athlete     the shared Postgres
namespace ea-<short name>  one school: django, workers, react, mosquitto, ingress
namespace kube-system      Traefik, CoreDNS (k3s's own)
namespace cert-manager     certificates
```

**Where it lives.** The YAML is in `k8s/`: `k8s/app/base/` (one school), `k8s/cluster/` (server-wide add-ons), `k8s/db/` (the shared Postgres). Nobody types `kubectl apply` for these by hand; `eactl` does it and prints each command first ({doc}`../../handbook/reference/eactl`).

**Worth knowing.**

- ⚠️ **Never forward 6443**, the cluster's control port. It's managed from inside the home network only.
- ⚠️ **Kernel updates can break every container.** On Nov 5, kernel 7.0.0-42 started applying the host's AppArmor rules inside containers. The kernel packages are held until that's fixed ({doc}`../../handbook/guides/remote-server`).
- The local install doesn't use k3s. One machine running one school is what Compose is the right size for.

**More:** {doc}`../core/remote/hosting` · {doc}`traefik` · {doc}`docker`
