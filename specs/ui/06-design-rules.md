# Feature Spec 6: Design rules for the coach interface

- Owner: Devin Walton
- Date: 2026-10-06
- Status: **Done** 2026-11-11, all four phases (pull request #21). The acceptance criteria
  below come true screen by screen as specs 07–10 rebuild the screens with these pieces
- Form item: #11 (unified coach interface, added 2026-10-06)
- Depends on: nothing. **Specs 07, 08, 09 and 10 (the athlete's pages) all depend on this one**
- Updated 2026-11-11: the shared pieces live in `react/src/ui/` (coach and athlete screens
  share them), `Button` carries every kind in rule 2, Phase 3 builds rule 12's top bar,
  and Phase 0 moves every colour into one token file with a guard against drift
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
| **End** | transparent, 1px border `coral`, text `coral-text`, 6px corner | **every button that ends something**, in both versions |
| **Danger** | filled `danger-fill #e5484d`, white text 19px weight 800, 6px corner | the button inside a confirm dialog that removes something for good (**Remove sensor**). Never on a row |
| **Quiet** | text only, grey `#89969d` or white | row actions, Close, Cancel |
| **Quiet, lime** | lime text, weight 800, set off by a dashed divider | an action inside a dashed "waiting" row (**Send login link**) |

- Primary buttons also get the 6px corner.
- **Anything pressable must look pressable.** A secondary action that matters is a
  solid button, not bare text. (Devin's comments on "Import a roster" and "Save as a
  new Training Block".)
- **End training day is the End button on every screen, local and hosted** (Devin,
  2026-10-06). This replaces the earlier ruling that it was lime, so the strip no
  longer carries a second lime button.
- Other destructive row actions (Archive, Delete, Remove) stay quiet grey. The row's
  button only opens the confirm dialog; the red **Danger** button is inside it.

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
- **Red** — an athlete is **Behind**, a button **ends or removes** something, or
  something **went wrong** (an error message, a field with a mistake). Nothing else is red.
  Two reds, each with one job (decided 2026-11-11, Devin):
  - **Coral `#ff646b`** for red **text, outlines and dots** on the dark background:
    Behind, End buttons, error messages, a field with a mistake. 6.3:1 against `panel`.
  - **`danger-fill #e5484d`** for a **filled** red button with white text (rule 2's
    Danger kind). White on it is 3.9:1, so its text is 19px weight 800, which meets
    the 3:1 bar for large text. White on coral would be 2.9:1, too faint.
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
- **The top bar** is the bold one: the signed-in person's **profile image** on a lime
  rounded square, with their name beside it at weight 800 (rule 12: the picture goes
  Home, the name opens the menu). On the sign-in and first-run pages, where nobody is
  signed in, the square holds the letters "EA" beside "Edge Athlete".
- **Administrator** is a pill badge: `admin-bg #1a2610`, lime border, lime text (2026-11-11).
- **The Calendar has two views behind one List | Month switch** (a two-option segmented
  control, the chosen option filled white). **Month** is a grid of solid square day
  blocks: a planned session has a mint bar, the next one a lime border, a finished one
  is greyed, and a date shared by two programs names the second ("+ Receivers · Day 1").
  This replaces the old List / Cards text buttons.
- **Forms and dialogs** (sign in, first-run setup, send a login link) are a solid
  `panel` card with a 10px corner; inputs are `#0b1114` with a `line` border and a 6px
  corner. A dialog sits over a dimmed page.

### 10. Fewer pages: do the job where it already is

Decided 2026-11-11 (Devin). The redesign exists to cut how many pages a coach, or an
athlete, drills through on average. Before adding a page, check whether the job fits on
the page already open: a row that expands, a panel that opens in place. Do it where it
fits; never cram a page to avoid one.

### 11. A drill-down page leads only back

Decided 2026-11-11 (Devin). A page opened to look closer at one thing (all sessions, a
sensor list, one past day) never branches into another workflow. Its one way out is a
back link, just under the top bar, to wherever it was opened from. A flow that has to
leave it (adding a sensor from the sensor list) returns to it when done.

### 12. The top bar: the picture goes Home, the name opens the menu

Decided 2026-11-11 (Devin), for coach and athlete screens alike, on every page:

- **The picture / logo at the top-left always goes Home.** A coach's Home is **Planning**,
  always, whether or not a training day is running. An athlete's Home is their home page.
- **The signed-in person's name, beside it, opens the account menu.** Coaches: Coaches
  (administrators only), Change password, Log out. Athletes: Account, Sign out.
- Today the coach's corner is one button (the picture and "Edge Athlete") that opens the
  account menu (`react/src/coach/AccountMenu.jsx`); it splits into the two targets above (Phase 3).

### 13. One shared piece per kind of element

Decided 2026-11-11 (Devin). Every kind of element (button, row, card, badge, chart,
dialog, top bar, tile) is drawn by **one** shared piece in `react/src/ui/`, set up with
options; nobody draws a second copy by hand. A different look in one place is a size or
option on the same piece: the coach's big live rep chart is `BarChart size="large"`, not
its own chart. Before building an element, look in `ui/`; if it's missing and will be used
twice, build it there first. When a shared piece lands, a guard test fails if the
hand-drawn version comes back.

- **`ui/BarChart`** (spec 10, Phase 3) is the one bar chart: the coach's live rep chart
  (`large`), the coach's history sparkline (`spark`), the athlete's past session rep bars
  and My Recent Progress (`normal`), and the rack screen's set summary (spec 19). Options:
  number above, text inside (written upward), label below, colour per bar, lighter bars,
  legend lines, a fixed top, scroll or fit, height. `ui.test.jsx` fails on a bar height set
  by hand anywhere outside `ui/`.
- Also shared (spec 10, Phase 4): `ui/PillGroup` (one chosen pill: range presets, Athlete /
  Group, LB | KG), `ui/RangePicker` (presets + From / To + label, coach History and athlete
  progress), `ui/UnitToggle` and `ui/Load` (pounds or kilograms, one device setting in
  `units.js`), `ui/TrendLine`, `ui/Tiles`.
- Copies that already exist elsewhere are for a later audit spec; meanwhile, one found
  while working in a file is folded in then.

## Tokens

From `react/src/theme.js` and `App.css` — existing values, unchanged:

`bg #070b0e` · `panel #10171b` · `panel2 #151e23` · `line #263239` · `ink #f5f7f2` ·
`muted #89969d` · `lime #a9f04d` · `mint #45dcb3` · `amber #ffb63e` · `coral #ff646b`.
Font: Inter.

New, added by this spec: `focus-bg #121b14` · `faint #7a868c` · `soft-ink #c9d1d5` ·
`button-edge #5c6a72` · `risk-bg #170d0e` · `hero-bg #101a17` · `admin-bg #1a2610` ·
`on-lime #071006` (dark text on a lime fill) · `danger-fill #e5484d` (rule 5) ·
`radius-button 6px`. Added in Phase 0, Stop B (Devin, 2026-11-11): `coral-text #ff9aa0`
(red words) · `field #0b1114` (inputs) · `shade #000000` (dims and shadows, always
see-through) · `warn-bg #1f1a0d` (amber notice boxes); `risk-bg` also backs error boxes.
`faint` was `#6f7c83` until Phase 1, lightened 8% so small labels read at 4.5:1 on every
surface. (`hairline #1b252a` and `outline #8d9aa1` from the first draft of
this spec are dropped: rule 9 uses `line` and `panel` instead.)

**Every colour in the app comes from one file** (decided 2026-11-11, Devin): change a
colour there and it changes everywhere. No colour code is typed anywhere else, and a test
keeps it that way. The sensor's own setup page (the captive portal in
`esp32/edge_athlete_node/src/setup_page.h`) runs on another device and can't load the
app's stylesheet, so it keeps its own copy, and a test fails if that copy stops matching.

### What it found (2026-11-11)

- The colours were defined twice, by hand: in `theme.js` (172 uses, the rack screen's
  inline styles) and as variables on the `.monitor` class in `App.css` (620 uses).
- The `.monitor` variables reach only the coach screens. The sign-in pages, the athlete
  pages and the account menu can't see them, so their stylesheets type colours out.
- **393 colour codes typed out in 20 files, 78 different values**, plus 47 `rgba(...)`
  see-through colours. About ten are the brand colours copied by hand; the rest are
  drift: six reds, four ambers (the sensor's setup page uses `#f2b84b`, the app
  `#ffb63e`) and about forty near-identical dark greys.
- `App.css` is one file of 1,020 lines.

---

## Phase 0 — One token file, and nothing typed anywhere else

Two stops. It changes how colours are written, never what a screen does.

### Stop A — the token file, the guards, the exact matches

- **New `react/src/styles/tokens.css`**, on `:root` so every screen can see it (not on
  `.monitor`). It holds every colour in "Tokens" above, plus `radius-button` and the
  font stacks. It is grouped into sections (surfaces, text, lime, mint, amber, red,
  shapes and type), and **each section opens with a comment naming the kinds of things
  that colour is used on**, in plain words. For example: *Red: coral is for red text,
  outlines and dots (Behind, End buttons, error messages, a field with a mistake);
  danger-fill is only for the filled button that confirms removing something.* A colour
  with no job written down doesn't go in.
- **`theme.js` stops holding colour codes.** Each entry points at its variable
  (`lime: 'var(--lime)'`), so the rack screen's inline styles read the same file.
  (Checked 2026-11-11: no code does arithmetic on the colour codes, so this is safe.)
- The `.monitor` block in `App.css` loses its copy of the variables.
- **Every typed colour that exactly matches a token becomes that token.**
- **The guards**, run by the frontend suite in CI:
  - a test fails if a colour code (`#…`, `rgb(…)`, `rgba(…)`, `hsl(…)`) appears in any
    stylesheet or component outside `tokens.css`. Until Stop B, it reads from a list of
    the leftovers it allows, and that list may only shrink;
  - a test reads the colours in the sensor's `setup_page.h` and fails if any differs from
    `tokens.css`. Until Stop B, it allows only the amber.

**Done when:**

- [x] `tokens.css` exists with a plain-language comment on every section.
- [x] `theme.js` holds no colour codes.
- [x] Both guard tests pass, and each fails when a colour code is typed into a component
      or the setup page's colours are changed (checked once by hand).
- [x] *(Browser)* The app looks exactly as before, as a local install and as the remote
      server: the rack screen, the coach's three states, sign-in, the athlete's pages.
      (Checked by comparing every element's colours, old against new, on the 9 screens that
      open without a server; Room Layout's header changed, kept by Devin. Screens behind a
      login not opened yet.)
- [x] Frontend suite and build pass.

**Stop. Devin reviews.**

### Stop B — the drift, the firmware, the files

- **Every leftover colour is mapped to the nearest token.** Before changing any, a list
  goes to Devin: each leftover value, where it is, the token it would become, and a
  side-by-side of any that visibly shift (the five stray reds, the ambers, the greys).
  A leftover that turns out to have a real job of its own becomes a new token, with its
  comment, only on Devin's say-so.
- **See-through colours** become a token plus how see-through it is, written with
  `color-mix()`, not a new `rgba(…)`.
- **The Remove sensor button** uses `danger-fill` at 19px (rule 2's Danger kind).
- **The sensor's setup page** takes the app's amber, `#ffb63e`. It reaches sensors at the
  next firmware update; nothing forces a re-flash.
- **`App.css` is split by area** into `react/src/styles/`: base (page, type, focus),
  the rack screen, the room display, and the coach's shared pieces. Each file opens with a
  plain-language comment saying what it styles. The component stylesheets that already
  sit beside their component (`coach/*.css`, `athlete/athlete.css`) stay there.
- The leftovers list is deleted: from now on the guard allows no colour code outside
  `tokens.css` at all.

**Done when:**

- [x] No colour code exists outside `tokens.css` and the sensor's setup page; the guard
      runs with no allowed list.
- [x] The setup page's colours all match `tokens.css`.
- [x] Every new token Devin approved has its comment.
- [x] *(Browser)* Every screen checked against its Final designs board; the only visible
      changes are the ones on the approved list.
- [x] Frontend suite, build and firmware build pass.

**Stop. Devin reviews.**

## Phase 1 — The shared pieces

New folder `react/src/ui/`, one small component per file, each opening with a
plain-language comment. It sits outside `coach/` because the athlete's pages (spec 10) are
built from the same pieces: one interface, one set of components (rule 8).

| Component | What it is |
|---|---|
| `FocusCard` | the tinted, lime-bordered panel with a label, a large title and an action area |
| `QuietRow` | one list row as its own solid block (rule 9: `panel`, 1px `line` border, 6px gap to the next): name, meta, a slot for a badge, quiet actions |
| `SectionLabel` | the small grey uppercase label |
| `Step` | a numbered step, active or idle, plus `StepLink` for one that goes elsewhere |
| `Button` | every kind in rule 2: `kind="primary" \| "next" \| "solid" \| "key" \| "end" \| "danger" \| "quiet" \| "quiet-lime"`. The only way to make a button on these screens |
| `Badge` | `scheduled` / `not-scheduled`, sensor on/off, rack state |
| `RiskTag` | the red "Behind 4/5" tag, and its small-triangle form |
| `Hero` | the existing header card, extracted unchanged |

Build them against the Final designs boards, each with a render test. Use them nowhere yet.

**Done when:**

- [x] Each component has a render test for every variant, including all eight `Button`
      kinds (`end` is the red outline from rule 2, `danger` the filled red, `key` the
      lime-bordered solid one).
- [x] `Button` refuses an unknown `kind` in development.
- [x] Buttons and row actions are at least 44px tall (touch targets on a tablet).
- [x] Text meets 4.5:1 contrast on its background — in particular grey text on the
      focus card and on the risk background.
- [x] Nothing else in the app changed, apart from `faint` lightening 8% (an archived
      coach's name, the zone labels on a rack row, the bar beside an idle rack).

**Stop. Devin reviews.**

## Phase 2 — The sub-tab rule, and the leftovers

- The sub-tab row renders only when the state has two or more tabs.
- Remove from the interface: the API paths printed on Room Layout, "built from N
  requests" in group history, raw ISO timestamps in report rows, the stale "deploy one
  from the Workouts tab" on the empty Calendar. (Each is also listed in the spec that
  owns its screen; do them here if those specs have not started.)
- Delete `react/src/coachTabs.js` if nothing imports it. On 2026-10-06 nothing did.
  (Already gone by 2026-11-11.)

**Done when:**

- [x] *(Frontend test)* SESSION renders no tab row; PLANNING and ANALYTICS render theirs.
- [x] A test fails if the coach bundle's source contains `/api/` in visible text or the
      phrase "server-local".
- [ ] *(Browser)* All three states still work.

**Stop. Devin reviews.**

## Phase 3 — The top bar (rule 12)

Today the coach's corner is one button, the picture and "Edge Athlete", that opens the
account menu (`react/src/coach/AccountMenu.jsx`). It splits into two targets, and the
result becomes a shared `TopBar` in `react/src/ui/` that the athlete's pages use too
(spec 10 Phase 1). The menu's contents and its rules (close on Escape or a press
elsewhere; Coaches shown to administrators only, as a courtesy, with the server as the
lock) move with it unchanged.

| Part | Coach | Athlete (spec 10) |
|---|---|---|
| The picture (profile image on the lime square) | Goes to **Planning**, always, even while a training day is running. The session strip stays and the day keeps running | Goes to the athlete's Home |
| The name beside it | Opens the menu: Coaches (administrators only), Change password, Log out | Opens the menu: Account, Sign out |
| Signed out (sign-in, first-run) | The square holds "EA", and neither part is pressable | The same |

Also in `react/src/ui/`: `BackLink`, the one link under the top bar on a drill-down page
(rule 11), back to wherever the page was opened from.

**Done when:**

- [x] *(Frontend test)* From SESSION and from ANALYTICS, pressing the picture lands on
      PLANNING; with a day running, the day is still running afterwards.
- [x] *(Frontend test)* Pressing the name opens the menu; Coaches appears only for an
      administrator; Escape and a press elsewhere close it.
- [x] Both parts are real buttons, at least 44px tall, reachable by keyboard, each with
      its own accessible name ("Home", "Account menu").
- [x] `BackLink` renders its label and goes where it is told; a render test covers it.
- [x] *(Browser)* The top bar works as a local install and as the remote server.
      (Checked on the real components in a preview page; not yet on a signed-in
      workspace, which needs the server running.)

**Stop. Devin reviews.**

---

## Acceptance criteria

- [ ] Every coach screen has one focus card and at most one lime button.
- [ ] No row, card or table is drawn without a solid surface and a border; only banners
      and the focus card are tinted.
- [ ] Every button that ends something uses the End style, in both deployments; every
      filled red button is the Danger kind on `danger-fill`.
- [ ] No colour code exists outside `tokens.css` (and the sensor's setup page, which a
      test keeps matching).
- [ ] Every pressable thing is a `Button`.
- [ ] The six vocabulary terms are used consistently; "deploy" and "head coach" (for
      the flag) appear nowhere a coach reads.
- [ ] Red appears only on **Behind**, End and Danger buttons, and errors.
- [ ] The strip, header cards, LIVE pill and navbar are unchanged.
- [ ] No component, page or stylesheet exists only for hosted mode, apart from the
      login-link dialog. Every hosted difference is reached through `useDeployment()`.
- [ ] With the switch set to gym box, every screen renders exactly as before the
      hosted additions were written (render tests run in both modes).

## Risks

| Risk | What reduces it |
|---|---|
| The rules drift as screens are rebuilt one at a time | Specs 07–10 may only use the Phase 1 components for buttons, rows and focus cards |
| A restyle quietly changes behaviour | This spec has no behaviour change at all; any is a bug |
| "One lime button" hides something that used to be obvious | Rule 3 wins over rule 2: if a coach needs it weekly, it is an outline button on the row, never a menu |

## Docs to update when done

`docs/journal/core/coach-screens.md` — a short section on the focus rule: what forced it
(everything read as equally loud), what was rejected (colour-coding sections; hiding
actions behind menus), what it cost.
