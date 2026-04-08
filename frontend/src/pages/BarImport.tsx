import { useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { GlassWater, ArrowLeft, Check, AlertCircle } from 'lucide-react'
import { useBarSharePreview, useImportBar } from '../hooks/useBar'
import { useAuth } from '../context/AuthContext'

const PREVIEW_LIMIT = 10

export default function BarImport() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const { user } = useAuth()

  const { data: preview, isLoading, isError } = useBarSharePreview(token)
  const importBar = useImportBar()
  const [imported, setImported] = useState<{ count: number; mode: string } | null>(null)

  async function handleImport(mode: 'add' | 'replace') {
    if (!token) return
    const result = await importBar.mutateAsync({ token, mode })
    setImported({ count: result.ingredients.length, mode })
  }

  if (!token) {
    return <ErrorState message="No share token provided." />
  }

  if (isLoading) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-24 pb-16 animate-pulse">
        <div className="h-5 bg-parchment-200 rounded w-24 mb-6" />
        <div className="h-8 bg-parchment-200 rounded w-2/3 mb-4" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-4 bg-parchment-200 rounded" />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !preview) {
    return <ErrorState message="This share link is invalid or has expired." />
  }

  if (imported) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-24 pb-16 text-center">
        <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
          <Check className="w-8 h-8 text-green-600" />
        </div>
        <h1 className="font-display text-3xl text-mahogany mb-2">Bar imported!</h1>
        <p className="font-body text-bark mb-6">
          {imported.mode === 'replace'
            ? `Your bar now has ${imported.count} ingredient${imported.count !== 1 ? 's' : ''}.`
            : `${imported.count} ingredient${imported.count !== 1 ? 's' : ''} are now in your bar.`}
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
          <GlassWater className="w-6 h-6 text-amber" />
        </div>
        <div>
          <h1 className="font-display text-3xl text-mahogany leading-tight">Someone shared their bar</h1>
          <p className="font-body text-sm text-bark mt-0.5">
            From <span className="font-semibold text-mahogany">{preview.owner_email}</span>
          </p>
        </div>
      </div>

      {/* Ingredient preview */}
      <div className="rounded-xl bg-white border border-parchment-200 mb-6">
        <div className="px-4 py-3 border-b border-parchment-200">
          <p className="font-body text-sm font-semibold text-mahogany">
            {preview.ingredient_count} ingredient{preview.ingredient_count !== 1 ? 's' : ''}
          </p>
        </div>
        <ul className="divide-y divide-parchment-100">
          {preview.ingredients.slice(0, PREVIEW_LIMIT).map(i => (
            <li key={i.ingredient_id} className="flex items-center justify-between px-4 py-2.5">
              <span className="font-body text-sm text-mahogany">{i.mapped_ingredient}</span>
              {i.alcohol_type && (
                <span className="badge-outline capitalize text-xs">{i.alcohol_type}</span>
              )}
            </li>
          ))}
        </ul>
        {preview.ingredient_count > PREVIEW_LIMIT && (
          <div className="px-4 py-2.5 border-t border-parchment-100">
            <p className="font-body text-sm text-bark">
              +{preview.ingredient_count - PREVIEW_LIMIT} more ingredients
            </p>
          </div>
        )}
      </div>

      {!user ? (
        <div className="text-center">
          <p className="font-body text-sm text-bark mb-4">Sign in to import this bar into your account.</p>
          <Link
            to={`/login?next=/bar/import?token=${token}`}
            className="btn-amber"
          >
            Sign in to import
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="font-body text-xs text-bark text-center">How would you like to import this bar?</p>
          <button
            onClick={() => handleImport('add')}
            disabled={importBar.isPending}
            className="w-full px-4 py-3 rounded-xl bg-amber text-white font-body font-semibold text-sm hover:bg-amber/90 transition-colors disabled:opacity-40"
          >
            Merge into my bar
            <span className="block font-normal text-xs opacity-80 mt-0.5">
              Add these ingredients alongside what you already have
            </span>
          </button>
          <button
            onClick={() => handleImport('replace')}
            disabled={importBar.isPending}
            className="w-full px-4 py-3 rounded-xl bg-parchment-100 text-mahogany font-body font-semibold text-sm hover:bg-parchment-200 transition-colors disabled:opacity-40 border border-parchment-300"
          >
            Replace my bar
            <span className="block font-normal text-xs text-bark mt-0.5">
              Start fresh with only these ingredients
            </span>
          </button>
        </div>
      )}
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="max-w-lg mx-auto px-4 pt-24 pb-16 text-center">
      <AlertCircle className="w-16 h-16 text-parchment-400 mx-auto mb-4" />
      <p className="font-display text-2xl text-mahogany mb-2">Link unavailable</p>
      <p className="font-body text-bark mb-6">{message}</p>
      <Link to="/" className="btn-amber">Go home</Link>
    </div>
  )
}
