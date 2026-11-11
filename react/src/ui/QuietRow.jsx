// QuietRow.jsx — one row in a list: a name, a detail line, a badge and its actions.
//
// Why this file exists: spec 06 rule 9 draws every list row as its own solid block with
// a border, and rule 3 keeps a row's actions visible on the row (no "more" menus). The
// rows on the Roster, Groups and Coaches pages all have the same parts, so they share
// this piece.
import './ui.css'

/** name, meta (the grey line under it), badge (e.g. a Badge or RiskTag), actions (quiet Buttons). */
export default function QuietRow({ name, meta, badge, actions, as: Tag = 'div', className = '', ...rest }) {
  return <Tag className={`ui-row${className ? ` ${className}` : ''}`} {...rest}>
    <span className="ui-row-text">
      <b className="ui-row-name">{name}</b>
      {meta && <span className="ui-row-meta">{meta}</span>}
    </span>
    {badge && <span className="ui-row-badge">{badge}</span>}
    {actions && <span className="ui-row-actions">{actions}</span>}
  </Tag>
}
