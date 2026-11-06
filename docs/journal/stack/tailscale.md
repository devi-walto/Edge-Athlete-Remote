# Tailscale

*Remote server*

**Why I picked it.** For my career, and it makes working away from home easy. I can reach the Dell from anywhere without opening anything else on my home router.

**What it is.** A private network between my own devices. The Dell and my laptop each join it and can reach each other directly, encrypted, wherever they are.

**How we use it.** Every admin job happens over it:

```
my laptop ──Tailscale──► the Dell ──► ssh, then eactl / kubectl
```

The schools themselves are public over HTTPS, through Traefik. Tailscale is only for me reaching the server.

**Where it lives.** On the Dell and my laptop, installed by hand when the machine is set up ({doc}`../../handbook/guides/remote-server`, step 1). Nothing in the repo configures it.

**Worth knowing.**

- **SSH is key-only.** My laptop's key is on the Dell and SSH passwords are off. Tailscale gets me to the machine; the key gets me in.
- **An early guard kept schools in testing reachable only over Tailscale.** It was dropped: every school is public, protected by its one-time setup code until it's claimed.
- **A visit from my laptop over Tailscale arrives with a `100.` address.** That's how I measured the "every visitor looks the same" bug: the test app saw the load balancer's address instead ({doc}`../core/remote/hosting`).

**More:** {doc}`k3s` · {doc}`../core/remote/hosting`
