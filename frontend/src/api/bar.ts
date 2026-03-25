import { api } from './client'

export interface BarIngredient {
  ingredient_id: number
  ingredient: string
  mapped_ingredient: string | null
  alcohol_type: string | null
}

export interface BarResponse {
  ingredients: BarIngredient[]
}

export interface MissingIngredient {
  ingredient_id: number
  mapped_ingredient: string
  cocktail_count: number
}

export interface BarStats {
  can_make_count: number
  partial_count: number
  cannot_make_count: number
  top_missing: MissingIngredient[]
}

export const barApi = {
  get:     ()                              => api.get<BarResponse>('/bar'),
  stats:   (includeGarnish = true)         => api.get<BarStats>(`/bar/stats?include_garnish=${includeGarnish}`),
  add:     (ingredient_ids: number[])      => api.post<BarResponse>('/bar/add', { ingredient_ids }),
  remove:  (ingredient_ids: number[])      => api.post<BarResponse>('/bar/remove', { ingredient_ids }),
  replace: (ingredient_ids: number[])      => api.put<BarResponse>('/bar', { ingredient_ids }),
}
