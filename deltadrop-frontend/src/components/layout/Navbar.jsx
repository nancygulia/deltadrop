import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { toast } from '../ui/Toast'
import UserMenu from './UserMenu'

export default function Navbar() {
  const { user, isLoggedIn } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const isActive = (path) => location.pathname === path

  return (
    <nav className="bg-white sticky top-0 w-full z-50 border-b border-outline-variant/40 h-16 flex items-center">
      <div className="max-w-7xl mx-auto px-8 w-full flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to={isLoggedIn ? "/discover" : "/"} className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-white text-base">bolt</span>
            </div>
            <div className="font-headline font-bold text-[17px] text-on-surface leading-tight tracking-tight">DeltaDrop</div>
          </Link>
          
          <div className="hidden md:flex gap-1 ml-4">
            <Link to="/trends"
              className={`text-sm px-3 py-1.5 rounded-md font-medium transition-colors
                ${isActive('/trends') ? 'text-primary bg-primary/5 font-semibold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'}`}>
              Price Trends
            </Link>
            <Link to="/stores"
              className={`text-sm px-3 py-1.5 rounded-md font-medium transition-colors
                ${isActive('/stores') ? 'text-primary bg-primary/5 font-semibold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'}`}>
              Stores
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isLoggedIn ? (
            <div className="flex items-center gap-4">
              <Link to="/discover" className="text-sm font-semibold text-primary px-3 py-1.5 rounded-md hover:bg-primary/5 transition-colors">
                Dashboard
              </Link>
              <div 
                className="w-9 h-9 rounded-full bg-primary flex items-center justify-center font-bold text-white text-sm cursor-pointer hover:ring-2 hover:ring-primary/20 transition-all overflow-hidden"
                onClick={() => setMenuOpen(true)}
              >
                {user?.avatar ? (
                  <img src={user.avatar} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <span>{(user?.full_name || user?.username || 'U')[0].toUpperCase()}</span>
                )}
              </div>
            </div>
          ) : (
            <>
              <Link to="/login" className="text-sm font-semibold text-on-surface-variant hover:text-on-surface px-4 py-2 transition-colors">
                Sign In
              </Link>
              <Link to="/register" className="bg-primary text-white px-5 py-2.5 rounded-lg font-bold text-sm hover:bg-primary-container active:scale-95 transition-all shadow-sm">
                Sign Up
              </Link>
            </>
          )}
        </div>
      </div>

      {isLoggedIn && (
        <UserMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)} />
      )}
    </nav>
  )
}
