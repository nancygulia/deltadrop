import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import ToastProvider    from './components/ui/Toast'
import SearchOverlay    from './components/ui/SearchOverlay'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import LandingPage      from './pages/LandingPage'
import LoginPage        from './pages/LoginPage'
import RegisterPage     from './pages/RegisterPage'
import DiscoverPage     from './pages/DiscoverPage'
import ProductPage      from './pages/ProductPage'
import AlertsPage       from './pages/AlertsPage'
import ExtensionPage    from './pages/ExtensionPage'
import TrendsPage       from './pages/TrendsPage'
import StoresPage       from './pages/StoresPage'
import PrivacyPage      from './pages/PrivacyPage'
import HelpPage         from './pages/HelpPage'
import TransparencyPage from './pages/TransparencyPage'
import TermsPage        from './pages/TermsPage'
import ProfilePage      from './pages/ProfilePage'
import WatchlistPage    from './pages/WatchlistPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import PriceIntelligenceSentinelPage from './pages/PriceIntelligenceSentinelPage'
import MRPAnalyzerSentinelPage   from './pages/MRPAnalyzerSentinelPage'
import { useAuth }      from './hooks/useAuth'

function Protected({ children }) {
  const { isLoggedIn, isInitializing } = useAuth()
  if (isInitializing) return <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest animate-pulse"><div className="w-12 h-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" /></div>
  return isLoggedIn ? children : <Navigate to="/login" replace />
}

/** Wrap any page in an ErrorBoundary so component errors never produce a blank screen */
function SafePage({ children }) {
  return <ErrorBoundary>{children}</ErrorBoundary>
}

export default function App() {
  const [globalSearch, setGlobalSearch] = useState(false)
  const { isInitializing } = useAuth()

  useEffect(() => {
    const handler = e => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setGlobalSearch(v => !v)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
          <p className="text-sm font-medium text-on-surface-variant animate-pulse">Initializing DeltaDrop...</p>

        </div>
      </div>
    )
  }

  return (
    <>
      <Routes>
        <Route path="/"             element={<SafePage><LandingPage /></SafePage>} />
        <Route path="/login"        element={<SafePage><LoginPage /></SafePage>} />
        <Route path="/register"     element={<SafePage><RegisterPage /></SafePage>} />
        <Route path="/reset-password" element={<SafePage><ResetPasswordPage /></SafePage>} />
        <Route path="/extension"    element={<SafePage><ExtensionPage /></SafePage>} />
        <Route path="/trends"       element={<SafePage><TrendsPage /></SafePage>} />
        <Route path="/stores"       element={<SafePage><StoresPage /></SafePage>} />
        <Route path="/privacy"      element={<SafePage><PrivacyPage /></SafePage>} />
        <Route path="/help"         element={<SafePage><HelpPage /></SafePage>} />
        <Route path="/transparency" element={<SafePage><TransparencyPage /></SafePage>} />
        <Route path="/terms"        element={<SafePage><TermsPage /></SafePage>} />
        <Route path="/discover"     element={<SafePage><Protected><DiscoverPage /></Protected></SafePage>} />
        <Route path="/watchlist"    element={<SafePage><WatchlistPage /></SafePage>} />

        <Route path="/product"      element={<SafePage><ProductPage /></SafePage>} />
        <Route path="/product/:id"  element={<SafePage><ProductPage /></SafePage>} />
        <Route path="/alerts"       element={<SafePage><Protected><AlertsPage /></Protected></SafePage>} />
        <Route path="/profile"      element={<SafePage><Protected><ProfilePage /></Protected></SafePage>} />
        <Route path="/price-sentinel" element={<SafePage><PriceIntelligenceSentinelPage /></SafePage>} />
        <Route path="/mrp-sentinel" element={<SafePage><MRPAnalyzerSentinelPage /></SafePage>} />
        <Route path="*"             element={<Navigate to="/" replace />} />
      </Routes>
      {/* Global Ctrl+K search overlay */}
      <SearchOverlay open={globalSearch} onClose={() => setGlobalSearch(false)} />
      {/* Single global toast provider */}
      <ToastProvider />
    </>
  )
}
