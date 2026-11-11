// BackLink.jsx — the one way out of a drill-down page, just under the top bar.
//
// Why this file exists: spec 06 rule 11. A page opened to look closer at one thing (all
// sessions, the sensor list, one past day) never branches into another workflow; its
// only exit is back to wherever it was opened from. Every such page uses this same link.
import './ui.css'

/** label: where it goes back to ("Home", "All sessions"); onBack: takes you there. */
export default function BackLink({ label, onBack }) {
  return <div className="ui-backlink-row">
    <button type="button" className="ui-backlink" onClick={onBack}><span aria-hidden="true">‹</span> {label}</button>
  </div>
}
