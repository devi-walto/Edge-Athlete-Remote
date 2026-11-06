# GitHub Actions

*Both installs (tests) · remote server (releases)*

**Why I picked it.** I learned it in CSC 450, Cloud Computing, and the code already lives on GitHub.

**What it is.** GitHub's automation: files in `.github/workflows/` that run jobs when something happens in the repo, like a pull request or a new tag.

**How we use it.** Three workflows:

| Workflow | When | What it does | Runs on |
|---|---|---|---|
| `ci.yml` | every pull request | the backend suite **twice** (as a local install, then as the remote server), the frontend suite and build, the docs build. Red means it can't merge | GitHub's machines |
| `promote-main.yml` | every 3 days, or a button | fast-forwards `main` to `SprintBranch`, pushing with a deploy key | GitHub's machines |
| `release.yml` | a version tag reaching `main` | builds the images into GitHub's registry (GHCR), deploys every school (demo first), then publishes the release page | GitHub's machines, then **the runner on the Dell** for the deploy |

**Where it lives.** `.github/workflows/`. The deploy runner is GitHub's own runner program, installed on the Dell as the `ea-deploy` user with the label `ea-deploy` ({doc}`../../handbook/guides/remote-server`, step 8).

**Worth knowing.**

- ⚠️ **Pull requests never run on the Dell.** The repo is public, and a stranger's pull request must never run code on a machine in my house. Only tagged releases reach the runner.
- **The runner reaches out to GitHub** to collect its job, so nothing is opened inward, and its cluster login can update schools and nothing else.
- **The workflow's own login (`GITHUB_TOKEN`) can't move `main`**: it can't be singled out by a branch rule, and its pushes don't start other workflows. That's why `promote-main.yml` uses a deploy key ({doc}`../core/remote/releases`).
- **"Move main forward" is switched off** while the build is locked for the class.

**More:** {doc}`../core/remote/releases`
