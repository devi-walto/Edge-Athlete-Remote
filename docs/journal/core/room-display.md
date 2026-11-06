<!--
this page — the big screen on the gym wall, and why it's the same file as the
coach's live room.

The live-room hook (react/src/useLiveRoomState.js) is mostly guards against showing
the room something untrue. Each guard here came from a real way it went wrong;
read the list before removing one.
-->

# Room display

The big screen on the gym wall. In a second mode, it's also the coach's live room: they're the same file, `react/src/Dashboard.jsx`.

## Tool changes at a glance

| Job | First | Now | Where it lives |
|---|---|---|---|
| Wall and coach views | — | **one component, `mode="wall"` or `mode="coach"`** | `Dashboard.jsx` |
| Knowing the room changed | MQTT messages only | **MQTT `room_state_changed`, plus a backstop poll every 20 seconds** | `useLiveRoomState.js` |
| Online | — | **the wall view signs in as a coach**; still the no-names snapshot | `Dashboard.jsx` (since v0.8.1) |

## The problem

The wall and the coach's screen show the same room, changing at the same moments. The wall is **public**: anyone walking past sees it, other athletes, visiting teams, parents. And a scoreboard that's quietly wrong is worse than no scoreboard: a coach who catches it lying once stops trusting it.

## Try 1: two separate screens

**Why I passed on it:** they'd drift. The same event would need handling twice, and the two views would eventually disagree about what the room looks like, which is exactly what a coach would notice.

**Where I landed:** one component with a `mode` prop. They share a file because they share a heartbeat: the same live-room hook drives both, and both ask the same route for different amounts of detail. **The mode check matters**, not cosmetic: every change has to be thought through for both audiences.

## The wall shows no names

The wall gets an **anonymous** snapshot. Names, IDs and history are only in the coach view.

Both views call {ref}`GET /api/room-state/ <mc-room-state>`. The coach view adds `?details=true`, and that needs a coach login. The wall can't receive names by accident: it never asks for them.

**Online it's one step stricter (Oct 30, v0.8.1).** The server only shows the room to a coach, so the wall view now asks a coach to sign in, sends that login, and still asks for the no-names snapshot. Before this, the online wall got a `401`, and the refusal signed the coach out of that browser. On the local install nothing changed: no sign-in, and no login sent even if one is left in the browser.

## How it finds out the room changed

MQTT only ever says "look again," never "here's the data": a `room_state_changed` with a revision number, then the screen fetches the room. That design, and why, is in {doc}`real-time`.

**Try 1: refresh only when a message says so.** Efficient while messages arrive, and a dead end when one goes missing. The screen sat on stale data until someone reloaded it. On Aug 11 the wall display never heard a session start.

The trap: a 15-second staleness timer looked like a refresh timer, and wasn't. It only changes a status label.

**Where I landed:** a **backstop poll every 20 seconds** calls the same refresh. It keeps the last good snapshot if the poll fails, and it yields to a fetch already running instead of stacking on top of one. Messages are still the fast path; the poll means a missed one can't freeze the room.

## The careful part: not lying to the room

Most of the live-room hook exists to stop a screen showing something untrue. Each guard came from a specific way it could go wrong:

- **A fetch in flight blocks a second one**, but remembers a newer revision arrived and fetches again once the first lands. Without it, a burst of changes could leave the screen on an older answer that happened to return last.
- **Answers meant for a previous mode or login are thrown away.** Switching wall to coach fires a new request; without a generation check, the old reply could land after the new one and overwrite it.
- **A failed refresh keeps the last good snapshot** and marks the connection stale, rather than blanking a wall screen mid-session. Stale but readable beats empty.
- **Incoming messages are checked hard before they're trusted:** schema version, message type, a sane positive revision, an ID matching a strict pattern, and a size cap. On the local install anything on the Wi-Fi can publish, so a malformed or hostile message is possible.
- **Revisions only move forward.** A replayed or out-of-order message can't rewind the screen.
- **If the broker goes quiet for 15 seconds, the connection shows as stale.** A frozen scoreboard that looks live is worse than one that admits it.

## The settings cog

The wall has a small settings cog holding one thing: **Change device role.** A wall-mounted screen has no keyboard and is often out of reach. Without an on-screen way to change what the device is, repurposing it means getting a keyboard up to a screen above head height. The cog is the difference between a two-minute change and a ladder.

## Things I passed on

- **Two separate screens.** Try 1.
- **Names on the wall.** It's public.
- **Data in the broadcast.** See {doc}`real-time`.
- **Assigning athletes to a rack ahead of time** on this screen. Who's at a rack is decided by who checks in there, not by a plan made earlier (see {doc}`rack-screen`).

## What it cost

- **One file, two audiences.** Every change gets thought through twice.
- **A room update is a message and a fetch,** plus a fetch every 20 seconds per screen even when nothing changed. Cheap, and it buys a room that can't freeze.
- **Online, the wall needs a coach signed in** on that screen.
