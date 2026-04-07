import { useState, useRef } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Menu, X, GlassWater, LogOut, DollarSign, ShoppingCart } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useCartCount, useClearCart } from '../hooks/useCocktails'

interface Props {
  onCartClick: () => void
}

const DROPDOWN_LIMIT = 5

export default function Navbar({ onCartClick }: Props) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [cartOpen, setCartOpen] = useState(false)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { data: cartData } = useCartCount()
  const cartCount = cartData?.count ?? 0
  const cartItems = cartData?.items ?? []
  const clearCart = useClearCart()

  function openCart() {
    if (closeTimer.current) clearTimeout(closeTimer.current)
    setCartOpen(true)
  }
  function scheduleClose() {
    closeTimer.current = setTimeout(() => setCartOpen(false), 150)
  }

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
            {user?.is_admin && <NavLink to="/admin" className={navLink}>Admin</NavLink>}
            {user && (
              <div
                className="relative"
                onMouseEnter={openCart}
                onMouseLeave={scheduleClose}
              >
                <button
                  onClick={onCartClick}
                  className="relative text-parchment-200 hover:text-amber transition-colors"
                  title="Tonight's cart"
                >
                  <ShoppingCart className="w-5 h-5" />
                  {cartCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-amber text-white text-[10px] flex items-center justify-center font-semibold leading-none">
                      {cartCount}
                    </span>
                  )}
                </button>

                {cartOpen && (
                  <div className="absolute right-0 top-full mt-2 w-64 rounded-xl bg-white shadow-lg border border-parchment-200 overflow-hidden z-50">
                    {cartCount === 0 ? (
                      <p className="px-4 py-3 text-sm font-body text-bark">Your cart is empty</p>
                    ) : (
                      <>
                        <ul className="divide-y divide-parchment-100">
                          {cartItems.slice(0, DROPDOWN_LIMIT).map(item => (
                            <li key={item.cocktail_id} className="px-4 py-2 text-sm font-body text-mahogany truncate">
                              {item.recipe_name}
                            </li>
                          ))}
                        </ul>
                        {cartCount > DROPDOWN_LIMIT && (
                          <p className="px-4 py-2 text-xs font-body text-bark border-t border-parchment-100">
                            +{cartCount - DROPDOWN_LIMIT} more
                          </p>
                        )}
                      </>
                    )}
                    <div className="flex border-t border-parchment-200">
                      <button
                        onClick={() => { onCartClick(); setCartOpen(false) }}
                        className="flex-1 px-3 py-2 text-xs font-body font-semibold text-amber hover:bg-amber/10 transition-colors"
                      >
                        View cart
                      </button>
                      <button
                        onClick={() => { clearCart.mutate(); setCartOpen(false) }}
                        className="flex-1 px-3 py-2 text-xs font-body font-semibold text-bark hover:bg-parchment-100 transition-colors border-l border-parchment-200"
                      >
                        Clear cart
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
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
          {user?.is_admin && (
            <NavLink to="/admin" className={navLink} onClick={() => setOpen(false)}>Admin</NavLink>
          )}
          {user && (
            <button
              onClick={() => { onCartClick(); setOpen(false) }}
              className="flex items-center gap-2 text-left font-body font-semibold text-sm text-parchment-200 hover:text-amber transition-colors"
            >
              <ShoppingCart className="w-4 h-4" />
              Tonight's cart{cartCount > 0 ? ` (${cartCount})` : ''}
            </button>
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
