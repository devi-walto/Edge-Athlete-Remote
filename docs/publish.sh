#!/usr/bin/env bash
#
# publish.sh — copy the documentation into the PUBLIC docs repo that Read the Docs builds.
#
# Run it:   ./docs/publish.sh            build the public copy and test it, push nothing
#           ./docs/publish.sh --push     same, then push it to the public repo
#
# WHY THERE ARE TWO COPIES
# This repo is private, and the free Read the Docs cannot read a private repo. So the
# docs live here, where they are written and versioned next to the code, and a copy of
# just the docs is pushed to a separate public repo that Read the Docs builds from:
#
#   private repo  docs/         the real thing — edit here, never in the public repo
#   public repo   docs/         a copy, replaced on every publish
#
# WHAT GOES PUBLIC, AND WHAT DOES NOT
# Only what the site build needs: the pages, conf.py, requirements.txt, _static/ and
# _erd.md. The underscore-prefixed working documents (_HANDOFF.md, _PATCH_NOTES.md, …)
# are excluded from the site already and stay private here too, as do the helper
# scripts. The copy is taken from the last COMMIT (git archive), never the working
# folder, so a half-written page or a stray local file cannot leak out by accident.
#
# The copy is test-built on its own before anything is pushed, with warnings fatal —
# if it does not build standalone here, it will not build on Read the Docs either.
#
set -euo pipefail

PUBLIC_REPO="${PUBLIC_DOCS_REPO:-git@github.com:devi-walto/Edge-Athlete-Remote-docs.git}"
PUSH=0
[ "${1:-}" = "--push" ] && PUSH=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Publishing a commit, not a working folder: refuse if docs/ has uncommitted changes,
# because the public copy would then not match anything in this repo's history.
if [ -n "$(git status --porcelain -- docs .readthedocs.yaml)" ]; then
    echo "[!] docs/ has uncommitted changes — commit them first, then publish." >&2
    exit 1
fi
REV="$(git rev-parse --short HEAD)"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "[*] copying docs from commit $REV..."
git archive HEAD docs .readthedocs.yaml | tar -x -C "$STAGE"
# Keep the shared diagram (_erd.md, {include}d into pages); drop the other working docs.
find "$STAGE/docs" -maxdepth 1 -name '_*.md' ! -name '_erd.md' -delete
rm -f "$STAGE/docs/build.sh" "$STAGE/docs/serve.sh" "$STAGE/docs/publish.sh" \
      "$STAGE/docs/refresh-routes.py" "$STAGE/docs/refresh-schema.py"

cat > "$STAGE/README.md" <<EOF
# Edge Athlete Remote — documentation

The source of the developer journal at Read the Docs.

**Do not edit here.** This repository is a copy, replaced on every publish from the
project's main repository (copied from commit \`$REV\`). Changes made here are
overwritten.
EOF

echo "[*] test-building the public copy on its own (warnings are fatal)..."
VENV="$ROOT/docs/venv"
if [ ! -x "$VENV/bin/sphinx-build" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip3" install -q -r "$ROOT/docs/requirements.txt"
fi
"$VENV/bin/sphinx-build" -q -b html -E -W --keep-going "$STAGE/docs" "$STAGE/_test_build"
rm -rf "$STAGE/_test_build"
echo "[✔] the public copy builds"

if [ "$PUSH" -eq 0 ]; then
    echo
    echo "    Nothing pushed. Run with --push to publish:  ./docs/publish.sh --push"
    exit 0
fi

echo "[*] pushing to $PUBLIC_REPO..."
CLONE="$STAGE/_public"
git clone -q "$PUBLIC_REPO" "$CLONE"
git -C "$CLONE" checkout -q -B main
# Replace everything except git's own folder, so files deleted here disappear there too.
find "$CLONE" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$STAGE/docs" "$STAGE/.readthedocs.yaml" "$STAGE/README.md" "$CLONE/"
git -C "$CLONE" add -A
if git -C "$CLONE" diff --cached --quiet; then
    echo "[✔] the public repo already matches $REV — nothing to push"
    exit 0
fi
git -C "$CLONE" commit -q -m "docs from $REV"
git -C "$CLONE" push -q origin main
echo "[✔] published docs from $REV. Read the Docs rebuilds on its own within a minute or two."
