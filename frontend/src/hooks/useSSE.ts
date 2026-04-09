import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { userManager } from '../lib/auth'

const API_BASE =
  import.meta.env.VITE_API_URL ||
  (window.location.hostname === '3h2os.com'
    ? 'https://3h2os.com'
    : 'http://localhost:8000')

/**
 * Connects to the backend SSE stream at /api/events and listens for
 * server-pushed notifications. On receiving an `activities_updated` event,
 * invalidates the `actuals` query so the UI refetches fresh data.
 *
 * The connection is established only when the user is authenticated and
 * is automatically closed on unmount or when authentication is lost.
 */
export function useSSE(enabled: boolean) {
  const queryClient = useQueryClient()
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!enabled) return

    let closed = false

    async function connect() {
      const user = await userManager.getUser()
      if (!user?.access_token || closed) return

      const url = `${API_BASE}/api/events?token=${encodeURIComponent(user.access_token)}`
      const es = new EventSource(url)
      esRef.current = es

      es.addEventListener('activities_updated', () => {
        queryClient.invalidateQueries({ queryKey: ['actuals'] })
      })

      es.onerror = () => {
        // EventSource reconnects automatically; no explicit action needed.
        // Log at debug level only — this fires on normal network hiccups.
      }
    }

    connect()

    return () => {
      closed = true
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [enabled, queryClient])
}
