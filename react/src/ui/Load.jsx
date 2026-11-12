// Load.jsx — a weight, written in the device's chosen unit: "225 lb" or "102 kg".
//
// Why this file exists: loads are stored in pounds, and any screen showing one should
// follow LB | KG without each screen wiring it up. Drop <Load lbs={225} /> anywhere and it
// redraws itself when the choice changes. (Inside a longer sentence, formatLoad from
// units.js with useUnit() does the same job.)
import { formatLoad, useUnit } from '../units.js'

/** lbs: the stored weight; empty: what to show when there's none (default "--"). */
export default function Load({ lbs, empty = '--' }) {
  return <>{formatLoad(lbs, useUnit()) ?? empty}</>
}
