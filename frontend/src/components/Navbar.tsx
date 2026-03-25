import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Menu, X, GlassWater, LogOut, DollarSign } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const navLink = ({ isActive }: { isActive: boolean }) =>
    `font-body font-semibold text-sm tracking-wide transition-colors duration-150 px-1 pb-0.5 border-b-2 ${
      isActive
        ? 'text-amber border-amber'
        : 'text-parchment-200 border-transparent hover:text-white hover:border-parchment-300'
    }`

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-mahogany shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <GlassWater className="w-6 h-6 text-amber group-hover:text-amber-light transition-colors" />
            <span className="font-display text-2xl text-white tracking-wider leading-none">
              Cocktail Finder
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-6">
            <NavLink to="/" end className={navLink}>Browse</NavLink>
            {user && <NavLink to="/mybar" className={navLink}>My Bar</NavLink>}
            <a
              href="https://venmo.com/jeremy-colon"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 font-body text-sm text-parchment-300 hover:text-amber transition-colors"
            >
              <DollarSign className="w-4 h-4" />
              Buy me a drink
            </a>
            {user ? (
              <button onClick={handleLogout} className="flex items-center gap-1.5 btn-ghost text-parchment-200 hover:text-white hover:bg-mahogany-light">
                <LogOut className="w-4 h-4" />
                Log out
              </button>
            ) : (
              <Link to="/login" className="btn-amber text-sm">Sign in</Link>
            )}
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setOpen(!open)}
            className="md:hidden p-2 text-parchment-200 hover:text-white transition-colors"
            aria-label="Toggle menu"
          >
            {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-mahogany-light border-t border-mahogany-medium px-4 py-4 flex flex-col gap-4">
          <NavLink to="/" end className={navLink} onClick={() => setOpen(false)}>Browse</NavLink>
          {user && (
            <NavLink to="/mybar" className={navLink} onClick={() => setOpen(false)}>My Bar</NavLink>
          )}
          <a
            href="https://venmo.com/jeremy-colon"
            target="_blank"
            rel="noopener noreferrer"
            className="font-body text-sm text-parchment-300 hover:text-amber transition-colors"
          >
            Buy me a drink
          </a>
          {user ? (
            <button onClick={handleLogout} className="text-left font-body text-sm text-parchment-200 hover:text-white">
              Log out
            </button>
          ) : (
            <Link to="/login" className="btn-amber text-sm text-center" onClick={() => setOpen(false)}>
              Sign in
            </Link>
          )}
        </div>
      )}
    </nav>
  )
}
