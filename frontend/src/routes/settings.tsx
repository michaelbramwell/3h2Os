import { useState, useEffect } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from 'react-oidc-context'
import { ArrowLeft, RefreshCw, Check, Lock } from 'lucide-react'
import { getProfile, patchProfile, patchSyncPrefs, syncProfileNow } from '../lib/api'
import type { UserProfile, ProfileSyncPrefs } from '../types/schema'
import { formatInstant } from '../lib/dateTime'

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPace(mps: number | null): string {
  if (mps === null || mps === 0) return '—'
  const secPerKm = 1000 / mps
  const m = Math.floor(secPerKm / 60)
  const s = Math.round(secPerKm % 60)
  return `${m}:${s.toString().padStart(2, '0')} /km`
}

function formatDate(iso: string | null): string {
  if (!iso) return 'Never'
  try {
    return formatInstant(iso, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    // Defensive fallback for legacy naive timestamps without an offset.
    return new Date(iso).toLocaleString()
  }
}

// Which source (if any) owns a given field. Only Strava remains as an
// automatic sync source now that the Garmin integration has been removed.
function ownerOf(prefs: ProfileSyncPrefs, field: keyof UserProfile): 'strava' | null {
  const stravaFields: Array<keyof ProfileSyncPrefs['strava']> = ['weight', 'ftp', 'hr_zones']
  const stravaKey = field as keyof ProfileSyncPrefs['strava']
  if (stravaFields.includes(stravaKey) && prefs.strava[stravaKey]) return 'strava'
  return null
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface FieldRowProps {
  label: string
  value: string | number | null | undefined
  owner: 'strava' | null
  editNode?: React.ReactNode
}

function FieldRow({ label, value, owner, editNode }: FieldRowProps) {
  const badge = owner ? (
    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide bg-orange-100 text-orange-700">
      {owner}
    </span>
  ) : null

  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-600 w-44">{label}</span>
        {badge}
      </div>
      <div className="flex items-center gap-2">
        {owner ? (
          <span className="text-sm font-medium text-slate-800 flex items-center gap-1">
            <Lock size={12} className="text-slate-400" />
            {value ?? '—'}
          </span>
        ) : editNode ?? (
          <span className="text-sm font-medium text-slate-800">{value ?? '—'}</span>
        )}
      </div>
    </div>
  )
}

interface ToggleProps {
  label: string
  checked: boolean
  disabled?: boolean
  onChange: (v: boolean) => void
}

function Toggle({ label, checked, disabled, onChange }: ToggleProps) {
  return (
    <label className={`flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0 ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}>
      <span className="text-sm text-slate-700">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none ${checked ? 'bg-blue-600' : 'bg-slate-300'} ${disabled ? '' : 'hover:opacity-90'}`}
      >
        <span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0 transition-transform ${checked ? 'translate-x-4' : 'translate-x-0'}`} />
      </button>
    </label>
  )
}

// ---------------------------------------------------------------------------
// Editable number input — saves on blur
// ---------------------------------------------------------------------------

interface EditableNumberProps {
  value: number | null
  onSave: (v: number | null) => void
  placeholder?: string
  min?: number
  max?: number
}

function EditableNumber({ value, onSave, placeholder, min, max }: EditableNumberProps) {
  const [draft, setDraft] = useState<string>(value !== null ? String(value) : '')
  const [saved, setSaved] = useState(false)

  // Keep draft in sync when the underlying profile value changes (e.g. after a
  // sync-now refetch), but only when the field is not being actively edited.
  const [isFocused, setIsFocused] = useState(false)
  useEffect(() => {
    if (!isFocused) {
      setDraft(value !== null ? String(value) : '')
    }
  }, [value, isFocused])

  const commit = () => {
    const parsed = draft === '' ? null : parseFloat(draft)
    onSave(parsed)
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  return (
    <div className="flex items-center gap-1.5">
      <input
        type="number"
        className="w-24 rounded border border-slate-300 px-2 py-1 text-sm text-slate-800 focus:border-blue-500 focus:outline-none"
        value={draft}
        min={min}
        max={max}
        placeholder={placeholder}
        onChange={e => setDraft(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => { setIsFocused(false); commit(); }}
        onKeyDown={e => e.key === 'Enter' && commit()}
      />
      {saved && <Check size={14} className="text-green-500" />}
    </div>
  )
}

interface EditableSelectProps {
  value: string | null
  options: { value: string; label: string }[]
  onSave: (v: string | null) => void
}

function EditableSelect({ value, options, onSave }: EditableSelectProps) {
  return (
    <select
      className="rounded border border-slate-300 px-2 py-1 text-sm text-slate-800 focus:border-blue-500 focus:outline-none"
      value={value ?? ''}
      onChange={e => onSave(e.target.value || null)}
    >
      <option value="">—</option>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

function SettingsPage() {
  const auth = useAuth()
  const queryClient = useQueryClient()
  const [syncMsg, setSyncMsg] = useState<string | null>(null)

  const { data: profile, isLoading, error } = useQuery<UserProfile>({
    queryKey: ['profile'],
    queryFn: getProfile,
    enabled: auth.isAuthenticated,
  })

  const patchMutation = useMutation({
    mutationFn: (data: Parameters<typeof patchProfile>[0]) => patchProfile(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  })

  const prefsMutation = useMutation({
    mutationFn: ({ source, field, enabled }: { source: 'strava'; field: string; enabled: boolean }) =>
      patchSyncPrefs(source, field, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  })

  const syncMutation = useMutation({
    mutationFn: () => syncProfileNow(),
    onSuccess: (data) => {
      setSyncMsg(data.message)
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      setTimeout(() => setSyncMsg(null), 4000)
    },
    onError: (e: Error) => {
      setSyncMsg(`Sync failed: ${e.message}`)
      setTimeout(() => setSyncMsg(null), 4000)
    },
  })

  if (!auth.isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-500">Please sign in to view settings.</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-6 h-6 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-red-500">Failed to load profile.</p>
      </div>
    )
  }

  const prefs = profile.sync_prefs

  const patch = (field: keyof UserProfile, value: number | string | null) => {
    patchMutation.mutate({ [field]: value } as Parameters<typeof patchProfile>[0])
  }

  const toggle = (source: 'strava', field: string, enabled: boolean) => {
    prefsMutation.mutate({ source, field, enabled })
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="max-w-2xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-center gap-3">
          <Link to="/" className="p-1.5 rounded-full hover:bg-slate-200 transition text-slate-500">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-xl font-bold text-slate-800">Settings</h1>
        </div>

        {/* ── Section 1: Athlete Profile ─────────────────────────────────── */}
        <section className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-1">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Athlete Profile</h2>

          <FieldRow
            label="Age"
            value={profile.age}
            owner={null}
            editNode={
              <EditableNumber
                value={profile.age}
                min={10} max={100}
                placeholder="e.g. 35"
                onSave={v => patch('age', v)}
              />
            }
          />
          <FieldRow
            label="Gender"
            value={profile.gender}
            owner={null}
            editNode={
              <EditableSelect
                value={profile.gender}
                options={[
                  { value: 'male', label: 'Male' },
                  { value: 'female', label: 'Female' },
                  { value: 'other', label: 'Other' },
                  { value: 'unknown', label: 'Unknown' },
                ]}
                onSave={v => patch('gender', v)}
              />
            }
          />
          <FieldRow
            label="Height (cm)"
            value={profile.height_cm}
            owner={null}
            editNode={
              <EditableNumber
                value={profile.height_cm}
                min={50} max={300}
                placeholder="e.g. 178"
                onSave={v => patch('height_cm', v)}
              />
            }
          />
          <FieldRow
            label="Weight (kg)"
            value={profile.weight_kg !== null ? `${profile.weight_kg} kg` : null}
            owner={ownerOf(prefs, 'weight_kg')}
            editNode={
              <EditableNumber
                value={profile.weight_kg}
                min={20} max={300}
                placeholder="e.g. 72.5"
                onSave={v => patch('weight_kg', v)}
              />
            }
          />
          <FieldRow
            label="Experience level"
            value={profile.experience_level}
            owner={null}
            editNode={
              <EditableSelect
                value={profile.experience_level}
                options={[
                  { value: 'beginner', label: 'Beginner' },
                  { value: 'intermediate', label: 'Intermediate' },
                  { value: 'advanced', label: 'Advanced' },
                  { value: 'elite', label: 'Elite' },
                ]}
                onSave={v => patch('experience_level', v)}
              />
            }
          />
          <FieldRow
            label="Training days/week"
            value={profile.weekly_availability}
            owner={null}
            editNode={
              <EditableNumber
                value={profile.weekly_availability}
                min={1} max={7}
                placeholder="e.g. 5"
                onSave={v => patch('weekly_availability', v)}
              />
            }
          />

          <div className="pt-3 border-t border-slate-100 mt-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Performance metrics</h3>
          </div>

          <FieldRow
            label="Resting HR (bpm)"
            value={profile.resting_hr}
            owner={null}
            editNode={
              <EditableNumber
                value={profile.resting_hr}
                min={30} max={120}
                placeholder="e.g. 52"
                onSave={v => patch('resting_hr', v)}
              />
            }
          />
          <FieldRow
            label="FTP (watts)"
            value={profile.ftp}
            owner={ownerOf(prefs, 'ftp')}
            editNode={
              <EditableNumber
                value={profile.ftp}
                min={50} max={600}
                placeholder="e.g. 220"
                onSave={v => patch('ftp', v)}
              />
            }
          />
          <FieldRow
            label="VO2max (ml/kg/min)"
            value={profile.vo2max !== null ? profile.vo2max?.toFixed(1) : null}
            owner={null}
            editNode={
              <EditableNumber
                value={profile.vo2max}
                min={20} max={90}
                placeholder="e.g. 52.0"
                onSave={v => patch('vo2max', v)}
              />
            }
          />
          <FieldRow
            label="Lactate threshold HR"
            value={profile.lactate_threshold_hr !== null ? `${profile.lactate_threshold_hr} bpm` : null}
            owner={null}
            editNode={
              <EditableNumber
                value={profile.lactate_threshold_hr}
                min={80} max={220}
                placeholder="e.g. 162"
                onSave={v => patch('lactate_threshold_hr', v)}
              />
            }
          />
          <FieldRow
            label="Lactate threshold pace"
            value={formatPace(profile.lactate_threshold_pace)}
            owner={null}
          />
        </section>

        {/* ── Section 2: Data Sources ─────────────────────────────────────── */}
        <section className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Data Sources</h2>

          {/* Strava */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-orange-500" />
              <span className="text-sm font-semibold text-slate-700">Strava</span>
              <span className="text-xs text-slate-400">(syncs daily + on each activity import)</span>
            </div>
            <div className="pl-4 space-y-0">
              <Toggle
                label="Weight"
                checked={prefs.strava.weight}
                onChange={v => toggle('strava', 'weight', v)}
              />
              <Toggle
                label="FTP (watts)"
                checked={prefs.strava.ftp}
                onChange={v => toggle('strava', 'ftp', v)}
              />
              <Toggle
                label="HR zones"
                checked={prefs.strava.hr_zones}
                onChange={v => toggle('strava', 'hr_zones', v)}
              />
            </div>
          </div>

          <p className="mt-4 text-xs text-slate-400 leading-relaxed">
            When a source toggle is ON, that field is managed automatically and cannot be edited manually.
          </p>
        </section>

        {/* ── Section 3: Sync ─────────────────────────────────────────────── */}
        <section className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Sync</h2>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-700 font-medium">Last synced</p>
              <p className="text-xs text-slate-400 mt-0.5">{formatDate(profile.profile_last_synced_at)}</p>
            </div>
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-sm transition"
            >
              <RefreshCw size={14} className={syncMutation.isPending ? 'animate-spin' : ''} />
              {syncMutation.isPending ? 'Syncing…' : 'Sync now'}
            </button>
          </div>

          {syncMsg && (
            <div className="mt-3 text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
              {syncMsg}
            </div>
          )}

          <p className="mt-4 text-xs text-slate-400 leading-relaxed">
            Strava is synced automatically each day. "Sync now" triggers a fresh Strava profile pull immediately.
          </p>
        </section>

      </div>
    </div>
  )
}
