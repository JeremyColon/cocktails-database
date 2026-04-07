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

export interface StarterIngredient {
  ingredient_id: number
  mapped_ingredient: string
  alcohol_type: string | null
}

export interface TopStarterIngredient extends StarterIngredient {
  cocktail_count: number
}

export interface StarterKit {
  name: string
  ingredients: StarterIngredient[]
}

export interface StartersResponse {
  kits: StarterKit[]
  top_ingredients: TopStarterIngredient[]
}

export interface ShareTokenResponse {
  token: string
  expires_at: string
}

export interface BarSharePreview {
  owner_email: string
  ingredient_count: number
  ingredients: StarterIngredient[]
  expires_at: string
}

export interface LinkInviteResponse {
  token: string
  expires_at: string
}

export interface BarLinkPreview {
  inviter_email: string
}

export interface BarLinkStatus {
  linked: boolean
  linked_to_emails: string[]
  household_size: number
}

export const barApi = {
  get:           ()                                          => api.get<BarResponse>('/bar'),
  stats:         (includeGarnish = true)                    => api.get<BarStats>(`/bar/stats?include_garnish=${includeGarnish}`),
  add:           (ingredient_ids: number[])                  => api.post<BarResponse>('/bar/add', { ingredient_ids }),
  remove:        (ingredient_ids: number[])                  => api.post<BarResponse>('/bar/remove', { ingredient_ids }),
  replace:       (ingredient_ids: number[])                  => api.put<BarResponse>('/bar', { ingredient_ids }),
  starters:      ()                                          => api.get<StartersResponse>('/bar/starters'),
  share:         ()                                              => api.post<ShareTokenResponse>('/bar/share'),
  sharePreview:  (token: string)                                 => api.get<BarSharePreview>(`/bar/share/${token}`),
  importBar:     (token: string, mode: 'add' | 'replace')       => api.post<BarResponse>(`/bar/import/${token}`, { mode }),
  linkInvite:    ()                                              => api.post<LinkInviteResponse>('/bar/link/invite'),
  linkPreview:   (token: string)                                 => api.get<BarLinkPreview>(`/bar/link/preview/${token}`),
  linkAccept:    (token: string, mode: 'merge' | 'replace')     => api.post<BarResponse>(`/bar/link/accept/${token}`, { mode }),
  unlink:        ()                                              => api.delete<void>('/bar/link'),
  linkStatus:    ()                                              => api.get<BarLinkStatus>('/bar/link/status'),
}
