import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import SearchOverlay from '../components/ui/SearchOverlay'
import AIButton from '../components/ui/AIButton'
import { toast } from '../components/ui/Toast'
import { useAuth } from '../hooks/useAuth'
import { products, formatPrice } from '../services/api'

export default function DiscoverPage() {
  const [searchOpen, setSearchOpen] = useState(false)
  const [watchlistItems, setWatchlistItems] = useState([])
  const [trendingProducts, setTrendingProducts] = useState([])
  const [allProducts, setAllProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [heroInput, setHeroInput] = useState('')
  // Price alerts are auth-gated; kept as empty array to prevent undefined errors
  const [priceAlerts, setPriceAlerts] = useState([])

  const { user } = useAuth()
  const navigate = useNavigate()

  const [preferences, setPreferences] = useState([])

  useEffect(() => {
    if (user?.id) {
      const saved = localStorage.getItem(`dd_preferences_${user.id}`)
      if (saved) setPreferences(JSON.parse(saved))
    }
  }, [user])

  const displayedTrending = trendingProducts.filter(p => {
    if (!preferences.length) return true
    return preferences.some(pref => 
      p.category?.toLowerCase().includes(pref.toLowerCase()) || 
      p.name?.toLowerCase().includes(pref.toLowerCase())
    )
  })

  const displayedAll = allProducts.filter(p => {
    if (!preferences.length) return true
    return preferences.some(pref => 
      p.category?.toLowerCase().includes(pref.toLowerCase()) || 
      p.name?.toLowerCase().includes(pref.toLowerCase())
    )
  })

  useEffect(() => {
    async function loadData() {
      try {
        const [recent, trending] = await Promise.all([
          products.publicRecent(),
          products.publicTrending()
        ])
        setTrendingProducts(trending?.data || [])
        setAllProducts(recent?.data || [])
      } catch (err) {
        console.error('Failed to load discovery data:', err)
        setLoadError(true)
      } finally {
        setLoading(false)
      }
    }
    
    loadData()

    try {
      const stored = JSON.parse(localStorage.getItem('watchlist_items') || '[]')
      const formattedWatchlist = stored.map((s, idx) => ({
        id: s.id || idx,
        product: {
          id: s.id || idx,
          name: s.product_name || s.title || s.query || 'Tracked Item',
          image_url: s.image || null,
          best_price: s.price || s.targetPrice || null,
        }
      }))
      setWatchlistItems(formattedWatchlist)
    } catch (e) {
      console.warn('Could not load local watchlist', e)
    }
  }, [])


  function toggleWatchlist(productId, name) {
    handleRemoveTracking(productId)
  }

  function handleRemoveTracking(productId) {
    try {
      const stored = JSON.parse(localStorage.getItem('watchlist_items') || '[]')
      const updated = stored.filter((s, idx) => (s.id || idx) !== productId)
      localStorage.setItem('watchlist_items', JSON.stringify(updated))
      
      const formattedWatchlist = updated.map((s, idx) => ({
        id: s.id || idx,
        product: {
          id: s.id || idx,
          name: s.product_name || s.title || s.query || 'Tracked Item',
          image_url: s.image || null,
          best_price: s.price || s.targetPrice || null,
        }
      }))
      setWatchlistItems(formattedWatchlist)
      toast('Removed from watchlist', 'neutral')
    } catch (e) {
      console.warn('Could not update watchlist', e)
    }
  }

  function handleHeroSearch(e) {
    e.preventDefault()
    if (!heroInput.trim()) return
    navigate(`/product?q=${encodeURIComponent(heroInput)}`)
  }

  const watchlistIds = new Set(watchlistItems.map(i => i.product_id))

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-screen bg-surface">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        </div>
      </AppLayout>
    )
  }

  if (loadError) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center h-screen gap-4 text-center px-4">
          <div className="w-16 h-16 rounded-full bg-error/10 flex items-center justify-center">
            <span className="material-symbols-outlined text-error text-3xl">wifi_off</span>
          </div>
          <h2 className="text-xl font-bold text-on-surface">Failed to load data</h2>
          <p className="text-on-surface-variant text-sm max-w-xs">Could not connect to the server. Please check your connection and try again.</p>
          <button onClick={() => window.location.reload()} className="bg-primary text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-primary/90 transition-colors">
            Retry
          </button>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="flex flex-col min-h-full pb-16">
        <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />

        {/* 1. HERO SECTION (SEARCH FIRST) */}
        <section className="bg-white py-24 px-8 border-b border-outline-variant/60 text-center animate-fade-up">
          <h1 className="text-4xl md:text-[52px] font-extrabold text-on-surface mb-4 tracking-tight leading-tight">
            The Precision <span className="text-primary italic">Ledger.</span>
          </h1>
          <p className="text-lg text-on-surface-variant max-w-2xl mx-auto mb-12">
            Locate assets, track fluctuations, and secure optimal entry points with precision data mapping.
          </p>
          
          <form onSubmit={handleHeroSearch} className="max-w-xl mx-auto relative group">
            <div className="flex items-center gap-3 p-2 bg-white rounded-2xl shadow-float border border-outline-variant/60 group-focus-within:border-primary/40 transition-all">
              <div className="flex-1 flex items-center gap-3 px-4">
                <span className="material-symbols-outlined text-outline">search</span>
                <input type="text" placeholder="Paste URL or Search Products..." value={heroInput} onChange={e => setHeroInput(e.target.value)}
                  className="w-full py-3 bg-transparent text-on-surface font-medium focus:outline-none placeholder:text-outline/60" />
              </div>
              <button type="submit" className="bg-primary text-white px-8 py-3.5 rounded-xl font-bold hover:bg-primary-container transition-all active:scale-95 shadow-sm">
                Search
              </button>
            </div>
          </form>
        </section>

        <div className="max-w-[1000px] mx-auto w-full px-8 py-12 flex flex-col gap-16">

          {/* 2. WATCHLIST */}
          <section className="animate-fade-up" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-on-surface tracking-tight">Active Watchlist</h2>
                <p className="text-sm text-on-surface-variant">Manage your high-priority items and tracking status.</p>
              </div>
              <button onClick={() => navigate('/alerts')} className="text-primary text-sm font-bold hover:underline bg-primary/5 px-4 py-2 rounded-lg transition-colors">View Detailed List</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {watchlistItems.length === 0 ? (
                <div className="col-span-3 p-16 bg-white border border-dashed border-outline-variant rounded-3xl text-center">
                   <div className="w-16 h-16 rounded-full bg-surface mx-auto mb-4 flex items-center justify-center">
                     <span className="material-symbols-outlined text-outline">bookmark_border</span>
                   </div>
                   <p className="text-on-surface-variant font-medium">Your watchlist is currently empty.</p>
                </div>
              ) : (
                watchlistItems.slice(0, 3).map(item => (
                  <div key={item.id} className="glass-card p-6 flex flex-col gap-5 group hover:-translate-y-1 transition-all duration-300">
                    <div onClick={() => navigate(`/product?q=${encodeURIComponent(item.product?.name || '')}`)} className="h-40 bg-surface rounded-2xl flex items-center justify-center p-6 cursor-pointer border border-outline-variant/20 relative overflow-hidden">
                      {item.product.image_url ? <img src={item.product.image_url} alt="" className="w-full h-full object-contain mix-blend-multiply" /> : <span className="text-5xl">🛍️</span>}
                    </div>
                    <div>
                      <h3 onClick={() => navigate(`/product?q=${encodeURIComponent(item.product?.name || '')}`)} className="font-bold text-on-surface truncate text-base mb-1 cursor-pointer hover:text-primary transition-colors">{item.product.name}</h3>
                      <span className="font-black text-xl text-primary">{formatPrice(item.product.best_price)}</span>
                    </div>
                    <div className="flex flex-col gap-2 pt-2">
                       <button onClick={(e) => { e.stopPropagation(); handleRemoveTracking(item.product.id) }} className="w-full py-2.5 rounded-xl text-xs font-bold bg-surface text-on-surface-variant hover:bg-surface-container transition-colors border border-outline-variant/40">
                         Remove Tracking
                       </button>
                       <button onClick={(e) => { e.stopPropagation(); toggleWatchlist(item.product.id, item.product.name) }} className="w-full py-2.5 rounded-xl text-xs font-bold text-red-500 hover:bg-red-50 transition-colors border border-red-100">
                         Remove
                       </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          {/* 3. TRENDS (HORIZONTAL SCROLL) */}
          <section className="animate-fade-up" style={{ animationDelay: '0.2s' }}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-on-surface tracking-tight">Trends</h2>
            </div>
            <div className="flex overflow-x-auto gap-5 pb-4 snap-x hide-scrollbar" style={{ scrollbarWidth: 'none' }}>
              {displayedTrending.map((t, i) => (
                <div key={t.id} onClick={() => navigate(`/product?q=${encodeURIComponent(t.name)}`)} className="glass-card flex-shrink-0 w-[280px] p-4 cursor-pointer snap-start flex gap-4 items-center">

                  <div className="w-16 h-16 bg-surface-container-low rounded-lg flex items-center justify-center p-2 flex-shrink-0">
                    {t.image_url ? <img src={t.image_url} alt="" className="w-full h-full object-contain mix-blend-multiply" /> : <span>🛍️</span>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm text-on-surface truncate mb-1">{t.name}</div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold">{formatPrice(t.best_price)}</span>
                      {t.drop_pct > 0 && <span className="text-[10px] font-bold text-tertiary">-{t.drop_pct}%</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 4. PRICE ALERTS */}
          <section className="animate-fade-up" style={{ animationDelay: '0.3s' }}>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-on-surface tracking-tight">Price Alerts</h2>
                <p className="text-sm text-on-surface-variant">Active sentinels monitoring your target thresholds.</p>
              </div>
              <button onClick={() => navigate('/alerts')} className="text-primary text-sm font-bold hover:underline">Manage All</button>
            </div>
            <div className="bg-white border border-outline-variant/40 rounded-3xl overflow-hidden shadow-sm divide-y divide-outline-variant/20">
              {priceAlerts.length === 0 ? (
                <div className="p-16 text-center text-on-surface-variant font-medium">
                   No active price alerts found.
                </div>
              ) : (
                priceAlerts.slice(0, 3).map((a) => (
                  <div key={a.id} className="flex items-center justify-between p-6 hover:bg-surface/50 transition-colors">
                    <div className="flex items-center gap-5">
                      <div className="w-12 h-12 bg-primary/5 rounded-xl flex items-center justify-center text-primary border border-primary/10">
                        <span className="material-symbols-outlined">notifications_active</span>
                      </div>
                      <div>
                        <div className="font-bold text-on-surface">Target: {formatPrice(a.target_price)}</div>
                        <div onClick={() => navigate(`/product?q=${encodeURIComponent(a.product?.name || '')}`)} className="text-sm text-on-surface-variant font-medium line-clamp-1 max-w-[300px] cursor-pointer hover:text-primary transition-colors">{a.product.name}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <span className={`text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider ${a.is_active ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-surface-container text-on-surface-variant'}`}>
                        {a.is_active ? 'Active' : 'Paused'}
                      </span>
                      <div 
                        onClick={() => handleToggleAlert(a.id)}
                        className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors duration-200 ${a.is_active ? 'bg-primary' : 'bg-outline-variant'}`}
                      >
                        <div className={`w-4.5 h-4.5 bg-white rounded-full absolute top-0.75 transition-all duration-200 shadow-sm ${a.is_active ? 'right-0.75' : 'left-0.75'}`}></div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          {/* 5. PRICE DROPS */}
          <section className="animate-fade-up" style={{ animationDelay: '0.4s' }}>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-on-surface tracking-tight">Price Drops</h2>
                <p className="text-sm text-on-surface-variant">Products whose price has decreased recently across indexed retailers.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {displayedAll.filter(p => p.drop_pct > 0).slice(0, 4).map(p => (

                <div key={p.id} onClick={() => navigate(`/product?q=${encodeURIComponent(p.name)}`)} className="bg-white border border-outline-variant/40 rounded-3xl p-6 hover:shadow-lg hover:border-primary/20 transition-all cursor-pointer flex items-center justify-between group">
                  <div className="flex flex-col gap-1">
                    <span className="font-bold text-on-surface group-hover:text-primary transition-colors truncate max-w-[200px]">{p.name}</span>
                    <span className="font-black text-2xl text-on-surface">{formatPrice(p.best_price)}</span>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <div className="px-3 py-1.5 rounded-xl font-black text-sm bg-tertiary-container text-on-tertiary-container">
                      -{p.drop_pct}%
                    </div>
                    <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Market Delta</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 6. PRICE INSIGHTS */}
          <section className="animate-fade-up" style={{ animationDelay: '0.5s' }}>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-on-surface tracking-tight">Price Insights</h2>
                <p className="text-sm text-on-surface-variant">AI-based analysis of market trends, predicted movements, and purchase recommendations.</p>
              </div>
            </div>
            <div className="bg-white border border-outline-variant/40 rounded-[32px] p-10 shadow-sm grid grid-cols-1 lg:grid-cols-3 gap-12 items-center">
              <div className="lg:col-span-2">
                <div className="flex items-center justify-between mb-6">
                  <span className="text-sm font-bold text-on-surface-variant uppercase tracking-widest">Market Performance Aggregate</span>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-primary animate-pulse" />
                    <span className="text-sm font-black text-primary">Bullish Trend</span>
                  </div>
                </div>
                <div className="h-48 flex items-end gap-3">
                  {[40, 70, 45, 90, 65, 80, 55, 95, 75, 85].map((h, i) => (
                    <div key={i} className="flex-1 bg-primary/10 rounded-t-lg relative group transition-all hover:bg-primary/20" style={{ height: `${h}%` }}>
                      <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-on-surface text-white text-[10px] font-bold py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                        {h}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-6 bg-surface p-8 rounded-3xl border border-outline-variant/40">
                <div className="pb-6 border-b border-outline-variant/40">
                   <div className="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em] mb-2">Recommendation</div>
                   <div className="text-3xl font-black text-primary">BUY NOW</div>
                </div>
                <div className="pb-6 border-b border-outline-variant/40">
                   <div className="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em] mb-2">Predicted Movement</div>
                   <div className="text-xl font-bold text-on-surface">+ ₹2,400 Expected</div>
                </div>
                <div>
                   <div className="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em] mb-2">Confidence Score</div>
                   <div className="flex items-center gap-3">
                     <div className="flex-1 h-2 bg-outline-variant/20 rounded-full overflow-hidden">
                        <div className="h-full bg-primary rounded-full" style={{ width: '92%' }} />
                     </div>
                     <span className="text-xs font-black text-on-surface">92%</span>
                   </div>
                </div>
              </div>
            </div>
          </section>

        </div>
      </div>
      {allProducts[0] && (
        <AIButton 
          product={{
            id: allProducts[0].id,
            name: allProducts[0].name,
            price: formatPrice(allProducts[0].best_price),
            category: allProducts[0].category,
            retailers: allProducts[0].retailers?.map(r => ({ name: r.retailer, price: formatPrice(r.current_price) }))
          }} 
          position="fixed" 
        />
      )}
    </AppLayout>
  )
}
