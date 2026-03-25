import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import CocktailBrowser from './pages/CocktailBrowser'
import MyBar from './pages/MyBar'
import Login from './pages/Login'

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

function AppRoutes() {
  const { loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-parchment-100 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-amber border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-parchment-100">
      <Navbar />
      <Routes>
        <Route path="/"       element={<CocktailBrowser />} />
        <Route path="/login"  element={<Login />} />
        <Route path="/mybar"  element={
          <ProtectedRoute><MyBar /></ProtectedRoute>
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
