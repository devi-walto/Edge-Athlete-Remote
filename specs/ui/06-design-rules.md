# Feature Spec 6: Design rules for the coach interface

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started
- Form item: #11 (unified coach interface, added 2026-10-06)
- Depends on: nothing. **Specs 07, 08 and 09 all depend on this one**
- Mockup: every screen in [`mockups/coach-ui-final.html`](mockups/coach-ui-final.html).
  On the canvas, the **Final designs** page (boards named `F_*`) is the only one to build from
- Look adopted 2026-10-06: **solid surfaces** (rule 9). It replaced the earlier hairline look

## Why

The redesign fixed the coach app's structure — three states instead of eight tabs — but
left every screen looking equally loud: the same size, weight and colour for the thing
the coach is working on and for everything around it. Devin's words: "it can seem a
little busy even with the accordions… the colors fonts and sizing are all uniform even
for the selected section."

There is also a second reason. The local and hosted versions have to look and behave
alike before anything is published. That only holds if both are built from the same
few pieces and the same rules, written down once.

This spec is those rules, and the shared pieces that carry them. It changes how things
look. It changes nothing a button does.

## The rules

### 1. One thing per screen is in focus

Every screen has exactly one **focus card**: the thing the coach opened or is acting on.

| | Focus card | Everything else |
|---|---|---|
| Title | 24px, weight 850 | 14px, weight 650, grey `#c9d1d5` |
| Container | tinted panel `#121b14`, 1px lime border `#a9f04d` | a solid surface with its own border (rule 9) |
| Section label above | — | 10px uppercase, `#6f7c83` ("Other Training Blocks") |

A step the coach is not in collapses to a single thin row (26px outlined number, 14px
grey title). The step they are in gets a filled lime number, a 24px title and a 3px
lime rail down the left.

### 2. One lime button per screen

The single most likely next action is the filled lime button. Everything else is one of:

| Kind | Looks like | For |
|---|---|---|
| **Primary** | filled `#a9f04d`, dark text, weight 800 | the one next step |
| **Primary, next step** | the same, ending in a right arrow | a button that moves the coach to the next stage |
| **Solid** | filled `#151e23`, 1px border `#5c6a72`, 6px corner, white text, weight 800 | real but secondary actions |
| **Solid, key** | the same with a lime border, and an icon where one helps | the main secondary action of a screen (**Copy session link**) |
| **End** | transparent, 1px border `#ff646b`, text `#ff9aa0`, 6px corner | **every button that ends something**, in both versions |
| **Quiet** | text only, grey `#89969d` or white | row actions, Close, Cancel |
| **Quiet, lime** | lime text, weight 800, set off by a dashed divider | an action inside a dashed "waiting" row (**Send login link**) |

- Primary buttons also get the 6px corner.
- **Anything pressable must look pressable.** A secondary action that matters is a
  solid button, not bare text. (Devin's comments on "Import a roster" and "Save as a
  new Training Block".)
- **End training day is the End button on every screen, local and hosted** (Devin,
  2026-10-06). This replaces the earlier ruling that it was lime, so the strip no
  longer carries a second lime button.
- Other destructive row actions (Archive, Delete, Remove) stay quiet grey.

### 3. Nothing important is buried

- Visible without drilling: who is at risk, a sensor that stopped responding, whether a
  Training Program is scheduled, whether an athlete has a login.
- A row's actions are visible on the row. No "more" menus for things a coach does weekly.
- No developer text in the interface: no API paths, no "built from N requests", no raw
  timestamps, no "server-local".

### 4. One vocabulary

Use these words, capitalised, everywhere a coach reads:

**Training Block** (template) · **Training Program** (your copy, for one
group) · **Training Session** (a day on the calendar, or the day as run) ·
**Training Group** · **Roster** · **Administrator**.

Never "deploy" for block → program. Never "head coach" for the administrator flag.
Never "template" as the name of a thing (it describes a Training Block).

### 5. Two accent colours, each meaning one thing

- **Lime** — where you are, and what to press next.
- **Red** (`#ff646b`) — an athlete is **Behind**, or a button **ends** something.
  Nothing else is red.
- Mint and amber keep their existing jobs: velocity zones, sensor state, elapsed time.

### 6. What stays exactly as it is

Devin ruled these intentional. Do not "fix" them:

- **The session strip appears on all three states** while a day is running. It is a
  notification slot that currently shows a session (`SessionWidget.jsx` says so).
- **The header card on every tab** (the large title with a sentence under it).
- **The LIVE pill** is the live feed's connection status, not a session indicator.
- **The glass navbar** and its sliding pill.
- **The Room Layout button** and page. Restyling it is a later decision.

### 7. A row of tabs needs at least two tabs

A state with one sub-tab shows no tab row. SESSION has one (`room`), so its lone ROOM
tab goes. If a second is ever added, the row comes back by itself.

### 8. Local and hosted are one interface: features change, form does not

**The rule.** Hosted mode may **add or hide elements on a screen**. A screen both
versions have is one screen: it never gets a hosted copy, its own layout, its own
components or its own tokens. Every difference hangs off one switch, `useDeployment()`
(spec 05).

**Hosted-only screens exist where the Final designs page draws them** (loosened by Devin,
2026-10-14): **Send a login link**, the athlete's sign-in and home pages, and the
session-ended page. They may look slightly different and have their own nuances, but
they are built from the same components and tokens and **call the same code and logic**
as the rest of the app: the same routes, the same rules on the server, the same shared
functions. A hosted-only screen is never a second copy of behaviour that already exists.

Compared screen by screen on 2026-10-06 (the mockup's Remote page is drawn by starting
from the local screens; a dashed **REMOTE** tag marks each addition and is an
annotation, not part of the interface):

| Screen | When hosted |
|---|---|
| Design, Create a Training Program, scheduling, Add to the existing sessions | Identical |
| Groups | Identical |
| Analytics: Athlete, History, History by group, Notes | Identical |
| Session with nothing running, Quick Training Session | Identical |
| Sign in, first-run setup, Coaches, account menu (spec 01) | Identical, in both. Sign in adds an **Athlete sign in** link |
| Header | **Room Layout** is hidden: there is no room |
| Session strip | Adds **Copy session link**; the count reads "5 of 8 athletes joined" |
| Roster (`Roster`) | Adds a **Login** column, a **Sensor** column, a **No login yet** filter, and **Send login link** as the first row action |
| Session, running (`Main`) | A rack card is headed by the athlete, not a rack number. Adds a **Not joined yet** list under the room, each with **Send login link** |
| Calendar (`RemCalendar`) | A session that is set up adds **Copy session link** |
| Sensor badge on a rack card | Shows status only. Linking a sensor from the badge is hidden: a remote sensor attaches to its owner's rack on its own |
| Send a login link (`LoginLink`) | Hosted only |

**How to keep it true while building:**

- An addition is a column, a button, a filter, a badge or one list. If a hosted
  feature seems to need a new page, stop and bring it back as a design question.
- Additions are added to the shared component behind the switch, never to a copy of it.
  There is no `HostedRoster.jsx`.
- A hosted column must not push a local action off the row. The Roster keeps
  **Change groups**, **Open in Analytics** and **Archive** in both; login and sensor
  are two-line cells so the row still fits at 1180 px.
- The athlete's own screens are drawn on Final designs (the REMOTE flow, `F_Ath_*`).
  Lifting uses the **same `RackScreen.jsx`** as the gym, with what a remote athlete does
  not need stripped away (spec 04 Phase 3); it keeps the rack screen's own look. Home and
  the sign-in pages use the solid look (spec 10).

### 9. Solid surfaces, clear edges

Adopted by Devin on 2026-10-06 after comparing three versions on the canvas. His words:
solid foreground colours that give clear element boundaries; no excessive gradients;
the exception is a banner that announces something.

- **Every row, card and table sits on a solid surface**: `panel #10171b` with a 1px
  `line #263239` border. No see-through rows separated only by thin lines.
- **List rows are separate blocks** with a 6px gap between them. **A table is one
  surface**: a header row and its rows inside one border, divided by `line`.
- **Selected** is `panel2 #151e23` with a lime border (a rack card, a calendar day).
- **Waiting / not there yet** is a dashed `line` border with no fill (an athlete who
  has not joined).
- **Gradients and tints are for banners only**: the header card on each tab (rule 6)
  and the focus card. Nothing else is tinted.
- **Filter chips are solid**: `panel2` with a `line` border; the chosen one is filled
  white with dark text.
- **The top bar** is the bold one: "Edge Athlete" at weight 800 beside the signed-in
  coach's **profile image** on a lime rounded square. On the sign-in and first-run
  pages, where nobody is signed in, the square holds the letters "EA".
- **Administrator** is a pill badge: `admin-bg #1a2610`, lime border, text `#c6f78a`.
- **The Calendar has two views behind one List | Month switch** (a two-option segmented
  control, the chosen option filled white). **Month** is a grid of solid square day
  blocks: a planned session has a mint bar, the next one a lime border, a finished one
  is greyed, and a date shared by two programs names the second ("+ Receivers · Day 1").
  This replaces the old List / Cards text buttons.
- **Forms and dialogs** (sign in, first-run setup, send a login link) are a solid
  `panel` card with a 10px corner; inputs are `#0b1114` with a `line` border and a 6px
  corner. A dialog sits over a dimmed page.

## Tokens

From `react/src/theme.js` and `App.css` — existing values, unchanged:

`bg #070b0e` · `panel #10171b` · `panel2 #151e23` · `line #263239` · `ink #f5f7f2` ·
`muted #89969d` · `lime #a9f04d` · `mint #45dcb3` · `amber #ffb63e` · `coral #ff646b`.
Font: Inter.

New, added by this spec: `focus-bg #121b14` · `faint #6f7c83` · `soft-ink #c9d1d5` ·
`button-edge #5c6a72` · `risk-bg #170d0e` · `hero-bg #101a17` · `admin-bg #1a2610` ·
`radius-button 6px`. (`hairline #1b252a` and `outline #8d9aa1` from the first draft of
this spec are dropped: rule 9 uses `line` and `panel` instead.)

---

## Phase 0 — Tokens

Add the new tokens to `theme.js` and as CSS variables in `App.css`, beside the existing
ones. Use nothing yet.

**Done when:**

- [ ] The tokens exist in both places with matching values (a test compares them, as
      the navbar's stylesheet comment already asks for).
- [ ] The app looks exactly as before. Frontend suite and build pass.

**Stop. Devin reviews.**

## Phase 1 — The shared pieces

New folder `react/src/coach/ui/`, one small component per file, each opening with a
plain-language comment:

| Component | What it is |
|---|---|
| `FocusCard` | the tinted, lime-bordered panel with a label, a large title and an action area |
| `QuietRow` | a hairline row: name, meta, a slot for a badge, quiet actions |
| `SectionLabel` | the small grey uppercase label |
| `Step` | a numbered step, active or idle, plus `StepLink` for one that goes elsewhere |
| `Button` | `kind="primary" \| "next" \| "outline" \| "quiet"` — the only way to make a button on these screens |
| `Badge` | `scheduled` / `not-scheduled`, sensor on/off, rack state |
| `RiskTag` | the red "Behind 4/5" tag, and its small-triangle form |
| `Hero` | the existing header card, extracted unchanged |

Build them against the mockup, each with a render test. Use them nowhere yet.

**Done when:**

- [ ] Each component has a render test for every variant.
- [ ] `Button` refuses an unknown `kind` in development.
- [ ] Buttons and row actions are at least 44px tall (touch targets on a tablet).
- [ ] Text meets 4.5:1 contrast on its background — in particular grey text on the
      focus card and on the risk background.
- [ ] Nothing else in the app changed.

**Stop. Devin reviews.**

## Phase 2 — The sub-tab rule, and the leftovers

- The sub-tab row renders only when the state has two or more tabs.
- Remove from the interface: the API paths printed on Room Layout, "built from N
  requests" in group history, raw ISO timestamps in report rows, the stale "deploy one
  from the Workouts tab" on the empty Calendar. (Each is also listed in the spec that
  owns its screen; do them here if those specs have not started.)
- Delete `react/src/coachTabs.js` if nothing imports it. On 2026-10-06 nothing did.

**Done when:**

- [ ] *(Frontend test)* SESSION renders no tab row; PLANNING and ANALYTICS render theirs.
- [ ] A test fails if the coach bundle's source contains `/api/` in visible text or the
      phrase "server-local".
- [ ] *(Browser)* All three states still work.

---

## Acceptance criteria

- [ ] Every coach screen has one focus card and at most one lime button.
- [ ] No row, card or table is drawn without a solid surface and a border; only banners
      and the focus card are tinted.
- [ ] Every button that ends something uses the End style, in both deployments.
- [ ] Every pressable thing is a `Button`.
- [ ] The six vocabulary terms are used consistently; "deploy" and "head coach" (for
      the flag) appear nowhere a coach reads.
- [ ] Red appears only on **Behind** and on End buttons.
- [ ] The strip, header cards, LIVE pill and navbar are unchanged.
- [ ] No component, page or stylesheet exists only for hosted mode, apart from the
      login-link dialog. Every hosted difference is reached through `useDeployment()`.
- [ ] With the switch set to gym box, every screen renders exactly as before the
      hosted additions were written (render tests run in both modes).

## Risks

| Risk | What reduces it |
|---|---|
| The rules drift as screens are rebuilt one at a time | Specs 07–09 may only use the Phase 1 components for buttons, rows and focus cards |
| A restyle quietly changes behaviour | This spec has no behaviour change at all; any is a bug |
| "One lime button" hides something that used to be obvious | Rule 3 wins over rule 2: if a coach needs it weekly, it is an outline button on the row, never a menu |

## Docs to update when done

`docs/journal/coach-tablet.md` — a short section on the focus rule: what forced it
(everything read as equally loud), what was rejected (colour-coding sections; hiding
actions behind menus), what it cost.
