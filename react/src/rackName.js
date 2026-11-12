// rackName.js — how every screen prints a rack: its name, never a bare number.
//
// Why this file exists (spec 18, Phase 2): a rack used to be "Rack 3", a numbered slot.
// Now each tablet names its own rack ("Platform", "Rack 3"), and two racks may share a
// name, so the server sends what to print as `label` ("Platform (4)" when shared). One
// helper, so no screen prints a number where a name belongs, and an older server (no
// label) still reads "Rack 3".

/** label: what the server says to print; number: the rack's number. */
export function rackLabel(label, number) {
  if (label) return label
  return number != null ? `Rack ${number}` : 'Rack'
}
