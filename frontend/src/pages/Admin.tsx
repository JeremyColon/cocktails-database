import { useState, useEffect, useRef } from 'react'
import { CheckCircle, Loader2, Wand2 } from 'lucide-react'
import { adminApi, type UnmappedIngredient } from '../api/admin'

interface RowState {
  mappedValue: string
  alcoholType: string
  suggestions: string[]
  suggestionsLoaded: boolean
  saving: boolean
  saved: boolean
}

export default function Admin() {
  const [ingredients, setIngredients] = useState<UnmappedIngredient[]>([])
  const [loading, setLoading] = useState(true)
  const [alcoholTypes, setAlcoholTypes] = useState<string[]>([])
  const [rowStates, setRowStates] = useState<Record<number, RowState>>({})
  const fetchedSuggestions = useRef<Set<number>>(new Set())

  useEffect(() => {
    Promise.all([adminApi.listUnmapped(), adminApi.listAlcoholTypes()])
      .then(([ings, types]) => {
        setIngredients(ings)
        setAlcoholTypes(types)
        const initial: Record<number, RowState> = {}
        for (const ing of ings) {
          initial[ing.ingredient_id] = {
            mappedValue: '',
            alcoholType: ing.alcohol_type ?? '',
            suggestions: [],
            suggestionsLoaded: false,
            saving: false,
            saved: false,
          }
        }
        setRowStates(initial)
      })
      .finally(() => setLoading(false))
  }, [])

  function updateRow(id: number, patch: Partial<RowState>) {
    setRowStates(s => ({ ...s, [id]: { ...s[id], ...patch } }))
  }

  async function loadSuggestions(id: number) {
    if (fetchedSuggestions.current.has(id)) return
    fetchedSuggestions.current.add(id)
    const result = await adminApi.getSuggestions(id)
    updateRow(id, {
      suggestions: result.suggestions,
      suggestionsLoaded: true,
      mappedValue: rowStates[id]?.mappedValue || result.suggestions[0] || '',
    })
  }

  async function save(id: number) {
    const state = rowStates[id]
    if (!state?.mappedValue.trim()) return
    updateRow(id, { saving: true })
    try {
      await adminApi.updateMapping(id, state.mappedValue.trim(), state.alcoholType || undefined)
      updateRow(id, { saving: false, saved: true })
      // Remove from list after short delay
      setTimeout(() => {
        setIngredients(prev => prev.filter(i => i.ingredient_id !== id))
      }, 800)
    } catch {
      updateRow(id, { saving: false })
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 flex justify-center">
        <Loader2 className="w-8 h-8 text-amber animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
      <div className="mb-6">
        <h1 className="font-display text-4xl text-mahogany">Ingredient Mapping</h1>
        <p className="font-body text-sm text-bark mt-1">
          {ingredients.length} unmapped ingredients — sorted by cocktail impact
        </p>
      </div>

      {ingredients.length === 0 ? (
        <div className="text-center py-24">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <p className="font-display text-2xl text-mahogany">All ingredients mapped</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-parchment-300 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-parchment-200 bg-parchment-50">
                <th className="text-left px-4 py-3 font-body font-semibold text-bark uppercase tracking-wider text-xs">Ingredient</th>
                <th className="text-center px-4 py-3 font-body font-semibold text-bark uppercase tracking-wider text-xs w-20">Cocktails</th>
                <th className="text-left px-4 py-3 font-body font-semibold text-bark uppercase tracking-wider text-xs">Map to</th>
                <th className="text-left px-4 py-3 font-body font-semibold text-bark uppercase tracking-wider text-xs w-44">Alcohol type</th>
                <th className="w-24 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-parchment-100">
              {ingredients.map(ing => {
                const state = rowStates[ing.ingredient_id]
                if (!state) return null
                return (
                  <tr key={ing.ingredient_id} className={`transition-colors ${state.saved ? 'bg-green-50' : 'hover:bg-parchment-50'}`}>
                    {/* Ingredient name */}
                    <td className="px-4 py-3 font-body text-mahogany">{ing.ingredient}</td>

                    {/* Cocktail count */}
                    <td className="px-4 py-3 text-center">
                      <span className="font-body text-xs font-semibold text-amber bg-amber/10 px-2 py-0.5 rounded-full">
                        {ing.cocktail_count}
                      </span>
                    </td>

                    {/* Mapping input with suggestions */}
                    <td className="px-4 py-3">
                      <MappingInput
                        value={state.mappedValue}
                        suggestions={state.suggestions}
                        suggestionsLoaded={state.suggestionsLoaded}
                        onChange={v => updateRow(ing.ingredient_id, { mappedValue: v })}
                        onFocus={() => loadSuggestions(ing.ingredient_id)}
                      />
                    </td>

                    {/* Alcohol type */}
                    <td className="px-4 py-3">
                      <select
                        className="input-field text-xs py-1.5"
                        value={state.alcoholType}
                        onChange={e => updateRow(ing.ingredient_id, { alcoholType: e.target.value })}
                      >
                        <option value="">— none —</option>
                        {alcoholTypes.map(t => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </td>

                    {/* Save button */}
                    <td className="px-4 py-3">
                      {state.saved ? (
                        <CheckCircle className="w-5 h-5 text-green-500 mx-auto" />
                      ) : (
                        <button
                          onClick={() => save(ing.ingredient_id)}
                          disabled={!state.mappedValue.trim() || state.saving}
                          className="btn-amber text-xs py-1.5 w-full disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {state.saving ? <Loader2 className="w-3.5 h-3.5 animate-spin mx-auto" /> : 'Save'}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Mapping input with suggestions dropdown ────────────────────────────────────
function MappingInput({
  value, suggestions, suggestionsLoaded, onChange, onFocus,
}: {
  value: string
  suggestions: string[]
  suggestionsLoaded: boolean
  onChange: (v: string) => void
  onFocus: () => void
}) {
  const [open, setOpen] = useState(false)

  const filtered = suggestions.filter(s =>
    s.toLowerCase().includes(value.toLowerCase())
  )

  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <input
          type="text"
          className="input-field text-sm py-1.5 flex-1"
          placeholder="Type or pick a suggestion…"
          value={value}
          onChange={e => onChange(e.target.value)}
          onFocus={() => { onFocus(); setOpen(true) }}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {!suggestionsLoaded && (
          <Wand2 className="w-3.5 h-3.5 text-parchment-400 shrink-0" />
        )}
      </div>

      {open && filtered.length > 0 && (
        <div className="absolute z-20 left-0 right-0 mt-1 bg-white border border-parchment-300 rounded-lg shadow-card overflow-hidden">
          {filtered.map(s => (
            <button
              key={s}
              onMouseDown={() => { onChange(s); setOpen(false) }}
              className="w-full text-left px-3 py-1.5 text-sm font-body text-mahogany hover:bg-parchment-100 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
