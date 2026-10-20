// db/repBuffer.js — the durability boundary (backed by Dexie).
//
// ── WHAT THIS FILE DOES (plain version) ────────────────────────────────────────
// Every rep that comes in over MQTT is saved HERE, in the browser's own on-device
// database, the instant it arrives — before we update the screen or talk to the
// server. That database survives reloads, closed tabs, and WiFi drops, so if the
// gym's access point blips at the exact moment a set ends, the reps are already
// safe on the tablet and nothing is lost. We only wipe the buffer AFTER a set's
// reps have been successfully saved to the server (that happens in Phase 11).
//
// Think of it as writing every rep in a notebook the moment it happens, so even
// if the phone line drops before you can call it in, you still have every rep.
//
// ── WHY DEXIE (for whoever maintains this) ─────────────────────────────────────
// The browser's built-in database is called "IndexedDB". It's reliable but its
// raw API is fiddly: you deal with version numbers, an "upgrade" event, manual
// transactions, and success/error callbacks just to add one row. "Dexie" is a
// small, popular library that wraps IndexedDB so it reads like normal async code —
// you declare your tables once, then add/read/clear with a single line each. Same
// database underneath, far less boilerplate.

import Dexie from 'dexie'

// Create (or open) one database named "edgeathlete".
//
// `.version(1).stores({ reps: '++id' })` declares what's inside it. Read it as:
//   • one table called "reps"
//   • '++id'  →  give every rep an auto-incrementing primary key named `id`
//                (the "++" is Dexie's shorthand for "auto-increment"). Insertion
//                order == id order, which is the order we want reps back in.
// We don't index any other fields because all we ever do is add reps, read them
// ALL back, and clear them — no searching or sorting by rep contents.
//
// If we ever change this shape later, bump to `.version(2)` and Dexie handles the
// upgrade — see https://dexie.org/docs/Tutorial/Design.
const db = new Dexie('edgeathlete')
db.version(1).stores({ reps: '++id' })

// The same rep arriving twice. Sensors send reps "at least once" (MQTT QoS 1, spec
// 14): if the broker's thank-you for a rep is lost, the sensor sends it again, so now
// and then one rep arrives twice. It is the same rep when the same sensor sent the
// same rep number at the same moment; two real reps always differ in at least one.
export function isRepeat(rep, stored) {
  return stored.some((row) => row.node_id === rep.node_id
    && row.rep_number === rep.rep_number && row.timestamp === rep.timestamp)
}

// Save one rep immediately on arrival, unless it is a repeat of one already saved for
// this set. Resolves to true once the rep is durably stored (Dexie assigns the `id`
// for us), or false for a repeat, which is not stored or counted. One transaction,
// so two copies arriving at the same instant can't both get in.
export function addRep(rep) {
  return db.transaction('rw', db.reps, async () => {
    if (isRepeat(rep, await db.reps.toArray())) return false
    await db.reps.add(rep)
    return true
  })
}

// Every buffered rep, in arrival order — read at set-end to build the batch POST.
export function getBufferedReps() {
  return db.reps.toArray()
}

// Wipe the buffer — called ONLY after a set's reps are safely saved server-side.
export function clearBuffer() {
  return db.reps.clear()
}
