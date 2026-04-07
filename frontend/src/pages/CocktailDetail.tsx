import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Star, Bookmark, ShoppingCart, GlassWater,
  ExternalLink, Link2, Check, Droplet, Leaf, Hourglass, Frown,
} from 'lucide-react'
import { useCocktail, useFavorite, useBookmark, useCart, useRate } from '../hooks/useCocktails'
import { useAuth } from '../context/AuthContext'

export default function CocktailDetail() {
  const { id } = useParams<{ id: string }>()
  const cocktailId = parseInt(id ?? '0', 10)
  const { data: c, isLoading, isError } = useCocktail(cocktailId)
  const { user } = useAuth()

  const favorite = useFavorite()
  const bookmark = useBookmark()
  const cart = useCart()
  const rate = useRate()

  const [showRating, setShowRating] = useState(false)
  const [hoverRating, setHoverRating] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)

  function handleShare() {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-16 animate-pulse">
        <div className="h-5 bg-parchment-200 rounded w-24 mb-6" />
        <div className="h-72 bg-parchment-200 rounded-xl mb-6" />
        <div className="h-8 bg-parchment-200 rounded w-2/3 mb-3" />
        <div className="h-4 bg-parchment-200 rounded w-1/3 mb-6" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-4 bg-parchment-200 rounded w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !c) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
        <GlassWater className="w-16 h-16 text-parchment-400 mx-auto mb-4" />
        <p className="font-display text-2xl text-mahogany">Cocktail not found</p>
        <p className="font-body text-bark mt-1 mb-6">This recipe may have been removed.</p>
        <Link to="/" className="btn-amber">Browse cocktails</Link>
      </div>
    )
  }

  // Deduplicate ingredients (same logic as CocktailCard)
  const dedupedIngredients = (() => {
    const seen = new Map<string, {
      displayName: string; isGarnish: boolean; hasNonGarnish: boolean;
      inBar: boolean; quantity: string | null; unit: string | null
    }>()
    for (const i of c.ingredients) {
      const key = i.mapped_ingredient ?? i.ingredient
      const isGarnishEntry = i.unit === 'garnish'
      const existing = seen.get(key)
      if (existing) {
        if (isGarnishEntry) existing.isGarnish = true
        if (!isGarnishEntry) {
          existing.hasNonGarnish = true
          if (!existing.quantity) { existing.quantity = i.quantity; existing.unit = i.unit }
        }
        if (i.in_bar) existing.inBar = true
      } else {
        seen.set(key, {
          displayName: key,
          isGarnish: isGarnishEntry,
          hasNonGarnish: !isGarnishEntry,
          inBar: i.in_bar,
          quantity: !isGarnishEntry ? i.quantity : null,
          unit: !isGarnishEntry ? i.unit : null,
        })
      }
    }
    return Array.from(seen.values())
  })()

  const haveIngredients = dedupedIngredients.filter(i => i.inBar)
  const missingIngredients = dedupedIngredients.filter(i => !i.inBar)

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      {/* Back + Share */}
      <div className="flex items-center justify-between mb-6">
        <Link to="/" className="flex items-center gap-1.5 font-body text-sm text-bark hover:text-mahogany transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Browse
        </Link>
        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 font-body text-sm text-bark hover:text-amber transition-colors"
          title="Copy share link"
        >
          {copied ? (
            <><Check className="w-4 h-4 text-green-600" /><span className="text-green-600">Copied!</span></>
          ) : (
            <><Link2 className="w-4 h-4" />Share</>
          )}
        </button>
      </div>

      {/* Hero image */}
      <div className="relative overflow-hidden rounded-xl bg-parchment-200 h-72 mb-6">
        {c.image ? (
          <img
            src={c.image}
            alt={c.recipe_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <GlassWater className="w-20 h-20 text-parchment-400" />
          </div>
        )}
        {c.alcohol_type && (
          <span className="absolute top-3 left-3 badge-amber capitalize">
            {c.alcohol_type}
          </span>
        )}
      </div>

      {/* Title row */}
      <div className="flex items-center justify-between gap-4 mb-2">
        <h1 className="font-display text-4xl text-mahogany leading-tight">
          {c.recipe_name}
        </h1>
        {c.link && (
          <a
            href={c.link}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 inline-flex items-center gap-2 btn-amber"
          >
            For Directions
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      {/* Ratings */}
      {c.num_ratings > 0 && (
        <div className="flex items-center gap-2 text-sm font-body text-bark mb-4">
          <Star className="w-4 h-4 text-amber fill-amber" />
          <span className="font-semibold text-mahogany">{c.avg_rating.toFixed(1)}</span>
          <span>({c.num_ratings} rating{c.num_ratings !== 1 ? 's' : ''})</span>
          {c.nps !== 0 && (
            <span className={`ml-2 font-semibold ${c.nps >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              NPS {c.nps > 0 ? '+' : ''}{c.nps.toFixed(0)}
            </span>
          )}
        </div>
      )}

      {/* Action row — logged-in only */}
      {user && (
        <div className="flex items-center gap-2 mb-6 pb-6 border-b border-parchment-200">
          <button
            onClick={() => favorite.mutate({ id: c.cocktail_id, val: !c.favorited })}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-body font-semibold transition-colors ${
              c.favorited ? 'bg-amber/10 text-amber' : 'bg-parchment-100 text-bark hover:bg-amber/10 hover:text-amber'
            }`}
          >
            <Star className={`w-4 h-4 ${c.favorited ? 'fill-amber' : ''}`} />
            {c.favorited ? 'Favorited' : 'Favorite'}
          </button>

          <button
            onClick={() => bookmark.mutate({ id: c.cocktail_id, val: !c.bookmarked })}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-body font-semibold transition-colors ${
              c.bookmarked ? 'bg-amber/10 text-amber' : 'bg-parchment-100 text-bark hover:bg-amber/10 hover:text-amber'
            }`}
          >
            <Bookmark className={`w-4 h-4 ${c.bookmarked ? 'fill-amber' : ''}`} />
            {c.bookmarked ? 'Bookmarked' : 'Bookmark'}
          </button>

          <button
            onClick={() => cart.mutate({ id: c.cocktail_id, val: !c.in_cart })}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-body font-semibold transition-colors ${
              c.in_cart ? 'bg-amber/10 text-amber' : 'bg-parchment-100 text-bark hover:bg-amber/10 hover:text-amber'
            }`}
          >
            <ShoppingCart className={`w-4 h-4 ${c.in_cart ? 'fill-amber' : ''}`} />
            {c.in_cart ? 'In cart' : 'Add to cart'}
          </button>

          <button
            onClick={() => setShowRating(!showRating)}
            className={`ml-auto px-3 py-1.5 rounded-lg text-sm font-body font-semibold transition-colors ${
              c.user_rating != null
                ? 'bg-amber/10 text-amber'
                : 'bg-parchment-100 text-bark hover:bg-amber/10 hover:text-amber'
            }`}
          >
            {c.user_rating != null ? `Rated ${c.user_rating}/10` : 'Rate'}
          </button>
        </div>
      )}

      {/* Rating panel */}
      {showRating && user && (
        <div className="mb-6 rounded-lg bg-parchment-100 p-4">
          <p className="text-sm font-body font-semibold text-mahogany mb-3">
            Your rating: {hoverRating ?? c.user_rating ?? '—'}/10
          </p>
          <div className="flex gap-1">
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                onMouseEnter={() => setHoverRating(i)}
                onMouseLeave={() => setHoverRating(null)}
                onClick={() => {
                  rate.mutate({ id: c.cocktail_id, rating: i })
                  setShowRating(false)
                }}
                className={`flex-1 h-8 rounded text-sm font-body font-semibold transition-colors ${
                  (hoverRating ?? c.user_rating ?? -1) >= i
                    ? 'bg-amber text-white'
                    : 'bg-parchment-200 text-bark hover:bg-amber/50'
                }`}
              >
                {i}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Ingredients */}
      {dedupedIngredients.length > 0 && (
        <div>
          <h2 className="font-display text-2xl text-mahogany mb-4">Ingredients</h2>
          <div className="rounded-xl bg-white border border-parchment-200 divide-y divide-parchment-200">
            {dedupedIngredients.map(i => (
              <div key={i.displayName} className="flex items-center gap-3 px-4 py-3">
                <div className="flex items-center gap-0.5 shrink-0">
                  {i.hasNonGarnish && (
                    <Droplet className={`w-3.5 h-3.5 ${i.inBar ? 'text-green-600' : 'text-parchment-400'}`} />
                  )}
                  {i.isGarnish && (
                    <Leaf className={`w-3.5 h-3.5 ${i.inBar ? 'text-green-500' : 'text-parchment-400'}`} />
                  )}
                </div>
                <span className={`font-body text-sm flex-1 ${i.inBar ? 'text-mahogany' : 'text-bark'}`}>
                  {i.displayName}
                </span>
                {i.quantity && (
                  <span className="font-body text-sm text-bark shrink-0">
                    {i.quantity}{i.unit ? ` ${i.unit}` : ''}
                  </span>
                )}
                {user && (
                  i.inBar
                    ? <span className="text-xs font-body text-green-600 font-semibold shrink-0">In bar</span>
                    : <span className="text-xs font-body text-parchment-400 shrink-0">Missing</span>
                )}
              </div>
            ))}
          </div>

          {/* Bar summary — logged-in only */}
          {user && dedupedIngredients.length > 0 && (
            <div className="mt-3 flex items-center gap-2 text-sm font-body text-bark">
              {missingIngredients.length === 0 ? (
                <><GlassWater className="w-4 h-4 text-green-600" /><span className="text-green-600 font-semibold">You can make this!</span></>
              ) : haveIngredients.length === 0 ? (
                <><Frown className="w-4 h-4" /><span>You're missing all ingredients</span></>
              ) : (
                <><Hourglass className="w-4 h-4 text-amber" /><span>You have <strong>{haveIngredients.length}</strong> of <strong>{dedupedIngredients.length}</strong> ingredients</span></>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
