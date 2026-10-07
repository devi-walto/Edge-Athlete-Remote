# Feature Spec 3: Athlete login links, and coach login codes

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started. Phase 5 (coach login codes) added 2026-10-06
- Form item: Definition of Done #4
- Depends on: [02 Roles](02-roles.md) (must be merged first), [05 Hosted mode](05-hosted-mode.md)
- Mockup: `F_Remote_Roster`, `F_Remote_LoginLink` and the REMOTE flow on the canvas's Final
  designs page. Phase 5 (coach login codes): proposed 2026-10-06 on the **Remote coach view**
  page, top row: `C1_CoachesCodes`, `C2_SignInCode`, `C3_CodeNewCoach`, `C4_CodeReset`.
  **Not approved yet**

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
(`https://<this installation>/login-link/<lookup>.<token>`), so it is right on every
installation without configuration.

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

- `/login-link/<link>`: calls `lookup`; shows "Hi <name>"; username, password, password
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

---

## Phase 5 — Coach login codes (replaces temporary passwords)

Added 2026-10-06 by Devin's decision. **This phase is for both deployments**, `local`
and `remote`; unlike the athlete phases above it does not depend on spec 05.

**Why.** Spec 01 brought in Braydon's way of adding a coach: the administrator types a
username, the system makes a temporary password, the administrator hands both over, and
the coach is forced to change the password at first sign-in. It works, and it has three
weaknesses:

- the administrator chooses the coach's username and, briefly, knows their password;
- **a temporary password never expires**, so a login that was made and never used sits
  there with a password someone else knows;
- it is a third way of getting somebody in, beside the setup code (first
  administrator) and the login link (athletes).

A coach login code makes it the same idea as the other two: **a one-time, expiring code
that lets the person choose their own username and password.** It is a typed code and
not a link, so it works on a gym box with no internet: the administrator reads it out.

| | Today (spec 01) | After this phase |
|---|---|---|
| New coach | Administrator picks the username; temporary password; forced change | Administrator gets a **login code**; the coach enters it and picks their own username and password |
| Forgotten password | Reset → temporary password → forced change | Reset → **login code** tied to that coach → they pick a new password. Same username, same login |
| Expires | Never | 3 days, and works once |
| Server lock while a change is due | `403 password_change_required` on every coach route | Not needed: there is no half-finished login |

**What the code is.** Eight characters from the setup code's alphabet (no `0`, `O`,
`1`, `I`, `L`), typed however the person likes: case, spaces and dashes are ignored.
Reuse `normalize_setup_code` and the alphabet from `coach_auth.py`.

**Data.** `CoachLoginCode`:

| Field | Notes |
|---|---|
| `user` | FK to the login, nullable. **Set for a reset. Empty for a new coach**, whose login does not exist until the code is used |
| `label` | Who a new-coach code is for ("Maria Reyes"). Shown on the Coaches page until the code is used. Empty for a reset |
| `code_hash` | `make_password` of the code. The code itself is never stored |
| `created_by` | the administrator, `SET_NULL` |
| `created_at`, `expires_at` | expiry = created + 3 days |
| `used_at`, `cancelled_at` | null until it happens |

The hashing, expiry, single-use and "one answer for every failure" rules are the ones
`services/login_links.py` already has from Phase 0. Put the shared part in one place
and use it for both; do not write it twice. A typed code has no public lookup id, so
`find` checks the code against the unused, unexpired rows; keep that set small by
cancelling a coach's older reset code when a new one is issued and by refusing more
than twenty outstanding new-coach codes.

**Coaches already live in the database, and their links must survive.** A coach login
is a row in the same PostgreSQL database as everything else (Django's own `auth_user`
table), with a `CoachProfile` beside it. Two things point at that row:

- `TrainingGroupCoach` — which coaches run which training group, as head or assistant.
  A label, never a permission.
- `TrainingBlock.coach` — who made a training block.

Both refuse to let the login be deleted. So:

- **A reset never creates a new login.** It sets a new password on the same row; every
  group and block still points at the same coach.
- **A new coach has no row until they use their code.** They cannot be put on a
  training group before that. The Coaches page shows them as "Invited", by label.
- **Deactivating is still never deleting.** Unchanged from spec 01.

**Routes.**

- `POST /api/coaches/invite/` `{label}` — administrator only. Returns the code **once**.
- `POST /api/coaches/{id}/reset/` — administrator only. Now returns a code tied to that
  coach, not a temporary password. Their current password keeps working until the code
  is used, so a reset pressed on the wrong row locks nobody out.
- `DELETE /api/coaches/codes/{id}/` — administrator only. Cancels an unused code.
- `GET /api/coaches/` — also lists unused new-coach codes: label, when they expire.
- `POST /api/auth/code/check/` `{code}` — open. `{kind: "new"}` or
  `{kind: "reset", username}`, or one `400` for every kind of bad code.
- `POST /api/auth/code/` `{code, username?, password}` — open. New: creates the login
  with a coach profile, not an administrator. Reset: sets the password on that login.
  Either way the code is spent and the reply is the same tokens signing in gives.
- Add both open routes to the sign-in rate limit in `nginx.conf`.

**Screens** (built in the look of the sign-in card; no new board is needed for the
card, but draw the Coaches page's "Invited" rows on the Final designs page first):

- **Coaches:** **Add coach** asks for a name, then shows the code in the same bordered
  card the temporary password uses today, with "Pass it on now. It cannot be shown
  again. It works once and expires in 3 days." Unused codes show as rows: the label,
  "Invited · expires Oct 9", and **Cancel**. **Reset password** shows a code the same way.
- **Sign in:** one quiet line under the form, "Have a login code?", opening a card that
  asks for the code. A new coach is then asked for a username and a password twice; a
  coach resetting sees their username and is asked only for the password.

**Removed in this phase:** temporary passwords and everything that existed only for
them — `CoachProfile.must_change_password` (a migration drops it),
`refuse_while_password_change_due` and its three call sites in `permissions.py`, the
`must_change_password` field in the sign-in and "who am I" replies, and the forced mode
of `ChangePassword.jsx`. **Changing your own password from the account menu stays.**

**The one case nobody on the website can fix** is a sole administrator who forgets
their own password. That is deliberate, the same rule as `setup_code` and `make_admin`:
it takes the machine. Django's own command does it, and the docs must say so:
`docker compose exec django python manage.py changepassword <username>`.

**Done when:**

- [ ] A new-coach code creates one login with the username and password the coach
      chose, a coach profile, and no administrator flag.
- [ ] A reset code changes the password of the coach it was issued for and nobody
      else's; their username, their id, their training groups and their training
      blocks are unchanged.
- [ ] A coach's old password works until their reset code is used, and stops then.
- [ ] A wrong code, an expired code, a used code and a cancelled code get the same
      answer from both open routes.
- [ ] A code cannot be used twice; two requests racing to use one create one login.
- [ ] Issuing a second reset code for a coach makes the first stop working.
- [ ] The code is nowhere in the database or the logs after it is issued.
- [ ] A regular coach gets `403` from invite, reset and cancel.
- [ ] A new-coach code can never produce an administrator, and cannot take a username
      that exists.
- [ ] After the migration no login is on a temporary password: every login that had
      `must_change_password` set is given a reset code instead (printed by the
      migration's management command, not stored), or the migration refuses to run
      until none are left. **Decide which before building.**
- [ ] `must_change_password` appears nowhere in the code base, and the spec 01 tests
      for the temporary-password lock are replaced, not just deleted.
- [ ] *(Browser)* Add a coach → read the code → "Have a login code?" → choose a
      username and password → the workspace opens. On a gym box with no internet.
- [ ] *(Browser)* Reset a coach → they use the code → same username, new password,
      still listed on their training groups.
- [ ] `changepassword` is documented beside `setup_code` and `make_admin`.

**Stop. Devin reviews.**

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
