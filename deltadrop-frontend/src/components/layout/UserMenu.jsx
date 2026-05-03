import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { toast } from '../ui/Toast'

export default function UserMenu({ isOpen, onClose }) {
  const { user, logout } = useAuth()

  if (!isOpen) return null

  const handleLogout = async () => {
    await logout()
    toast('Signed out successfully', 'neutral')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-[60] flex justify-end p-6 md:p-12 items-start pointer-events-none">
      {/* Backdrop for click-away */}
      <div 
        className="fixed inset-0 pointer-events-auto bg-black/5 backdrop-blur-[2px]" 
        onClick={onClose}
      />
      
      {/* User Account Quick Switcher Modal */}
      <div className="w-full max-w-sm bg-surface-container-lowest editorial-shadow rounded-xl pointer-events-auto border border-outline-variant/15 overflow-hidden relative z-10 animate-fade-in-down">
        {/* Current User Profile Section */}
        <div className="p-8 bg-surface-container-low border-b border-surface-container-highest">
          <div className="flex items-center gap-5">
            <div className="relative">
              {user?.avatar ? (
                <img 
                  alt="User profile avatar" 
                  className="w-16 h-16 rounded-full object-cover ring-4 ring-white" 
                  src={user.avatar}
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-3xl font-bold text-white ring-4 ring-white">
                  {(user?.full_name || user?.username || user?.name || 'U')[0].toUpperCase()}
                </div>
              )}
              <div className="absolute bottom-0 right-0 w-4 h-4 bg-tertiary-fixed rounded-full border-2 border-white"></div>
            </div>
            <div>
              <h3 className="text-xl font-bold font-headline text-on-surface tracking-tight leading-tight">
                {user?.full_name || user?.username || user?.name || 'User'}
              </h3>
              <p className="text-sm font-medium text-on-secondary-container font-body truncate max-w-[180px]">
                {user?.email || ''}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Actions */}
        <div className="p-2">
          <Link 
            to="/profile" 
            onClick={onClose}
            className="group flex items-center gap-4 px-6 py-4 cursor-pointer hover:bg-surface-container rounded-lg transition-all"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-container text-primary">
              <span className="material-symbols-outlined">manage_accounts</span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold font-headline text-on-surface">Manage Account</p>
              <p className="text-xs text-on-secondary-container">Profile, security, and settings</p>
            </div>
            <span className="material-symbols-outlined text-outline-variant group-hover:text-primary transition-colors">chevron_right</span>
          </Link>

          <Link 
            to="/watchlist" 
            onClick={onClose}
            className="group flex items-center gap-4 px-6 py-4 cursor-pointer hover:bg-surface-container rounded-lg transition-all"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
              <span className="material-symbols-outlined">bookmarks</span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold font-headline text-on-surface">Watchlist</p>
              <p className="text-xs text-on-secondary-container">Tracked items and price drops</p>
            </div>
            <span className="material-symbols-outlined text-outline-variant group-hover:text-primary transition-colors">chevron_right</span>
          </Link>
        </div>

        {/* Footer Action */}
        <div className="p-6 bg-surface-container-low">
          <button 
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-lg border border-outline-variant text-on-surface hover:bg-white transition-all font-bold text-sm font-headline"
          >
            <span className="material-symbols-outlined text-error">logout</span>
            Sign Out
          </button>
        </div>
      </div>
    </div>
  )
}
