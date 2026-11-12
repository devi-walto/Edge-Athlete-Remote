// rack/NoSession.jsx — what a rack shows when no session is running: ready, and waiting.
//
// ── WHY THIS FILE EXISTS (plain version) ───────────────────────────────────────
// A gym tablet is often switched on before practice. With nothing running, the old
// screen showed an empty check-in list ("No athletes in this session") and a "scan
// your band" prompt nobody could use yet, which looked broken. Board F_Rack_NoSession
// (spec 19 Phase 0, local and remote) says instead: this rack is ready, it's waiting
// for today's session, a coach starts it, and the screen will change on its own.
//
// The small chip under it says whether the rack's sensor is live, so a coach walking
// past can see the rack is ready before anyone lifts. It listens for the sensor's
// pulse (sent every few seconds while it's on); no pulse for a while reads "not
// responding". The rack screen listens the whole time it's open (useSensorLive) and
// hands the answer in, so coming back to this screen after a session never starts
// from a stale guess. The rack screen keeps asking the server for a session in the
// background, and the check-in list replaces this screen as soon as one starts.

import { useEffect, useState } from 'react'
import { subscribeNodePulse } from '../mqtt/client.js'
import { T } from '../theme.js'
import Badge from '../ui/Badge.jsx'

// The sensor pulses every 5 seconds; missing three in a row means it isn't there.
export const LIVE_WITHIN_MS = 15_000

/** Is the rack's sensor live? Seen recently when the screen opened, or pulsing since. */
export function useSensorLive(node) {
  const nodeId = node?.node_id
  const [lastPulse, setLastPulse] = useState(() => (node?.last_seen ? Date.parse(node.last_seen) : 0))
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!nodeId) return undefined
    return subscribeNodePulse(nodeId, () => { const t = Date.now(); setLastPulse(t); setNow(t) })
  }, [nodeId])
  // Re-check every few seconds, so a sensor switched off stops reading live.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(id)
  }, [])
  return Boolean(nodeId) && now - lastPulse < LIVE_WITHIN_MS
}

/** live: from useSensorLive, held by the rack screen. */
export default function NoSession({ rackNumber, node, live }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 16, padding: 28, textAlign: 'center' }}>
      <div style={{ fontSize: 10, fontWeight: 900, letterSpacing: '.14em', textTransform: 'uppercase',
        color: T.lime }}>Rack {rackNumber} is ready</div>
      <h1 style={{ fontSize: 30, fontWeight: 850, letterSpacing: '-.035em', lineHeight: 1.1, margin: 0 }}>
        Waiting for<br />today&apos;s session
      </h1>
      <p style={{ color: T.muted, fontSize: 15, lineHeight: 1.5, maxWidth: 280, margin: 0 }}>
        A coach starts it from the coach app. This screen updates on its own, then shows who can
        check in.
      </p>
      <div style={{ marginTop: 6 }}>
        {!node?.node_id
          ? <Badge kind="sensor-off">No sensor linked to this rack</Badge>
          : live
            ? <Badge kind="sensor-on">Sensor {node.node_id} is live</Badge>
            : <Badge kind="sensor-off">Sensor {node.node_id} not responding</Badge>}
      </div>
    </div>
  )
}
