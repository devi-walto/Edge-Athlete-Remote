# Stack

Every tool this is built with, what it does here, and why I picked it. Each linked page is short: what it is, how we use it, where it lives, and the one thing worth knowing.

| Tool | Its job here | Why I picked it | Install |
|---|---|---|---|
| {doc}`django` | The API, logins and roles | The easiest way to get the server and login logic working. I'd used it on Privacy Dots, my freshman expo design winner, and this project is a descendant of it | both |
| {doc}`react` | One app (a PWA) on any phone, tablet or laptop | I learned it at my internship at the Cyber Innovation Center in Bossier, where they also taught me to use IndexedDB in a PWA to keep app state | both |
| {doc}`postgres` | The database: one per local install; one shared Postgres with a database per school online | The standard choice for Django | both |
| {doc}`mosquitto` | Carries every rep to the screens live (MQTT) | Built for small devices: tiny messages, delivery guarantees (QoS), WebSockets for the browser, and TLS | both |
| {doc}`docker` | Every part runs in its own container | I wanted to learn it for my DevOps career | both |
| {doc}`k3s` | Runs the containers on the remote server, one copy per school | Same reason as Docker: Kubernetes for my DevOps career | remote |
| {doc}`traefik` | The reverse proxy on the remote server, one entry point on 443 | It ships with k3s and routes by school address. Replaced nginx there | remote |
| {doc}`cert-manager` | Gets and renews HTTPS certificates from Let's Encrypt | Certificates that renew themselves, with nobody logging in every few months | remote |
| {doc}`nginx` | The reverse proxy on the local install | Sends `/api/` to Django and the rest to React on one box | local |
| {doc}`networkmanager` | The base station's own Wi-Fi | Devices join the base station, never the gym's network | local |
| {doc}`systemd` | Starts things at boot and restarts them when they die | The Linux service manager; nothing extra to install | local |
| {doc}`chromium` | The browser every screen runs, locked full screen as a kiosk | So I could download the web app as a clickable icon and "install" the project on a device | local |
| {doc}`hardware-agents` | The NFC wristband reader on a rack laptop (and the unused WT901 agent) | A browser can't talk to a USB card reader | local |
| {doc}`tailscale` | Private access to the Dell from anywhere | For my career, and it makes working away from home easy | remote |
| {doc}`github-actions` | Tests every pull request, builds every release | I learned it in CSC 450, Cloud Computing | both |
| {doc}`ESP32-C6 + BNO085 <esp32>` | The sensor: its Wi-Fi chip and its motion sensor | The ESP32 was hardware I had on hand; the BNO085 was the most accurate motion sensor I could find | both |

**Where it runs:** the remote server is a Dell OptiPlex at my house, not the cloud. The Pi 3 it replaced was hitting hard bottlenecks and library-support problems. I chose on-prem to keep cloud costs down and to learn to troubleshoot a bare Linux machine myself.

```{toctree}
:maxdepth: 1
:hidden:

django
react
postgres
mosquitto
docker
nginx
networkmanager
systemd
chromium
hardware-agents
k3s
traefik
cert-manager
tailscale
github-actions
esp32
```
