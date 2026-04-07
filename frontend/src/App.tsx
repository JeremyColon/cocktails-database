import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import CocktailBrowser from './pages/CocktailBrowser'
import MyBar from './pages/MyBar'
import Login from './pages/Login'
import Admin from './pages/Admin'
import CocktailDetail from './pages/CocktailDetail'
import BarImport from './pages/BarImport'
import BarLink from './pages/BarLink'
import { type CocktailFilters, DEFAULT_FILTERS } from './api/cocktails'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user || !user.is_admin) return <Navigate to="/" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { loading } = useAuth()
  const [filters, setFilters] = useState<CocktailFilters>(DEFAULT_FILTERS)

  if (loading) {
    return (
      <div className="min-h-screen bg-parchment-100 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-amber border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-parchment-100">
      <Navbar onCartClick={() => setFilters({ ...DEFAULT_FILTERS, cart_only: true })} />
      <Routes>
        <Route path="/"       element={<CocktailBrowser filters={filters} setFilters={setFilters} />} />
        <Route path="/cocktail/:id" element={<CocktailDetail />} />
        <Route path="/bar/import" element={<BarImport />} />
        <Route path="/bar/link" element={<BarLink />} />
        <Route path="/login"  element={<Login />} />
        <Route path="/mybar"  element={
          <ProtectedRoute><MyBar /></ProtectedRoute>
        } />
        <Route path="/admin"  element={
          <AdminRoute><Admin /></AdminRoute>
        } />
        <Route path="*"       element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
