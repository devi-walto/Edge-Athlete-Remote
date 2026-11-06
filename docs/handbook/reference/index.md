# Reference

Exact shapes, for looking things up. Don't read these front to back.

**{doc}`eactl`**
: Every remote-server command, what it changes, and where things live on the server.

**{doc}`api`**
: Every route, grouped by what it touches, with its permission and the reasoning beside it. The permission rule and how a login's role is worked out are at the top.

**{doc}`database-tables`**
: Every table, collapsed, with its schema and the decisions attached to it. New here? Open the plain-English tour at the top first.

**{doc}`message-contract`**
: What every REST route takes and returns: the bodies the screens send and get back. All collapsed; open the one you need.

**{doc}`mqtt-topics`**
: Everything that moves live: how one rep travels, how a room update travels, and for each topic what starts it, how it travels, who hears it and what they do next.

**{doc}`versions`**
: What the version numbers mean, when each part moves, and what `1.0.0` would take. Short.

```{toctree}
:maxdepth: 1
:hidden:

eactl
api
database-tables
message-contract
mqtt-topics
versions
```
