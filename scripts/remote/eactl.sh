#!/usr/bin/env bash
# eactl.sh — run the remote Edge Athlete server. Runs ON the server: SSH in
# first, then type eactl.
#
#   eactl help             this list
#   eactl init             once per server: ask its settings, save eactl.env
#   eactl check            is this server's cluster answering?
#   eactl apply-cluster    put the server-wide add-ons (k8s/cluster) on the cluster
#   eactl apply-db         put the shared database (k8s/db) on the cluster
#   eactl new "Name"       make a new school (starts private)
#   eactl list             every school: name, short name, access, release, address
#   eactl apply-school S   rebuild school S exactly as the template says
#
# Why it exists: the remote service is many schools on one server. Every chore
# (make a school, list them, apply the add-ons) is a few kubectl commands that
# must be typed the same way every time; this types them, and prints each one
# first so you can see, and learn, exactly what it ran.
#
# Assumes the server already works: Linux, your user, SSH and Tailscale set up.
# Setting up the machine itself is not eactl's job.
#
#  *** Not the same family as scripts/basestation/ea.sh (the local install's ea-*
# commands). Both run on the machine they manage, but ea-* manages a local install
# with Docker; eactl manages a remote server with Kubernetes. ***

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

# ── Schools ──────────────────────────────────────────────────────────────────
#
# A school is known by its short name (demo-u-u3fyig), which never changes. Its
# namespace is ea-<short name>, and the namespace itself remembers everything
# else about it:
#   labels       ea/school=<short name>  ea/access=private|public  ea/version=v0.3.1
#   annotations  ea/display-name="Demo U"  ea/address=<its web address>
# (Labels can't hold spaces, so the display name is an annotation.)

APP_IMAGES="ghcr.io/devi-walto/edge-athlete-django ghcr.io/devi-walto/edge-athlete-react"

# school_info <short name> <field> — read one thing the namespace remembers.
school_info() {
    local ns="ea-$1"
    case "$2" in
        access|version) kubectl get namespace "$ns" -o "jsonpath={.metadata.labels.ea/$2}" ;;
        address|display-name)
            kubectl get namespace "$ns" -o "jsonpath={.metadata.annotations.ea/$2}" ;;
    esac
}

# require_school <short name> — stop with a plain message if there's no such school.
require_school() {
    if ! kubectl get namespace "ea-$1" -o name >/dev/null 2>&1; then
        echo "[!] no school called \"$1\". See: eactl list"
        exit 1
    fi
}

# build_school <short name> — the school's full YAML: the base template, plus the
# private or https component, at the school's release, in its namespace.
#
# Kustomize builds from a folder, so this writes a tiny one in a temporary
# folder (one file: "the base, plus this component, at this release") and points
# it back at the repo. Kustomize only accepts relative paths for that, so they're
# worked out from the temporary folder's real location.
build_school() {
    local short="$1" ns="ea-$1" access version address component tmp img
    access="$(school_info "$short" access)"
    version="$(school_info "$short" version)"
    address="$(school_info "$short" address)"
    case "$access" in
        private) component=private ;;
        public)  component=https ;;
        *) echo "[!] $short has no ea/access label (private or public)" >&2; return 1 ;;
    esac
    tmp="$(mktemp -d)" && tmp="$(cd "$tmp" && pwd -P)"
    {
        echo "apiVersion: kustomize.config.k8s.io/v1beta1"
        echo "kind: Kustomization"
        echo "namespace: $ns"
        echo "resources:"
        echo "  - $(relpath "$REPO_DIR/k8s/app/base" "$tmp")"
        echo "components:"
        echo "  - $(relpath "$REPO_DIR/k8s/app/components/$component" "$tmp")"
        echo "images:"
        for img in $APP_IMAGES; do
            echo "  - name: $img"
            echo "    newTag: $version"
        done
    } > "$tmp/kustomization.yaml"
    kubectl kustomize --load-restrictor=LoadRestrictionsNone "$tmp" \
        | NAMESPACE="$ns" SCHOOL_HOST="$address" envsubst '${NAMESPACE} ${SCHOOL_HOST}'
    local rc=$?
    rm -f "$tmp/kustomization.yaml" && rmdir "$tmp"
    return $rc
}

# short_name_from "Demo U" — demo-u-k7m2qx: the display name made safe (lowercase
# letters, digits and dashes, at most 20 characters), plus 6 random characters
# that start with a letter, so two schools with the same name never collide.
short_name_from() {
    local base tail
    # iconv turns accented letters into plain ones first (Ü -> U), where it can.
    base="$(printf '%s' "$1" | { iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || cat; } \
        | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' \
        | tr -s '-' | sed 's/^-*//; s/-*$//' | cut -c1-20 | sed 's/-*$//')"
    [ -n "$base" ] || base=school
    tail="$(LC_ALL=C tr -dc 'a-z' < /dev/urandom | head -c1)$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c5)"
    echo "$base-$tail"
}

# psql_admin — run SQL, read from stdin, as the shared Postgres's administrator.
# Passwords travel in the SQL on stdin, never on a command line where other
# programs on the server could see them.
psql_admin() {
    kubectl -n edge-athlete exec -i deploy/postgres -- psql -U postgres -v ON_ERROR_STOP=1 -q
}

# relpath <target> <from> — the path to <target> as seen from folder <from>.
relpath() {
    python3 -c 'import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$1" "$2"
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
#
# ask VAR "question" "example" "explanation" ["found"]
#   explanation: printed above the question, so anyone knows what is being asked
#                for and how to find it.
#   found:       an answer eactl worked out itself on this server, offered when
#                there is no saved answer yet.
ask() {
    local var="$1" question="$2" example="$3" explanation="$4" found="${5:-}"
    local current answer label=""
    current="${!var:-}"
    if [ -n "$current" ]; then
        label="saved: $current"
    elif [ -n "$found" ]; then
        current="$found"
        label="found on this server: $found"
    fi
    echo
    printf '%s\n' "$explanation" | sed 's/^/    /'
    while true; do
        if [ -n "$label" ]; then
            read -r -p "$question [$label]: " answer
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
    ask DOMAIN "Type your domain" "example.com" \
"The domain this server's sites live under: the one you bought from your domain
provider (Porkbun today). Just the domain, with nothing in front of it."

    ask ACME_EMAIL "Type an email for certificate warnings" "you@example.com" \
"Let's Encrypt gives this server its free HTTPS certificates. It emails this
address only if a certificate is close to expiring and hasn't renewed itself.
Use an address you actually read."

    ask SUBDOMAINS "Type your subdomains, separated by spaces" "test demo" \
"The names in front of your domain that should lead to this server: \"test\"
for test.example.com. The DNS updater keeps each one pointed at this server,
and each needs its first A record made by hand (scripts/remote/README.md)."

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

    # Make `eactl` typeable from any folder, the same way the local install's ea-*
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

new)
    # Make a new school on this server: its own namespace, its own database and
    # database login in the shared Postgres, its settings and secrets, and the app
    # from the template. Every new school starts PRIVATE (Tailscale only).
    #   eactl new "Demo U"                       the usual way
    #   eactl new "Demo U" --version v0.3.2      a different release than the others
    #   eactl new "Demo U" --address x.y.com     an address other than the usual one
    name="" version="" address=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --version) version="${2:-}"; shift 2 ;;
            --address) address="${2:-}"; shift 2 ;;
            --*) echo "unknown option $1"; exit 1 ;;
            *) name="$1"; shift ;;
        esac
    done
    if [ -z "$name" ]; then
        echo 'usage: eactl new "School Name" [--version v0.3.1] [--address name.example.com]'
        exit 1
    fi
    load_config
    require_cluster

    # The release: by default, the one the other schools run, so every school
    # stays on the same version. Asked for if there's no single answer.
    if [ -z "$version" ]; then
        releases="$(kubectl get namespaces -l ea/school -o jsonpath='{range .items[*]}{.metadata.labels.ea/version}{"\n"}{end}' | sort -u | grep -v '^$')"
        if [ "$(printf '%s\n' "$releases" | grep -c .)" = 1 ]; then
            version="$releases"
        else
            [ -n "$releases" ] && echo "    the schools here run: $(echo $releases)"
            read -r -p "Which release should it run (e.g. v0.3.1)? " version
            [ -n "$version" ] || { echo "nothing made"; exit 0; }
        fi
    fi
    for s in postgres-admin ghcr-pull; do
        kubectl -n edge-athlete get secret "$s" >/dev/null 2>&1 || {
            echo "[!] Secret $s is missing in edge-athlete. See scripts/remote/README.md, item 6."; exit 1; }
    done

    short="$(short_name_from "$name")"
    ns="ea-$short"
    db="school_${short//-/_}"          # Postgres prefers _ over -
    address="${address:-$short.$DOMAIN}"

    echo "==> about to make a new school:"
    echo "    display name   $name"
    echo "    short name     $short   (never changes)"
    echo "    namespace      $ns"
    echo "    database       $db   (with a login of the same name)"
    echo "    address        $address"
    echo "    release        $version"
    echo "    access         private (Tailscale only, until it goes public)"
    read -r -p "Make it? (y/N) " answer
    [ "$answer" = y ] || { echo "nothing made"; exit 0; }

    echo
    echo "==> its namespace, which also records everything about it"
    kube create namespace "$ns" || exit 1
    kube label namespace "$ns" ea/school="$short" ea/access=private ea/version="$version"
    kube annotate namespace "$ns" ea/display-name="$name" ea/address="$address"

    echo "==> its database and login in the shared Postgres"
    echo "+ (psql) CREATE ROLE $db … ; CREATE DATABASE $db OWNER $db ; REVOKE CONNECT … FROM PUBLIC" >&2
    pw="$(openssl rand -hex 24)"
    printf '%s\n' \
        "CREATE ROLE $db LOGIN PASSWORD '$pw';" \
        "CREATE DATABASE $db OWNER $db;" \
        "REVOKE CONNECT ON DATABASE $db FROM PUBLIC;" | psql_admin || exit 1

    echo "==> its settings (ConfigMap) and secrets (Secret)"
    kube -n "$ns" create configmap school-settings \
        --from-literal=EA_DEPLOYMENT=remote --from-literal=DEBUG=False \
        --from-literal=EA_INSTALLATION_NAME="$name" \
        --from-literal=ALLOWED_HOSTS="$address,localhost" \
        --from-literal=POSTGRES_DB="$db" --from-literal=POSTGRES_USER="$db" \
        --from-literal=MQTT_HOST=mosquitto --from-literal=MQTT_PORT=1883
    echo "+ kubectl -n $ns create secret generic school-secrets (values hidden)" >&2
    kubectl -n "$ns" create secret generic school-secrets \
        --from-literal=POSTGRES_PASSWORD="$pw" \
        --from-literal=SECRET_KEY="$(openssl rand -base64 48)" || exit 1
    unset pw

    echo "==> a copy of the image pull key"
    echo "+ kubectl -n $ns create secret … ghcr-pull (copied from edge-athlete)" >&2
    kubectl -n edge-athlete get secret ghcr-pull -o json \
        | python3 -c 'import json,sys; s=json.load(sys.stdin); print(json.dumps({"apiVersion":"v1","kind":"Secret","type":s["type"],"metadata":{"name":"ghcr-pull"},"data":s["data"]}))' \
        | kubectl -n "$ns" apply -f - || exit 1

    echo "==> the app, from the template"
    school="$(build_school "$short")" || exit 1
    kube -n "$ns" apply -f - <<< "$school" || exit 1
    for d in mosquitto django react mqtt-listener monitoring-publisher; do
        kube -n "$ns" rollout status "deployment/$d" --timeout=300s || {
            echo "[!] $d is not ready. Look: kubectl -n $ns get pods"; exit 1; }
    done

    echo
    echo "✓ made $short (\"$name\"), private, at $address"
    echo
    echo "Next:"
    echo "  - open it over Tailscale; to claim it, issue a setup code:"
    echo "      kubectl -n $ns exec deploy/django -- python manage.py setup_code"
    echo "  - see every school: eactl list"
    ;;

list)
    # Every school on this server, from what each namespace remembers.
    require_cluster
    printf '%-24s %-26s %-8s %-10s %s\n' "NAME" "SHORT NAME" "ACCESS" "RELEASE" "ADDRESS"
    kubectl get namespaces -l ea/school -o go-template='{{range .items}}{{index .metadata.annotations "ea/display-name"}}	{{index .metadata.labels "ea/school"}}	{{index .metadata.labels "ea/access"}}	{{index .metadata.labels "ea/version"}}	{{index .metadata.annotations "ea/address"}}
{{end}}' | while IFS=$'\t' read -r dn sn ac ve ad; do
        printf '%-24s %-26s %-8s %-10s %s\n' "$dn" "$sn" "$ac" "$ve" "$ad"
    done
    ;;

apply-school)
    # Rebuild one school exactly as its namespace says it should be: used after
    # a change to the template, a release, or going public.
    short="${1:-}"
    [ -n "$short" ] || { echo "usage: eactl apply-school <short name>   (see: eactl list)"; exit 1; }
    require_cluster
    require_school "$short"
    ns="ea-$short"

    school="$(build_school "$short")" || exit 1
    CHANGES=0
    preview "$(school_info "$short" display-name) ($short)" "$school" || exit 1
    # The guard from when it was private, if it's public now. (A preview only
    # shows what's in the new build, so leftovers are listed here.)
    if [ "$(school_info "$short" access)" = public ] \
        && kubectl -n "$ns" get middleware private-only >/dev/null 2>&1; then
        echo "    and remove: the Tailscale-only guard (the school is public)"
        CHANGES=1
    fi
    echo
    if [ "$CHANGES" = 0 ]; then
        echo "✓ $short already matches the template. Nothing to do."
        exit 0
    fi
    read -r -p "Apply these changes? (y/N) " answer
    [ "$answer" = y ] || { echo "nothing applied"; exit 0; }

    echo
    kube -n "$ns" apply -f - <<< "$school" || { echo "[!] $short did not apply"; exit 1; }
    if [ "$(school_info "$short" access)" = public ]; then
        kube -n "$ns" delete middleware private-only --ignore-not-found
    fi
    echo "==> waiting for every part to be ready"
    for d in mosquitto django react mqtt-listener monitoring-publisher; do
        kube -n "$ns" rollout status "deployment/$d" --timeout=240s || {
            echo "[!] $d is not ready. Look: kubectl -n $ns get pods"; exit 1; }
    done
    echo
    echo "✓ $short is up to date: $(school_info "$short" address)"
    ;;

apply-db)
    # The shared database every school keeps its own database in. Applied on
    # its own, with its own preview: if it goes wrong, every school is affected.
    require_cluster

    # Its password is made by hand (README checklist). Unlike the DNS keys this
    # is not optional: Postgres cannot start without it.
    if ! kubectl -n edge-athlete get secret postgres-admin >/dev/null 2>&1; then
        echo "[!] no Secret postgres-admin in namespace edge-athlete."
        echo "    Make it first: scripts/remote/README.md, \"Before you start\"."
        exit 1
    fi

    db="$(kubectl kustomize "$REPO_DIR/k8s/db/postgres")" \
        || { echo "[!] could not build k8s/db/postgres"; exit 1; }

    CHANGES=0
    preview "the shared database (Postgres)" "$db" || exit 1
    echo
    if [ "$CHANGES" = 0 ]; then
        echo "✓ the cluster already matches k8s/db. Nothing to do."
        exit 0
    fi
    read -r -p "Apply these changes? (y/N) " answer
    if [ "$answer" != y ]; then
        echo "nothing applied"
        exit 0
    fi

    echo
    echo "==> applying the shared database"
    kube apply -f - <<< "$db" || { echo "[!] the database did not apply"; exit 1; }
    # Ready means its readiness check (pg_isready) passes: Postgres answers.
    echo "==> waiting for Postgres to answer (up to 3 minutes)"
    kube -n edge-athlete rollout status deployment/postgres --timeout=180s \
        || { echo "[!] Postgres is not ready. Look: kubectl -n edge-athlete get pods"; exit 1; }

    # Every login may connect to Postgres's own maintenance databases (postgres,
    # template1) unless told otherwise. They hold no school data, but a school's
    # login has no business there either, so close them. Safe to repeat.
    echo "==> closing the maintenance databases to school logins"
    echo "+ (psql) REVOKE CONNECT ON DATABASE postgres, template1 FROM PUBLIC" >&2
    printf '%s\n' "REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;" \
        "REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;" | psql_admin || exit 1

    echo
    echo "✓ the shared database is running: postgres.edge-athlete, port 5432."
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
