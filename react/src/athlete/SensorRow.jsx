// SensorRow.jsx — "My sensor", one row: the athlete's live sensor and a Manage button.
//
// Why this file exists: Home and Account both show the athlete's sensor the same way
// (board F_Ath_H1): the sensor they lift with now (the one heard from most recently),
// whether it's connected, and Manage, which opens the Manage sensors page. With no sensor
// yet there's nothing to manage, so "Add my sensor" goes straight to the page with the
// codes. Either page is told where it was opened from, so its back link leads there.
import { useEffect, useState } from 'react'
import { navigate } from '../router.js'
import Button from '../ui/Button.jsx'
import QuietRow from '../ui/QuietRow.jsx'
import SectionLabel from '../ui/SectionLabel.jsx'
import { SENSORS_PATH, SENSOR_ADD_PATH, fromQuery } from './AthletePage.jsx'
import { SENSORS, getJson } from './athleteApi.js'
import { sensorStatus } from './MySensor.jsx'

/** The one to show: heard from most recently; never heard from comes last. */
export function liveSensor(sensors) {
  return [...(sensors || [])].sort((a, b) => (b.last_seen ? Date.parse(b.last_seen) : 0) - (a.last_seen ? Date.parse(a.last_seen) : 0))[0] || null
}

/** from: 'account' when the row sits on Account; left out on Home. */
export default function SensorRow({ from }) {
  const [sensors, setSensors] = useState(null)
  useEffect(() => {
    let cancelled = false
    getJson(SENSORS).then(({ status, body }) => { if (!cancelled) setSensors(status === 200 ? body.sensors || [] : []) })
    return () => { cancelled = true }
  }, [])
  if (sensors === null) return null
  const live = liveSensor(sensors)
  const query = fromQuery(from)
  const seen = live && sensorStatus(live.last_seen)
  return <section aria-labelledby="my-sensor-label">
    <SectionLabel as="h2"><span id="my-sensor-label">My sensor</span></SectionLabel>
    {live
      ? <QuietRow lead={<span className={`athlete-dot${seen.connected ? ' is-on' : ''}`} />}
          name={<span className="athlete-sensor-id">{live.node_id}</span>} meta={seen.text}
          actions={<Button kind="solid" onClick={() => navigate(SENSORS_PATH + query)}>Manage</Button>} />
      : <QuietRow name="None yet" meta="Add yours to lift with it at home."
          actions={<Button kind="solid" onClick={() => navigate(SENSOR_ADD_PATH + query)}>Add my sensor</Button>} />}
  </section>
}
