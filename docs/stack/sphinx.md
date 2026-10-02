# Sphinx and Read the Docs

**What it is.** What turns this folder of Markdown into the site you are reading.
Sphinx builds it.

**How we use it.** Written and built here, **published** from a copy:

```
./docs/build.sh            build the whole site once, then open the file it prints
./docs/serve.sh            live preview on localhost that rebuilds as you save
./docs/publish.sh --push   copy the docs to the public repo Read the Docs builds from
```

This repo is private, and the free Read the Docs cannot clone a private repo. So the
docs live here, next to the code, and `publish.sh` pushes **a copy of just the docs**
to a separate public repo, which Read the Docs builds. Edit here, never there — the
public copy is replaced on every publish.

The copy is taken from the last commit, leaves out the underscore-prefixed working
documents, and is test-built on its own before it is pushed.

**Where it lives.** `docs/`. Settings in `docs/conf.py`, dependencies in
`docs/requirements.txt`, RTD's build config in `.readthedocs.yaml` (copied to the public
repo on publish).

**Worth knowing.** ⚠️ `conf.py` and `requirements.txt` must stay in step. An
extension listed in one and missing from the other kills the build — and Read the
Docs keeps serving the **last build that worked**, so the site stays up and silently
goes stale. That is exactly how it froze for weeks.

`fail_on_warning` is on, so one bad cross-reference fails the whole build.

`build.sh` builds with warnings fatal, exactly as a hosted build would, so a broken
cross-reference fails on your laptop instead of reaching a site. `serve.sh` does not —
mid-sentence links break constantly and a hard failure there is just noise.

**More:** {doc}`../reference/versioning` for what the version numbers mean
