#!/usr/bin/env bash
# release-version.sh — which versions should a release build, and which one deploy?
#
# Why this file exists: a version is released only once its tagged commit is on
# main (spec 12, Phase 3). The release workflow (.github/workflows/release.yml)
# starts in two ways, and asks this script what to do:
#
#   release-version.sh tag <tag> <main>
#       Someone pushed a tag. Prints the tag if its commit is already on <main>,
#       nothing if not (it waits: the next time main moves, it is picked up).
#
#   release-version.sh moved <old main> <new main>
#       main moved forward. Prints every plain version tag (v1.2.3) that is on the
#       new main but was not on the old one, oldest first. The workflow builds all
#       of them (so each can be rolled back to) and deploys only the last, newest.
#
# Prints one version per line; nothing means "nothing to release". Kept in its own
# file, apart from the workflow, so scripts/remote/tests/release-version.sh can
# check every case against a throwaway repository.

set -euo pipefail

# Only plain versions release by themselves when main moves. A test tag such as
# v0.6.0-test.1 would sort AFTER v0.6.0 and could wrongly win "newest"; pushing a
# test tag on a commit already on main still releases it, as before.
PLAIN='^v[0-9]+\.[0-9]+\.[0-9]+$'

# Every v* tag whose commit is part of <commit>'s history, one per line.
tags_on() {
    # A brand-new branch has no "before": git reports it as all zeros.
    if [ -z "$1" ] || [ -z "${1//0/}" ]; then return 0; fi
    git tag --merged "$1" --list 'v*'
}

case "${1:-}" in
tag)
    tag="${2:?usage: release-version.sh tag <tag> <main>}"
    main="${3:?usage: release-version.sh tag <tag> <main>}"
    commit="$(git rev-list -n 1 "refs/tags/$tag")"
    if git merge-base --is-ancestor "$commit" "$main"; then
        echo "$tag"
    fi
    ;;
moved)
    old="${2:?usage: release-version.sh moved <old main> <new main>}"
    new="${3:?usage: release-version.sh moved <old main> <new main>}"
    # On the new main, not on the old one: comm -13 keeps lines only in the second list.
    comm -13 <(tags_on "$old" | sort) <(tags_on "$new" | sort) \
        | { grep -E "$PLAIN" || true; } \
        | sort -V
    ;;
*)
    sed -n '/^#   release-version.sh/,/^#$/p' "$0" | sed 's/^# \{0,3\}//'
    exit 1
    ;;
esac
