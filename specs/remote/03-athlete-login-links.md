# Feature Spec 3: Athlete login links

- Owner: Devin Walton
- Date: 2026-10-06
- Status: **Built 2026-10-18** (Phases 0–4) on `feature-login_links`; browser checks still
  to do. Coach login codes (once Phase 5 here) moved to spec 11, Phase 4
- Form item: Definition of Done #4
- Depends on: [02 Roles](02-roles.md) (must be merged first), [05 Hosted mode](05-hosted-mode.md)
- Mockup: `F_Remote_Roster`, `F_Remote_LoginLink` and the REMOTE flow on the canvas's Final
  designs page. Coach login codes (now spec 11, Phase 4): **approved 2026-10-07**, on the Final designs page
  ("The same in both: accounts and access"): `F_Coaches` (the code in the same dialog an
  athlete login link uses, with the link icon on **Copy code**; Invited and Reset rows),
  `F_SignIn` ("I have a login code"), `F_CodeNewCoach`, `F_CodeReset`

## Why

A remote athlete has to prove who they are, because on the internet the session link
alone would let anyone lift as anyone. Athletes never create themselves, so the login
has to be attached to the athlete record the coach already made — by something only
that athlete received.

## User story

As a coach, I want one button that gets an athlete signed in — the first time, and
again if they forget — without collecting emails or resetting passwords by hand.

As an athlete, I want to open a link, pick a username and password once, and after
that just sign in.

## Decisions this spec locks in

- **One button on the roster: Send login link.** First sign-in and "I forgot" are the
  same action.
- **The link is personal.** Its page shows **only that athlete's name** — "Hi Jake
  Smith, choose a username and password". No roster, no list of names, ever, before
  sign-in.
- **A link replaces the login, never the data.** The athlete record, sets, maxes and
  reports are untouched. Only the credentials change.
- **A link is treated like a password:**
  - works once;
  - expires after **3 days**;
  - a new link cancels any older unused one;
  - using a link signs the old login out everywhere;
  - the server stores only a one-way hash of it.
- **After that it is username and password.** Devices stay signed in for **30 days**.
  A new link is needed only for a forgotten password.
- **The coach is the recovery path.** No email recovery, no email collected.
- **Rejected:** an "invite the whole group" button (unnecessary — the session link plus
  membership admits the right people); claiming an athlete through the session link
  (that is picking your name, in public).

## What exists (after specs 01, 02, 05)

- `Athlete.user`, `role_of()`, `IsCoach`, `IsAthlete`.
- Braydon's setup code (`coach_auth.py`): the model for this feature. It stores a hash
  with `make_password`, checks it with `check_password`, has an expiry, and is cleared
  on use. **Reuse the pattern; do not copy the table.**
- `CoachTokenObtainPairSerializer` — the sign-in serializer to extend for token lifetime.
- `is_hosted()` and `useDeployment()`.

## Scope

- A table of login links and the service that issues, cancels and redeems them.
- Coach endpoints: issue, cancel, unlink; link status on the roster.
- Public endpoints: look up a link (returns one name), redeem a link.
- A 30-day refresh lifetime for athlete logins.
- Coach interface: status and **Send login link** on the roster, and the dialog that
  shows the link once.
- Athlete pages: redeem a link; sign in.

## Non-goals

- The athlete's rack screen and what they see after signing in (spec 04 and the athlete
  screens, not yet designed).
- One login across several programs (future; `docs/remote/access.md`).
- Sending the link for the coach. The coach copies it and sends it themselves.

---

## Phase 0 — The table and the service

`AthleteLoginLink` (migration `0027`):

| Field | Notes |
|---|---|
| `athlete` | FK, cascade |
| `token_hash` | `make_password` of the token. **The token itself is never stored** |
| `lookup` | a short random public id, so a link can be found without scanning every hash |
| `created_by` | the coach, `SET_NULL` |
| `created_at`, `expires_at` | expiry = created + 3 days |
| `used_at`, `cancelled_at` | null until it happens |

`services/login_links.py`:

- `issue(athlete, coach)` → cancels any unused link for that athlete, creates one,
  returns the **plain token once**.
- `find(lookup, token)` → the link if it is unused, uncancelled, unexpired and the
  token checks; otherwise `None`. **One answer for every failure**, so a caller cannot
  tell "expired" from "never existed".
- `redeem(link, username, password)` → in one transaction: if the athlete already has a
  login, set it inactive and detach it; create a new login; attach it; mark the link
  used. Deactivating the old login is what signs it out everywhere — the JWT layer
  already refuses inactive users, so no token blacklist is needed.
- `unlink(athlete)` → deactivate and detach the login; cancel any unused link.

**Done when:**

- [ ] Issuing twice leaves exactly one usable link; the first token no longer works.
- [ ] `find` returns `None` for: a wrong token, an expired link, a used link, a
      cancelled link, an unknown lookup — and the five are indistinguishable.
- [ ] The plain token appears nowhere in the database after `issue`.
- [ ] `redeem` on an athlete with an existing login: the old login is inactive, a token
      issued to it before now gets `401`, the new login works, and the athlete's sets
      and reps are byte-for-byte unchanged.
- [ ] `redeem` is all-or-nothing: a failure part way leaves the old login working and
      the link unused.
- [ ] A redeemed login has role `athlete` (spec 02) and no coach profile.

**Stop. Devin reviews.**

## Phase 1 — The coach endpoints

| Route | Who | Does |
|---|---|---|
| `POST /api/athletes/{id}/login-link/` | coach | issues; returns `{link, expires_at}` — the only time the link is shown |
| `DELETE /api/athletes/{id}/login-link/` | coach | cancels the unused link |
| `DELETE /api/athletes/{id}/login/` | coach | unlinks the login |

The athlete list (`GET /api/athletes/`) adds, for coaches only: `login_status`
(`none` · `link_sent` · `linked`), `login_username`, `link_expires_at`.

The full link is built from the request's own address
(`https://<this installation>/login-link#<lookup>.<token>`), so it is right on every
installation without configuration.

**The link goes after a `#`, not a `/`** (Devin, 2026-10-17). A browser never sends
the part after `#` to the server: it stays on the athlete's phone, and the page reads
it and sends it inside the request body (Phase 2). So the secret never appears in
Traefik's or nginx's request logs, and is never passed on to another site in the
page's address.

**Done when:**

- [ ] All three routes refuse an athlete (`403`) and no login (`401`).
- [ ] Issuing for an archived athlete is refused.
- [ ] The athlete list never includes a token or a hash.
- [ ] `login_status` is right in each of the three states, and `link_sent` becomes
      `none` once the link expires.
- [ ] On a gym box (`EA_DEPLOYMENT=local`) the routes exist but the roster does not
      show them (Phase 3); the tests still pass in both modes.

**Stop. Devin reviews.**

## Phase 2 — Redeeming a link, and signing in

| Route | Who | Does |
|---|---|---|
| `POST /api/auth/login-link/lookup/` `{link}` | open | `{athlete_name}` or `404` |
| `POST /api/auth/login-link/redeem/` `{link, username, password}` | open | creates the login; returns tokens |

- Both are rate-limited (a handful per minute per address).
- Password goes through Django's validators; username through the same check Braydon's
  coach creation uses (unique, case-insensitive).
- Sign-in is the existing endpoint. The serializer gives an athlete a **30-day** refresh
  token and a coach the existing 7 days.
- These two routes are the only new open ones. Add them to spec 05's allow-list on purpose.

**Done when:**

- [ ] `lookup` returns only the one athlete's name, and `404` for anything invalid.
- [ ] A link redeemed once cannot be redeemed again.
- [ ] A weak password and a taken username are refused with a message, and the link
      stays usable.
- [ ] After redeeming, signing in with the new username and password works; the refresh
      token is valid 30 days.
- [ ] Repeated bad attempts get `429`.
- [ ] No response in this phase ever contains another athlete's name.

**Stop. Devin reviews.**

## Phase 3 — The coach interface

On the Roster (spec 07 builds the tab; if it does not exist yet, add this to the
existing roster in PLANNING → Groups), **only when `useDeployment()` says hosted**:

- A **Remote login** column: *Linked* with the username · *Link sent* with its expiry ·
  *No login yet*.
- **Send login link** on each row (the lime button on a row with no login, a quiet one
  otherwise), and **Unlink**.
- The dialog: the link with **Copy link**; "Works once · Expires <date> · Earlier links
  cancelled"; the warning **"Don't post this in a group chat. Whoever opens it becomes
  <name>."**; **Cancel this link**; **Done**.
- The same shortcut on SESSION's "Not joined yet" list (spec 04).

**Done when:**

- [ ] *(Frontend test)* The column and buttons are absent on a gym box and present when hosted.
- [ ] *(Frontend test)* The link is rendered once and is not kept in state after the dialog closes.
- [ ] *(Browser)* Send, copy, cancel and unlink each update the row's status without a reload.

**Stop. Devin reviews.**

## Phase 4 — The athlete's two pages

Mockups `F_Ath_R1` (login link), `F_Ath_R1b` (a link that no longer works) and
`F_Ath_R2` (sign in), on the canvas's Final designs page, REMOTE flow.

- `/login-link#<link>`: reads the link from after the `#`, calls `lookup`; shows "Hi <name>"; username, password, password
  again; **Create my login**. An invalid link shows one message for every cause: "This
  link doesn't work any more. Ask your coach for a new one."
- `/athlete`: username and password; a line under it — "Forgot it? Ask your coach for a
  new login link." The coach sign-in page links here ("Athlete? …").
- Both use the solid look (spec 06 rule 9), sized for a phone. After either, the
  athlete lands on a placeholder ("You're signed in. Open the session link your coach
  sent.") until [spec 10](10-athlete-pages.md) replaces it with the home page.

**Done when:**

- [ ] *(Browser)* The whole path works: coach sends a link → athlete opens it in a
      private window → sets a login → signs out → signs in again.
- [ ] *(Browser)* Sending a second link after that, and using it, makes the first login
      stop working and keeps the athlete's history.
- [ ] *(Browser)* Neither page shows any name but the athlete's own.

### Built (Phases 0–4, 2026-10-17/18)

- **Phase 0:** `AthleteLoginLink` (migration `0027`), `services/login_links.py`. A link is
  `<lookup>.<secret>`: the lookup finds the row, the secret is stored only as a hash.
  Using a link switches the old login off **and renames it** (`<name>~replaced-<id>`) so
  the athlete can keep their username; an archived athlete's link stops working.
- **Phase 1:** the coach routes, in `athlete_logins.py`; the link is built from the
  request's own address, after a `#`.
- **Phase 2:** the athlete routes. A bad link answers `404`, which also counts toward
  the wrong-attempt limit (`LimitWrongAttempts.counted_statuses`), so links can't be
  guessed freely. Usernames ignore capitals. An athlete's sign-in lasts 30 days on
  sign-in, link and renewal (`ATHLETE_SIGN_IN_LIFETIME`); a coach keeps 7.
- **Phase 3:** the roster has no Roster tab yet (spec 07 builds it), so the Login
  column, Send login link / Send new link / Unlink and the dialog went on the existing
  roster table in PLANNING → Groups (Devin, 2026-10-18: build with what exists; the
  server side is already what the redesign needs). Remote only.
- **Phase 4:** `/login-link#…` (read, then wiped from the address bar) and `/athlete`.
  **The screens had never renewed a sign-in**, so the 30 days would have been 8 hours
  in practice: an athlete's renewal token is now kept and used
  (`athlete/athleteAuth.js`, `freshAthleteToken()`). Coaches are unchanged. The coach
  sign-in page links to the athlete one on a remote school.
- **Not yet:** the browser checks in Phases 3 and 4 (no browser in the build session),
  and the "Send login link" shortcut on SESSION's "Not joined yet" list (that list is
  spec 04, Phase 4).

---

## Coach login codes: moved to spec 11

Moved 2026-10-18 (Devin): coach login codes are built as the **last phase of the coach
interface redesign**, [spec 11, Phase 4](../ui/11-mine-first.md), not here. They change
the Coaches page and coach sign-in, which the redesign rebuilds anyway, and they are not
needed for Definition of Done #4. This spec is complete without them.

---

## Acceptance criteria

- [ ] A coach can get an athlete signed in, and re-signed-in, with one button.
- [ ] A link works once, expires, is cancelled by a newer one, and is never stored readable.
- [ ] Using a link ends the old login's access everywhere.
- [ ] Training data is never changed by any of this.
- [ ] No athlete's name is visible to someone who is not signed in, except their own on
      their own link.
- [ ] A gym box shows none of it and loses nothing.

## Risks

| Risk | What reduces it |
|---|---|
| A coach posts a login link in a group chat | The warning in the dialog; single use and a 3-day expiry limit the damage; Unlink fixes a wrong claim |
| Someone guesses links | A long random token, a hash at rest, and rate limits on lookup and redeem |
| An athlete login becomes a coach for a moment during creation | Spec 02 is refused-by-default, and `redeem` is one transaction |

## Docs to update when done

`docs/remote/access.md` section 4 becomes a description of the code.
`docs/journal/apis.md` route table (regenerate). `docs/journal/coach-tablet.md` — the
roster's new column.
