<!--
this page — who gets a login, how a remote athlete gets to their own rack, and
what each kind of login can do.

The local install's rules were written for a closed network, and the journal
said so (journal/apis: "if this ever runs on a network that is not private, this
is the first decision to revisit"). This page is that revisit. The local install
stays exactly as it was; logins only appear where the internet makes them
necessary.
-->

# Access

*Oct 5 – Oct 20, 2026 · specs 01, 03, 05*

## Tool changes at a glance

| Job | Local install | Remote server | Where it lives |
|---|---|---|---|
| Who's a coach | anyone logged in | **a login attached to a coach profile** (no stored role) | {doc}`../../../handbook/reference/api` |
| Athlete logins | none | **login links** a coach sends | `AthleteLoginLink` |
| One-time secrets (setup code, login links, sensor codes) | — | **one shared file** that makes, hashes and checks all of them | `services/one_time_secrets.py` |
| Sign-in limit | nginx: 10 sign-in tries a minute | **Django**, remote only: 10 *wrong* tries a minute per address | `coach_auth.py` |
| Staying signed in | 8-hour sign-in, never renewed | **simplejwt refresh tokens**: athletes 30 days, coaches 7 | `coach_auth.py`, `settings.py` |

:::{warning}
**Making a new one-time secret? Use `one_time_secrets.py`.** Before it, each secret made, hashed and checked itself its own way. Now there's one set of rules: only a hash is stored, it works once, a newer one cancels the older one, and every kind of failure gives the same answer. A fix there reaches all of them.
:::

## The problem

In the gym, **the network is the lock.** Only devices on the base station's Wi-Fi can connect, so the rack screen needs no login, and "coach" can just mean "logged in."

Online, anyone on the internet can reach the server. Every open route is open to everyone. And the moment an athlete has a login, "logged in" stops meaning "coach."

So I needed three things: athletes who can only be themselves, coaches who can't be faked, and a remote athlete who lands on their own rack without picking anything.

## Try 1: the gym rules, as is

No login at the rack. Tap your name, lift. Any login is a coach.

**What worked:** in the gym, it's perfect. Nobody types a password between sets, and the results go up on the room's screens like a PR board. **The local install still works this way.**

**Why I moved on:** online, anyone with the address could lift as anyone, and it writes into a real athlete's history. And an athlete login would get full coach powers over the roster, plans and sessions. That check guarded 32 endpoints.

## Try 2: a session link where the athlete picks their name

The coach shares one link in the video call's chat. The athlete opens it and picks themselves.

**What worked:** one link for the whole group. That part stayed.

**Why I moved on:** it's Try 1 again with an extra step. Whoever has the link can pick any name. Linking a login *through* the session link has the same hole: it's shared with a whole group, so it can't prove who you are.

## Where I landed: two links, two jobs

**The login link says who you are.** Every athlete on the coach's roster has one button: **Send login link.** The coach sends it to that athlete directly, by text or DM. The athlete opens it and sets a username and password. Forgot it? The coach presses the same button again.

A link replaces the login, never the data. Every set, max and report stays where it was, so resending is always safe. Since whoever opens it *becomes* that athlete, it's treated like a password:

- **Single use, 3 days.** A newer link cancels an older one.
- **The secret goes after a `#`** (`https://<school>/login-link#<lookup>.<secret>`). Browsers never send that part to the server, so it never shows up in a request log, and the page wipes it from the address bar once read.
- **Using a link signs the old login out everywhere.** If an old password leaked, the reset locks the other person out.
- **The coach sees each athlete's state** (not linked, link sent, linked) and can unlink if the wrong person claimed it.

**The session link says which session.** It isn't a secret. The server only lets you in if your login is linked to an athlete who's on that session's roster, or in a training group that's part of it. Everyone else is turned away, logged in or not.

:::{warning}
**Two links, two rules.** A session link is fine in a group chat. A login link is personal: posted in a group chat, anyone in it can claim that athlete. The coach screen says so beside the button.
:::

**Once they're in, the server makes them a rack.** That's its own page: {doc}`virtual-racks`.

**What an online athlete sees.** Only themselves, in the live room. Their program's results are open to them, filtered to themselves by default, the same as the wall in the gym. The wall that matters is *between* programs, and that one is a separate database per school ({doc}`databases`).

## How the server tells logins apart

Nothing stores a role. A login attached to a coach profile is a coach. With the staff flag on, an administrator. A login attached to an athlete record is an athlete. A login attached to neither, or both, is refused everywhere, including at sign-in. Archiving an athlete switches their login off at once and keeps their history.

The coach side is work Braydon did on the team repository, brought in and built the same way for both installs:

- **One coach role.** Every coach can do everything. "Head coach" is only a label on a training group.
- **One administrator flag.** It does one thing: create, reset, switch off and promote coach logins. There's always at least one.
- **A one-time setup code** printed on the machine claims a new install, so the first visitor can't make themselves the administrator. Online, I hand the code to the school's coach.
- **No public sign-up.** The well-known demo login refuses to exist outside development, since its password is in the repo.

**The demo is its own school**, with its own database and fake athletes. A demo coach inside a real school would see real athletes, because a coach login says who's coaching, not what they can see.

## Things I passed on

- **Password recovery by email.** I'd have to collect and verify an email for every athlete, for a recovery path the coach already has.
- **Athletes signing themselves up.** The roster would fill with records the coach didn't make.
- **Athlete logins at the gym rack.** Tapping a name already answers "who's lifting," and logins cost forgotten passwords between sets.
- **An "invite the whole group" button.** Once athletes are linked, the session link plus their group already lets in exactly the right people.
- **The login link's secret in the path** (`/login-link/<secret>`). Every request log on the way would record it.
- **Deleting the old login when a new link is used.** Rows that record who made a training block point at it. It's switched off and renamed out of the way instead.

## What it cost

- **The coach is the only recovery path.** An athlete who forgets their login waits for their coach. With 30-day sign-ins, that should be rare.
- **The open routes behave differently on the two installs**: open on the local install, signed-in online. That's one setting tested both ways in CI, never two copies of the routes.
- **Removing an athlete from a group removes their remote access** to that group's sessions. That's on purpose.
- **An athlete in two programs has two logins** for now. One sign-in across programs is future work.
