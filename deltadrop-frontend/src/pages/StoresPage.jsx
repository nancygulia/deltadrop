import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import { toast } from '../components/ui/Toast'

const STORES = [
  {
    id: 'amazon',  logo: '🅰',  logoColor: '#FF9900', logoBg: '#FFF3E0',
    name: 'Amazon.in', badge: 'HIGH STABILITY', badgeColor: 'bg-tertiary-container/15 text-tertiary-container',
    tracked: '1.2M+', discount: '22.4%', updated: '2 mins ago',
  },
  {
    id: 'flipkart', logo: 'F', logoColor: '#F77F00', logoBg: '#FFF3E0',
    name: 'Flipkart', badge: 'FAST REFRESH', badgeColor: 'bg-blue-100 text-blue-700',
    tracked: '840K+', discount: '18.1%', updated: 'Just now',
  },
  {
    id: 'reliance', logo: 'R', logoColor: '#1B4FD8', logoBg: '#EEF3FF',
    name: 'Reliance Digital', badge: 'VERIFIED', badgeColor: 'bg-tertiary-container/15 text-tertiary-container',
    tracked: '115K+', discount: '12.5%', updated: '15 mins ago',
  },
  {
    id: 'myntra',  logo: 'M', logoColor: '#FF3EA5', logoBg: '#FFE4F0',
    name: 'Myntra', badge: 'LIFESTYLE', badgeColor: 'bg-pink-100 text-pink-700',
    tracked: '350K+', discount: '45.0%', updated: '8 mins ago',
  },
  {
    id: 'croma',   logo: 'C', logoColor: '#E91E63', logoBg: '#FCE4EC',
    name: 'Croma', badge: 'PRECISION', badgeColor: 'bg-tertiary-container/15 text-tertiary-container',
    tracked: '92K+', discount: '9.2%', updated: '45 mins ago',
  },
]

export default function StoresPage() {
  const [searchQ, setSearchQ]   = useState('')
  const navigate = useNavigate()

  const filtered = STORES.filter(s =>
    s.name.toLowerCase().includes(searchQ.toLowerCase())
  )

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-8 py-12">
        {/* Header Section */}
        <div className="mb-12 animate-fade-up">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 text-primary text-xs font-bold uppercase tracking-wider mb-6">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Verified Retailer Network
          </div>
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
            <div className="max-w-2xl">
              <h1 className="text-4xl font-extrabold text-on-surface tracking-tight mb-4">
                Global Marketplace Intelligence
              </h1>
              <p className="text-lg text-on-surface-variant leading-relaxed">
                We monitor the pulse of the largest marketplaces in real-time. Access historical volatility data and secure the best entry points across 2 million tracked products.
              </p>
            </div>
            <div className="bg-white rounded-2xl p-6 border border-outline-variant/40 shadow-sm flex items-center gap-4 min-w-[240px]">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-2xl">hub</span>
              </div>
              <div>
                <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Active Retailers</div>
                <div className="text-2xl font-black text-on-surface">5,000+</div>
              </div>
            </div>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-col md:flex-row gap-4 mb-12 animate-fade-up" style={{ animationDelay: '0.1s' }}>
          <div className="flex-1 relative group">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors">search</span>
            <input 
              type="text"
              value={searchQ}
              onChange={e => setSearchQ(e.target.value)}
              placeholder="Filter retailers by name or platform..."
              className="w-full bg-white border border-outline-variant/40 rounded-2xl pl-12 pr-6 py-4 text-sm font-medium focus:ring-4 focus:ring-primary/5 focus:border-primary outline-none transition-all shadow-sm"
            />
          </div>
          <button className="px-6 py-4 bg-white border border-outline-variant/40 rounded-2xl text-sm font-bold text-on-surface flex items-center gap-2 hover:bg-surface transition-all shadow-sm">
            <span className="material-symbols-outlined text-lg">filter_list</span>
            Category: All
          </button>
        </div>

        {/* Store Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16 animate-fade-up" style={{ animationDelay: '0.2s' }}>
          {filtered.map((store, i) => (
            <div key={store.id} className="bg-white rounded-3xl p-8 border border-outline-variant/40 shadow-sm hover:shadow-md transition-all group flex flex-col">
              <div className="flex items-start justify-between mb-8">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black shadow-inner"
                  style={{ background: store.logoBg, color: store.logoColor }}>
                  {store.logo}
                </div>
                <span className={`text-[10px] font-black px-3 py-1.5 rounded-lg uppercase tracking-wider ${store.badgeColor}`}>
                  {store.badge}
                </span>
              </div>
              
              <h3 className="text-xl font-bold text-on-surface mb-6 group-hover:text-primary transition-colors">{store.name}</h3>

              <div className="space-y-4 mb-8 flex-1">
                <div className="flex justify-between items-center py-2 border-b border-outline-variant/20">
                  <span className="text-sm font-medium text-on-surface-variant">Products Indexed</span>
                  <span className="text-sm font-bold text-on-surface">{store.tracked}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-outline-variant/20">
                  <span className="text-sm font-medium text-on-surface-variant">Avg. Volatility</span>
                  <span className="text-sm font-bold text-tertiary-container">{store.discount}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm font-medium text-on-surface-variant">Sync Status</span>
                  <span className="text-sm font-bold text-primary">{store.updated}</span>
                </div>
              </div>

              <button 
                onClick={() => toast(`Establishing connection to ${store.name}...`, 'info')}
                className="w-full py-4 bg-primary text-white rounded-2xl font-bold text-sm hover:bg-primary-container active:scale-95 transition-all shadow-sm"
              >
                Analyze Trends
              </button>
            </div>
          ))}

          {/* Request Card */}
          <div className="bg-surface rounded-3xl p-8 border-2 border-dashed border-outline-variant/60 flex flex-col items-center justify-center text-center group hover:border-primary/40 transition-all">
            <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center mb-6 shadow-sm group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-outline text-3xl">add_business</span>
            </div>
            <h3 className="text-lg font-bold text-on-surface mb-2">Request Integration</h3>
            <p className="text-sm text-on-surface-variant max-w-[200px] mb-8 leading-relaxed">
              Missing your favorite platform? Propose a new retailer for our ledger.
            </p>
            <button 
              onClick={() => toast('Request logged into protocol.', 'success')}
              className="text-sm font-bold text-primary flex items-center gap-2 hover:underline"
            >
              Submit Proposal
              <span className="material-symbols-outlined text-base">arrow_forward</span>
            </button>
          </div>
        </div>

        {/* Intelligence Banner */}
        <div className="bg-primary/5 rounded-[32px] p-12 flex flex-col lg:flex-row items-center gap-12 animate-fade-up">
          <div className="flex-1">
            <h2 className="text-3xl font-bold text-on-surface mb-4 tracking-tight">Institutional Accuracy</h2>
            <p className="text-on-surface-variant leading-relaxed max-w-xl mb-8">
              Our proprietary engine leverages sub-millisecond price indexing to ensure every drop is captured with 99.8% precision. We eliminate noise and deliver actionable market intelligence.
            </p>
            <div className="flex flex-wrap gap-8">
              <div>
                <div className="text-3xl font-black text-primary">99.8%</div>
                <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mt-1">Sync Precision</div>
              </div>
              <div>
                <div className="text-3xl font-black text-tertiary-container">2M+</div>
                <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mt-1">Products Tracked</div>
              </div>
            </div>
          </div>
          <div className="lg:w-1/3 w-full bg-white rounded-2xl p-6 shadow-sm border border-outline-variant/40">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-lg bg-tertiary-container/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-tertiary-container text-base">monitoring</span>
              </div>
              <span className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">Network Stability</span>
            </div>
            <div className="space-y-4">
              {[70, 45, 90, 60, 85].map((w, i) => (
                <div key={i} className="h-1.5 w-full bg-surface rounded-full overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: `${w}%` }} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
