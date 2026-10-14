// useDeployment.js — the one place a screen asks "is this a local or a remote installation?"
//
// Why this file exists: the same screens run in a gym (local) and online (remote).
// A few things differ: online-only buttons, the online-only screens on the Final
// designs page, how the screens reach the live-update broker. Every one of those asks
// this hook, so the answer comes from one place and the code stays one codebase.
//
// The server says which it is at /api/system/info/ (open, no login). It is asked ONCE
// per page load and the answer is shared by every screen that uses the hook: the kind
// of installation never changes while the page is open. If the server cannot be
// reached, the answer is "local", which is also the server's own default.
import { useEffect, useState } from 'react'

let answer = null   // 'local' | 'remote' once known
let asking = null   // the one request in flight, shared by everyone who asks

export function getDeployment() {
  if (answer) return Promise.resolve(answer)
  if (!asking) {
    asking = fetch('/api/system/info/')
      .then((res) => (res.ok ? res.json() : {}))
      .catch(() => ({}))
      .then((info) => {
        answer = info.deployment === 'remote' ? 'remote' : 'local'
        return answer
      })
  }
  return asking
}

/** 'local' or 'remote', or null on the first render before the server has answered. */
export default function useDeployment() {
  const [deployment, setDeployment] = useState(answer)
  useEffect(() => {
    if (answer) return undefined
    let cancelled = false
    getDeployment().then((value) => { if (!cancelled) setDeployment(value) })
    return () => { cancelled = true }
  }, [])
  return deployment
}

/** Tests only: forget the answer so the next ask goes to the server again. */
export function forgetDeploymentForTests() {
  answer = null
  asking = null
}
