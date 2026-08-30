import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'

// The station writes a row every time an egg is inspected. Without a poll the
// screen keeps showing whatever was there when the page loaded, so during a
// live demo an egg is placed, the board lights up, and the dashboard sits there
// unchanged until somebody presses refresh.
//
// What is polled is /api/inspections/revision, not the list itself. The list
// has no LIMIT and returns every non-'no_egg' row -- thousands on a seeded
// database. Fetching that on a timer would move a megabyte at a time and
// re-render the charts on every tick. The revision call returns three numbers;
// only when one of them moves is the full list fetched again.
const POLL_INTERVAL_MS = 3000

export function useDatabaseInspections() {
  const { authenticatedFetch } = useAuth()
  const [inspections, setInspections] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  // Refs, not state: changing these must never trigger a render on its own.
  const lastRevision = useRef('')
  const inFlight = useRef(false)

  const loadList = useCallback(
    async (quiet) => {
      // A slow response must not stack up behind the interval.
      if (inFlight.current) return
      inFlight.current = true
      if (!quiet) setIsLoading(true)
      try {
        const response = await authenticatedFetch('/api/inspections')
        const result = await response.json().catch(() => ({}))
        if (!response.ok)
          throw new Error(result.error || 'Unable to load inspection records from MariaDB.')
        setInspections(result.inspections || [])
        setError('')
      } catch (requestError) {
        // The rows already on screen are kept deliberately. A dropped poll should
        // not blank a dashboard somebody is watching.
        setError(requestError.message || 'Unable to load inspection records from MariaDB.')
      } finally {
        inFlight.current = false
        if (!quiet) setIsLoading(false)
      }
    },
    [authenticatedFetch]
  )

  const refresh = useCallback(() => loadList(false), [loadList])

  const checkForChanges = useCallback(async () => {
    if (document.hidden || inFlight.current) return
    try {
      const response = await authenticatedFetch('/api/inspections/revision')
      if (!response.ok) return
      const revision = await response.json()
      const stamp = `${revision.total}:${revision.latestId}:${revision.lastChange}`
      if (stamp === lastRevision.current) return
      lastRevision.current = stamp
      await loadList(true)
    } catch {
      // Silent on purpose. A failed revision check is not worth an error banner
      // in front of a panel; the next tick retries, and a genuinely dead backend
      // surfaces through the full fetch instead.
    }
  }, [authenticatedFetch, loadList])

  useEffect(() => {
    loadList(false)
    checkForChanges()

    const timer = setInterval(checkForChanges, POLL_INTERVAL_MS)
    // Catch up the moment the tab is focused again, rather than waiting out the
    // interval -- switching back to the dashboard should show current data.
    document.addEventListener('visibilitychange', checkForChanges)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', checkForChanges)
    }
  }, [loadList, checkForChanges])

  return { inspections, isLoading, error, refresh, dataSource: 'MariaDB' }
}
