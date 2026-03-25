import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, type User } from '../api/auth'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login:    (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout:   () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const u = await authApi.login(email, password)
    setUser(u)
  }

  async function register(email: string, password: string) {
    const u = await authApi.register(email, password)
    setUser(u)
  }

  async function logout() {
    await authApi.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
