import { Logo } from './Logo'

export function AppBrand() {
  return (
    <div className="flex items-center gap-3">
      <Logo size={36} />
      <div>
        <p className="text-lg font-bold text-slate-900 leading-tight">3h2Os</p>
        <p className="text-sm text-slate-500">Build your own running training plan</p>
      </div>
    </div>
  )
}

export function AppDescription() {
  return (
    <div className="space-y-2 text-sm text-slate-600 leading-relaxed">
      <p>
        A free tool for self-coached runners who want a structured, periodised training
        plan — not a generic PDF, not a spreadsheet, not a coached subscription. You set
        your goal race, your current fitness, and how many days a week you can train. The
        app builds a plan around you and tracks your Strava activities against it.
      </p>

    </div>
  )
}

export function AppFooter({ showPrivacy = false }: { showPrivacy?: boolean }) {
  return (
    <p className="text-xs text-slate-400">
      © {new Date().getFullYear()} 3h2Os
      {showPrivacy && (
        <>
          {' · '}
          <a href="/privacy" className="hover:underline">Privacy policy</a>
        </>
      )}
    </p>
  )
}
