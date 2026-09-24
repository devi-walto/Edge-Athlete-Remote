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
athlete, and the athlete's login is attached to that existing record through a
**login link** the coach sends (below).

### 2. The gym stays account-free

At a rack in the gym, an athlete taps their name or their tag, lifts, and results show
on the room's shared screens — **published, arcade style**, the way a weight room's PR
board already works.

- No athlete logs in at a gym rack. Nobody types a password between sets.
- **The coach can hide one athlete, or the whole board**, from the shared screens.

### 3. Remote athletes: the session link is the whole flow

1. The coach starts the session and shares its link — in the video call's chat is fine.
2. The athlete opens it. Their device is already signed in (or they sign in once).
3. **The server lets them in only if their login is linked to an athlete who is in one
   of the training groups taking part in that session.** Everyone else is turned away,
   logged in or not.
4. They land straight on **their** rack screen for that session.

**The link says which session; the login says who you are; the group says whether you
belong there.** The last check needs no new data: a session already lists the programs
running in it, and each program belongs to a training group.

Remote athletes are not asked which rack they are at. Each is alone with their own
sensor, so **their device is the rack**. The server gives each athlete a rack slot of
their own when they join, so two athletes can never land on the same one, and the rack
screen, check-in and set lifecycle run exactly as they do in the gym.

### 4. Login links: first sign-in and "I forgot" are the same button

Each athlete on the coach's roster has one button: **Send login link.**

- The coach sends the link **to that athlete, directly** — a text or a direct message.
- The athlete opens it and sets a username and password. That login is now linked to
  their athlete record.
- **Forgot it? The coach presses the same button again.** Opening the new link sets a
  new username and password on the same athlete.

**A link replaces the login, never the data.** The athlete record, every set, max and
report stays exactly where it was; only the credentials change. So resending is always
safe, and there is no state a login can get stuck in that another link does not fix.

Whoever opens a login link **becomes** that athlete, so a link is treated like a
password:

- **Single use, and it expires** after a few days. The coach can always send another.
- **A new link cancels any older unused one.**
- **Using a link signs the old login out everywhere** — if an old password leaked, the
  reset locks the other person out.
- **The server stores only a one-way hash of the link**, never the link itself — the
  same treatment as the setup code below — so a database leak hands out nothing usable.
- **The coach sees each athlete's state:** not linked, link sent (expires on a date),
  or linked — and can **unlink**, if the wrong person claimed it.

:::{warning}
**Two links, two rules.** The **session link** is not a secret — it only works for
athletes who are already linked and in the session's groups — so a group chat is fine.
A **login link** is personal. Posted in a group chat, anyone in that chat can claim
that athlete. The coach screen says so beside the button.
:::

### 5. Two kinds of login

| | Coach | Athlete |
|---|---|---|
| Created by | the head coach | a coach creates the athlete; the athlete sets the login from a login link |
| Roster, plans, sessions, settings | full control | **none** |
| Their own rack screen, in a session their group is in | — | yes |
| Published results of their program | yes | yes — **filtered to themselves by default**, one tap to see everyone |

**Within a program, results are not hidden from other athletes** — they are already on
the wall in the gym. The fence that matters is **between programs**, and that one is
structural ({doc}`databases`). The coach's hide setting applies online exactly as on
the wall, so the two can never disagree.

### 6. Setting up the coaches

The coach side is not new design — it is being ported from work Braydon did on the
team repository:

- **A one-time setup code** printed on the machine itself claims a new installation, so
  the first visitor to the site cannot make themselves the administrator.
- **No public sign-up.** The head coach creates the other coach logins, with a
  temporary password that must be changed at first sign-in, and can deactivate, promote
  or reset them.
- **The well-known demo login refuses to exist** outside development. Its password is in
  the repository.

On the hosted service the setup code is read by whoever operates the cluster, not from
a screen in a gym.

### 7. The demo is its own installation

Faculty and staff need something to click through. That is a **separate demo
installation** ({doc}`databases`): its own address, its own database, a fictional
program full of fake athletes and history, and a coach login with a password that is
**not** the one in the repository — shared only with the people being shown.

It has to be separate, not a fake program inside the real installation. **Coach logins
do not wall off data inside one installation** — an account says who is coaching, not
what they may see — so a demo coach inside the real installation would see real
athletes. In its own installation it can see only fake ones.

### 8. Athletes in more than one program

An athlete who trains with two programs — a school's gym box and a remote coach, say —
has an athlete record in each, in two databases ({doc}`databases`). For now that means
**a login per program**. Linking them under one sign-in is a separate, shared sign-in
service that sits above the installations, and it is future work.

The same athlete in **one** program that runs both a gym box and the hosted service is
not this case: that program's athletes exist on both sides from the first copy, so it
is one athlete, with one login, on the hosted side.

## What we rejected, and why

**An open link where the athlete picks their name.** Fine on a closed network. On the
internet, anyone with the link can lift as anyone, and it writes into a real athlete's
history.

**Linking a login to an athlete through the session link.** The session link is shared
with a whole group, so claiming an athlete through it is the pick-your-name problem
again. Linking needs something only that athlete received.

**An "invite the whole group" button.** Unnecessary: once athletes are linked, the
session link plus group membership already admits exactly the right people, every
session.

**Password recovery by email.** It would mean collecting and verifying an email for
every athlete, for a recovery path the coach already provides.

**Athlete logins at the gym rack.** They buy almost nothing — tapping a name or a tag
already answers "who is lifting" — and they cost forgotten passwords and a coach
resetting logins for a team.

**Athletes signing themselves up.** It would let the roster fill with records the
coach did not make, and it breaks the one rule that holds in both shapes.

**Keeping "coach means logged in".** The moment an athlete has a login, that rule gives
them full coach powers over the roster, plans and sessions. The check currently guards
34 endpoints; it must become "is a coach", and the rack's open routes must require an
athlete login **on the hosted service**.

**Demo logins inside the real installation.** See section 7.

## What it cost

- **A role split that must be complete before the first athlete login exists.** Adding
  athlete logins first and fixing permissions after is the order that ships a hole.
- **The open routes behave differently in the two shapes.** Open on the gym box, where
  the network guards them; authenticated on the hosted service. That difference must
  be a setting, tested in both positions — not two copies of the routes.
- **The coach is the only recovery path.** An athlete who forgets their login waits for
  their coach. With devices staying signed in, that should be rare.
- **Removing an athlete from a group removes their remote access** to that group's
  sessions — group membership is current-state only. That is the intended behaviour,
  and it is worth a line in the coach screen.
