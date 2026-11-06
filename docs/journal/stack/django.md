# Django

*Both installs*

**Why I picked it.** The easiest way to get the server and the login logic working. I'd used it on Privacy Dots, my freshman expo design winner, and this project is a descendant of Privacy Dots.

**What it is.** The web server and the only thing that writes to the database. A
Python framework; we use it with Django REST Framework for the API.

**How we use it.** Three processes from one image, because they have different jobs:

| Process | Job |
|---|---|
| `django` | serves `/api/…` — everything the screens read and write |
| `mqtt-listener` | subscribes to node heartbeats and records them |
| `monitoring-publisher` | drains change events and broadcasts them to screens |

It is deliberately **not** in the live rep path. Reps go node → broker → tablet, and
Django only sees a set when the tablet posts the whole thing at once.

**Where it lives.** `django/`, built from `django/Dockerfile`: on the base station for a local install, by GitHub Actions into GitHub's registry for the remote server, where the three processes run as the `django` and `workers` deployments. Models in
`django/event_handler/models.py`, routes in `urls.py`, handlers in `views.py`.

**Worth knowing.** ⚠️ The image **bakes the source in** — there is no volume mount.
Editing a file changes nothing until you rebuild. Every "my change did nothing"
report so far has been this.

**One switch, `EA_DEPLOYMENT`** (`local` or `remote`), read only through `is_hosted()`, decides the few things that behave differently online ({doc}`../core/remote/deployments`).

**More:** {doc}`../../handbook/reference/api` for the endpoints and the reasoning ·
{doc}`../../handbook/guides/database-changes` for changing the schema
