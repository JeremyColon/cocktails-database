import { useState, useRef, type Dispatch, type SetStateAction } from 'react'
import { X, SlidersHorizontal, RotateCcw } from 'lucide-react'
import { useFilterOptions } from '../hooks/useCocktails'
import { useAuth } from '../context/AuthContext'
import { type CocktailFilters, DEFAULT_FILTERS } from '../api/cocktails'

interface Props {
  filters: CocktailFilters
  setFilters: Dispatch<SetStateAction<CocktailFilters>>
  total: number
}

// ── Chip-style multi-select (small lists like Spirit) ─────────────────────────
function MultiSelect({
  label, options, value, onChange,
}: {
  label: string
  options: string[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  return (
    <div>
      <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <div className="flex flex-wrap gap-1.5">
        {options.map(opt => {
          const active = value.includes(opt)
          return (
            <button
              key={opt}
              onClick={() => onChange(active ? value.filter(v => v !== opt) : [...value, opt])}
              className={`text-xs font-body px-2.5 py-1 rounded-full border transition-colors ${active
                  ? 'bg-amber border-amber text-white'
                  : 'border-parchment-400 text-bark hover:border-amber hover:text-amber'
                }`}
            >
              {opt}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Searchable dropdown multi-select (large lists) ────────────────────────────
function SearchableMultiSelect({
  label, options, value, onChange,
}: {
  label: string
  options: string[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = options.filter(
    o => !value.includes(o) && o.toLowerCase().includes(query.toLowerCase())
  )

  function add(opt: string) {
    onChange([...value, opt])
    setQuery('')
    inputRef.current?.focus()
  }

  function remove(opt: string) {
    onChange(value.filter(v => v !== opt))
  }

  return (
    <div>
      <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">
        {label}
      </label>

      {/* Selected chips */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {value.map(v => (
            <span
              key={v}
              className="flex items-center gap-1 text-xs font-body px-2 py-0.5 rounded-full bg-amber/10 text-amber border border-amber/30"
            >
              {v}
              <button onClick={() => remove(v)} className="hover:text-red-500 transition-colors">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input + dropdown */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          className="input-field text-sm"
          placeholder={`Search ${label.toLowerCase()}…`}
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {open && filtered.length > 0 && (
          <div className="absolute z-10 left-0 right-0 mt-1 bg-white border border-parchment-300 rounded-lg shadow-card overflow-hidden max-h-48 overflow-y-auto">
            {filtered.slice(0, 50).map(opt => (
              <button
                key={opt}
                onMouseDown={() => add(opt)}
                className="w-full text-left px-3 py-2 text-sm font-body text-mahogany hover:bg-parchment-100 transition-colors"
              >
                {opt}
              </button>
            ))}
            {filtered.length > 50 && (
              <p className="px-3 py-2 text-xs font-body text-bark">
                {filtered.length - 50} more — keep typing to narrow results
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────
export default function FilterPanel({ filters, setFilters, total }: Props) {
  const [open, setOpen] = useState(false)
  const { data: options } = useFilterOptions()
  const { user } = useAuth()

  function update(partial: Partial<CocktailFilters>) {
    setFilters(f => ({ ...f, ...partial, page: 1 }))
  }

  function reset() {
    setFilters(DEFAULT_FILTERS)
  }

  const activeCount = [
    filters.liquor_types?.length,
    filters.ingredients_or?.length,
    filters.bitters?.length,
    filters.syrups?.length,
    filters.garnishes?.length,
    filters.search,
    filters.favorites_only,
    filters.bookmarks_only,
    filters.cart_only,
    filters.can_make,
    filters.nps_min != null || filters.nps_max != null,
  ].filter(Boolean).length

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 btn-outline relative"
      >
        <SlidersHorizontal className="w-4 h-4" />
        Filters
        {activeCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-amber text-white text-xs flex items-center justify-center font-semibold">
            {activeCount}
          </span>
        )}
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-mahogany/20 z-40"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-white z-50 shadow-panel
          transform transition-transform duration-300 ease-in-out overflow-y-auto
          ${open ? 'translate-x-0' : '-translate-x-full'}`}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-parchment-200 px-5 py-4 flex items-center justify-between">
          <div>
            <h2 className="font-display text-2xl text-mahogany">Filters</h2>
            <p className="text-xs font-body text-bark">{total.toLocaleString()} cocktails</p>
          </div>
          <div className="flex items-center gap-2">
            {activeCount > 0 && (
              <button onClick={reset} className="btn-ghost text-xs flex items-center gap-1">
                <RotateCcw className="w-3 h-3" /> Reset
              </button>
            )}
            <button onClick={() => setOpen(false)} className="p-2 text-bark hover:text-mahogany transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="px-5 py-5 flex flex-col gap-6">

          {/* Search */}
          <div>
            <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">
              Search
            </label>
            <div className="relative">
              <input
                type="text"
                className="input-field text-sm pr-8"
                placeholder="e.g. mojito, negroni…"
                value={filters.search ?? ''}
                onChange={e => update({ search: e.target.value || undefined })}
              />
              {filters.search && (
                <button
                  onClick={() => update({ search: undefined })}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-bark hover:text-mahogany transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Sort */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">Sort by</label>
              <select
                className="input-field text-sm"
                value={filters.sort_by ?? 'recipe_name'}
                onChange={e => update({ sort_by: e.target.value as CocktailFilters['sort_by'] })}
              >
                <option value="recipe_name">Name</option>
                <option value="date_added">Newest</option>
                <option value="avg_rating">Rating</option>
                <option value="nps">NPS</option>
                <option value="num_ratings"># Ratings</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">Dir</label>
              <select
                className="input-field text-sm"
                value={filters.sort_dir ?? 'asc'}
                onChange={e => update({ sort_dir: e.target.value as 'asc' | 'desc' })}
              >
                <option value="asc">A → Z</option>
                <option value="desc">Z → A</option>
              </select>
            </div>
          </div>

          {/* Ingredient availability — auth only */}
          {user && (
            <div>
              <p className="text-xs font-body font-semibold text-bark uppercase tracking-wider mb-2">
                Ingredient Availability
              </p>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { val: undefined, label: 'All' },
                  { val: 'all', label: 'Can make now' },
                  { val: 'some', label: 'Have some' },
                  { val: 'none', label: 'Missing all' },
                ].map(({ val, label }) => {
                  const active = filters.can_make === val
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => update({ can_make: val as any })}
                      className={`text-xs font-body px-2.5 py-1 rounded-full border transition-colors ${
                        active
                          ? 'bg-amber border-amber text-white'
                          : 'border-parchment-400 text-bark hover:border-amber hover:text-amber'
                      }`}
                    >
                      {label}
                    </button>
                  )
                })}
              </div>
              <label className="flex items-center gap-2.5 cursor-pointer mt-3">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-parchment-400 text-amber focus:ring-amber"
                  checked={filters.include_garnish ?? true}
                  onChange={e => update({ include_garnish: e.target.checked })}
                />
                <span className="font-body text-sm text-bark">Include garnishes</span>
              </label>
            </div>
          )}

          {/* My cocktails — auth only */}
          {user && (
            <div>
              <p className="text-xs font-body font-semibold text-bark uppercase tracking-wider mb-2">My Cocktails</p>
              <div className="space-y-2">
                {[
                  { key: 'favorites_only', label: 'Favorites' },
                  { key: 'bookmarks_only', label: 'Bookmarks' },
                  { key: 'cart_only', label: "Tonight's cart" },
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center gap-2.5 cursor-pointer group">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded border-parchment-400 text-amber focus:ring-amber"
                      checked={!!(filters as any)[key]}
                      onChange={e => update({ [key]: e.target.checked || undefined })}
                    />
                    <span className="font-body text-sm text-mahogany group-hover:text-amber transition-colors">
                      {label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* NPS range */}
          <div>
            <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">
              NPS Range
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number" min="-10" max="10"
                className="input-field text-sm w-20"
                placeholder="-10"
                value={filters.nps_min ?? ''}
                onChange={e => update({ nps_min: e.target.value ? Number(e.target.value) : undefined })}
              />
              <span className="text-bark font-body text-sm">to</span>
              <input
                type="number" min="-10" max="10"
                className="input-field text-sm w-20"
                placeholder="10"
                value={filters.nps_max ?? ''}
                onChange={e => update({ nps_max: e.target.value ? Number(e.target.value) : undefined })}
              />
            </div>
          </div>

          {/* Spirit — chip style (small list) */}
          {options?.liquor_types.length ? (
            <MultiSelect
              label="Spirit"
              options={options.liquor_types}
              value={filters.liquor_types ?? []}
              onChange={v => update({ liquor_types: v.length ? v : undefined })}
            />
          ) : null}

          {/* Ingredients — searchable dropdown (OR within) */}
          {options?.ingredients.length ? (
            <SearchableMultiSelect
              label="Ingredients"
              options={options.ingredients}
              value={filters.ingredients_or ?? []}
              onChange={v => update({ ingredients_or: v.length ? v : undefined })}
            />
          ) : null}

          {/* Bitters */}
          {options?.bitters.length ? (
            <SearchableMultiSelect
              label="Bitters"
              options={options.bitters}
              value={filters.bitters ?? []}
              onChange={v => update({ bitters: v.length ? v : undefined })}
            />
          ) : null}

          {/* Syrups */}
          {options?.syrups.length ? (
            <SearchableMultiSelect
              label="Syrups"
              options={options.syrups}
              value={filters.syrups ?? []}
              onChange={v => update({ syrups: v.length ? v : undefined })}
            />
          ) : null}

          {/* Garnishes */}
          {options?.garnishes.length ? (
            <SearchableMultiSelect
              label="Garnishes"
              options={options.garnishes}
              value={filters.garnishes ?? []}
              onChange={v => update({ garnishes: v.length ? v : undefined })}
            />
          ) : null}

        </div>
      </div>
    </>
  )
}
