import { Link } from 'react-router-dom'

export default function Footer() {
  const retailers = ['Amazon', 'Flipkart', 'Croma', 'Reliance', 'Myntra', 'Tata CLiQ', 'Nykaa']
  
  return (
    <footer className="bg-white border-t border-outline-variant/40 py-16 px-8">
      <div className="max-w-7xl mx-auto">
        {/* Retailers Section */}
        <div className="text-center mb-16">
          <p className="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.3em] mb-10">Indexed Retail Network</p>
          <div className="flex flex-wrap items-center justify-center gap-x-16 gap-y-8 opacity-25">
            {retailers.map(s => (
              <span key={s} className="font-headline font-extrabold text-xl grayscale">{s}</span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 pt-12 border-t border-outline-variant/20">
          <div className="col-span-1 md:col-span-1">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="material-symbols-outlined text-white text-sm">bolt</span>
              </div>
              <div className="font-headline font-bold text-lg text-on-surface">DeltaDrop</div>
            </div>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Precision price tracking and market intelligence for the modern consumer.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-black text-on-surface uppercase tracking-widest mb-6">Platform</h4>
            <ul className="space-y-4">
              <li><Link to="/trends" className="text-sm text-on-surface-variant hover:text-primary transition-colors">Market Trends</Link></li>
              <li><Link to="/discover" className="text-sm text-on-surface-variant hover:text-primary transition-colors">Discover Deals</Link></li>
              <li><Link to="/alerts" className="text-sm text-on-surface-variant hover:text-primary transition-colors">Price Alerts</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-black text-on-surface uppercase tracking-widest mb-6">Company</h4>
            <ul className="space-y-4">
              <li><Link to="/discover" className="text-sm text-on-surface-variant hover:text-primary transition-colors">About Us</Link></li>
              <li><Link to="/transparency" className="text-sm text-on-surface-variant hover:text-primary transition-colors">Transparency</Link></li>
              <li><Link to="/help" className="text-sm text-on-surface-variant hover:text-primary transition-colors">Contact</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-black text-on-surface uppercase tracking-widest mb-6">Legal</h4>
            <ul className="space-y-4">
              <li><Link to="/terms" className="text-sm text-on-surface-variant hover:text-primary transition-colors">Terms of Service</Link></li>
              <li><Link to="/privacy" className="text-sm text-on-surface-variant hover:text-primary transition-colors">Privacy Policy</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-outline-variant/10 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-outline font-medium">
            © {new Date().getFullYear()} DeltaDrop Technologies. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
             <span className="text-xs text-outline hover:text-primary cursor-pointer transition-colors">Twitter</span>
             <span className="text-xs text-outline hover:text-primary cursor-pointer transition-colors">LinkedIn</span>
             <span className="text-xs text-outline hover:text-primary cursor-pointer transition-colors">GitHub</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
