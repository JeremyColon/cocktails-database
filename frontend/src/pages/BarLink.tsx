import { useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Users, ArrowLeft, Check, AlertCircle } from 'lucide-react'
import { useBarLinkPreview, useAcceptLink } from '../hooks/useBar'
import { useAuth } from '../context/AuthContext'

export default function BarLink() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const { user } = useAuth()

  const { data: preview, isLoading, isError } = useBarLinkPreview(token)
  const acceptLink = useAcceptLink()
  const [accepted, setAccepted] = useState(false)
  const [acceptError, setAcceptError] = useState<string | null>(null)

  async function handleAccept(mode: 'merge' | 'replace') {
    if (!token) return
    setAcceptError(null)
    try {
      await acceptLink.mutateAsync({ token, mode })
      setAccepted(true)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Something went wrong. Please try again.'
      setAcceptError(msg)
    }
  }

  if (!token) return <ErrorState message="No invite token provided." />

  if (isLoading) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-24 pb-16 animate-pulse">
        <div className="h-5 bg-parchment-200 rounded w-24 mb-6" />
        <div className="h-8 bg-parchment-200 rounded w-2/3 mb-4" />
        <div className="h-4 bg-parchment-200 rounded w-1/2" />
      </div>
    )
  }

  if (isError || !preview) return <ErrorState message="This invite link is invalid or has expired." />

  if (accepted) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-24 pb-16 text-center">
        <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
          <Check className="w-8 h-8 text-green-600" />
        </div>
        <h1 className="font-display text-3xl text-mahogany mb-2">Bars linked!</h1>
        <p className="font-body text-bark mb-6">
          You're now sharing a bar with {preview.inviter_email}. Any changes either of you make will be reflected for both.
        </p>
        <Link to="/mybar" className="btn-amber">View my bar</Link>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 pt-24 pb-16">
      <Link
        to="/"
        className="flex items-center gap-1.5 font-body text-sm text-bark hover:text-mahogany transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Browse
      </Link>

      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-full bg-amber/10 flex items-center justify-center shrink-0">
          <Users className="w-6 h-6 text-amber" />
        </div>
        <div>
          <h1 className="font-display text-3xl text-mahogany leading-tight">Household bar invite</h1>
          <p className="font-body text-sm text-bark mt-0.5">
            From <span className="font-semibold text-mahogany">{preview.inviter_email}</span>
          </p>
        </div>
      </div>

      <div className="rounded-xl bg-parchment-100 border border-parchment-200 px-4 py-3 mb-6">
        <p className="font-body text-sm text-bark">
          Linking bars means you and {preview.inviter_email} will share one bar inventory. Either person can add or remove ingredients and both will see the change immediately.
        </p>
        <p className="font-body text-sm text-mahogany font-semibold mt-2">
          Your current bar cannot be recovered after linking.
        </p>
      </div>

      {!user ? (
        <div className="text-center">
          <p className="font-body text-sm text-bark mb-4">Sign in to link your bar.</p>
          <Link to={`/login?next=/bar/link?token=${token}`} className="btn-amber">
            Sign in to link
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="font-body text-xs text-bark text-center">How would you like to combine your bars?</p>
          <button
            onClick={() => handleAccept('merge')}
            disabled={acceptLink.isPending}
            className="w-full px-4 py-3 rounded-xl bg-amber text-white font-body font-semibold text-sm hover:bg-amber/90 transition-colors disabled:opacity-40"
          >
            Merge bars
            <span className="block font-normal text-xs opacity-80 mt-0.5">
              Your unique ingredients are added to {preview.inviter_email}'s bar
            </span>
          </button>
          <button
            onClick={() => handleAccept('replace')}
            disabled={acceptLink.isPending}
            className="w-full px-4 py-3 rounded-xl bg-parchment-100 text-mahogany font-body font-semibold text-sm hover:bg-parchment-200 transition-colors disabled:opacity-40 border border-parchment-300"
          >
            Replace my bar
            <span className="block font-normal text-xs text-bark mt-0.5">
              Adopt {preview.inviter_email}'s bar as-is; your current ingredients are discarded
            </span>
          </button>
          {acceptError && (
            <p className="font-body text-sm text-red-600 text-center">{acceptError}</p>
          )}
        </div>
      )}
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="max-w-lg mx-auto px-4 pt-24 pb-16 text-center">
      <AlertCircle className="w-16 h-16 text-parchment-400 mx-auto mb-4" />
      <p className="font-display text-2xl text-mahogany mb-2">Invite unavailable</p>
      <p className="font-body text-bark mb-6">{message}</p>
      <Link to="/" className="btn-amber">Go home</Link>
    </div>
  )
}
