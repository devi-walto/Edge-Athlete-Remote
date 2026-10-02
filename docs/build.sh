#!/usr/bin/env bash
#
# build.sh — build the whole documentation site once, locally.
#
# Run it:   ./docs/build.sh        then open the file it prints
#
# WHERE THE HOSTED SITE COMES FROM
# This repo is private, and the free Read the Docs cannot clone a private repo. So the
# hosted site is built from a public copy of docs/ that publish.sh pushes to a separate
# repo. This script is the check before that: the same Sphinx build, the same
# requirements.txt, the same rules — run it before you publish.
#
# HOW THIS DIFFERS FROM serve.sh, AND WHY BOTH EXIST
#   serve.sh   live preview while writing. Warnings are NOT fatal, because a
#              half-typed cross-reference is normal mid-sentence.
#   build.sh   the real thing. Warnings ARE fatal (-W), exactly as a hosted build
#              would treat them, so a dead link fails on your laptop instead of
#              shipping quietly to whoever you send the site to.
#
# That distinction is load-bearing. A hosted build keeps serving the LAST BUILD THAT
# WORKED, which is how these docs once sat frozen for weeks while every URL still
# resolved and nothing on the page admitted it was old. Catching a broken build here,
# before publishing, is what stops that from happening again.
#
set -euo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DOCS_DIR/venv"
OUT="${1:-$DOCS_DIR/_build/html}"

# Same toolchain, same place, same requirements file as serve.sh — so whichever you
# ran first, the other one starts instantly. docs/venv is gitignored.
if [ ! -x "$VENV/bin/sphinx-build" ]; then
    echo "[*] setting up the docs toolchain in docs/venv (one time)..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip3" install -q --upgrade pip
    "$VENV/bin/pip3" install -q -r "$DOCS_DIR/requirements.txt"
    echo "[*] done"
fi

echo "[*] building the site (warnings are fatal)..."
# -W turns warnings into errors; --keep-going reports ALL of them in one run rather
# than stopping at the first, which turns "fix, rebuild, discover the next one" into
# a single list.
#
# -E rebuilds from scratch instead of reusing the cache, and it is here because the
# cache got it wrong: adding a new SECTION updated the front page but left every
# other page's sidebar still showing the old navigation. The pages were individually correct and
# the site was wrong, which is the worst kind of wrong to debug. A full rebuild of a
# site this size costs a few seconds; believing a stale sidebar costs longer.
"$VENV/bin/sphinx-build" -b html -E -W --keep-going "$DOCS_DIR" "$OUT"

echo
echo "[✔] built. Open it:"
echo "      open $OUT/index.html"
echo
echo "    This is a plain folder of HTML — it works from disk with no server, and it"
echo "    can be zipped and handed to somebody as-is."
