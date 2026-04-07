import { type Dispatch, type SetStateAction } from 'react'
import { ChevronLeft, ChevronRight, GlassWater, Loader2, ShoppingCart, X } from 'lucide-react'
import { useCocktails, useClearCart } from '../hooks/useCocktails'
import { type CocktailFilters, DEFAULT_FILTERS } from '../api/cocktails'
import CocktailCard from '../components/CocktailCard'
import FilterPanel from '../components/FilterPanel'
import LegendPopover from '../components/LegendModal'

interface Props {
  filters: CocktailFilters
  setFilters: Dispatch<SetStateAction<CocktailFilters>>
}

export default function CocktailBrowser({ filters, setFilters }: Props) {
  const { data, isFetching, isError } = useCocktails(filters)
  const clearCart = useClearCart()

  const total      = data?.total ?? 0
  const totalPages = data ? Math.ceil(data.total / (data.page_size || 24)) : 1

  function setPage(p: number) {
    setFilters(f => ({ ...f, page: p }))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
      {/* Cart banner */}
      {filters.cart_only && (
        <div className="flex items-center gap-3 mb-5 px-4 py-3 rounded-xl bg-amber/10 border border-amber/30">
          <ShoppingCart className="w-4 h-4 text-amber shrink-0" />
          <span className="font-body text-sm font-semibold text-mahogany flex-1">
            Viewing tonight's cart
          </span>
          <button
            onClick={() => {
              clearCart.mutate()
              setFilters(DEFAULT_FILTERS)
            }}
            className="font-body text-xs text-bark hover:text-red-500 transition-colors"
          >
            Clear cart
          </button>
          <button
            onClick={() => setFilters(DEFAULT_FILTERS)}
            className="p-1 text-bark hover:text-mahogany transition-colors"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <h1 className="font-display text-4xl text-mahogany leading-none">
          {total > 0
            ? `${total.toLocaleString()} recipes`
            : isFetching ? 'Loading…' : 'No results'}
        </h1>
        <div className="flex items-center gap-1">
          <LegendPopover />
          <FilterPanel filters={filters} setFilters={setFilters} total={total} />
        </div>
      </div>

      {/* Loading shimmer */}
      {isFetching && !data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="card-cocktail animate-pulse">
              <div className="h-48 bg-parchment-200" />
              <div className="p-4 space-y-3">
                <div className="h-5 bg-parchment-200 rounded w-3/4" />
                <div className="h-3 bg-parchment-200 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-24">
          <GlassWater className="w-16 h-16 text-parchment-400 mx-auto mb-4" />
          <p className="font-display text-2xl text-mahogany">Something went wrong</p>
          <p className="font-body text-bark mt-1">Try refreshing the page.</p>
        </div>
      )}

      {/* Empty state */}
      {!isFetching && !isError && data?.results.length === 0 && (
        <div className="text-center py-24">
          <GlassWater className="w-16 h-16 text-parchment-400 mx-auto mb-4" />
          <p className="font-display text-2xl text-mahogany">No cocktails found</p>
          <p className="font-body text-bark mt-1">Try adjusting your filters.</p>
        </div>
      )}

      {/* Grid */}
      {data && data.results.length > 0 && (
        <>
          <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 transition-opacity duration-200 ${isFetching ? 'opacity-60' : 'opacity-100'}`}>
            {data.results.map(cocktail => (
              <CocktailCard key={cocktail.cocktail_id} cocktail={cocktail} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-10">
              <button
                onClick={() => setPage(filters.page! - 1)}
                disabled={filters.page === 1}
                className="p-2 rounded-lg text-bark hover:text-mahogany hover:bg-parchment-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              {/* Page numbers — show at most 7 */}
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(p =>
                  p === 1 ||
                  p === totalPages ||
                  Math.abs(p - (filters.page ?? 1)) <= 2
                )
                .reduce<(number | 'ellipsis')[]>((acc, p, i, arr) => {
                  if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push('ellipsis')
                  acc.push(p)
                  return acc
                }, [])
                .map((p, i) =>
                  p === 'ellipsis' ? (
                    <span key={`e${i}`} className="px-2 text-bark font-body">…</span>
                  ) : (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`w-9 h-9 rounded-lg font-body text-sm font-semibold transition-colors ${
                        filters.page === p
                          ? 'bg-amber text-white'
                          : 'text-bark hover:bg-parchment-200 hover:text-mahogany'
                      }`}
                    >
                      {p}
                    </button>
                  )
                )}

              <button
                onClick={() => setPage(filters.page! + 1)}
                disabled={filters.page === totalPages}
                className="p-2 rounded-lg text-bark hover:text-mahogany hover:bg-parchment-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-5 h-5" />
              </button>

              {isFetching && <Loader2 className="w-4 h-4 text-amber animate-spin ml-2" />}
            </div>
          )}
        </>
      )}
    </div>
  )
}
