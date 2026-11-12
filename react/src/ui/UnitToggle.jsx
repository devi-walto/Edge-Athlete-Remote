// UnitToggle.jsx — LB | KG: the one place a person picks pounds or kilograms.
//
// Why this file exists: the choice is remembered on the device (units.js) and every load on
// every screen follows it, so the picker is the same everywhere it appears: My Recent
// Progress now, the rack screen's plate loader later (spec 16). No props needed: it reads
// and writes the one setting itself.
import { setUnit, useUnit } from '../units.js'
import PillGroup from './PillGroup.jsx'

export default function UnitToggle({ className }) {
  return <PillGroup className={className} label="Units" value={useUnit()} onChange={setUnit}
    choices={[{ value: 'lb', label: 'LB' }, { value: 'kg', label: 'KG' }]} />
}
