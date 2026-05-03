import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { toast } from '../ui/Toast'
import UserMenu from './UserMenu'

export default function DashboardHeader({ tabs = [] }) {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const [scrolled, setScrolled] = useState(false)
  const u = user || {}

  // Handle scroll shadow
  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', handleScroll)
    handleScroll()
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`sticky top-0 z-50 bg-white transition-shadow duration-200 ${scrolled ? 'shadow-sm border-b border-outline-variant/10' : 'border-b border-outline-variant/10'} h-16 flex items-center justify-between px-8`}>
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/discover')}>
        <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center flex-shrink-0">
          <span className="material-symbols-outlined text-white text-base">bolt</span>
        </div>
        <div>
          <div className="font-headline font-bold text-[15px] text-on-surface leading-tight tracking-tight">DeltaDrop</div>
        </div>
      </div>

      <div className="flex items-center gap-5">
        <button 
          onClick={() => navigate('/alerts')}
          className="text-sm font-semibold text-primary hover:text-primary-container transition-colors"
        >
          Track Product
        </button>
        <button 
          onClick={() => navigate('/trends')}
          className="text-sm font-semibold text-on-surface-variant hover:text-on-surface transition-colors"
        >
          Explore Deals
        </button>

        <div className="w-px h-6 bg-outline-variant/40 mx-2" />

        {/* Notifications */}
        <button 
          onClick={() => toast('3 new price alerts — iPhone 15 Pro dropped ₹5,000!', 'success')}
          className="relative w-9 h-9 rounded-full bg-surface hover:bg-surface-container transition-colors flex items-center justify-center text-on-surface-variant"
        >
          <span className="material-symbols-outlined text-xl">notifications</span>
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 border-2 border-white"/>
        </button>

        {/* User Avatar */}
        <div 
          className="w-9 h-9 rounded-full bg-primary flex items-center justify-center font-bold text-white text-sm cursor-pointer hover:ring-2 hover:ring-primary/20 transition-all overflow-hidden"
          onClick={() => navigate('/profile')}
        >
          {u.avatar ? (
            <img src={u.avatar} alt="Profile" className="w-full h-full object-cover" />
          ) : (
            <span>{(u.full_name || u.username || u.name || 'U')[0].toUpperCase()}</span>
          )}
        </div>
      </div>

      <UserMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)} />
    </header>
  )
}
