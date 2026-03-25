import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GlassWater, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../api/client'

type Mode = 'login' | 'register'

export default function Login() {
  const { login, register } = useAuth()
  const navigate = useNavigate()

  const [mode, setMode]         = useState<Mode>('login')
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm]   = useState('')
  const [showPwd, setShowPwd]   = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (mode === 'register' && password !== confirm) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(email, password)
      }
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-parchment-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-mahogany mb-4">
            <GlassWater className="w-8 h-8 text-amber" />
          </div>
          <h1 className="font-display text-4xl text-mahogany">Cocktail Finder</h1>
          <p className="font-body text-bark mt-1">
            {mode === 'login' ? 'Welcome back.' : 'Create your account.'}
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-card p-8">
          {/* Mode toggle */}
          <div className="flex rounded-lg bg-parchment-100 p-1 mb-6">
            {(['login', 'register'] as Mode[]).map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setError('') }}
                className={`flex-1 py-2 text-sm font-body font-semibold rounded-md transition-colors capitalize ${
                  mode === m
                    ? 'bg-white text-mahogany shadow-sm'
                    : 'text-bark hover:text-mahogany'
                }`}
              >
                {m === 'login' ? 'Sign in' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">
                Email
              </label>
              <input
                type="email"
                className="input-field"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div>
              <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  className="input-field pr-10"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-bark hover:text-mahogany transition-colors"
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-xs font-body font-semibold text-bark uppercase tracking-wider mb-1.5">
                  Confirm password
                </label>
                <input
                  type={showPwd ? 'text' : 'password'}
                  className="input-field"
                  placeholder="••••••••"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  required
                  autoComplete="new-password"
                />
              </div>
            )}

            {error && (
              <p className="text-sm font-body text-red-500 bg-red-50 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-amber w-full mt-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-xs font-body text-bark mt-6">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-amber hover:text-amber-hover font-semibold transition-colors"
            >
              {mode === 'login' ? 'Register' : 'Sign in'}
            </button>
          </p>
        </div>

        <p className="text-center mt-6">
          <Link to="/" className="font-body text-sm text-bark hover:text-amber transition-colors">
            ← Back to browsing
          </Link>
        </p>
      </div>
    </div>
  )
}
