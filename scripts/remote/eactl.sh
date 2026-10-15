#!/usr/bin/env bash
# eactl.sh — run the hosted Edge Athlete server. Runs ON the server: SSH in
# first, then type eactl.
#
#   eactl help             this list
#   eactl init             once per server: ask its settings, save eactl.env
#   eactl check            is this server's cluster answering?
#   eactl apply-cluster    put the server-wide add-ons (k8s/cluster) on the cluster
#
# Why it exists: the hosted service is many schools on one server. Every chore
# (make a school, list them, apply the add-ons) is a few kubectl commands that
# must be typed the same way every time; this types them, and prints each one
# first so you can see, and learn, exactly what it ran.
#
# Assumes the server already works: Linux, your user, SSH and Tailscale set up.
# Setting up the machine itself is not eactl's job.
#
#  *** Not the same family as scripts/basestation/ea.sh (the gym box's ea-*
# commands). Both run on the machine they manage, but ea-* manages a gym box
# with Docker; eactl manages a hosted server with Kubernetes. ***

set -uo pipefail

# Where the repo is, found from this file's own location (following the symlink
# in /usr/local/bin), so eactl works from any folder.
REPO_DIR="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"

# The server's settings: asked once by `eactl init`. Kept in /etc, apart from
# the code, so updating or moving the code never loses them.
# EACTL_CONFIG points at a different file (for a test).
CONFIG="${EACTL_CONFIG:-/etc/edgeathlete/eactl.env}"

# The command list is the one at the top of this file: every "#   eactl ..." line.
usage() {
    grep '^#   eactl ' "$0" | sed 's/^#   //'
}

load_config() {
    if [ ! -r "$CONFIG" ]; then
        echo "[!] cannot read $CONFIG. Run: eactl init"
        exit 1
    fi
    # shellcheck source=/dev/null
    . "$CONFIG"
}

# kubectl reads the cluster key from your home folder. k3s keeps the original
# where only root can read it, so this is your own copy (see `eactl init`).
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

# kube <args...> — run kubectl, printing the command first so you can see,
# and learn, exactly what ran.
kube() {
    echo "+ kubectl $*" >&2
    kubectl "$@"
}

# render <folder> — stack a k8s folder's files into one (kustomize), then fill
# in the placeholders from eactl.env.
#
# envsubst is given the exact list of names to fill. Without it, it would also
# blank out every other $WORD it found, such as the DNS updater's own $IP.
# An empty setting would be filled in as nothing (an issuer with no email), so
# each one is checked first.
#
# HAIRPIN_RULES is made here, not asked: one CoreDNS rewrite line per subdomain,
# so adding a subdomain in `eactl init` updates the hairpin too. Lines after the
# first start with four spaces, to sit inside the YAML block they land in.
PLACEHOLDERS='${DOMAIN} ${ACME_EMAIL} ${SUBDOMAINS} ${HAIRPIN_RULES}'
render() {
    local v sub rules=""
    for v in DOMAIN ACME_EMAIL SUBDOMAINS; do
        if [ -z "${!v:-}" ]; then
            echo "[!] $v is not set. Run: eactl init" >&2
            return 1
        fi
    done
    for sub in $SUBDOMAINS; do
        [ -n "$rules" ] && rules+=$'\n    '
        rules+="rewrite name exact $sub.$DOMAIN traefik.kube-system.svc.cluster.local answer auto"
    done
    kubectl kustomize "$REPO_DIR/$1" \
        | DOMAIN="$DOMAIN" ACME_EMAIL="$ACME_EMAIL" SUBDOMAINS="$SUBDOMAINS" \
          HAIRPIN_RULES="$rules" envsubst "$PLACEHOLDERS"
}

# preview <label> <yaml> — show what applying <yaml> would change on the
# cluster, as -/+ lines like git diff. kubectl diff's answer:
#   0 = nothing would change, 1 = changes (printed above), 2+ = it failed.
# Sets CHANGES=1 if anything would change.
preview() {
    local label="$1" yaml="$2" rc
    echo
    echo "==> preview: $label"
    kube diff -f - <<< "$yaml"
    rc=$?
    case "$rc" in
        0) echo "    (no changes)" ;;
        1) CHANGES=1 ;;
        *) echo "[!] could not preview $label (see the error above)"; return 1 ;;
    esac
}

# Stop early, with a plain message, if the cluster is not answering.
require_cluster() {
    if ! kubectl get --raw /readyz >/dev/null 2>&1; then
        echo "[!] the cluster is not answering."
        echo "    Is k3s running? Try: sudo systemctl status k3s"
        exit 1
    fi
}

# ask VAR "question" "example" — asks. If there is a saved answer it shows in
# [brackets] and Enter keeps it; otherwise the example is shown and an answer
# is required.
ask() {
    local var="$1" question="$2" example="$3" current answer
    current="${!var:-}"
    while true; do
        if [ -n "$current" ]; then
            read -r -p "$question [saved: $current]: " answer
        else
            read -r -p "$question (e.g. $example): " answer
        fi
        answer="${answer:-$current}"
        [ -n "$answer" ] && break
        echo "    an answer is needed"
    done
    printf -v "$var" '%s' "$answer"
}

CMD="${1:-help}"
shift || true

case "$CMD" in

init)
    # Load the saved answers, if any, so they show up as the defaults.
    # shellcheck source=/dev/null
    [ -r "$CONFIG" ] && . "$CONFIG"

    echo "==> this server's settings (saved to $CONFIG)"
    if [ -r "$CONFIG" ]; then
        echo "    Your saved answers are shown in [brackets]."
        echo "    Press Enter to keep one, or type a new answer to replace it."
    fi
    ask DOMAIN     "Type your domain"                            "example.com"
    ask ACME_EMAIL "Type an email for certificate warnings"      "you@example.com"
    ask SUBDOMAINS "Type your subdomains, separated by spaces"   "test demo"

    # Write the answers to a scratch file first, then put it in place with sudo
    # (only root can write in /etc). %q wraps each answer in quotes so it reads
    # back exactly as typed.
    TMP="$(mktemp)"
    {
        echo "# eactl.env — this server's settings. Made by 'eactl init'. NEVER commit."
        printf 'DOMAIN=%q\n'     "$DOMAIN"
        printf 'ACME_EMAIL=%q\n' "$ACME_EMAIL"
        printf 'SUBDOMAINS=%q\n' "$SUBDOMAINS"
    } > "$TMP"
    # Owned by root, readable by your group, by nobody else (640).
    sudo mkdir -p "$(dirname "$CONFIG")" \
        && sudo install -m 640 -o root -g "$(id -gn)" "$TMP" "$CONFIG" \
        || { rm -f "$TMP"; echo "[!] could not save $CONFIG"; exit 1; }
    rm -f "$TMP"
    echo "==> saved"

    # Tools eactl needs. Ubuntu normally has both; k3s brings kubectl.
    echo "==> checking this server"
    for tool in kubectl envsubst; do
        if ! command -v "$tool" >/dev/null; then
            echo "[!] $tool is missing."
            [ "$tool" = envsubst ] && echo "    Install it: sudo apt install gettext-base"
            exit 1
        fi
    done

    # Your own copy of the cluster key. If missing, make it (needs sudo once).
    if [ ! -r "$KUBECONFIG" ]; then
        echo "==> making your copy of the cluster key at $KUBECONFIG"
        mkdir -p "$(dirname "$KUBECONFIG")" \
            && sudo cp /etc/rancher/k3s/k3s.yaml "$KUBECONFIG" \
            && sudo chown "$USER": "$KUBECONFIG" \
            && chmod 600 "$KUBECONFIG" \
            || { echo "[!] could not make $KUBECONFIG. Is k3s installed?"; exit 1; }
    fi
    require_cluster
    echo "==> the cluster is answering"

    # Make `eactl` typeable from any folder, the same way the gym box's ea-*
    # commands are: a shortcut in /usr/local/bin pointing at this file.
    LINK=/usr/local/bin/eactl
    if [ "$(readlink "$LINK" 2>/dev/null)" != "$REPO_DIR/scripts/remote/eactl.sh" ]; then
        sudo ln -sfn "$REPO_DIR/scripts/remote/eactl.sh" "$LINK" \
            || { echo "[!] could not link $LINK"; exit 1; }
        echo "==> linked $LINK"
    fi

    # Every problem above stops with [!], so reaching here means it all worked.
    echo
    echo "✓ eactl init finished: this server is ready."
    echo
    echo "Commands:"
    usage | sed 's/^/  /'
    ;;

apply-cluster)
    # The server-wide add-ons in k8s/cluster. (Pieces still to come: checks,
    # the preview, and applying.)
    load_config
    require_cluster

    # The DNS updater's API keys are made by hand (README checklist), so they
    # may not exist yet. A warning, not a stop: everything else still works, and
    # the updater simply waits until they do.
    if ! kubectl -n ddns get secret porkbun-api >/dev/null 2>&1; then
        echo "[!] warning: no Secret porkbun-api in namespace ddns yet."
        echo "    The DNS updater will not run until it exists. Steps:"
        echo "    scripts/remote/README.md, \"Before you start\", item 5."
        echo
    fi

    echo "==> filling in k8s/cluster with this server's settings"
    cert_manager="$(kubectl kustomize "$REPO_DIR/k8s/cluster/cert-manager")" \
        || { echo "[!] could not build k8s/cluster/cert-manager"; exit 1; }
    addons="$(render k8s/cluster)" || exit 1

    # Show every change before making any. On a brand-new server the issuers
    # cannot be previewed: they are a kind cert-manager defines, and it is not
    # installed yet. Then they are simply all new.
    CHANGES=0
    preview "cert-manager" "$cert_manager" || exit 1
    if kubectl get crd clusterissuers.cert-manager.io >/dev/null 2>&1; then
        preview "add-ons (issuers, hairpin, DNS updater)" "$addons" || exit 1
    else
        echo
        echo "==> preview: add-ons. cert-manager is not installed yet, so these are all"
        echo "    new: 2 certificate issuers, the hairpin rules, the DNS updater."
        CHANGES=1
    fi

    echo
    if [ "$CHANGES" = 0 ]; then
        echo "✓ the cluster already matches k8s/cluster. Nothing to do."
        exit 0
    fi
    read -r -p "Apply these changes? (y/N) " answer
    if [ "$answer" != y ]; then
        echo "nothing applied"
        exit 0
    fi

    # cert-manager first, then wait until it is ready: its webhook checks every
    # issuer as it is created, and refuses them all while it is still starting.
    echo
    echo "==> applying cert-manager"
    kube apply -f - <<< "$cert_manager" >/dev/null || { echo "[!] cert-manager did not apply"; exit 1; }
    echo "==> waiting for cert-manager to be ready (up to 3 minutes)"
    kube -n cert-manager wait --for=condition=Available deployment --all --timeout=180s \
        || { echo "[!] cert-manager is not ready. Look: kubectl -n cert-manager get pods"; exit 1; }

    echo "==> applying the add-ons"
    kube apply -f - <<< "$addons" || { echo "[!] the add-ons did not apply"; exit 1; }

    echo
    echo "✓ k8s/cluster is on the cluster."
    ;;

check)
    load_config
    require_cluster
    echo "==> the cluster is answering"
    kube get nodes
    ;;

help|-h|--help)
    usage
    ;;

*)
    echo "unknown command '$CMD'"; echo
    usage
    exit 1
    ;;

esac
