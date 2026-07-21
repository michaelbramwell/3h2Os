import { createFileRoute } from '@tanstack/react-router'
import { useAuth } from 'react-oidc-context'
import { AppBrand, AppDescription, AppFooter } from '../components/AppShell'

export const Route = createFileRoute('/privacy')({
  component: PrivacyPolicy,
})

function PrivacyPolicy() {
  const auth = useAuth()

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center px-6 py-16">
      <div className="w-full max-w-xl space-y-10">
        <AppBrand />
        <AppDescription />

        <div className="space-y-6 text-sm text-slate-600 leading-relaxed">
          <div>
            <h1 className="text-base font-semibold text-slate-900 mb-1">Privacy Policy</h1>
            <p className="text-xs text-slate-400">Last updated: February 2026</p>
          </div>

          <p>
            We collect only what is needed to run the service: your name and email (via SSO),
            athlete profile data you enter, your training plans, and activity data synced from
            Strava with your explicit consent.
          </p>

          <div>
            <h2 className="font-semibold text-slate-800 mb-1">Strava</h2>
            <p>
              We request <code className="bg-slate-100 px-1 rounded text-xs">activity:read_all</code>{' '}
              and <code className="bg-slate-100 px-1 rounded text-xs">profile:read_all</code> to sync
              activities and your athlete profile. Tokens are stored server-side only. Disconnecting
              or revoking access in Strava deletes your tokens immediately. Your data is never sold
              or shared.
            </p>
          </div>

          <div>
            <h2 className="font-semibold text-slate-800 mb-1">Historical imported records</h2>
            <p>
              Previously imported activity records (including any synced from legacy integrations)
              may remain on your account as read-only history. They are no longer refreshed by any
              third-party integration and are kept only for your reference. You can delete them at
              any time from the activity list.
            </p>
          </div>

          <div>
            <h2 className="font-semibold text-slate-800 mb-1">Storage</h2>
            <p>
              Data is stored in an EU-based PostgreSQL database, encrypted in transit via TLS.
              Used only to generate and display your training plan. No advertising, no
              third-party sharing.
            </p>
          </div>

          <div>
            <h2 className="font-semibold text-slate-800 mb-1">Deletion</h2>
            <p>
              Email{' '}
              <a href="mailto:privacy@3h2os.com" className="text-blue-600 hover:underline">
                privacy@3h2os.com
              </a>{' '}
              to delete all your data at any time.
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-200">
          <button
            onClick={() => auth.signinRedirect()}
            className="text-sm text-blue-600 hover:underline"
          >
            Sign in to 3h2Os
          </button>
        </div>

        <AppFooter />
      </div>
    </div>
  )
}
