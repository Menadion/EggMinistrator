import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'

export function useDatabaseInspections() {
  const { authenticatedFetch } = useAuth()
  const [inspections, setInspections] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const response = await authenticatedFetch('/api/inspections')
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.error || 'Unable to load inspection records from MariaDB.')
      setInspections(result.inspections || [])
    } catch (requestError) {
      setError(requestError.message || 'Unable to load inspection records from MariaDB.')
    } finally {
      setIsLoading(false)
    }
  }, [authenticatedFetch])

  useEffect(() => { refresh() }, [refresh])

  return { inspections, isLoading, error, refresh, dataSource: 'MariaDB' }
}
