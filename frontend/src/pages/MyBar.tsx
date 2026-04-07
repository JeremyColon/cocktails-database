import { useState, useMemo, useRef } from 'react'
import { Trash2, GlassWater, TrendingUp, X, Plus, ChevronDown, Check, Zap, Share2, Link2, Users } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useBar, useBarStats, useAddToBar, useRemoveFromBar, useBarStarters, useShareBar, useBarLinkStatus, useCreateLinkInvite, useUnlink } from '../hooks/useBar'
import { cocktailsApi, type IngredientSearchResult } from '../api/cocktails'
import type { StarterKit as StarterKitType } from '../api/bar'

export default function MyBar() {
  const { data: bar, isLoading: barLoading } = useBar()
  const [includeGarnish, setIncludeGarnish] = useState(true)
  const { data: stats } = useBarStats(includeGarnish)
  const { data: starters } = useBarStarters()

  const addToBar = useAddToBar()
  const removeFromBar = useRemoveFromBar()

  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [starterTab, setStarterTab] = useState<'kits' | 'popular'>('kits')
  const [shareToken, setShareToken] = useState<string | null>(null)
  const [shareCopied, setShareCopied] = useState(false)
  const [linkToken, setLinkToken] = useState<string | null>(null)
  const [linkCopied, setLinkCopied] = useState(false)
  const shareBar = useShareBar()
  const { data: linkStatus } = useBarLinkStatus()
  const createLinkInvite = useCreateLinkInvite()
  const unlink = useUnlink()

  const barMappedNames = useMemo(
    () => new Set(bar?.ingredients.map(i => (i.mapped_ingredient ?? i.ingredient).toLowerCase()) ?? []),
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
      <div className="flex items-start justify-between gap-4 mb-2">
        <h1 className="font-display text-5xl text-mahogany leading-none">My Bar</h1>
        <div className="shrink-0 pt-1">
          {shareToken ? (
            <div className="flex items-center gap-2 bg-parchment-100 rounded-lg px-3 py-2">
              <span className="font-body text-xs text-bark max-w-48 truncate">
                {`${window.location.origin}/bar/import?token=${shareToken}`}
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`${window.location.origin}/bar/import?token=${shareToken}`)
                  setShareCopied(true)
                  setTimeout(() => setShareCopied(false), 1500)
                }}
                className="shrink-0 text-bark hover:text-amber transition-colors"
                title="Copy link"
              >
                {shareCopied ? <Check className="w-4 h-4 text-green-600" /> : <Link2 className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setShareToken(null)}
                className="shrink-0 text-bark hover:text-mahogany transition-colors"
                title="Dismiss"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={async () => {
                const result = await shareBar.mutateAsync()
                setShareToken(result.token)
              }}
              disabled={shareBar.isPending}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber/10 text-amber font-body text-sm font-semibold hover:bg-amber/20 transition-colors disabled:opacity-40"
            >
              <Share2 className="w-4 h-4" />
              {shareBar.isPending ? 'Generating…' : 'Share my bar'}
            </button>
          )}
        </div>
      </div>
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
              <div className="space-y-1.5 max-h-[820px] overflow-y-auto p-3">
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

        {/* Add ingredients */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="font-display text-2xl text-mahogany">Add Ingredients</h2>

          {starters && (
            <div>
              <h3 className="font-body text-sm font-semibold text-mahogany mb-2 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber" />
                Bulk add
              </h3>

              <div className="flex gap-1 mb-3 bg-parchment-100 rounded-lg p-1">
                {(['kits', 'popular'] as const).map(tab => (
                  <button
                    key={tab}
                    onClick={() => setStarterTab(tab)}
                    className={`flex-1 py-1.5 text-xs font-body font-semibold rounded-md transition-colors ${
                      starterTab === tab
                        ? 'bg-white text-mahogany shadow-sm'
                        : 'text-bark hover:text-mahogany'
                    }`}
                  >
                    {tab === 'kits' ? 'Starter Kits' : 'Most Popular'}
                  </button>
                ))}
              </div>

              {starterTab === 'kits' && (
                <div className="space-y-2">
                  {starters.kits.map(kit => (
                    <KitRow
                      key={kit.name}
                      kit={kit}
                      barMappedNames={barMappedNames}
                      onAdd={ids => addToBar.mutateAsync(ids)}
                      loading={addToBar.isPending}
                    />
                  ))}
                </div>
              )}

              {starterTab === 'popular' && (
                <div className="flex flex-wrap gap-1.5">
                  {starters.top_ingredients.map(ing => {
                    const inBar = barMappedNames.has(ing.mapped_ingredient.toLowerCase())
                    return (
                      <button
                        key={ing.ingredient_id}
                        onClick={() => !inBar && addToBar.mutateAsync([ing.ingredient_id])}
                        disabled={inBar || addToBar.isPending}
                        title={`${ing.cocktail_count} cocktails`}
                        className={`inline-flex items-center gap-1 text-xs font-body px-2.5 py-1 rounded-full border transition-colors ${
                          inBar
                            ? 'bg-green-50 text-green-700 border-green-200 cursor-default'
                            : 'bg-white text-mahogany border-parchment-300 hover:border-amber hover:text-amber cursor-pointer'
                        }`}
                      >
                        {inBar && <Check className="w-2.5 h-2.5" />}
                        {ing.mapped_ingredient}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          <div>
            <h3 className="font-body text-sm font-semibold text-mahogany mb-2">Search & add</h3>
            <AddIngredientSearch
              barMappedNames={barMappedNames}
              onAdd={ids => addToBar.mutateAsync(ids)}
              loading={addToBar.isPending}
            />
          </div>

          {stats?.top_missing && stats.top_missing.length > 0 && (
            <div>
              <h3 className="font-body text-sm font-semibold text-mahogany mb-2 flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-amber" />
                Top missing
              </h3>
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

          {/* Household */}
          <div>
            <h2 className="font-display text-2xl text-mahogany mb-3 flex items-center gap-2">
              <Users className="w-5 h-5 text-amber" />
              Household
            </h2>

            {linkStatus?.linked ? (
              <div className="space-y-3">
                <p className="font-body text-xs text-bark">
                  Sharing this bar with:
                </p>
                {linkStatus.linked_to_emails.map(email => (
                  <div key={email} className="flex items-center justify-between py-2 border-b border-parchment-200">
                    <span className="font-body text-sm text-mahogany">{email}</span>
                    <button
                      onClick={() => unlink.mutate()}
                      disabled={unlink.isPending}
                      className="text-xs font-body text-red-500 hover:text-red-700 transition-colors disabled:opacity-40"
                    >
                      Unlink
                    </button>
                  </div>
                ))}
                <p className="font-body text-xs text-bark">
                  Unlinking will give you a new empty bar.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="font-body text-xs text-bark mb-3">
                  Link bars with a household member so you share one inventory.
                </p>
                {linkToken ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 bg-parchment-100 rounded-lg px-3 py-2">
                      <span className="font-body text-xs text-bark flex-1 truncate">
                        {`${window.location.origin}/bar/link?token=${linkToken}`}
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(`${window.location.origin}/bar/link?token=${linkToken}`)
                          setLinkCopied(true)
                          setTimeout(() => setLinkCopied(false), 1500)
                        }}
                        className="shrink-0 text-bark hover:text-amber transition-colors"
                        title="Copy link"
                      >
                        {linkCopied ? <Check className="w-4 h-4 text-green-600" /> : <Link2 className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => setLinkToken(null)}
                        className="shrink-0 text-bark hover:text-mahogany transition-colors"
                        title="Dismiss"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <p className="font-body text-xs text-bark">Link expires in 7 days.</p>
                  </div>
                ) : (
                  <button
                    onClick={async () => {
                      const result = await createLinkInvite.mutateAsync()
                      setLinkToken(result.token)
                    }}
                    disabled={createLinkInvite.isPending}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-parchment-100 text-mahogany font-body text-sm font-semibold hover:bg-parchment-200 transition-colors disabled:opacity-40 border border-parchment-300 w-full justify-center"
                  >
                    <Users className="w-4 h-4" />
                    {createLinkInvite.isPending ? 'Generating…' : 'Invite a household member'}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function KitRow({
  kit,
  barMappedNames,
  onAdd,
  loading,
}: {
  kit: StarterKitType
  barMappedNames: Set<string>
  onAdd: (ids: number[]) => Promise<unknown>
  loading: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const missing = kit.ingredients.filter(i => !barMappedNames.has(i.mapped_ingredient.toLowerCase()))
  const allInBar = missing.length === 0

  return (
    <div className="border border-parchment-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2.5 bg-white hover:bg-parchment-50 transition-colors text-left"
      >
        <span className="font-body font-semibold text-sm text-mahogany">{kit.name}</span>
        <div className="flex items-center gap-2 shrink-0">
          {allInBar ? (
            <span className="text-xs font-body text-green-600 font-semibold flex items-center gap-1">
              <Check className="w-3 h-3" /> All set
            </span>
          ) : (
            <span className="text-xs font-body text-bark">{missing.length} to add</span>
          )}
          <ChevronDown className={`w-4 h-4 text-bark transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-3 py-3 bg-parchment-50 border-t border-parchment-200">
          <div className="flex flex-wrap gap-1.5 mb-3">
            {kit.ingredients.map(i => {
              const inBar = barMappedNames.has(i.mapped_ingredient.toLowerCase())
              return (
                <span
                  key={i.ingredient_id}
                  className={`inline-flex items-center gap-1 text-xs font-body px-2 py-1 rounded-full border ${
                    inBar
                      ? 'bg-green-50 text-green-700 border-green-200'
                      : 'bg-white text-mahogany border-parchment-300'
                  }`}
                >
                  {inBar && <Check className="w-2.5 h-2.5" />}
                  {i.mapped_ingredient}
                </span>
              )
            })}
          </div>
          {!allInBar && (
            <button
              onClick={() => onAdd(missing.map(i => i.ingredient_id))}
              disabled={loading}
              className="btn-amber w-full text-sm disabled:opacity-40"
            >
              Add {missing.length} missing ingredient{missing.length !== 1 ? 's' : ''}
            </button>
          )}
        </div>
      )}
    </div>
  )
}


function AddIngredientSearch({
  barMappedNames,
  onAdd,
  loading,
}: {
  barMappedNames: Set<string>
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

  const filtered = suggestions.filter(s => {
    const mappedName = (s.mapped_ingredient ?? s.ingredient).toLowerCase()
    return !barMappedNames.has(mappedName) && !pending.some(p => p.ingredient_id === s.ingredient_id)
  })

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
