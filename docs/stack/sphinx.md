# Sphinx and Read the Docs

**What it is.** What turns this folder of Markdown into the site you are reading.
Sphinx builds it.

**How we use it.** Built **locally**, not hosted:

```
./docs/build.sh     build the whole site once, then open the file it prints
./docs/serve.sh     live preview on localhost that rebuilds as you save
```

This repo is private, and the free Read the Docs cannot clone a private repo — that
is a Business-plan feature. `.readthedocs.yaml` is still here and still correct, so
connecting a paid account later needs no work. Hosted, it would serve two versions
saying different things: `/en/latest/` from `main`, and `/en/stable/` from the newest
release tag — what the gym is actually running.

**Where it lives.** `docs/`. Settings in `docs/conf.py`, dependencies in
`docs/requirements.txt`, RTD's build config in `.readthedocs.yaml`.

**Worth knowing.** ⚠️ `conf.py` and `requirements.txt` must stay in step. An
extension listed in one and missing from the other kills the build — and Read the
Docs keeps serving the **last build that worked**, so the site stays up and silently
goes stale. That is exactly how it froze for weeks.

`fail_on_warning` is on, so one bad cross-reference fails the whole build.

`build.sh` builds with warnings fatal, exactly as a hosted build would, so a broken
cross-reference fails on your laptop instead of reaching a site. `serve.sh` does not —
mid-sentence links break constantly and a hard failure there is just noise.

**More:** {doc}`../reference/versioning` for what the version numbers mean
