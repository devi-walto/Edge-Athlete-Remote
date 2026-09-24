<!--
this page — who creates athletes, who gets a login, and what a login can do.

The gym box's access rules were written for a closed network, and the journal says so
(journal/apis: "if this ever runs on a network that is not private, this is the first
decision to revisit"). This is that revisit. The short version: the gym stays exactly
as it is, and logins appear only where the internet makes them necessary.
-->

# Who can get in

## What forced it

On the gym box, **the network is the lock.** Only devices on the box's own Wi-Fi can
connect at all, so the rack screen needs no login and "coach" can simply mean "logged
in" ({doc}`../journal/apis`). Both were accepted trades, written down with the
condition that would end them.

The hosted service meets that condition. Anyone on the internet can reach it. So every
open route becomes open to everyone, and any login becomes a coach.

## What we chose

### 1. The coach creates every athlete — everywhere

Athletes never create themselves, in either shape. The roster stays in the coach's
hands, as it is today. A remote login does not change this: the coach creates the
athlete, then **invites** them, and the invite attaches a login to that existing
athlete record.

### 2. The gym stays account-free

At a rack in the gym, an athlete taps their name or their tag, lifts, and results show
on the room's shared screens — **published, arcade style**, the way a weight room's PR
board already works.

- No athlete logs in at a gym rack. Nobody types a password between sets.
- **The coach can hide one athlete, or the whole board**, from the shared screens.

### 3. Remote athletes: a session link plus a login

1. The coach starts the session and shares its link in the video call's chat.
2. The athlete opens it. The first time, they sign in with the login from their invite;
   after that the device remembers them.
3. They land straight on **their** rack screen for that session.

**The link says which session; the login says who you are.**

Remote athletes are not asked which rack they are at. Each is alone with their own
sensor, so **their device is the rack**. The server gives each athlete a rack slot of
their own when they join, and the rack screen, check-in and set lifecycle run exactly
as they do in the gym.

### 4. Two kinds of login

| | Coach | Athlete |
|---|---|---|
| Created by | the head coach | a coach, by invite |
| Roster, plans, sessions, settings | full control | **none** |
| Their own rack screen in a session they joined | — | yes |
| Published results of their program | yes | yes — **filtered to themselves by default**, one tap to see everyone |

**Within a program, results are not hidden from other athletes** — they are already on
the wall in the gym. The fence that matters is **between programs**, and that one is
structural ({doc}`databases`). The coach's hide setting applies online exactly as on
the wall, so the two can never disagree.

### 5. Setting up the coaches

The coach side is not new design — it is being ported from work Braydon did on the
team repository:

- **A one-time setup code** printed on the machine itself claims a new installation, so
  the first visitor to the site cannot make themselves the administrator.
- **No public sign-up.** The head coach creates the other coach logins, with a
  temporary password that must be changed at first sign-in, and can deactivate, promote
  or reset them.
- **The demo login refuses to exist** outside development. Its password is public.

On the hosted service the setup code is read by whoever operates the cluster, not from
a screen in a gym.

### 6. Athletes in more than one program

An athlete who trains with two programs — a school's gym box and a remote coach, say —
has an athlete record in each, in two databases ({doc}`databases`). For now that means
**a login per program**. Linking them under one sign-in is a separate, shared sign-in
service that sits above the installations, and it is future work.

The same athlete in **one** program that runs both a gym box and the hosted service is
not this case: that program has one database, copied between the two, so it is one
athlete record with one login.

## What we rejected, and why

**An open link where the athlete picks their name.** Fine on a closed network. On the
internet, anyone with the link can lift as anyone, and it writes into a real athlete's
history.

**Athlete logins at the gym rack.** They buy almost nothing — tapping a name or a tag
already answers "who is lifting" — and they cost forgotten passwords and a coach
resetting logins for a team.

**Athletes signing themselves up.** It would let the roster fill with records the
coach did not make, and it breaks the one rule that holds in both shapes.

**Keeping "coach means logged in".** The moment an athlete has a login, that rule gives
them full coach powers over the roster, plans and sessions. The check currently guards
34 endpoints; it must become "is a coach", and the rack's open routes must require an
athlete login **on the hosted service**.

## What it cost

- **A role split that must be complete before the first athlete login exists.** Adding
  athlete logins first and fixing permissions after is the order that ships a hole.
- **The open routes behave differently in the two shapes.** Open on the gym box, where
  the network guards them; authenticated on the hosted service. That difference must
  be a setting, tested in both positions — not two copies of the routes.
- **Remote athletes cannot use the gym's quick re-pick** or tag tap; the login replaces
  both.
