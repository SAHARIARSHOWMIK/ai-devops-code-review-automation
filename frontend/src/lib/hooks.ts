import { useCallback, useEffect, useState } from 'react'
import { get } from './api'

export function useApi<T>(path: string, initial: T) {
  const [data, setData] = useState<T>(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const reload = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await get<T>(path)) }
    catch (err) { setError(err instanceof Error ? err.message : 'Request failed') }
    finally { setLoading(false) }
  }, [path])
  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload, setData }
}
