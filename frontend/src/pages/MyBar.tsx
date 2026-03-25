import { useState, useMemo, useRef } from 'react'
import { Trash2, GlassWater, TrendingUp, X, Plus } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useBar, useBarStats, useAddToBar, useRemoveFromBar } from '../hooks/useBar'
import { cocktailsApi, type IngredientSearchResult } from '../api/cocktails'

export default function MyBar() {
  const { data: bar, isLoading: barLoading } = useBar()
  const [includeGarnish, setIncludeGarnish] = useState(true)
  const { data: stats } = useBarStats(includeGarnish)

  const addToBar = useAddToBar()
  const removeFromBar = useRemoveFromBar()

  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<number[]>([])

  const barIds = useMemo(
    () => new Set(bar?.ingredients.map(i => i.ingredient_id) ?? []),
    [bar]
  )

  const filteredBar = useMemo(() => {
    if (!bar) return []
    const q = search.toLowerCase()
    return bar.ingredients.filter(i =>
      i.ingredient.toLowerCase().includes(q) ||
      (i.mapped_ingredient ?? '').toLowerCase().includes(q)
    )
  }, [bar, search])

  function toggleSelect(id: number) {
    setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id])
  }

  async function removeSelected() {
    if (!selected.length) return
    await removeFromBar.mutateAsync(selected)
    setSelected([])
  }

  const statCards = [
    { label: 'Can make', count: stats?.can_make_count ?? 0, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Partially', count: stats?.partial_count ?? 0, color: 'text-amber', bg: 'bg-amber/5' },
    { label: 'Missing all', count: stats?.cannot_make_count ?? 0, color: 'text-bark', bg: 'bg-parchment-100' },
  ]

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
      <h1 className="font-display text-5xl text-mahogany leading-none mb-2">My Bar</h1>
      <p className="font-body text-bark mb-8">Track what you have and see what you can make.</p>

      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          {statCards.map(({ label, count, color, bg }) => (
            <div key={label} className={`${bg} rounded-xl p-4 text-center`}>
              <p className={`font-display text-4xl ${color}`}>{count}</p>
              <p className="font-body text-sm text-bark mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Garnish toggle */}
      <label className="flex items-center gap-2.5 cursor-pointer mb-6">
        <input
          type="checkbox"
          className="w-4 h-4 rounded border-parchment-400 text-amber focus:ring-amber"
          checked={includeGarnish}
          onChange={e => setIncludeGarnish(e.target.checked)}
        />
        <span className="font-body text-sm text-bark">Include garnishes in counts</span>
      </label>

      <div className="grid lg:grid-cols-5 gap-8">
        {/* Bar inventory */}
        <div className="lg:col-span-3">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-2xl text-mahogany">
              Ingredients ({bar?.ingredients.length ?? 0})
            </h2>
            <div className="flex items-center gap-3">
              {filteredBar.length > 0 && (
                <button
                  onClick={() => {
                    const allIds = filteredBar.map(i => i.ingredient_id)
                    const allSelected = allIds.every(id => selected.includes(id))
                    setSelected(allSelected ? [] : allIds)
                  }}
                  className="text-sm font-body text-bark hover:text-mahogany transition-colors"
                >
                  {filteredBar.every(i => selected.includes(i.ingredient_id))
                    ? 'Deselect all'
                    : `Select all (${filteredBar.length})`}
                </button>
              )}
              {selected.length > 0 && (
                <button
                  onClick={removeSelected}
                  disabled={removeFromBar.isPending}
                  className="flex items-center gap-1.5 text-sm font-body font-semibold text-red-500 hover:text-red-700 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Remove {selected.length}
                </button>
              )}
            </div>
          </div>

          <input
            type="text"
            className="input-field text-sm mb-3"
            placeholder="Search your bar…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />

          <div className="border border-parchment-300 rounded-xl bg-parchment-50">
            {barLoading ? (
              <div className="space-y-2 p-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-10 bg-parchment-200 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : filteredBar.length === 0 ? (
              <div className="text-center py-12 text-bark font-body">
                <GlassWater className="w-10 h-10 mx-auto mb-3 text-parchment-400" />
                {bar?.ingredients.length === 0
                  ? 'Your bar is empty. Add some ingredients to get started.'
                  : 'No ingredients match your search.'}
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[610px] overflow-y-auto p-3">
                {filteredBar.map(ing => (
                  <label
                    key={ing.ingredient_id}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                    ${selected.includes(ing.ingredient_id)
                        ? 'bg-red-50 border border-red-200'
                        : 'hover:bg-parchment-100 border border-transparent'}`}
                  >
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded border-parchment-400 text-red-500 focus:ring-red-400"
                      checked={selected.includes(ing.ingredient_id)}
                      onChange={() => toggleSelect(ing.ingredient_id)}
                    />
                    <span className="font-body text-sm text-mahogany flex-1 min-w-0">
                      {ing.ingredient}
                      {ing.mapped_ingredient && ing.mapped_ingredient !== ing.ingredient && (
                        <span className="text-bark ml-1.5">→ {ing.mapped_ingredient}</span>
                      )}
                    </span>
                    {ing.alcohol_type && (
                      <span className="ml-auto badge-outline capitalize text-xs shrink-0">
                        {ing.alcohol_type}
                      </span>
                    )}
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Add ingredients + top missing */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h2 className="font-display text-2xl text-mahogany mb-3">Add Ingredients</h2>
            <p className="font-body text-xs text-bark mb-3">
              Search and add ingredients to your bar.
            </p>
            <AddIngredientSearch
              barIds={barIds}
              onAdd={ids => addToBar.mutateAsync(ids)}
              loading={addToBar.isPending}
            />
          </div>

          {stats?.top_missing && stats.top_missing.length > 0 && (
            <div>
              <h2 className="font-display text-2xl text-mahogany mb-3 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-amber" />
                Top Missing
              </h2>
              <p className="font-body text-xs text-bark mb-3">
                Adding these would unlock the most cocktails.
              </p>
              <div className="space-y-2">
                {stats.top_missing.map(m => (
                  <div key={m.ingredient_id} className="flex items-center justify-between py-2 border-b border-parchment-200">
                    <span className="font-body text-sm text-mahogany">{m.mapped_ingredient}</span>
                    <span className="badge-amber">{m.cocktail_count} cocktails</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function AddIngredientSearch({
  barIds,
  onAdd,
  loading,
}: {
  barIds: Set<number>
  onAdd: (ids: number[]) => Promise<unknown>
  loading: boolean
}) {
  const [query, setQuery] = useState('')
  const [pending, setPending] = useState<IngredientSearchResult[]>([])
  const [showList, setShowList] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: suggestions = [] } = useQuery({
    queryKey: ['ingredient-search', query],
    queryFn: () => cocktailsApi.searchIngredients(query),
    enabled: query.trim().length >= 2,
    staleTime: 60_000,
  })

  const filtered = suggestions.filter(
    s => !barIds.has(s.ingredient_id) && !pending.some(p => p.ingredient_id === s.ingredient_id)
  )

  function addPending(ing: IngredientSearchResult) {
    setPending(p => [...p, ing])
    setQuery('')
    setShowList(false)
    inputRef.current?.focus()
  }

  function removePending(id: number) {
    setPending(p => p.filter(x => x.ingredient_id !== id))
  }

  async function handleAdd() {
    if (!pending.length) return
    await onAdd(pending.map(p => p.ingredient_id))
    setPending([])
  }

  return (
    <div className="space-y-3">
      {/* Search input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          className="input-field text-sm"
          placeholder="e.g. bourbon, lime juice…"
          value={query}
          onChange={e => { setQuery(e.target.value); setShowList(true) }}
          onFocus={() => setShowList(true)}
          onBlur={() => setTimeout(() => setShowList(false), 150)}
        />
        {showList && filtered.length > 0 && (
          <div className="absolute z-10 left-0 right-0 mt-1 bg-white border border-parchment-300 rounded-lg shadow-card overflow-hidden">
            {filtered.map(s => (
              <button
                key={s.ingredient_id}
                onMouseDown={() => addPending(s)}
                className="w-full text-left px-3 py-2.5 text-sm font-body hover:bg-parchment-100 transition-colors flex items-center justify-between gap-2"
              >
                <span className="text-mahogany">{s.mapped_ingredient ?? s.ingredient}</span>
                {s.alcohol_type && (
                  <span className="badge-outline capitalize text-xs shrink-0">{s.alcohol_type}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Pending chips */}
      {pending.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {pending.map(p => (
            <span key={p.ingredient_id} className="flex items-center gap-1 badge bg-amber/10 text-amber border border-amber/30 font-body text-xs">
              {p.mapped_ingredient ?? p.ingredient}
              <button onClick={() => removePending(p.ingredient_id)} className="hover:text-red-500 transition-colors ml-0.5">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Add button */}
      <button
        onClick={handleAdd}
        disabled={!pending.length || loading}
        className="btn-amber w-full flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Plus className="w-4 h-4" />
        {loading ? 'Adding…' : `Add to my bar${pending.length ? ` (${pending.length})` : ''}`}
      </button>
    </div>
  )
}
