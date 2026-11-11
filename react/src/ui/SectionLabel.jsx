// SectionLabel.jsx — the small grey uppercase label over a group of rows.
//
// Why this file exists: spec 06 rule 1 keeps everything around the focus card quiet,
// and a group of rows is introduced by a small label ("Other Training Blocks") rather
// than a big heading. One piece, so every screen's labels match.
import './ui.css'

export default function SectionLabel({ children, as: Tag = 'h3', className = '' }) {
  return <Tag className={`ui-section-label${className ? ` ${className}` : ''}`}>{children}</Tag>
}
