import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cocktailsApi, type CocktailFilters } from '../api/cocktails'

export function useFilterOptions() {
  return useQuery({
    queryKey: ['cocktail-options'],
    queryFn:  cocktailsApi.options,
    staleTime: 60 * 60 * 1000, // 1 hour — matches server cache TTL
  })
}

export function useCocktails(filters: CocktailFilters) {
  return useQuery({
    queryKey: ['cocktails', filters],
    queryFn:  () => cocktailsApi.list(filters),
    placeholderData: (prev) => prev, // keep previous results while loading next page
  })
}

export function useFavorite() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, val }: { id: number; val: boolean }) =>
      cocktailsApi.favorite(id, val),
    onMutate: async ({ id, val }) => {
      // Optimistic update
      await qc.cancelQueries({ queryKey: ['cocktails'] })
      const prev = qc.getQueriesData({ queryKey: ['cocktails'] })
      qc.setQueriesData({ queryKey: ['cocktails'] }, (old: any) => {
        if (!old) return old
        return {
          ...old,
          results: old.results.map((c: any) =>
            c.cocktail_id === id ? { ...c, favorited: val } : c
          ),
        }
      })
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueriesData({ queryKey: ['cocktails'] }, ctx.prev)
    },
  })
}

export function useBookmark() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, val }: { id: number; val: boolean }) =>
      cocktailsApi.bookmark(id, val),
    onMutate: async ({ id, val }) => {
      await qc.cancelQueries({ queryKey: ['cocktails'] })
      const prev = qc.getQueriesData({ queryKey: ['cocktails'] })
      qc.setQueriesData({ queryKey: ['cocktails'] }, (old: any) => {
        if (!old) return old
        return {
          ...old,
          results: old.results.map((c: any) =>
            c.cocktail_id === id ? { ...c, bookmarked: val } : c
          ),
        }
      })
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueriesData({ queryKey: ['cocktails'] }, ctx.prev)
    },
  })
}

export function useRate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, rating }: { id: number; rating: number }) =>
      cocktailsApi.rate(id, rating),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cocktails'] }),
  })
}
