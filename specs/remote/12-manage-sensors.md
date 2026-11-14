# Feature Spec 12: Manage sensors, several sensors with one live

- Owner: Devin Walton
- Date: 2026-11-11 (split out 2026-11-14)
- Previously spec 14, Phase 10 (split out when the specs were put in build order, 2026-11-14)
- Status: Specced, 1 phase. Builds on spec 10 (racks and sensors that pair themselves)
- Depends on: [14 Sensors online](07-sensors-online.md) (Phases 0–9, done), [16 The athlete's pages](09-athlete-pages.md)

## Phase 0 — Manage sensors: several sensors, one live (written 2026-11-11)

Boards: Final designs, `F_Ath_M1` (Manage sensors), `F_Ath_M1b` (two sensors, one on
standby), `F_Ath_M2` (remove confirm), approved 2026-11-11 with the athlete pages
(spec 09). The My sensor row on Home and Account (`F_Ath_H1`, `F_Ath_A1`) opens this page.

**Decisions (Devin, 2026-11-11):**

- **An athlete may own several sensors.** One is **live** and follows them onto their
  rack; the rest are **on standby** and send nothing that counts. The live one is the
  sensor **seen most recently**. Today nothing stops an athlete owning two, and both would
  follow them onto their rack and could count the same rep twice; this closes that.
- **To keep two switched-on sensors from trading places every few seconds**, live passes
  to another sensor only when the live one has gone quiet (no pulse for 30 seconds), and
  never in the middle of a set.
- **The My sensor row** (Home and Account) shows the live sensor, "Connected · seen just
  now", and one **Manage** button. The school code is not on the row any more: it lives
  on the Add my sensor page, large.
- **Manage sensors is its own page** with one way out, back to where it was opened
  (spec 08 rule 11). Each sensor is a card: its ID, "Live · connected · seen just now" or
  "On standby · seen 3 days ago", and **Swap** and **Remove**. At the bottom, the lime
  **Add new sensor**.
- **Add new sensor** and **Swap** open the existing Add my sensor page and setup steps
  (`F_Ath_S2`, `F_Setup1–5`). **Setup's Done returns to Manage sensors**, not Home.
- **Swap** is "add this new sensor in place of that one": when the new sensor claims
  itself, the swapped one is removed in the same step. Its sets stay the athlete's.
- **Remove** confirms first (`F_Ath_M2`): "It stops connecting straight away. Every set it
  measured stays." The red **Remove sensor** and **Keep it**.

**Server:**

- `GET /api/athlete/sensors/` gains `state` (`live` | `standby`) and `last_seen` per
  sensor, newest seen first.
- The rule for live lives in one function, used when the athlete joins a session and when
  a sensor's pulse arrives: only the live sensor holds the athlete's rack; a standby
  sensor's reps are ignored, the same way an unlinked sensor's are today.
- The claim (Phase 2) takes an optional `replaces: <sensor id>`, accepted only for a
  sensor the claiming athlete owns. The claim and the removal happen in one transaction:
  if the claim fails, the old sensor stays.

**Page:** `/athlete/sensors`, new file `react/src/athlete/ManageSensors.jsx` opening with
a plain-language comment on why it exists. Its back link names where it was opened from
(Home or Account). The Add my sensor page learns where to return when setup is done.

**Done when:**

- [ ] *(Backend test)* With two sensors, the one seen most recently is `live`; the other is
      `standby` and its reps are not saved.
- [ ] *(Backend test)* Live does not move while the live sensor keeps pulsing, nor during
      an open set; it moves after 30 seconds of silence.
- [ ] *(Backend test)* A claim with `replaces` removes the replaced sensor only when the
      claim succeeds; `replaces` naming someone else's sensor is refused.
- [ ] *(Backend test)* Removing a sensor keeps every set it measured.
- [ ] *(Frontend test)* Manage sensors shows one card per sensor with Swap and Remove, and
      Remove asks first.
- [ ] *(Browser)* Home → Manage → Add new sensor → setup → Done lands back on Manage
      sensors with the new sensor listed.
- [ ] *(Real sensors)* Two sensors switched on: reps from the standby one never reach the
      rack; switch the live one off, and within 30 seconds the other is live.

**Stop. Devin reviews.**

