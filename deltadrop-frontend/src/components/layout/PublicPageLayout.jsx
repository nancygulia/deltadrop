import { Link } from 'react-router-dom'
import Navbar from './Navbar'

/**
 * PublicPageLayout — clean, centered layout for informational pages.
 * (Privacy, Transparency, Help, Terms)
 * No dashboard sidebar. No Watchlist/Drops/Analytics nav.
 * Content is centered with a max-width, with a standard footer.
 */
export default function PublicPageLayout({ children }) {
  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <Navbar />

      <main className="flex-1 w-full max-w-4xl mx-auto px-6 py-12">
        {children}
      </main>

      <footer className="bg-surface-container-low border-t border-outline-variant/10 py-8">
        <div className="max-w-4xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-headline font-black text-on-surface">DeltaDrop</span>
            <span className="text-xs text-on-surface-variant uppercase tracking-wider">Precision Ledger © 2026</span>
          </div>
          <div className="flex gap-6">
            {[['Privacy', '/privacy'], ['Transparency', '/transparency'], ['Terms', '/terms'], ['Help', '/help'], ['Extension', '/extension']].map(([l, to]) => (
              <Link key={l} to={to} className="text-sm text-on-surface-variant hover:text-primary transition-colors">{l}</Link>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}
