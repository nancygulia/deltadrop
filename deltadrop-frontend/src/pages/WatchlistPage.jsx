import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import { toast } from '../components/ui/Toast'
import { products } from '../services/api'

const STORAGE_KEY = 'watchlist_items'

function loadWatchlist() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function saveWatchlist(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export default function WatchlistPage() {
  const [items, setItems]         = useState([])
  const [loaded, setLoaded]       = useState(false)
  const [showTracker, setShowTracker] = useState(false)
  const [trackUrl, setTrackUrl]   = useState('')
  const [trackTarget, setTrackTarget] = useState('')
  const [trackName, setTrackName] = useState('')
  const inputRef = useRef(null)
  const navigate = useNavigate()

  // ── Load on mount ──────────────────────────────────────────────────────────
  useEffect(() => {
    setItems(loadWatchlist())
    setLoaded(true)
  }, [])

  // ── Price drop check on load ───────────────────────────────────────────────
  useEffect(() => {
    if (!loaded) return
    items.forEach(item => {
      if (item.targetPrice && item.price && item.price < item.targetPrice) {
        toast(`🔔 Price drop! "${item.query}" is now ₹${item.price.toLocaleString()} (target: ₹${item.targetPrice.toLocaleString()})`, 'success')
      }
    })
  }, [loaded]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Helpers ────────────────────────────────────────────────────────────────
  const removeItem = (indexToRemove) => {
    const updated = items.filter((_, idx) => idx !== indexToRemove)
    saveWatchlist(updated)
    setItems(updated)
    toast('Removed from watchlist', 'neutral')
  }

  const updateTargetPrice = (idOrTitle, rawValue) => {
    const val = parseFloat(rawValue)
    if (isNaN(val) || val <= 0) return
    const updated = items.map(i =>
      (i.id === idOrTitle || i.title === idOrTitle || i.query === idOrTitle) ? { ...i, targetPrice: val } : i
    )
    saveWatchlist(updated)
    setItems(updated)
    toast(`Target price set to ₹${val.toLocaleString()}`, 'success')
  }

  // ── Add via URL tracker ────────────────────────────────────────────────────
  const [isCreating, setIsCreating] = useState(false)

  const handleAddTracker = async () => {
    const url    = trackUrl.trim()
    let name     = trackName.trim()
    const target = parseFloat(trackTarget)

    if (!name && !url) {
      toast('Please enter a product name or URL', 'error')
      return
    }

    setIsCreating(true)

    if (!name && url) {
      name = url
      if (url.startsWith('http://') || url.startsWith('https://')) {
        try {
          const urlObj = new URL(url);
          const pathParts = urlObj.pathname.split('/').filter(p => p.length > 0);
          const namePart = pathParts.find(p => p.includes('-') && p.length > 10) || pathParts[0];
          if (namePart) {
            let cleanName = decodeURIComponent(namePart).replace(/-/g, ' ').trim();
            cleanName = cleanName.split(' ').filter(word => !/^[A-Za-z0-9]{10,}$/.test(word)).join(' ').trim();
            if (cleanName) {
              name = cleanName;
            }
          }
        } catch (e) {
          console.warn('URL parsing failed', e)
        }
      }
    }

    const wl = loadWatchlist()
    const key = name.toLowerCase()

    if (wl.some(i => i.id === key || i.name?.toLowerCase() === key || i.title?.toLowerCase() === key || i.product_name?.toLowerCase() === key)) {
      toast('Already in watchlist', 'info')
      setIsCreating(false)
      return
    }

    let fetchedPrice = null
    let fetchedImage = null
    let fetchedUrl = url
    let bestTitle = name

    try {
      const searchRes = await products.compareSearch(name)
      if (searchRes) {
        // Use best_price and best_store_url from API
        if (searchRes.best_price)     fetchedPrice = searchRes.best_price
        if (searchRes.best_store_url) fetchedUrl   = searchRes.best_store_url

        const allStores = searchRes.stores || []

        // Find the store matching best_store_url for most accurate title + image
        const bestStore = allStores.find(s => s.url === searchRes.best_store_url || s.product_url === searchRes.best_store_url)
          || allStores.find(s => s.title)  // fallback: first store with a title
          || allStores[0]

        if (bestStore?.title) bestTitle  = bestStore.title
        if (!bestTitle && searchRes.query) bestTitle = searchRes.query

        // Get image: prefer best store, then any store
        const imageStore = allStores.find(s => s.image)
        if (imageStore?.image) fetchedImage = imageStore.image
      }
    } catch (e) {
      console.warn('Initial price fetch failed', e)
    }

    const newItem = {
      id:          key,
      name:        bestTitle,
      product_name: bestTitle,
      title:       bestTitle, // Keep for backward compatibility
      price:       fetchedPrice,
      image:       fetchedImage,
      url:         fetchedUrl,
      targetPrice: isNaN(target) || target <= 0 ? null : target,
      timestamp:   Date.now(),
      is_active:   true
    }

    wl.push(newItem)
    saveWatchlist(wl)
    setItems(wl)
    setShowTracker(false)
    setTrackUrl('')
    setTrackName('')
    setTrackTarget('')
    setIsCreating(false)
    toast(`"${name}" added to watchlist!`, 'success')
  }

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (!loaded) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="w-8 h-8 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto px-4 py-12">

        {/* Header */}
        <div className="flex items-center justify-between mb-10 gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-black text-on-surface tracking-tight">Your Watchlist</h1>
            <p className="text-on-surface-variant mt-1">Tracked products and price drop alerts.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 text-primary px-4 py-2 rounded-full font-bold text-sm">
              {items.length} {items.length === 1 ? 'Item' : 'Items'}
            </div>
            <button
              onClick={() => { setShowTracker(true); setTimeout(() => inputRef.current?.focus(), 100) }}
              className="bg-primary text-on-primary px-5 py-2.5 rounded-full font-bold text-sm hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              Track a Product
            </button>
          </div>
        </div>

        {/* ── URL Tracker modal ──────────────────────────────────────────── */}
        {showTracker && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={() => setShowTracker(false)}>
            <div className="bg-surface rounded-3xl p-8 w-full max-w-md shadow-2xl border border-outline-variant" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-black text-on-surface">Track a Product</h2>
                <button onClick={() => setShowTracker(false)} className="p-2 text-on-surface-variant hover:bg-surface-container rounded-full transition-colors">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="flex flex-col gap-4">
                <div>
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1.5 block">Product Name *</label>
                  <input
                    ref={inputRef}
                    type="text"
                    value={trackName}
                    onChange={e => setTrackName(e.target.value)}
                    placeholder="e.g. iPhone 15 Pro 128GB"
                    className="w-full bg-surface-container-low border border-outline-variant rounded-2xl px-4 py-3 text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1.5 block">Product URL (optional)</label>
                  <input
                    type="url"
                    value={trackUrl}
                    onChange={e => setTrackUrl(e.target.value)}
                    placeholder="https://www.amazon.in/..."
                    className="w-full bg-surface-container-low border border-outline-variant rounded-2xl px-4 py-3 text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1.5 block">Target Price (₹) — alert when below</label>
                  <input
                    type="number"
                    value={trackTarget}
                    onChange={e => setTrackTarget(e.target.value)}
                    placeholder="e.g. 70000"
                    min="0"
                    className="w-full bg-surface-container-low border border-outline-variant rounded-2xl px-4 py-3 text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
                  />
                </div>

                <button
                  onClick={handleAddTracker}
                  disabled={isCreating}
                  className="w-full bg-primary text-on-primary font-bold py-3 rounded-2xl hover:bg-primary/90 transition-colors mt-2 disabled:opacity-70"
                >
                  {isCreating ? 'Adding...' : 'Add to Watchlist'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Empty state ────────────────────────────────────────────────── */}
        {items.length === 0 ? (
          <div className="bg-surface-container-low border border-dashed border-outline-variant rounded-[32px] p-20 text-center">
            <div className="w-20 h-20 bg-surface-container rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-outline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-on-surface">Watchlist is Empty</h3>
            <p className="text-on-surface-variant mt-2 mb-8 max-w-sm mx-auto">
              Add products to track price drops. Click "Track a Product" or add directly from search results.
            </p>
            <div className="flex gap-3 justify-center flex-wrap">
              <button onClick={() => navigate('/discover')} className="bg-surface-container-high text-on-surface px-6 py-3 rounded-full font-bold hover:bg-surface-container-highest transition-all text-sm">
                Discover Products
              </button>
              <button onClick={() => setShowTracker(true)} className="bg-primary text-on-primary px-6 py-3 rounded-full font-bold hover:shadow-lg transition-all text-sm">
                Track a Product
              </button>
            </div>
          </div>

        ) : (
          /* ── Items grid ─────────────────────────────────────────────── */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {items.map((item, idx) => {
              // Resolve display name — never show a raw URL
              const rawName = item.name || item.product_name || item.title || item.query || ''
              const displayName = rawName.startsWith('http') ? (item.title || item.product_name || 'Product') : rawName

              // Resolve price — support both field names
              const currentPrice = item.current_price ?? item.price ?? null

              const hasAlert = item.targetPrice && currentPrice && currentPrice <= item.targetPrice

              return (
                <div
                  key={idx}
                  className={`bg-surface-container-low border rounded-3xl p-6 hover:shadow-md transition-all group relative overflow-hidden ${
                    hasAlert ? 'border-primary/50 bg-primary/5' : 'border-outline-variant/40'
                  }`}
                >
                  {/* Price drop alert badge */}
                  {hasAlert && (
                    <div className="absolute top-4 right-12 bg-primary text-on-primary text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full shadow animate-pulse">
                      Price Drop! 🔔
                    </div>
                  )}

                  {/* Remove button */}
                  <button
                    onClick={() => removeItem(idx)}
                    className="w-8 h-8 rounded-full hover:bg-error/10 text-outline hover:text-error transition-colors flex items-center justify-center absolute top-4 right-4"
                    title="Remove"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>

                  {/* Product image + name */}
                  <div className="flex items-start gap-4 mb-4 pr-10">
                    {/* Image */}
                    <div className="w-16 h-16 shrink-0 rounded-2xl bg-surface border border-outline-variant/40 flex items-center justify-center overflow-hidden">
                      {item.image
                        ? <img src={item.image} alt={displayName} className="w-full h-full object-contain p-1"
                            onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22150%22 height=%22150%22 fill=%22%23ccc%22%3E%3Crect width=%22150%22 height=%22150%22 fill=%22%23f0f0f0%22/%3E%3Ctext x=%2275%22 y=%2280%22 text-anchor=%22middle%22 font-size=%2214%22 fill=%22%23999%22%3ENo Image%3C/text%3E%3C/svg%3E' }} />
                        : <span className="text-2xl flex">📦</span>}
                    </div>

                    {/* Name + date */}
                    <div className="flex-1 min-w-0">
                      <h3
                        onClick={() => navigate(`/product?q=${encodeURIComponent(displayName)}`)}
                        className="text-base font-bold text-on-surface group-hover:text-primary transition-colors cursor-pointer line-clamp-2"
                      >
                        {displayName}
                      </h3>
                      <p className="text-xs text-on-surface-variant font-medium mt-0.5 uppercase tracking-wider">
                        Added {new Date(item.timestamp).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </p>
                    </div>
                  </div>

                  {/* Prices row */}
                  <div className="flex items-end justify-between gap-4 mb-5">
                    <div>
                      <p className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-0.5">Current Price</p>
                      <p className="text-2xl font-black text-primary">
                        {currentPrice != null ? `₹${Number(currentPrice).toLocaleString()}` : 'Not available'}
                      </p>
                    </div>
                    {item.targetPrice && (
                      <div className="text-right">
                        <p className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-0.5">Target</p>
                        <p className={`text-lg font-black ${hasAlert ? 'text-primary' : 'text-on-surface-variant'}`}>
                          ₹{Number(item.targetPrice).toLocaleString()}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Set target price input */}
                  <TargetPriceInput item={item} onSet={updateTargetPrice} />

                  {/* Actions */}
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => navigate(`/product?q=${encodeURIComponent(displayName)}`)}
                      className="flex-1 bg-surface-container-high text-on-surface font-bold py-2.5 px-4 rounded-xl hover:bg-surface-container-highest transition-all text-sm"
                    >
                      Check Live Price
                    </button>
                    {item.url && !item.url.startsWith('http') === false && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="bg-primary/10 text-primary font-bold py-2.5 px-4 rounded-xl hover:bg-primary/20 transition-all text-sm flex items-center gap-1"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        Buy Now
                      </a>
                    )}
                  </div>

                  <div className="absolute top-0 right-0 w-1.5 h-full bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity rounded-r-3xl" />
                </div>
              )
            })}
          </div>
        )}
      </div>
    </AppLayout>
  )
}

// ── Inline target price setter component ─────────────────────────────────────
function TargetPriceInput({ item, onSet }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal]         = useState('')

  if (!editing) {
    return (
      <button
        onClick={() => { setEditing(true); setVal(item.targetPrice ? String(item.targetPrice) : '') }}
        className="text-xs text-on-surface-variant hover:text-primary font-medium underline underline-offset-2 transition-colors"
      >
        {item.targetPrice ? `Change target (₹${item.targetPrice.toLocaleString()})` : '+ Set alert price'}
      </button>
    )
  }

  return (
    <div className="flex gap-2 items-center">
      <input
        autoFocus
        type="number"
        value={val}
        onChange={e => setVal(e.target.value)}
        placeholder="Target ₹"
        className="flex-1 bg-surface-container border border-outline-variant rounded-xl px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40"
        onKeyDown={e => {
          if (e.key === 'Enter') { onSet(item.id || item.title || item.query, val); setEditing(false) }
          if (e.key === 'Escape') setEditing(false)
        }}
      />
      <button
        onClick={() => { onSet(item.id || item.title || item.query, val); setEditing(false) }}
        className="bg-primary text-on-primary font-bold px-4 py-2 rounded-xl text-sm hover:bg-primary/90 transition-colors"
      >Set</button>
      <button
        onClick={() => setEditing(false)}
        className="text-on-surface-variant hover:text-error px-2 py-2 rounded-xl text-sm transition-colors"
      >✕</button>
    </div>
  )
}
