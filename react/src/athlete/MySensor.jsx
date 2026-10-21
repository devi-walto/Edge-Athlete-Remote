// MySensor.jsx — an athlete adds, sees and removes their own sensor (spec 14).
//
// Why this file exists: online, an athlete lifts at home with their own sensor, and
// sets it up without anyone's help. Their page gives them a one-time code; they type
// it into the sensor's setup with their home Wi-Fi; the sensor sends it to the school
// and gets its own token back. This page never sees that token, and the sensor never
// sees the athlete's password.
//
// Two parts, built to the Final designs boards F_Ath_S1 to S5:
//   MySensorSection  the "My sensor" row on the athlete's page: none yet, or each
//                    sensor with whether it is connected, and Remove (with a confirm).
//   AddSensorPage    the code, large, while it waits for the sensor to use it. It asks
//                    the server every few seconds, so it changes by itself when the
//                    sensor claims the code.
// Remote only: a gym's sensors are linked to racks by a coach, as before.

import { useCallback, useEffect, useState } from 'react'
import { signInHeaders } from '../api/client.js'

const CODE = '/api/athlete/sensor-code/'
const SENSORS = '/api/athlete/sensors/'
const CHECK_MS = 3000            // how often the code page asks "has the sensor used it?"
const CONNECTED_WITHIN_MS = 60_000   // seen this recently = connected (it pulses every 5 s)

async function call(url, method = 'GET') {
  try {
    const response = await fetch(url, {
      method, headers: { Accept: 'application/json', ...(await signInHeaders()) },
    })
    return { status: response.status, body: await response.json().catch(() => ({})) }
  } catch {
    return { status: 0, body: {} }
  }
}

/** "Connected · seen just now", "Last seen 12 min ago", or "Not connected yet". */
export function sensorStatus(lastSeen, now = Date.now()) {
  if (!lastSeen) return { connected: false, text: 'Not connected yet' }
  const ago = now - new Date(lastSeen).getTime()
  if (ago < CONNECTED_WITHIN_MS) return { connected: true, text: 'Connected · seen just now' }
  const minutes = Math.round(ago / 60_000)
  if (minutes < 60) return { connected: false, text: `Last seen ${minutes} min ago` }
  const hours = Math.round(minutes / 60)
  if (hours < 48) return { connected: false, text: `Last seen ${hours} h ago` }
  return { connected: false, text: `Last seen ${new Date(lastSeen).toLocaleDateString()}` }
}

function clock(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

export function MySensorSection({ onAdd }) {
  const [sensors, setSensors] = useState(null)   // null while loading
  const [removing, setRemoving] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    const { status, body } = await call(SENSORS)
    setSensors(status === 200 ? body.sensors || [] : [])
  }, [])
  useEffect(() => { load() }, [load])

  async function remove() {
    const { status, body } = await call(`${SENSORS}${encodeURIComponent(removing)}/`, 'DELETE')
    if (status === 204) {
      setRemoving(null)
      setError('')
      load()
    } else {
      setError(body.detail || "That didn't work. Try again in a moment.")
    }
  }

  if (sensors === null) return null
  return <section className="athlete-sensors" aria-labelledby="my-sensor">
    <span id="my-sensor" className="athlete-label">My sensor</span>
    {sensors.length === 0 && <div className="athlete-row">
      <span className="athlete-row-text"><b>None yet</b><span>Add yours to lift with it at home.</span></span>
      <button type="button" className="acct-primary athlete-row-button" onClick={onAdd}>Add my sensor</button>
    </div>}
    {sensors.map((sensor) => {
      const seen = sensorStatus(sensor.last_seen)
      return <div className="athlete-row" key={sensor.node_id}>
        <span className={`athlete-dot${seen.connected ? ' is-on' : ''}`} aria-hidden="true" />
        <span className="athlete-row-text"><b className="athlete-sensor-id">{sensor.node_id}</b>
          <span>{seen.text}</span></span>
        <button type="button" className="acct-solid athlete-row-button"
          onClick={() => { setError(''); setRemoving(sensor.node_id) }}>Remove</button>
      </div>
    })}
    {removing && <div className="athlete-overlay">
      <div role="dialog" aria-modal="true" aria-labelledby="remove-title" className="athlete-dialog">
        <h2 id="remove-title">Remove {removing}?</h2>
        <p>It stops connecting straight away. Every set it measured stays. To use it again,
          add it with a new code.</p>
        {error && <p className="acct-error" role="alert">{error}</p>}
        <button type="button" className="athlete-danger" onClick={remove}>Remove sensor</button>
        <button type="button" className="acct-solid" onClick={() => setRemoving(null)}>Keep it</button>
      </div>
    </div>}
  </section>
}

export function AddSensorPage({ onDone }) {
  // code: the text, shown once; status: waiting | used | expired | offline
  const [code, setCode] = useState(null)
  const [state, setState] = useState({ status: 'loading' })

  const newCode = useCallback(async () => {
    setState({ status: 'loading' })
    const { status, body } = await call(CODE, 'POST')
    if (status === 201) {
      setCode(body)
      setState({ status: 'waiting' })
    } else {
      setState({ status: 'offline' })
    }
  }, [])
  useEffect(() => { newCode() }, [newCode])

  // While waiting: has the sensor used it yet?
  useEffect(() => {
    if (state.status !== 'waiting') return undefined
    const timer = setInterval(async () => {
      const { status, body } = await call(CODE)
      if (status !== 200) return            // a missed check; the next one tries again
      if (body.status === 'used') setState({ status: 'used', sensor: body.sensor })
      else if (body.status === 'expired') setState({ status: 'expired' })
    }, CHECK_MS)
    return () => clearInterval(timer)
  }, [state.status])

  const used = state.status === 'used'
  return <main className="athlete-page">
    <header className="athlete-bar is-back">
      <button type="button" className="acct-quiet is-strong athlete-back" onClick={onDone}>‹ Home</button>
    </header>
    <div className="athlete-body">
      <h1 className="athlete-title">Add my sensor</h1>
      {state.status === 'offline' && <p className="acct-error" role="alert">
        The school couldn't be reached. Check your connection, then get a code again.</p>}
      {code && <div className={`athlete-code-card${used ? ' is-used' : ''}`}>
        <span className="athlete-label">Your sensor's code</span>
        <span className="athlete-code">{code.code}</span>
        <span className="athlete-muted">{used ? "Used. It won't work again."
          : state.status === 'expired' ? 'This code ran out.'
            : `Works once, until ${clock(code.expires_at)} (15 minutes)`}</span>
      </div>}
      <ol className="athlete-steps">
        <li>Switch your sensor on and open its setup. For now that's its USB cable and the
          setup tool on a computer.</li>
        <li>Pick your home Wi-Fi and type its password.</li>
        <li>Type this code. Your sensor does the rest.</li>
      </ol>
      {code && <div className="athlete-row is-status" role="status">
        <span className={`athlete-dot${used ? ' is-on' : state.status === 'waiting' ? ' is-waiting' : ''}`}
          aria-hidden="true" />
        <b>{used ? `${state.sensor} is added and connected`
          : state.status === 'expired' ? 'Get a new code to try again'
            : 'Waiting for your sensor…'}</b>
      </div>}
      <p className="athlete-muted athlete-lead">Your sensor only ever needs this code. Never
        type your password into a sensor.</p>
      {used
        ? <button type="button" className="acct-primary athlete-wide" onClick={onDone}>Done</button>
        : <button type="button" className="acct-solid athlete-wide" onClick={newCode}
          disabled={state.status === 'loading'}>Get a new code</button>}
    </div>
  </main>
}
