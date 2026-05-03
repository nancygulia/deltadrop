import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import AIButton from '../components/ui/AIButton'
import { toast } from '../components/ui/Toast'
import { watchlist, alerts, products, formatPrice } from '../services/api'

function parseThresholdValue(value) {
  if (value == null) return null
  const raw = String(value).trim()
  if (!raw) return null
  if (raw.toLowerCase().includes('any')) return null

  const match = raw.match(/(\d+(?:\.\d+)?)/)
  return match ? Number(match[1]) : null
}

function inferRetailerFromUrl(url) {
  const normalized = url.toLowerCase()
  if (normalized.includes('flipkart.com')) return 'Flipkart'
  if (normalized.includes('myntra.com')) return 'Myntra'
  if (normalized.includes('reliancedigital.in')) return 'Reliance Digital'
  if (normalized.includes('nykaa.com')) return 'Nykaa'
  if (normalized.includes('croma.com')) return 'Croma'
  if (normalized.includes('ajio.com')) return 'AJIO'
  if (normalized.includes('tatacliq.com')) return 'Tata CLiQ'
  if (normalized.includes('meesho.com')) return 'Meesho'
  if (normalized.includes('snapdeal.com')) return 'Snapdeal'
  return 'Amazon.in'
}

export default function AlertsPage() {
  const [product,    setProduct]   = useState('')
  const [price,      setPrice]     = useState('45000')
  const [threshold,  setThreshold] = useState('10% Drop')
  const [trackList,  setTrackList] = useState([])
  const [priceAlerts, setPriceAlerts] = useState([])
  const [loading,    setLoading]   = useState(true)
  const [creating,   setCreating]  = useState(false)
  
  const navigate = useNavigate()

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    setLoading(true)
    try {
      const existing = JSON.parse(localStorage.getItem('watchlist_items') || '[]')
      setPriceAlerts(existing)
      setTrackList(existing)
    } catch (err) {
      toast('Failed to load tracking data', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleAlert(alertId) {
    const existing = JSON.parse(localStorage.getItem('watchlist_items') || '[]')
    const updated = existing.map(a => a.id === alertId ? { ...a, is_active: !a.is_active } : a)
    localStorage.setItem('watchlist_items', JSON.stringify(updated))
    setPriceAlerts(updated)
    setTrackList(updated)
  }

  async function handleRemoveAlert(indexToRemove) {
    const existing = JSON.parse(localStorage.getItem('watchlist_items') || '[]')
    const updated = existing.filter((_, idx) => idx !== indexToRemove)
    localStorage.setItem('watchlist_items', JSON.stringify(updated))
    setPriceAlerts(updated)
    setTrackList(updated)
    toast('Alert removed', 'neutral')
  }

  async function createAlert() {
    if (!product) {
      toast('Please enter a product name or URL', 'error')
      return
    }
    
    setCreating(true)
    let finalTitle = product.trim()
    let initialUrl = null

    if (finalTitle.startsWith('http://') || finalTitle.startsWith('https://')) {
      initialUrl = finalTitle
      try {
        const urlObj = new URL(finalTitle);
        const pathParts = urlObj.pathname.split('/').filter(p => p.length > 0);
        const namePart = pathParts.find(p => p.includes('-') && p.length > 10) || pathParts[0];
        if (namePart) {
          let cleanName = decodeURIComponent(namePart).replace(/-/g, ' ').trim();
          cleanName = cleanName.split(' ').filter(word => !/^[A-Za-z0-9]{10,}$/.test(word)).join(' ').trim();
          if (cleanName) {
            finalTitle = cleanName;
          }
        }
      } catch (e) {
        console.warn('URL parsing failed', e)
      }
    }

    const key = finalTitle.toLowerCase()
    const existing = JSON.parse(localStorage.getItem('watchlist_items') || '[]')
    
    if (existing.some(i => i.id === key || i.name?.toLowerCase() === key || i.product_name?.toLowerCase() === key || i.title?.toLowerCase() === key)) {
      toast('Already tracking this product', 'info')
      setCreating(false)
      return
    }

    let fetchedPrice = null
    let fetchedImage = null
    let fetchedUrl = initialUrl
    let bestTitle = finalTitle

    try {
      const searchRes = await products.compareSearch(finalTitle)
      if (searchRes) {
        if (searchRes.best_price) fetchedPrice = searchRes.best_price
        if (searchRes.best_store_url) fetchedUrl = searchRes.best_store_url || fetchedUrl
        if (searchRes.stores && searchRes.stores.length > 0) {
          const s = searchRes.stores.find(x => x.image)
          if (s) fetchedImage = s.image
          // Use the clean title from the best matching store
          if (searchRes.stores[0].title) bestTitle = searchRes.stores[0].title
        }
      }
    } catch (e) {
      console.warn('Initial data fetch failed', e)
    }

    const newAlert = {
      id: key,
      name: bestTitle,
      product_name: bestTitle, // Keep for backward compat with other pages
      title: bestTitle,
      price: fetchedPrice,
      image: fetchedImage,
      url: fetchedUrl,
      targetPrice: parseFloat(price) || null,
      is_active: true,
      timestamp: Date.now()
    }
    
    existing.push(newAlert)
    localStorage.setItem('watchlist_items', JSON.stringify(existing))
    
    setPriceAlerts(existing)
    setTrackList(existing)
    setProduct('')
    setPrice('')
    setCreating(false)
    toast('Alert created!', 'success')
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-8 py-12">
        {/* Header Section */}
        <div className="mb-12 animate-fade-up">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 text-primary text-xs font-bold uppercase tracking-wider mb-6">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Precision Tracking Center
          </div>
          <h1 className="text-4xl font-extrabold text-on-surface tracking-tight mb-4">
            Command Your Price Alerts
          </h1>
          <p className="text-lg text-on-surface-variant max-w-2xl leading-relaxed">
            Configure high-fidelity monitoring for any product. We scan Amazon.in, Flipkart, and 5,000+ others to ensure you catch the perfect market entry.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
          {/* Configure Panel */}
          <div className="lg:col-span-1 space-y-8 animate-fade-up">
            <div className="bg-white rounded-3xl border border-outline-variant/40 p-8 shadow-sm">
              <div className="flex items-center gap-3 mb-8">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary">add_circle</span>
                </div>
                <h2 className="text-xl font-bold text-on-surface">Activate Sentinel</h2>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-3">Product URL</label>
                  <div className="relative group">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors">link</span>
                    <input 
                      type="text"
                      value={product}
                      onChange={e => setProduct(e.target.value)}
                      placeholder="Paste marketplace link..."
                      className="w-full bg-white border border-outline-variant/40 rounded-2xl pl-12 pr-6 py-4 text-sm font-medium focus:ring-4 focus:ring-primary/5 focus:border-primary outline-none transition-all shadow-sm"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-3">Target Price</label>
                    <div className="relative group">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant font-bold text-sm">₹</span>
                      <input 
                        type="number"
                        value={price}
                        onChange={e => setPrice(e.target.value)}
                        className="w-full bg-white border border-outline-variant/40 rounded-2xl pl-8 pr-4 py-4 text-sm font-bold text-on-surface focus:ring-4 focus:ring-primary/5 focus:border-primary outline-none transition-all shadow-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-3">Threshold</label>
                    <select 
                      value={threshold}
                      onChange={e => setThreshold(e.target.value)}
                      className="w-full bg-white border border-outline-variant/40 rounded-2xl px-4 py-4 text-sm font-bold text-on-surface focus:ring-4 focus:ring-primary/5 focus:border-primary outline-none transition-all shadow-sm cursor-pointer"
                    >
                      {['5% Drop','10% Drop','15% Drop','Any Drop'].map(t => <option key={t}>{t}</option>)}
                    </select>
                  </div>
                </div>

                <button 
                  onClick={createAlert}
                  disabled={creating}
                  className="w-full py-5 bg-primary text-white rounded-2xl font-bold text-sm hover:bg-primary-container active:scale-95 transition-all shadow-sm disabled:opacity-50"
                >
                  {creating ? 'Activating Protocol...' : 'Initialize Tracking'}
                </button>
              </div>
            </div>

            {/* AI Insights Card */}
            <div className="bg-primary text-white rounded-3xl p-8 shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 blur-2xl group-hover:bg-white/20 transition-all" />
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-6">
                  <span className="material-symbols-outlined text-white">psychology</span>
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] opacity-60">AI Intelligence</span>
                </div>
                <h3 className="text-xl font-bold mb-4 leading-tight">Predictive Value Analysis</h3>
                <p className="text-sm text-white/80 leading-relaxed mb-8">
                  Our neural network identifies price patterns before they manifest. Hold high-value electronics alerts for 48 hours to capture the upcoming volatility swing.
                </p>
                <div className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-widest bg-white/20 px-3 py-1.5 rounded-lg">
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                  Live Prediction Active
                </div>
              </div>
            </div>
          </div>

          {/* Active Alerts List */}
          <div className="lg:col-span-2 space-y-8 animate-fade-up" style={{ animationDelay: '0.1s' }}>
            <div className="bg-white rounded-3xl border border-outline-variant/40 shadow-sm overflow-hidden">
              <div className="px-8 py-6 border-b border-outline-variant/40 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-on-surface">Active Sentinels</h2>
                  <p className="text-sm text-on-surface-variant font-medium">Monitoring {trackList.length} global price streams</p>
                </div>
                <button onClick={fetchData} className="w-10 h-10 rounded-xl bg-surface flex items-center justify-center text-outline hover:text-primary transition-colors">
                  <span className="material-symbols-outlined text-lg">refresh</span>
                </button>
              </div>

              <div className="divide-y divide-outline-variant/20">
                {loading ? (
                  [...Array(3)].map((_, i) => (
                    <div key={i} className="p-8 animate-pulse flex items-center gap-6">
                      <div className="w-16 h-16 rounded-2xl bg-surface" />
                      <div className="flex-1 space-y-3">
                        <div className="h-4 bg-surface rounded w-1/3" />
                        <div className="h-3 bg-surface rounded w-1/4" />
                      </div>
                    </div>
                  ))
                ) : priceAlerts.length === 0 ? (
                  <div className="p-24 text-center">
                    <div className="w-20 h-20 rounded-full bg-surface flex items-center justify-center mx-auto mb-6">
                      <span className="material-symbols-outlined text-outline text-4xl">notifications_off</span>
                    </div>
                    <h3 className="text-lg font-bold text-on-surface mb-2">No Active Trackers</h3>
                    <p className="text-sm text-on-surface-variant max-w-xs mx-auto">
                      Initiate tracking on a product to begin catching price drops across our retailer network.
                    </p>
                  </div>
                ) : (
                  priceAlerts.map((item, i) => {
                    const itemName = item.product_name || item.title || item.query || item.product?.name || 'Unknown Product'
                    const itemImage = item.image || item.product?.image_url
                    return (
                      <div key={item.id || i} className="p-8 flex items-center gap-6 hover:bg-surface transition-all cursor-pointer group">
                        <div onClick={() => navigate(`/product?q=${encodeURIComponent(itemName)}`)} className="w-20 h-20 rounded-2xl bg-white border border-outline-variant/40 flex items-center justify-center overflow-hidden flex-shrink-0 group-hover:scale-105 transition-transform shadow-sm">
                          {itemImage ? (
                            <img src={itemImage} alt="" className="w-full h-full object-contain p-3 mix-blend-multiply" />
                          ) : (
                            <span className="text-3xl">🛍️</span>
                          )}
                        </div>
                        <div onClick={() => navigate(`/product?q=${encodeURIComponent(itemName)}`)} className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider ${item.is_active !== false ? 'bg-primary/5 text-primary' : 'bg-surface-container text-on-surface-variant'}`}>
                              {item.is_active !== false ? 'Active Sentinel' : 'Paused'}
                            </span>
                            <span className="w-1 h-1 rounded-full bg-outline-variant" />
                            <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Target: {formatPrice(item.targetPrice || item.target_price)}</span>
                            {item.price && (
                              <>
                                <span className="w-1 h-1 rounded-full bg-outline-variant" />
                                <span className="text-[10px] font-bold text-primary uppercase tracking-widest">Last: {formatPrice(item.price)}</span>
                              </>
                            )}
                          </div>
                          <h3 className="text-lg font-bold text-on-surface group-hover:text-primary transition-colors truncate">{itemName}</h3>
                          <div className="flex items-center gap-4 mt-2">
                            <div className="flex items-center gap-1.5 text-xs font-bold text-on-surface-variant">
                              <span className="material-symbols-outlined text-[10px]">show_chart</span>
                              Volatility tracking active
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-6">
                           <div 
                             onClick={(e) => { e.stopPropagation(); handleToggleAlert(item.id) }}
                             className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors duration-200 ${item.is_active ? 'bg-primary' : 'bg-outline-variant'}`}
                           >
                             <div className={`w-4.5 h-4.5 bg-white rounded-full absolute top-0.75 transition-all duration-200 shadow-sm ${item.is_active ? 'right-0.75' : 'left-0.75'}`}></div>
                           </div>
                           <button 
                             onClick={(e) => { e.stopPropagation(); handleRemoveAlert(i) }}
                             className="w-10 h-10 rounded-xl bg-surface border border-outline-variant/20 flex items-center justify-center text-red-400 hover:text-red-600 hover:bg-red-50 transition-all"
                           >
                             <span className="material-symbols-outlined text-lg">delete</span>
                           </button>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
              
              {!loading && trackList.length > 0 && (
                <div className="p-6 bg-surface text-center">
                  <button className="text-sm font-bold text-on-surface-variant hover:text-primary transition-colors flex items-center justify-center gap-2 mx-auto">
                    Load Archived Protocols
                    <span className="material-symbols-outlined text-sm">expand_more</span>
                  </button>
                </div>
              )}
            </div>

            {/* Saving Pulse Card */}
            <div className="bg-white rounded-3xl border border-outline-variant/40 p-8 shadow-sm">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-tertiary-container/10 flex items-center justify-center">
                    <span className="material-symbols-outlined text-tertiary-container">insights</span>
                  </div>
                  <h3 className="text-lg font-bold text-on-surface">Saving Velocity</h3>
                </div>
                <div className="text-2xl font-black text-tertiary-container">72%</div>
              </div>
              <p className="text-sm text-on-surface-variant leading-relaxed mb-6 font-medium">
                Our network is currently capturing an average of ₹4,200 in monthly savings per verified user. Your protocol efficiency is 12% above benchmark.
              </p>
              <div className="w-full h-3 bg-surface rounded-full overflow-hidden">
                <div className="h-full bg-tertiary-container rounded-full" style={{ width: '72%' }} />
              </div>
            </div>
          </div>
        </div>
      </div>
      <AIButton position="fixed" />
    </AppLayout>
  )
}
