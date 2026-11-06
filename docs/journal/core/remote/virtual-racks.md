<!--
this page — how a remote athlete ends up on a rack of their own without anyone
setting one up, and the rack rules that had to change to get there.

Virtual racks touched the oldest parts of the app (the rack's controller lease,
check-in, the rack screen itself), so more ideas were tried and dropped here than
anywhere else in the remote work. They're kept in order so the next change
doesn't bring one back.
-->

# Virtual racks

*Oct 5 – Oct 30, 2026 · spec 04 · migration 0028*

## Tool changes at a glance

| Job | Gym rack | Virtual rack | Where it lives |
|---|---|---|---|
| Making the rack | a coach sets up a tablet | **made by the server when the athlete joins** | `services/session_join.py`, `POST /api/sessions/{id}/join/` |
| Rack number | small numbers (1, 2, 3) | **from 10,000 up** | `VIRTUAL_RACK_BASE` in `models.py` |
| Who's lifting | tap a name on the rack | **the rack's owner, stored as a fact** | `RackRuntime.owner_athlete` |
| Who controls the rack | the browser tab holding a 20-second lease | **the athlete's login** | `rack_controller_acquire` |
| The sensor | a coach links it to the rack | **the athlete's own sensor, attached on join** | `Node.owner` |
| Cleaning up | the rack stays | **released when the session ends** | `RackRuntime.session` |

:::{warning}
**Don't work out "who's lifting" from anything else.** On a virtual rack the lifter is always `owner_athlete`. It's checked by the server, and a request that would clear it or check in someone else is refused (`409 owned_rack`). Guessing it from recent check-ins was considered and dropped (Try 2).
:::

## The problem

In the gym, a rack is a tablet a coach set up, with a sensor a coach linked. A coach running fifty athletes over a video call can't set up fifty racks.

So when a signed-in athlete joins a session, the server has to make their rack, attach their sensor, and put them on it, with nobody picking anything.

## Try 1: ask the athlete which rack they're at

The gym way: the screen asks "which rack?", and the athlete picks one.

**Why I moved on:** a remote athlete is alone, with their own sensor. There's no rack to pick. **Their device is the rack.** Joining makes one just for them, and joining again gives the same one back.

Two decisions came with it:

- **Numbered from 10,000.** A school can run both a local install and the remote server, so virtual racks can never land on a gym's rack 1, 2, 3.
- **Joins take turns.** Each join takes a row lock before picking the next free number, so fifty athletes joining at once get fifty different racks. There's a test for exactly that.

## Try 2: guess who's lifting

A rack with one athlete checked in recently is probably theirs, so select them.

**Why I moved on:** in the gym, the first athlete to check in would trip it. It depends on a timer. And it would still let a remote athlete reach a list of names. **Where it landed:** the owner is a fact the server stores (`RackRuntime.owner_athlete`), set only on a virtual rack. It can't be cleared and nobody else can be checked in.

## Try 3: a second rack screen for remote athletes

**Why I moved on (Oct 6):** two copies drift. The gym's rack screen was already built to be portable and is a phone-width column. And it never chose the lifter itself: tapping a name sends a check-in and the screen draws whatever the server says. So a rack whose state already names an athlete just opens on Ready. **Same screen, no second flow.**

## Try 4: the gym's controller lease

In the gym, a rack is controlled by one browser tab holding a 20-second lease, with a token in `sessionStorage`. Reload the tab and the token's gone, so a **recover** step ends the abandoned set, because someone else might be at the rack now.

**Why I moved on:** on your own rack, nobody else can be at it. A reload would have thrown an athlete into recovery mid-set for no reason. **Where it landed:** on a virtual rack, the lease follows the login. Reload and you get your rack back, set still open. The gym's lease is unchanged.

## Who may join

**First rule (Oct 5):** you must be in a training group assigned to the session.

**Why it changed (Oct 14):** quick sessions (spec 08) let a coach pick athletes one by one with no workout, so they have no group, and the rule locked everyone out. **Now:** you may join if you're on the session's roster *or* in a group taking part in it. A group member who wasn't on the roster is added, so the coach's room and report include them.

## Where an online browser lands

**Before:** `/` showed the "Set up this device" picker, the same as a gym tablet.

**Why it changed (Oct 17):** online, nobody should land on a rack setup screen. **Now:** the login decides. A coach goes to the coach screens, an athlete to their overview, and a session link (`/session/<id>`) joins straight away. A saved device setting in the browser is ignored online.

**The display view stays coach only.** It reads the room's state, which is coach only. Opening it to athletes would be a server change for a nice-to-have nobody asked for.

## Where it all landed

1. The athlete opens the session link. Already signed in, they skip straight to joining.
2. The server checks the session is live and they belong in it.
3. It finds or makes their virtual rack, checks them in, and points their sensor at it. The check-in is **`record_check_in()` in `services/rack_checkin.py`**, the same function the gym's check-in route (`POST /api/racks/<n>/checkin/`, when an athlete taps their name) calls. It records the check-in, makes the athlete the rack's selected lifter, bumps the rack's state version, and tells the live room. One function for both, so the rack screen, the live room and the report can never see a gym check-in and an online join differently. **Don't write a second check-in for a new way onto a rack; call this one.**
4. They land on the gym's own rack screen, on Ready.
5. Online, an athlete may use only their own rack, check in only themselves, and start or finish only their own sets. A coach can't take it over either.
6. Ending the session ends any open set and keeps it, frees the sensors, and deletes the virtual racks. Sets, reps and the report are untouched.

**Two athletes on one bar** each get their own rack and their own sensor. Both sensors feel every rep, but a rack only listens while its own set is running, so nobody's reps land on the other.

**Demo data (Oct 30):** phantom lifters (`eactl sim --phantom`) are seeded athletes who join, take their own rack and lift through the same routes a phone uses. A demo school looks alive with no hardware.

## Next: shared racks online (decided, not built)

*Spec 18 · decided Oct 26–27*

Virtual racks fit athletes training apart, one phone each. A school whose athletes lift together can't use the remote server that way yet: a tablet at a rack, or a TV showing the room, has no login, and online every rack route needs one.

**The decision: a common login.** A fourth kind of login beside administrator, coach and athlete, one per school, shared by every rack tablet and TV. Like the others it isn't a stored role. It comes from what the login is attached to. Each device signed in with it gets its own record, so a coach can see them and sign one out.

- **On a tablet:** the normal sign-in, then **Set up this rack** (named "Rack 3" by itself, renamable), then the gym's own rack screen with its check-in list. A small corner button switches the tablet to the room display and back, and asks first.
- **School sensors:** a sensor can be claimed for the school instead of an athlete, with the same one-time code.
- **Pairing confirms itself with one rep:** pick a sensor and a 60-second countdown says "Do one rep with the bar". No rep, no link.
- **Everything can also be set up from the coach's Room Layout.** Only signing a tablet in has to happen on the tablet.
- **The risk of a shared password is accepted.** Anyone who knows it can check athletes in and log sets during a session. If it's misused, a coach resets it and every device signs in again.

The rack routes keep their numbers, so they stay as they are; only who may use them online changes. Virtual racks don't change at all. The local install moves to the same naming and pairing later, minus the login.

## Things I passed on

- **The gym's recover step on a virtual rack.** Only one person can be at it.
- **A display view for athletes.** See above.
- **One phone shared by two athletes.** Out of scope for now.

## What it cost

- **Two lease rules** (gym tab vs. login), so rack-control changes get tested on both.
- **Rack numbers aren't a count.** Rack 10,003 doesn't mean there are 10,003 racks.
- **Every virtual rack has exactly one owner.** Athletes sharing a bar online need the common login above, which isn't built yet.
