import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useRef } from 'react'
import { useAuth } from 'react-oidc-context'
import { exchangeStravaCode } from '../lib/api'
import { toast } from 'sonner'

export const Route = createFileRoute('/strava/callback')({
    validateSearch: (search: Record<string, unknown>) => ({
        code: (search.code as string) ?? '',
        state: (search.state as string) ?? '',
        error: (search.error as string) ?? '',
        scope: (search.scope as string) ?? '',
    }),
    component: StravaCallbackPage,
})

function StravaCallbackPage() {
    const { code, state, error } = Route.useSearch()
    const navigate = useNavigate()
    const auth = useAuth()
    const attempted = useRef(false)

    useEffect(() => {
        // Wait until auth is loaded before attempting the exchange
        if (auth.isLoading) return
        // Only run once
        if (attempted.current) return
        attempted.current = true

        async function exchange() {
            if (error) {
                toast.error(`Strava connection failed: ${error}`)
                navigate({ to: '/' })
                return
            }

            if (!code || !state) {
                toast.error('Strava connection failed: missing parameters')
                navigate({ to: '/' })
                return
            }

            if (!auth.isAuthenticated) {
                // Not logged in — redirect to home, which will trigger login
                toast.error('You must be logged in to connect Strava')
                navigate({ to: '/' })
                return
            }

            try {
                await exchangeStravaCode(code, state)
                toast.success('Strava connected')
            } catch {
                toast.error('Strava connection failed')
            }

            navigate({ to: '/' })
        }

        exchange()
    }, [auth.isLoading, auth.isAuthenticated, code, state, error, navigate])

    return (
        <div className="min-h-screen flex items-center justify-center text-slate-500 text-sm">
            Connecting Strava…
        </div>
    )
}
