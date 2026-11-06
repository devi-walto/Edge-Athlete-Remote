# Core

The decisions both installs stand on. The local install came first, and almost everything it decided carries over to the remote server unchanged: the same images, the same database tables, the same messages, the same screens. Only a few things differ, and those live in the two children below.

**{doc}`real-time`**
: The message broker, and what actually listens to it.

**{doc}`rack-screen`**
: What the athlete uses, and where reps are kept safe.

**{doc}`coach-screens`**
: Sign-in, room setup, planning, spreadsheet import.

**{doc}`room-display`**
: The wall display.

**Two Core decision pages live in the Handbook,** because their dropdowns are what you look up: {doc}`../../handbook/reference/api` (the permission rule, how a login's role is worked out) and {doc}`../../handbook/reference/database-tables` (why each table looks the way it does, the three weights, how a target is worked out).

## Children

**{doc}`Local only <local/index>`**
: Decisions that only apply to the base station in the gym: its installer, its own Wi-Fi, its screens.

**{doc}`Remote <remote/index>`**
: Decisions that only apply to the remote server: hosting, one database per school, logins for athletes, virtual racks, sensors over the internet.

```{toctree}
:maxdepth: 2
:hidden:

real-time
rack-screen
coach-screens
room-display
local/index
remote/index
```
