import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Star, Bookmark, ShoppingCart, GlassWater, Link2, Check, Hourglass, Frown, Droplet, Leaf } from 'lucide-react'
import type { Cocktail } from '../api/cocktails'
import { useFavorite, useBookmark, useCart, useRate } from '../hooks/useCocktails'
import { useAuth } from '../context/AuthContext'

interface Props {
  cocktail: Cocktail
}

export default function CocktailCard({ cocktail: c }: Props) {
  const { user } = useAuth()
  const favorite = useFavorite()
  const bookmark = useBookmark()
  const cart = useCart()
  const rate = useRate()

  const [showIngredients, setShowIngredients] = useState(false)
  const [showRating, setShowRating] = useState(false)
  const [hoverRating, setHoverRating] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)

  function handleShare() {
    navigator.clipboard.writeText(`${window.location.origin}/cocktail/${c.cocktail_id}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  // Deduplicate by mapped_ingredient, merging garnish/non-garnish variants
  const dedupedIngredients = (() => {
    const seen = new Map<string, { displayName: string; isGarnish: boolean; hasNonGarnish: boolean; inBar: boolean; quantity: string | null; unit: string | null }>()
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
  const canMakePercent = dedupedIngredients.length > 0
    ? Math.round((haveIngredients.length / dedupedIngredients.length) * 100)
    : 0

  return (
    <div className="card-cocktail flex flex-col">
      {/* Image — links to detail page */}
      <Link to={`/cocktail/${c.cocktail_id}`} className="relative overflow-hidden h-48 bg-parchment-200 block">
        {c.image ? (
          <img
            src={c.image}
            alt={c.recipe_name}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <GlassWater className="w-16 h-16 text-parchment-400" />
          </div>
        )}
        {/* Alcohol type badge */}
        {c.alcohol_type && (
          <span className="absolute top-2 left-2 badge-amber capitalize text-xs">
            {c.alcohol_type}
          </span>
        )}
        {/* Source favicon badge */}
        {c.source && (
          <img
            src={`https://www.google.com/s2/favicons?domain=${c.source}&sz=32`}
            alt={c.source}
            title={c.source}
            className="absolute top-2 right-2 w-6 h-6 rounded-full bg-white/90 p-0.5 shadow-sm"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        )}
        {/* Can-make bar */}
        {user && c.ingredients.length > 0 && (
          <div className="absolute bottom-0 left-0 right-0 h-1.5 bg-black/50">
            <div
              className="h-full bg-amber transition-all duration-300 shadow-[0_0_6px_2px_rgba(192,125,16,0.7)]"
              style={{ width: `${canMakePercent}%` }}
            />
          </div>
        )}
      </Link>

      {/* Body */}
      <div className="p-4 flex flex-col flex-1 gap-3">
        {/* Name + share */}
        <div className="flex items-start justify-between gap-2">
          <Link
            to={`/cocktail/${c.cocktail_id}`}
            className="font-display text-xl text-mahogany leading-tight line-clamp-2 hover:text-amber transition-colors"
          >
            {c.recipe_name}
          </Link>
          <button
            onClick={handleShare}
            className="shrink-0 text-bark hover:text-amber transition-colors mt-0.5"
            title="Copy share link"
          >
            {copied
              ? <Check className="w-4 h-4 text-green-600" />
              : <Link2 className="w-4 h-4" />}
          </button>
        </div>

        {/* NPS / rating */}
        {c.num_ratings > 0 && (
          <div className="flex items-center gap-2 text-xs text-bark font-body">
            <Star className="w-3.5 h-3.5 text-amber fill-amber" />
            <span className="font-semibold text-mahogany">{c.avg_rating.toFixed(1)}</span>
            <span>({c.num_ratings} rating{c.num_ratings !== 1 ? 's' : ''})</span>
            {c.nps !== 0 && (
              <span className={`ml-auto font-semibold ${c.nps >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                NPS {c.nps > 0 ? '+' : ''}{c.nps.toFixed(0)}
              </span>
            )}
          </div>
        )}

        {/* Action row */}
        {user && (
          <div className="flex items-center gap-1 mt-auto pt-2 border-t border-parchment-200">
            {/* Favorite */}
            <button
              onClick={() => favorite.mutate({ id: c.cocktail_id, val: !c.favorited })}
              className={`p-2 rounded-lg transition-colors ${
                c.favorited
                  ? 'text-amber bg-amber/10'
                  : 'text-bark hover:text-amber hover:bg-amber/10'
              }`}
              title={c.favorited ? 'Remove favorite' : 'Add to favorites'}
            >
              <Star className={`w-4 h-4 ${c.favorited ? 'fill-amber' : ''}`} />
            </button>

            {/* Bookmark */}
            <button
              onClick={() => bookmark.mutate({ id: c.cocktail_id, val: !c.bookmarked })}
              className={`p-2 rounded-lg transition-colors ${
                c.bookmarked
                  ? 'text-amber bg-amber/10'
                  : 'text-bark hover:text-amber hover:bg-amber/10'
              }`}
              title={c.bookmarked ? 'Remove bookmark' : 'Bookmark'}
            >
              <Bookmark className={`w-4 h-4 ${c.bookmarked ? 'fill-amber' : ''}`} />
            </button>

            {/* Cart */}
            <button
              onClick={() => cart.mutate({ id: c.cocktail_id, val: !c.in_cart })}
              className={`p-2 rounded-lg transition-colors ${
                c.in_cart
                  ? 'text-amber bg-amber/10'
                  : 'text-bark hover:text-amber hover:bg-amber/10'
              }`}
              title={c.in_cart ? 'Remove from tonight\'s cart' : 'Add to tonight\'s cart'}
            >
              <ShoppingCart className={`w-4 h-4 ${c.in_cart ? 'fill-amber' : ''}`} />
            </button>

            {/* Ingredients */}
            <button
              onClick={() => setShowIngredients(!showIngredients)}
              className={`p-2 rounded-lg transition-colors ${showIngredients ? 'bg-parchment-200' : 'hover:bg-parchment-100'}`}
              title={
                !user || c.ingredients.length === 0 ? 'View ingredients' :
                missingIngredients.length === 0 ? 'You can make this!' :
                haveIngredients.length === 0 ? 'Missing all ingredients' :
                'You have some ingredients'
              }
            >
              {!user || c.ingredients.length === 0 ? (
                <GlassWater className="w-4 h-4 text-bark" />
              ) : missingIngredients.length === 0 ? (
                <GlassWater className="w-4 h-4 text-green-600" />
              ) : haveIngredients.length === 0 ? (
                <Frown className="w-4 h-4 text-bark" />
              ) : (
                <Hourglass className="w-4 h-4 text-amber" />
              )}
            </button>

            {/* Rate */}
            <button
              onClick={() => setShowRating(!showRating)}
              className={`ml-auto text-xs font-body font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                c.user_rating != null
                  ? 'bg-amber/10 text-amber'
                  : 'bg-parchment-100 text-bark hover:bg-amber/10 hover:text-amber'
              }`}
            >
              {c.user_rating != null ? `Rated ${c.user_rating}/10` : 'Rate'}
            </button>
          </div>
        )}

        {/* Ingredients panel */}
        {showIngredients && (
          <div className="mt-1 rounded-lg bg-parchment-100 p-3 text-xs font-body space-y-1">
            {haveIngredients.length > 0 && (
              <div>
                <p className="font-semibold text-green-700 mb-1">In your bar</p>
                {haveIngredients.map(i => (
                  <div key={i.displayName} className="flex items-center gap-1.5 text-mahogany">
                    {i.hasNonGarnish && <Droplet className="w-2.5 h-2.5 text-green-600 shrink-0" />}
                    {i.isGarnish && <Leaf className="w-2.5 h-2.5 text-green-500 shrink-0" style={i.hasNonGarnish ? {marginLeft: '-2px'} : undefined} />}
                    <span>{i.displayName}</span>
                    {i.quantity && <span className="text-bark ml-auto">{i.quantity}{i.unit ? ` ${i.unit}` : ''}</span>}
                  </div>
                ))}
              </div>
            )}
            {missingIngredients.length > 0 && (
              <div className={haveIngredients.length > 0 ? 'pt-1 border-t border-parchment-200' : ''}>
                <p className="font-semibold text-bark mb-1">Missing</p>
                {missingIngredients.map(i => (
                  <div key={i.displayName} className="flex items-center gap-1.5 text-bark">
                    {i.hasNonGarnish && <Droplet className="w-2.5 h-2.5 shrink-0 opacity-40" />}
                    {i.isGarnish && <Leaf className="w-2.5 h-2.5 shrink-0 opacity-40" style={i.hasNonGarnish ? {marginLeft: '-2px'} : undefined} />}
                    <span>{i.displayName}</span>
                    {i.quantity && <span className="ml-auto">{i.quantity}{i.unit ? ` ${i.unit}` : ''}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Rating panel */}
        {showRating && user && (
          <div className="mt-1 rounded-lg bg-parchment-100 p-3">
            <p className="text-xs font-body font-semibold text-mahogany mb-2">
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
                  className={`flex-1 h-6 rounded text-xs font-body font-semibold transition-colors ${
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
      </div>
    </div>
  )
}
