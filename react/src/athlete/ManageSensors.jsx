// ManageSensors.jsx — /athlete/sensors: the athlete's sensors, opened from My sensor's Manage.
//
// Why this file exists: Home's sensor row needs somewhere to go. For now this is the sensor
// list that already existed (MySensor.jsx: remove with a confirm, add a new one); spec 14
// Phase 10 rebuilds it to board F_Ath_M1 (live / standby, Swap). It's a drill-down page, so
// its only way out is back to Home, and setting a new sensor up comes back here when done.
import { useState } from 'react'
import AthletePage, { HOME_PATH, SENSORS_PATH } from './AthletePage.jsx'
import { AddSensorPage, MySensorSection } from './MySensor.jsx'

export default function ManageSensors() {
  const [adding, setAdding] = useState(false)
  if (adding) return <AddSensorPage onDone={() => setAdding(false)} />
  return <AthletePage here={SENSORS_PATH} back={{ label: 'Home', to: HOME_PATH }}>
    <h1 className="athlete-page-title">My sensors</h1>
    <MySensorSection onAdd={() => setAdding(true)} />
  </AthletePage>
}
