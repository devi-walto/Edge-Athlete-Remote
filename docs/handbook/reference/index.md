# Reference

Exact shapes, for looking things up. Don't read these front to back.

**{doc}`eactl`**
: Every remote-server command, what it changes, and where things live on the server.

**{doc}`api`**
: Every route, grouped by what it touches, with its permission and the reasoning beside it. The permission rule and how a login's role is worked out are at the top.

**{doc}`database-tables`**
: Every table, collapsed, with its schema and the decisions attached to it. New here? Open the plain-English tour at the top first.

**{doc}`mqtt-messages`**
: The wire formats: what sensors publish, what the server broadcasts, and the request and response bodies the screens are built against.

**{doc}`versions`**
: What the version numbers mean, when each part moves, and what `1.0.0` would take. Short.

```{toctree}
:maxdepth: 1
:hidden:

eactl
api
database-tables
mqtt-messages
versions
```
