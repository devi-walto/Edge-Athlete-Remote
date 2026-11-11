// ContextTabs.jsx — the row of sub-tabs under the top bar, and which tabs each state has.
//
// Why this file exists: each of the coach's three states (PLANNING, SESSION, ANALYTICS)
// has its own sub-tabs. Spec 06 rule 7: a row of tabs needs at least two tabs, so a
// state with only one (SESSION has just Room) shows no row at all, and if a second tab
// is ever added the row comes back by itself. The lists live here so the row and its
// test read the same ones.

// Which sub-tabs belong to which state: the three moments of a coach's day.
//
//   PLANNING   what you set up before anyone lifts
//   SESSION    the live room, while they do
//   ANALYTICS  what you read afterwards, one athlete at a time
//
// The first entry in each list is that state's landing tab.
export const STATE_TABS = {
  planning: ["design", "groups", "catalog", "calendar"],
  session: ["room"],
  analytics: ["athlete", "history", "notes", "reports"],
};

export const TAB_LABELS = {
  design: "Design",
  groups: "Groups",
  catalog: "Workout catalog",
  calendar: "Calendar",
  room: "Room",
  athlete: "Athlete",
  history: "History",
  notes: "Notes",
  reports: "Reports",
};

/** tabs: this state's list; active: the open tab; onChoose(tab). Nothing for fewer than two. */
export default function ContextTabs({ tabs, active, onChoose }) {
  if (!tabs || tabs.length < 2) return null;
  return <nav className="coach-context-tabs" aria-label="Coach workspace tabs" role="tablist">
    {tabs.map((t) => <button className={active === t ? "active" : ""} aria-selected={active === t} role="tab"
      onClick={() => onChoose(t)} key={t}>{TAB_LABELS[t] ?? t}</button>)}
  </nav>;
}
