import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { barApi } from '../api/bar'

export function useBar() {
  return useQuery({
    queryKey: ['bar'],
    queryFn:  barApi.get,
  })
}

export function useBarStats(includeGarnish = true) {
  return useQuery({
    queryKey: ['bar-stats', includeGarnish],
    queryFn:  () => barApi.stats(includeGarnish),
  })
}

export function useAddToBar() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: number[]) => barApi.add(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bar'] })
      qc.invalidateQueries({ queryKey: ['bar-stats'] })
    },
  })
}

export function useRemoveFromBar() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: number[]) => barApi.remove(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bar'] })
      qc.invalidateQueries({ queryKey: ['bar-stats'] })
    },
  })
}
