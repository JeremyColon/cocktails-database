import { api } from './client'

export interface CocktailIngredient {
  ingredient_id: number
  ingredient: string
  mapped_ingredient: string | null
  unit: string | null
  quantity: string | null
  in_bar: boolean
}

export interface Cocktail {
  cocktail_id: number
  recipe_name: string
  image: string | null
  link: string | null
  alcohol_type: string | null
  source: string | null
  nps: number
  avg_rating: number
  num_ratings: number
  favorited: boolean
  bookmarked: boolean
  user_rating: number | null
  ingredients: CocktailIngredient[]
}

export interface CocktailListResponse {
  total: number
  page: number
  page_size: number
  results: Cocktail[]
}

export interface FilterOptions {
  liquor_types: string[]
  ingredients: string[]
  garnishes: string[]
  bitters: string[]
  syrups: string[]
}

export interface CocktailFilters {
  search?: string
  liquor_types?: string[]
  ingredients?: string[]
  ingredients_or?: string[]
  garnishes?: string[]
  bitters?: string[]
  syrups?: string[]
  nps_min?: number
  nps_max?: number
  favorites_only?: boolean
  bookmarks_only?: boolean
  can_make?: 'all' | 'some' | 'none'
  include_garnish?: boolean
  sort_by?: 'recipe_name' | 'nps' | 'avg_rating' | 'num_ratings' | 'date_added'
  sort_dir?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface IngredientSearchResult {
  ingredient_id: number
  ingredient: string
  mapped_ingredient: string | null
  alcohol_type: string | null
}

export const cocktailsApi = {
  searchIngredients: (q: string) =>
    api.get<IngredientSearchResult[]>(`/cocktails/ingredients?search=${encodeURIComponent(q)}`),
  list:    (filters: CocktailFilters)     => api.post<CocktailListResponse>('/cocktails', filters),
  options: ()                             => api.get<FilterOptions>('/cocktails/options'),
  favorite:(id: number, val: boolean)     => api.post<void>(`/cocktails/${id}/favorite`, { favorite: val }),
  bookmark:(id: number, val: boolean)     => api.post<void>(`/cocktails/${id}/bookmark`, { bookmark: val }),
  rate:    (id: number, rating: number)   => api.post<{ nps: number; avg_rating: number; num_ratings: number }>(`/cocktails/${id}/rating`, { rating }),
}
