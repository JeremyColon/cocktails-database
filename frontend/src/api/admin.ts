import { api } from './client'

export interface UnmappedIngredient {
  ingredient_id: number
  ingredient: string
  alcohol_type: string | null
  cocktail_count: number
}

export interface SuggestionsResponse {
  ingredient: string
  suggestions: string[]
}

export const adminApi = {
  listUnmapped: () =>
    api.get<UnmappedIngredient[]>('/admin/unmapped'),

  getSuggestions: (ingredientId: number) =>
    api.get<SuggestionsResponse>(`/admin/suggestions/${ingredientId}`),

  updateMapping: (ingredientId: number, mapped_ingredient: string, alcohol_type?: string) =>
    api.patch<UnmappedIngredient>(`/admin/ingredients/${ingredientId}`, {
      mapped_ingredient,
      alcohol_type: alcohol_type || null,
    }),

  listAlcoholTypes: () =>
    api.get<string[]>('/admin/alcohol-types'),
}
