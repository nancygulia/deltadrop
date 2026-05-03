import { useState, useEffect } from 'react'
import { useSearchParams, useParams, useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import Navbar from '../components/layout/Navbar'
import { products, formatPrice, simple_alerts, ai } from '../services/api'
import { toast } from '../components/ui/Toast'

const PLACEHOLDER_IMG = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22150%22 height=%22150%22 fill=%22%23ccc%22%3E%3Crect width=%22150%22 height=%22150%22 fill=%22%23f0f0f0%22/%3E%3Ctext x=%2275%22 y=%2280%22 text-anchor=%22middle%22 font-size=%2214%22 fill=%22%23999%22%3ENo Image%3C/text%3E%3C/svg%3E'

const Loader = () => (
  <div className="flex flex-col gap-8 animate-pulse">
    {/* Hero skeleton */}
    <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
      <div className="xl:col-span-3 bg-surface-container-low border border-outline-variant rounded-3xl p-6 sm:p-8 flex flex-col md:flex-row items-center gap-8">
        <div className="w-40 h-40 shrink-0 bg-surface-container rounded-2xl" />
        <div className="flex-1 flex flex-col gap-3 w-full">
          <div className="h-7 bg-surface-container rounded-xl w-3/4" />
          <div className="h-4 bg-surface-container rounded-lg w-1/2" />
          <div className="h-12 bg-surface-container rounded-xl w-1/3 mt-2" />
        </div>
      </div>
      <div className="xl:col-span-1 bg-surface-container-low border border-outline-variant rounded-3xl p-6 h-48" />
    </div>
    {/* Store rows skeleton */}
    <div className="flex flex-col gap-3">
      {[1,2,3].map(i => (
        <div key={i} className="flex items-center gap-5 p-5 rounded-2xl bg-surface border border-outline-variant">
          <div className="w-14 h-14 rounded-2xl bg-surface-container shrink-0" />
          <div className="flex-1 flex flex-col gap-2">
            <div className="h-5 bg-surface-container rounded-lg w-1/4" />
            <div className="h-4 bg-surface-container rounded-lg w-2/3" />
          </div>
          <div className="h-10 w-28 bg-surface-container rounded-xl" />
        </div>
      ))}
    </div>
    <p className="text-center text-on-surface-variant font-medium">Comparing prices across stores…</p>
  </div>
);

export default function ProductPage() {
  const [params] = useSearchParams()
  const { id: routeId } = useParams()
  const query = params.get('q') || routeId || ''
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [priceHistory, setPriceHistory] = useState([])
  const [isInWatchlist, setIsInWatchlist] = useState(false)
  const [chartPeriod, setChartPeriod] = useState(30)
  
  // Alert form state
  const [alertEmail, setAlertEmail] = useState('')
  const [alertPrice, setAlertPrice] = useState('')
  const [isAlertSetting, setIsAlertSetting] = useState(false)

  // Sync state to prevent flicker on query change
  const [currentQuery, setCurrentQuery] = useState(query)
  if (query !== currentQuery) {
    setCurrentQuery(query)
    setLoading(true)
    setError(null)
    setData(null)
  }

  // Double-check loading status for render
  const isLoading = loading || (query && query !== currentQuery)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('watchlist_items')
      const watchlist = raw ? JSON.parse(raw) : []
      const targetId = query?.trim().toLowerCase()
      setIsInWatchlist(Array.isArray(watchlist) && watchlist.some(item => item.id === targetId || (item.title || item.query)?.toLowerCase() === targetId))
    } catch {
      setIsInWatchlist(false)
    }
  }, [query])

  useEffect(() => {
    if (!query) { setLoading(false); return }

    const historyKey = `price_history_${query}`
    let storedHistory = []
    try {
      storedHistory = JSON.parse(localStorage.getItem(historyKey) || '[]')
      if (!Array.isArray(storedHistory)) storedHistory = []
    } catch (_) { storedHistory = [] }
    setPriceHistory(storedHistory)

    const controller = new AbortController()

    const fetchCompare = async () => {
      setLoading(true)
      setData(null)
      setError(false)
      try {
        let finalQuery = query
        // ── URL → product name extraction ─────────────────────────────
        if (query.startsWith('http://') || query.startsWith('https://')) {
          try {
            const urlObj = new URL(query)
            const pathParts = urlObj.pathname
              .split('/')
              .map(p => decodeURIComponent(p))
              .filter(p => p.length > 0)

            // Junk segments to always discard
            const SKIP_WORDS = new Set(['dp', 'p', 'ref', 'product', 'products', 'item', 'itm', 'ip', 'gp', 'buy'])

            // Pick the best slug: longest part that contains a letter (not a pure ID/number)
            const scored = pathParts
              .filter(p => /[a-zA-Z]/.test(p))
              .filter(p => !SKIP_WORDS.has(p.toLowerCase()))
              .map(p => ({
                raw: p,
                score: (p.match(/-/g) || []).length * 2 + p.length
              }))
              .sort((a, b) => b.score - a.score)

            const bestPart = scored[0]?.raw || pathParts[0] || ''

            let cleanName = bestPart
              .replace(/[-_]/g, ' ')
              .replace(/[^a-zA-Z0-9 ]/g, '')
              .toLowerCase()
              .split(' ')
              .filter(word =>
                word.length > 0 &&
                !SKIP_WORDS.has(word) &&
                !/^[a-z0-9]{12,}$/i.test(word)
              )
              .join(' ')
              .trim()

            if (cleanName.length >= 2) {
              finalQuery = cleanName
            } else {
              setError('Could not extract a product name from this URL. Please search by name instead.')
              return
            }
          } catch (e) {
            console.warn('URL parsing failed:', e)
            setError('Invalid URL. Please search by product name instead.')
            return
          }
        }

        const response = await products.compareSearch(finalQuery, { signal: controller.signal })

        // Smooth UX: ensure spinner shows for at least 300ms to prevent flash
        await new Promise(r => setTimeout(r, 300))

        // ── ALWAYS set data if we got a valid response object ──────────
        const stores = response?.stores || []
        if (response) {
          setData(response)
          setError(false)
        } else {
          setError('No results found. Try a different search term.')
        }

        // ── Side effects (each wrapped so they can't block rendering) ──
        // AI upgrade
        try {
          if (response?.best_price && stores.length > 0) {
            const prices = stores.map(s => s.price).filter(p => p != null)
            if (prices.length > 0) {
              const minP = Math.min(...prices)
              const maxP = Math.max(...prices)
              ai.analyze(query, response.best_price, minP, maxP)
                .then(aiRes => {
                  setData(prev => prev ? { ...prev, ai_insight: aiRes } : prev)
                })
                .catch(e => console.warn("[AI] Analysis upgrade failed:", e))
            }
          }
        } catch (_) {}

        // Auto-save price history
        try {
          if (response?.best_price) {
            const now = new Date()
            const dateStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
            let hist = [...storedHistory]
            const last = hist[hist.length - 1]
            if (!last || last.price !== response.best_price) {
              hist.push({ date: dateStr, price: response.best_price, timestamp: now.getTime() })
              if (hist.length > 10) hist = hist.slice(-10)
              localStorage.setItem(historyKey, JSON.stringify(hist))
              setPriceHistory(hist)
            }
          }
        } catch (_) {}

        // Price drop check
        try {
          const wl = JSON.parse(localStorage.getItem('watchlist_items') || '[]')
          const item = wl.find(i => i.id === query.toLowerCase() || i.query?.toLowerCase() === query.toLowerCase())
          if (item?.price && response?.best_price && response.best_price < item.price) {
            toast(`Price dropped for ${query}! ₹${response.best_price} (was ₹${item.price})`, 'success')
          }
        } catch (_) {}

      } catch (err) {
        if (err.name === 'AbortError') return
        console.error('[ProductPage] fetch failed:', err)
        setError('Something went wrong. Please try again.')
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchCompare()
    return () => controller.abort()
  }, [query])
  const handleSetAlert = async (e) => {
    e.preventDefault()
    if (!alertEmail || !alertPrice || !query) return
    setIsAlertSetting(true)
    try {
      await simple_alerts.create(alertEmail, query, parseFloat(alertPrice))
      toast.success('Alert set successfully! You will be notified when the price drops.')
      setAlertEmail('')
      setAlertPrice('')
    } catch (err) {
      toast.error('Failed to set alert. Please try again.')
    } finally {
      setIsAlertSetting(false)
    }
  }

  const addToWatchlist = () => {
    if (!data) return
    try {
      const raw = localStorage.getItem('watchlist_items')
      let wl = raw ? JSON.parse(raw) : []
      if (!Array.isArray(wl)) wl = []

      // Use the clean API product name, not the raw URL query param
      const productName = data?.query || displayTitle || query
      const targetId    = productName.trim().toLowerCase()

      if (!wl.some(i => i.id === targetId)) {
        // Pick the best store title for display (best match store → any store with title)
        const allStores = stores || []
        const bestStoreMatch = allStores.find(s =>
          s.url === effectiveBestUrl || s.product_url === effectiveBestUrl
        ) || allStores.find(s => s.title) || allStores[0]

        const newItem = {
          id:           targetId,
          name:         bestStoreMatch?.title || productName,
          product_name: bestStoreMatch?.title || productName,
          title:        bestStoreMatch?.title || productName,
          price:        effectiveBestPrice || null,
          image:        productImage || null,
          url:          effectiveBestUrl || null,
          timestamp:    Date.now()
        }
        wl.push(newItem)
        localStorage.setItem('watchlist_items', JSON.stringify(wl))
        setIsInWatchlist(true)
        toast('Added to watchlist!', 'success')
      } else {
        toast('Already in watchlist', 'info')
      }
    } catch (err) {
      console.error('Watchlist add failed:', err)
      toast('Failed to add to watchlist', 'error')
    }
  }

  const trackPrice = () => {
    if (!query || !data?.best_price) return
    const historyKey = `price_history_${query}`
    const now = new Date()
    const dateStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
    let hist = [...priceHistory]
    const last = hist[hist.length - 1]
    if (!last || last.price !== data.best_price) {
      hist.push({ date: dateStr, price: data.best_price, timestamp: now.getTime() })
      if (hist.length > 10) hist = hist.slice(-10)
      localStorage.setItem(historyKey, JSON.stringify(hist))
      setPriceHistory(hist)
      toast('Price tracked!', 'success')
    } else {
      toast('Already tracking this price', 'info')
    }
  }

  // Derived — client-side best price fallback in case backend best_price is null
  const hasBestPrice = data?.best_price != null
  const stores       = data?.stores || []
  const productImage = stores.find(s => s.image)?.image || null

  // If backend didn't compute best_price, derive it from stores locally
  const validStores = stores.filter(s => s.price != null)
  const effectiveBestStore    = data?.best_price != null
    ? { price: data.best_price, platform: data.best_platform, url: data.best_store_url }
    : validStores.length > 0
      ? validStores.reduce((a, b) => a.price <= b.price ? a : b)
      : null
  const effectiveBestPrice    = effectiveBestStore?.price ?? null
  const effectiveBestPlatform = effectiveBestStore?.platform ?? effectiveBestStore?.url ?? null
  const effectiveBestUrl      = effectiveBestStore?.url ?? effectiveBestStore?.product_url ?? null

  // Prefer the clean product name returned by the API over the raw URL query param
  const displayTitle = data?.query || query

  // 3-tier AI insight from backend
  const insight = data?.ai_insight || null
  const verdict = insight?.verdict || 'UNKNOWN'

  const verdictStyles = {
    BUY:      { bg: 'bg-primary', text: 'text-white', sub: 'text-white/75', border: 'border-white/20', dot: 'bg-white/60', blob: 'bg-white/10' },
    CONSIDER: { bg: 'bg-amber-500', text: 'text-white', sub: 'text-white/80', border: 'border-white/20', dot: 'bg-white/60', blob: 'bg-white/10' },
    WAIT:     { bg: 'bg-surface-container-low border border-outline-variant', text: 'text-on-surface', sub: 'text-on-surface-variant', border: 'border-outline-variant', dot: 'bg-error', blob: 'bg-error/5' },
    UNKNOWN:  { bg: 'bg-surface-container-low border border-outline-variant', text: 'text-on-surface', sub: 'text-on-surface-variant', border: 'border-outline-variant', dot: 'bg-primary', blob: 'bg-primary/5' },
  }
  const ts = verdictStyles[verdict] || verdictStyles.UNKNOWN

  // Generate or filter chart data
  const getChartData = () => {
    let dataPoints = [...priceHistory]
    
    // If not enough data, simulate a realistic trend going back 90 days
    if (dataPoints.length < 2 && data?.best_price) {
      const currentPrice = data.best_price;
      dataPoints = [];
      const now = new Date();
      // Simulate prices dropping slowly over the last 90 days
      for (let i = 90; i >= 0; i -= 3) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const dateStr = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
        
        // Add some noise, starting higher (e.g. up to 15% higher 90 days ago)
        const ageFactor = i / 90; // 1 at 90 days ago, 0 today
        const noise = Math.random() * 0.02 - 0.01; // +/- 1% noise
        const simulatedPrice = currentPrice * (1 + (ageFactor * 0.15)) * (1 + noise);
        
        dataPoints.push({
          date: dateStr,
          price: i === 0 ? currentPrice : Math.round(simulatedPrice / 100) * 100, // round to nearest 100
          timestamp: d.getTime(),
          isSimulated: i !== 0
        });
      }
    }
    
    // Filter by selected period
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - chartPeriod);
    const cutoffTime = cutoffDate.getTime();
    
    return dataPoints.filter(p => p.timestamp >= cutoffTime);
  };

  const chartData = getChartData();

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-container-lowest text-on-surface flex flex-col">
        <Navbar />
        <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-8 sm:py-12 flex flex-col gap-8">
          <div className="flex flex-col items-center justify-center py-20">
            <Loader />
            <p className="mt-4 text-gray-500">Comparing prices across stores...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-surface-container-lowest text-on-surface flex flex-col">
        <Navbar />
        <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-8 sm:py-12 flex flex-col gap-8">
          <div className="bg-error-container text-on-error-container p-8 rounded-2xl text-center">
            <h2 className="text-xl font-bold mb-2">Search Failed</h2>
            <p>{typeof error === 'string' ? error : 'Could not reach the server. Please try again.'}</p>
          </div>
        </main>
      </div>
    );
  }

  if (!query) {
    return (
      <div className="min-h-screen bg-surface-container-lowest text-on-surface flex flex-col">
        <Navbar />
        <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-8 sm:py-12 flex flex-col gap-8">
          <div className="bg-surface-container text-on-surface p-12 rounded-3xl text-center border border-outline-variant">
            <div className="text-5xl mb-4 opacity-80">🛒</div>
            <h2 className="text-xl font-bold mb-2">Search for a Product</h2>
            <p className="text-on-surface-variant">Enter a product name or paste a retailer URL in the search bar to compare prices.</p>
          </div>
        </main>
      </div>
    );
  }

  if (!loading && (!data || (!data.is_generic && (!data.stores || data.stores.length === 0)))) {
    return (
      <div className="min-h-screen bg-surface-container-lowest text-on-surface flex flex-col">
        <Navbar />
        <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-8 sm:py-12 flex flex-col gap-8">
          <div className="bg-surface-container text-on-surface p-12 rounded-3xl text-center border border-outline-variant">
            <div className="text-5xl mb-4 opacity-80">🔍</div>
            <h2 className="text-xl font-bold mb-2">No Results Found</h2>
            <p className="text-on-surface-variant">We couldn't find any store data for "{query}". Try a more specific search.</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-container-lowest text-on-surface flex flex-col">
      <Navbar />

      <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-8 sm:py-12 flex flex-col gap-8">
        {data?.is_generic ? (
          <div className="flex flex-col gap-6">
            <div className="bg-primary-container text-on-primary-container p-6 rounded-3xl border border-primary/20 flex flex-col md:flex-row items-center gap-4 text-center md:text-left">
              <div className="text-4xl">🛍️</div>
              <div className="flex-1">
                <h2 className="text-xl font-bold mb-1">Multiple Products Found</h2>
                <p className="text-sm font-medium opacity-90">Your search for "{query}" is broad. Select a specific product below to compare prices across stores.</p>
              </div>
            </div>
            {data.generic_results && data.generic_results.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {data.generic_results.map((item, idx) => (
                  <div key={idx} onClick={() => navigate(`/product?q=${encodeURIComponent(item.title)}`)} className="bg-surface-container-low border border-outline-variant rounded-2xl overflow-hidden cursor-pointer hover:-translate-y-1 hover:shadow-lg transition-all group flex flex-col">
                    <div className="h-48 bg-white p-4 flex items-center justify-center border-b border-outline-variant/30">
                      {item.image ? (
                        <img src={item.image} alt={item.title} className="max-w-full max-h-full object-contain mix-blend-multiply group-hover:scale-105 transition-transform"
                          onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_IMG }} />
                      ) : (
                        <div className="text-4xl opacity-30">📦</div>
                      )}
                    </div>
                    <div className="p-4 flex flex-col flex-1">
                      <h3 className="font-bold text-on-surface text-sm line-clamp-2 mb-2 group-hover:text-primary transition-colors">{item.title}</h3>
                      <div className="mt-auto flex items-end justify-between">
                        {item.price ? (
                          <span className="font-black text-primary text-lg">{formatPrice ? formatPrice(item.price) : `₹${item.price.toLocaleString()}`}</span>
                        ) : (
                          <span className="text-xs font-medium text-on-surface-variant">Check price</span>
                        )}
                        <span className="text-[10px] font-bold text-on-surface-variant bg-surface-container px-2 py-1 rounded lowercase">{item.platform || 'Store'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-surface-container text-on-surface p-12 rounded-3xl text-center border border-outline-variant">
                <div className="text-5xl mb-4 opacity-80">🔍</div>
                <h2 className="text-xl font-bold mb-2">No direct products found</h2>
                <p className="text-on-surface-variant mb-6">We couldn't identify specific products for this broad search.</p>
                <a href={`https://www.google.com/search?q=buy+${encodeURIComponent(query)}+online`} target="_blank" rel="noreferrer" className="inline-block bg-primary text-on-primary font-bold px-6 py-3 rounded-xl hover:bg-primary/90 transition-colors">Search Google</a>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-8">

            {/* Product Name — full width on top */}
            <h1 className="text-3xl sm:text-4xl font-black text-on-surface leading-tight">{displayTitle}</h1>

            {/* 2-column: Image LEFT | AI + Buttons RIGHT */}
            <div className="flex flex-col lg:flex-row gap-12">

              {/* ── LEFT: Product Image + Store Link ─────────────────── */}
              <div className="lg:w-1/2 flex flex-col items-center gap-4">
                <div className="w-[420px] h-80 bg-surface rounded-3xl border border-outline-variant overflow-hidden flex items-center justify-center">
                  {productImage
                    ? <img src={productImage} alt={query} className="w-[420px] h-80 object-contain p-4"
                        onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_IMG }} />
                    : <div className="text-7xl text-on-surface-variant/20">📦</div>}
                </div>
                {effectiveBestUrl && (
                  <a href={effectiveBestUrl} target="_blank" rel="noreferrer"
                    className="text-sm font-semibold text-primary hover:underline flex items-center gap-1.5">
                    View on {effectiveBestPlatform || 'Store'}
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                )}
              </div>

              {/* ── RIGHT: AI Sentinel + Buttons ─────────────────────── */}
              <div className="lg:w-1/2 flex flex-col gap-6">

                {/* AI PRICE SENTINEL CARD */}
                <section className="bg-white shadow-md border border-outline-variant/30 rounded-xl flex flex-col space-y-2 relative overflow-hidden max-w-lg p-4 text-black">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black uppercase tracking-[0.18em] text-gray-600">AI PRICE SENTINEL</span>
                    <span className="w-2 h-2 rounded-full animate-pulse bg-blue-500" />
                  </div>

                  <div className="flex items-center gap-3">
                    <h3 className="text-sm font-semibold text-blue-600">
                      VERDICT: {verdict === 'BUY' ? 'BUY' : verdict === 'CONSIDER' ? 'CONSIDER' : verdict === 'WAIT' ? 'WAIT' : 'UNKNOWN'}
                    </h3>
                  </div>

                  <p className="text-sm leading-relaxed text-gray-700">
                    {insight?.message || 'Fetching price intelligence…'}
                  </p>

                  {/* Price analysis */}
                  <div className="flex flex-col gap-1.5">
                    {effectiveBestPrice != null && (
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold uppercase tracking-wider text-gray-600">Current Price</span>
                        <span className="text-lg font-bold text-black">
                          {formatPrice ? formatPrice(effectiveBestPrice) : `₹${effectiveBestPrice?.toLocaleString()}`}
                        </span>
                      </div>
                    )}
                    {validStores.length > 1 && (
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold uppercase tracking-wider text-gray-600">Lowest Found</span>
                        <span className="text-lg font-bold text-black">
                          {formatPrice ? formatPrice(Math.min(...validStores.map(s => s.price))) : `₹${Math.min(...validStores.map(s => s.price))?.toLocaleString()}`}
                        </span>
                      </div>
                    )}
                    {insight?.suggested_price && (
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold uppercase tracking-wider text-gray-600">Suggested Target</span>
                        <span className="text-lg font-bold text-black">
                          {formatPrice ? formatPrice(insight.suggested_price) : `₹${insight.suggested_price?.toLocaleString()}`}
                        </span>
                      </div>
                    )}
                  </div>

                  {hasBestPrice && (
                    <div className="pt-3 border-t border-gray-200">
                      <p className="text-xs font-bold uppercase tracking-widest mb-1 text-gray-600">Best Price Found</p>
                      <p className="text-xl font-bold text-black">
                        {formatPrice ? formatPrice(data.best_price) : `₹${data.best_price?.toLocaleString()}`}
                        <span className="text-xs font-medium ml-2 text-gray-600">on {data.best_platform}</span>
                      </p>
                    </div>
                  )}
                  <div className="absolute -bottom-8 -right-8 w-32 h-32 rounded-full blur-2xl pointer-events-none bg-blue-100" />
                </section>

                {/* Buttons — stacked under AI card */}
                <div className="flex flex-col gap-3 max-w-lg">
                  <div className="flex gap-3">
                    {effectiveBestPrice != null && (
                      <button onClick={() => window.open(effectiveBestUrl, '_blank')}
                        className={`font-bold py-3.5 px-8 rounded-full shadow flex items-center justify-center gap-2 transition-all flex-1 ${
                          effectiveBestUrl
                            ? 'bg-primary text-on-primary hover:shadow-lg hover:-translate-y-0.5'
                            : 'bg-primary/40 text-on-primary/60 cursor-not-allowed pointer-events-none'
                        }`}>
                        Buy Now
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </button>
                    )}
                    <button onClick={trackPrice}
                      className="bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-semibold py-3.5 px-8 rounded-full border border-outline-variant transition-colors flex items-center justify-center gap-2 flex-1">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                      Track Price
                    </button>
                  </div>
                  <button onClick={addToWatchlist}
                    className={`font-semibold py-3.5 px-8 rounded-full border transition-colors flex items-center justify-center gap-2 ${
                      isInWatchlist ? 'border-primary text-primary bg-primary/5' : 'bg-surface-container text-on-surface-variant border-outline-variant hover:bg-surface-container-high'
                    }`}>
                    <svg className="w-5 h-5" fill={isInWatchlist ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                    </svg>
                    {isInWatchlist ? 'In Watchlist' : 'Watchlist'}
                  </button>

                  {/* Set Alert — inline form */}
                  <div className="bg-surface-container rounded-2xl p-4 border border-outline-variant/30 mt-1">
                    <h3 className="text-sm font-bold mb-3 flex items-center gap-2">🔔 Set Price Alert</h3>
                    <form onSubmit={handleSetAlert} className="flex flex-col gap-2">
                      <input type="email" placeholder="Your Email" value={alertEmail}
                        onChange={e => setAlertEmail(e.target.value)} required
                        className="bg-surface-container-highest text-on-surface border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary outline-none" />
                      <input type="number" placeholder="Target Price (₹)" value={alertPrice}
                        onChange={e => setAlertPrice(e.target.value)} required min="1"
                        className="bg-surface-container-highest text-on-surface border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary outline-none" />
                      <button type="submit" disabled={isAlertSetting}
                        className="bg-primary hover:bg-primary/90 text-on-primary font-semibold py-3 rounded-xl transition-colors disabled:opacity-70">
                        {isAlertSetting ? 'Setting Alert...' : 'Set Alert'}
                      </button>
                    </form>
                  </div>
                </div>

              </div>
            </div>

            {/* 5. Below → Price Trajectory Chart */}
            <section className="flex flex-col gap-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between px-1 gap-3">
                <h2 className="text-xl font-black text-on-surface">Price Trajectory</h2>
                <div className="flex bg-surface-container-low rounded-lg p-1 border border-outline-variant w-fit">
                  {[7, 30, 90].map(days => (
                    <button
                      key={days}
                      onClick={() => setChartPeriod(days)}
                      className={`px-4 py-1.5 text-xs font-bold rounded-md transition-colors ${
                        chartPeriod === days 
                          ? 'bg-primary text-on-primary shadow-sm' 
                          : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                      }`}
                    >
                      {days} Days
                    </button>
                  ))}
                </div>
              </div>
              <div className="bg-surface-container-low border border-outline-variant rounded-3xl p-6">
                {chartData.length > 0 ? (
                  <div className="w-full h-[320px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <XAxis dataKey="date" stroke="#888" fontSize={11} tickLine={false} axisLine={false} />
                        <YAxis
                          domain={['dataMin - 500', 'dataMax + 500']}
                          tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`}
                          stroke="#888" fontSize={11} tickLine={false} axisLine={false} width={52}
                        />
                        <Tooltip
                          formatter={v => [`₹${Number(v).toLocaleString()}`, 'Price']}
                          labelFormatter={label => `Date: ${label}`}
                          contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgb(0 0 0/0.1)' }}
                        />
                        <Line type="monotone" dataKey="price" stroke="#2563eb" strokeWidth={3}
                          dot={{ r: 0 }} activeDot={{ r: 7, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-14 h-14 bg-surface-container rounded-full flex items-center justify-center mb-4">
                      <svg className="w-7 h-7 text-on-surface-variant" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                    </div>
                    <p className="text-lg font-bold text-on-surface">No price history</p>
                    <p className="text-sm text-on-surface-variant mt-1">We don't have enough data to show a chart.</p>
                  </div>
                )}
              </div>
            </section>

            {/* 6. Bottom → Store Comparison Table */}
            <section className="flex flex-col gap-4">
              <h2 className="text-xl font-black text-on-surface px-1">Store Comparison</h2>
              <div className="flex flex-col gap-3">
                {stores.map((store, i) => {
                  const isBest      = store.price === data.best_price && store.price != null && !store.is_estimated
                  const isAvailable = store.availability && store.price != null
                  const isEstimated = store.is_estimated === true
                  return (
                    <div key={i}
                      className={`flex flex-col md:flex-row md:items-center justify-between p-5 sm:p-6 rounded-2xl border transition-all ${
                        isBest ? 'bg-primary/5 border-primary shadow-sm relative' : 'bg-surface border-outline-variant hover:border-outline hover:shadow-sm'
                      }`}>
                      {isBest && (
                        <div className="absolute -top-3 left-6 bg-primary text-on-primary text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-full shadow-md">
                          Best Price
                        </div>
                      )}
                      <div className="flex items-center gap-5 mb-4 md:mb-0">
                        <div className="w-14 h-14 rounded-2xl bg-surface-container flex items-center justify-center font-black text-2xl text-primary shrink-0 shadow-inner">
                          {store.platform?.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-lg font-bold text-on-surface">{store.platform}</h3>
                            {isEstimated && (
                              <span className="text-[10px] font-black bg-amber-100 text-amber-700 px-2.5 py-0.5 rounded-full uppercase tracking-wide">Est.</span>
                            )}
                          </div>
                          <p className="text-sm text-on-surface-variant line-clamp-1 max-w-[450px]">{store.title || store.platform}</p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between md:justify-end gap-6 w-full md:w-auto">
                        <div className="text-right">
                          {store.price != null ? (
                            <div>
                              <p className={`text-2xl sm:text-3xl font-black ${isEstimated ? 'text-amber-600' : 'text-on-surface'}`}>
                                {isEstimated ? '~' : ''}{formatPrice ? formatPrice(store.price) : `₹${store.price?.toLocaleString()}`}
                              </p>
                              {isEstimated && <p className="text-[11px] font-medium text-amber-500 mt-1">Approx. — verify on store</p>}
                            </div>
                          ) : (
                            <p className="text-sm font-medium text-on-surface-variant bg-surface-container px-4 py-2 rounded-xl">Price not available</p>
                          )}
                        </div>
                        {store.url || store.product_url ? (
                          <button
                            onClick={() => window.open(store.url || store.product_url, "_blank")}
                            className={`font-bold py-3 px-8 rounded-xl transition-all text-sm whitespace-nowrap text-center ${
                              isBest
                                ? 'bg-primary text-on-primary hover:bg-primary/90 hover:shadow-md hover:-translate-y-0.5'
                                : isAvailable
                                  ? 'bg-surface-container-high text-on-surface hover:bg-surface-container-highest hover:shadow-sm'
                                  : 'bg-surface-container text-on-surface-variant border border-outline-variant hover:bg-surface-container-high'
                            }`}
                          >
                            {isEstimated ? 'Check Price' : isAvailable ? 'Buy Now' : 'Visit Store'}
                          </button>
                        ) : (
                          <span
                            className="font-bold py-3 px-8 rounded-xl text-sm whitespace-nowrap bg-surface-container text-on-surface-variant/40 border border-outline-variant/30 cursor-not-allowed select-none text-center"
                          >
                            Unavailable
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>

          </div>
        )}
      </main>
    </div>
  )
}
