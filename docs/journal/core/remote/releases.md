<!--
this page — how a change gets from a pull request onto the Dell and every school,
without opening the cluster to the internet and without one bad release taking
every school down.

Each try below was a real dead end. They're written down so nobody walks back
into one: GitHub's own login can't move a locked branch, re-applying the old
release can re-apply what broke, and the deploy runner must never have root.
-->

# Releases

*Oct 17 – Nov 4, 2026 · spec 12 · `.github/workflows/`*

## Tool changes at a glance

| Job | Local install | Remote server |
|---|---|---|
| Getting new code | the box pulls from its own clone (`self-update`) | a version tag builds images and deploys them |
| Where images come from | built on the box | **GitHub's container registry (GHCR)**, private |
| Who deploys | the box itself | **a self-hosted GitHub Actions runner on the Dell** |
| Tests | — | **GitHub Actions on GitHub's machines**, every pull request |

## The problem

Every change has to reach every school the same way, tested, and never break all of them at once. But the cluster sits behind my home router, and its control port is never opened to the internet. So GitHub can't reach in to deploy.

And the repo is public. A stranger's pull request must never run code on a machine in my house.

## Try 1: test and deploy from GitHub's machines

**What worked:** tests. Every pull request runs on GitHub's own machines: the backend suite twice (once as a local install, once as the remote server), the frontend suite and build, and the docs build. About 1,100 tests. Red means it can't merge. That part stayed, and it stays on GitHub's machines because of the public repo.

**Why I moved on for deploys:** GitHub's machines can't reach the cluster without opening its control port, and that's the one port I'll never open.

**Where it went:** a **self-hosted runner on the Dell**. It reaches *out* to GitHub to collect a deploy job, so nothing new is exposed. It only runs deploy jobs, never pull requests.

## Try 2: move `main` with the workflow's own login

`main` is where releases are tagged, so it should only ever hold work that passed CI. A job moves `main` forward to `SprintBranch` every 3 days, or on a button.

**What worked:** the fast-forward. If `main` ever has something `SprintBranch` doesn't, the job fails loudly instead of merging.

**Why I moved on:** GitHub's built-in workflow login (`GITHUB_TOKEN`) can't be singled out in a branch rule. Locking `main` locked the job out too. And pushes made with that login never start another workflow, so a tag reaching `main` couldn't release itself.

**Where I landed:** a **write deploy key**, kept in GitHub's secret store (`PROMOTE_MAIN_KEY`) and used by that one job. The branch rule lets only a deploy key move `main`, so a pull request into `main` can't be merged by anyone.

## Try 3: undo a bad update by re-applying the old release

**Why I moved on:** v0.5.0. The broker's new settings file couldn't be read, and the demo school's live updates went down. Re-applying the old version would have re-applied the *new* template with old images, and the template was what broke.

**Where I landed:** every part that changed goes back to its **exact previous setup**, on its own. A release that fails on a school now undoes itself.

## Try 4: run the setup script from the pipeline

The Dell's own copy of the tools (`eactl`) has to stay current, or the commands I type there won't match what the schools run.

**Why I moved on:** the setup script runs as root, and the deploy runner was built to have no root at all. Giving it root would let anything that reaches the runner own the machine.

**Where I landed:** an **hourly timer on the Dell** moves its copy to the newest release with a read-only key. It needs no new access. The setup script is only for a new machine.

## Where it all landed

1. **Pull request** into `SprintBranch`. CI runs on GitHub's machines.
2. **I merge.** Only green CI can merge.
3. **Tag a version.** Once the tag is on `main`, GitHub builds the images from the same Dockerfiles the local install uses and stores them privately in GHCR. Every version that arrives gets built, so each one can be rolled back to.
4. **The Dell deploys.** The runner moves every school to the newest version with `eactl`, **demo school first**. If the demo fails, nothing else moves.
5. **Release page.** Once the version is live on every school, GitHub publishes a release page for it by itself.

A school can also be **held** at its version. Moving one school back to an older release holds it automatically, after checking which database changes the older version doesn't know about and offering to undo them behind a safety copy.

The deploy login can update schools and nothing else: no secrets, no shared database, no cluster add-ons.

## What it cost

- **A write deploy key to look after.** If it ever leaks, delete it under the repo's deploy keys and make a new one. The steps are in `scripts/remote/README.md`.
- **Releases wait for `main`.** A tag placed on `SprintBranch` doesn't release until `main` catches up, on the schedule or the button.
- **The runner lives on the same Dell it deploys to.** If the Dell is down, so are deploys. That's fine, since the schools are down too.
