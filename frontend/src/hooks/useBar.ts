import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { barApi } from '../api/bar'
import { useAuth } from '../context/AuthContext'

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

export function useBarStarters() {
  return useQuery({
    queryKey: ['bar-starters'],
    queryFn:  barApi.starters,
    staleTime: 60 * 60 * 1000,
  })
}

export function useShareBar() {
  return useMutation({ mutationFn: barApi.share })
}

export function useBarSharePreview(token: string | null) {
  return useQuery({
    queryKey: ['bar-share-preview', token],
    queryFn:  () => barApi.sharePreview(token!),
    enabled:  !!token,
    retry:    false,
  })
}

export function useImportBar() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ token, mode }: { token: string; mode: 'add' | 'replace' }) =>
      barApi.importBar(token, mode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bar'] })
      qc.invalidateQueries({ queryKey: ['bar-stats'] })
      qc.invalidateQueries({ queryKey: ['cocktails'] })
    },
  })
}

export function useBarLinkStatus() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['bar-link-status'],
    queryFn:  barApi.linkStatus,
    enabled:  !!user,
  })
}

export function useCreateLinkInvite() {
  return useMutation({ mutationFn: barApi.linkInvite })
}

export function useBarLinkPreview(token: string | null) {
  return useQuery({
    queryKey: ['bar-link-preview', token],
    queryFn:  () => barApi.linkPreview(token!),
    enabled:  !!token,
    retry:    false,
  })
}

export function useAcceptLink() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ token, mode }: { token: string; mode: 'merge' | 'replace' }) =>
      barApi.linkAccept(token, mode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bar'] })
      qc.invalidateQueries({ queryKey: ['bar-stats'] })
      qc.invalidateQueries({ queryKey: ['bar-link-status'] })
      qc.invalidateQueries({ queryKey: ['cocktails'] })
    },
  })
}

export function useUnlink() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: barApi.unlink,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bar'] })
      qc.invalidateQueries({ queryKey: ['bar-stats'] })
      qc.invalidateQueries({ queryKey: ['bar-link-status'] })
      qc.invalidateQueries({ queryKey: ['cocktails'] })
    },
  })
}
