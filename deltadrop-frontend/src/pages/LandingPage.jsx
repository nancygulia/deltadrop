import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Navbar from '../components/layout/Navbar'
import Footer from '../components/layout/Footer'
import { toast } from '../components/ui/Toast'
import SearchOverlay from '../components/ui/SearchOverlay'
import { useAuth } from '../hooks/useAuth'

import { products } from '../services/api'

const INITIAL_LIVE_PRODUCTS = [
  {
    icon: '💻', name: 'MacBook Pro 14" M3', price: '₹1,47,900', mrp: '₹1,69,900',
    badge: '-28% Drop', badgeColor: 'bg-tertiary-container/20 text-tertiary-container',
    barWidth: '72%', barColor: 'bg-tertiary-container',
    cta: 'Login to Set Alert', ctaStyle: 'secondary',
  },
  {
    icon: '🎧', name: 'Sony WH-1000XM5', price: '₹24,990', mrp: '₹34,990',
    badge: '-15% Drop', badgeColor: 'bg-tertiary-container/20 text-tertiary-container',
    barWidth: '55%', barColor: 'bg-primary',
    cta: 'Register for Alerts', ctaStyle: 'primary',
  },
  {
    icon: '☕', name: 'Breville Barista Pro', price: '₹78,500', mrp: null,
    badge: 'Trending Up', badgeColor: 'bg-surface-container text-on-surface-variant',
    barWidth: '38%', barColor: 'bg-outline-variant',
    cta: 'Login for History', ctaStyle: 'secondary',
  },
]

export default function LandingPage() {
  const [heroInput, setHeroInput] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [imgLoading, setImgLoading] = useState(false)
  const [previewImg, setPreviewImg] = useState(null)
  const [liveProducts, setLiveProducts] = useState(INITIAL_LIVE_PRODUCTS)
  const { user } = useAuth()
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const fileRef = useRef(null)

  function handleViewAllDrops(e) {
    e.preventDefault()
    if (!user) {
      toast('To view Live Market Flux, please Sign In or Sign Up.', 'info')
      return
    }
    navigate('/trends')
  }

  function handleTrack(e) {
    e.preventDefault()
    if (!heroInput.trim()) { inputRef.current?.focus(); return }
    navigate(`/product?q=${encodeURIComponent(heroInput)}`)
  }

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const d = await products.publicRecent();
        
        if (d && d.data && Array.isArray(d.data)) {
          const mapped = d.data.map((p, i) => ({
            id: p.id,
            icon: '📦',
            image_url: p.image_url,
            name: p.name.length > 35 ? p.name.substring(0, 35) + '...' : p.name,
            price: p.best_price ? `₹${p.best_price.toLocaleString('en-IN')}` : 'N/A',
            mrp: p.retailers?.[0]?.mrp ? `₹${p.retailers[0].mrp.toLocaleString('en-IN')}` : null,
            badge: p.drop_pct > 0 ? `-${p.drop_pct}% Drop` : 'Trending Up',
            badgeColor: p.drop_pct > 0 ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-surface-container text-on-surface-variant',
            barWidth: p.drop_pct > 0 ? `${Math.min(100, 30 + p.drop_pct * 2)}%` : '38%',
            barColor: p.drop_pct > 0 ? 'bg-tertiary' : 'bg-outline-variant',
            cta: user ? 'Set Price Alert' : (i === 1 ? 'Register for Alerts' : 'Login to Set Alert'),
            ctaStyle: i === 1 ? 'primary' : 'secondary',
          }));
          
          if (mapped.length > 0) {
            setLiveProducts(mapped.slice(0, 3));
          }
        }
      } catch (err) {
        console.warn('Live Market Flux: Backend connection failed. Using cached/static data.', err);
        // Fallback is already handled by the default state, but we ensure it stays stable
      }
    };

    fetchRecent();
  }, []);

  function handleSignup(e) {
    e.preventDefault()
    if (!email || !email.includes('@')) { toast('Please enter a valid email', 'error'); return }
    navigate(`/register?email=${encodeURIComponent(email)}`)
  }

  async function handleImageUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) { toast('Please select an image file', 'error'); return }
    const reader = new FileReader()
    reader.onload = ev => setPreviewImg(ev.target.result)
    reader.readAsDataURL(file)

    setImgLoading(true)
    try {
      const data = await products.imageSearch(file)
      if (data.results && data.results.length > 0) {
        navigate(`/product?q=${encodeURIComponent(data.results[0].name)}`)
      } else {
        toast('No products found in image', 'info')
      }
    } catch (err) {
      toast(err.message || 'Image search failed', 'error')
    } finally {
      setImgLoading(false)
      setPreviewImg(null)
      e.target.value = ''
    }
  }

  return (
    <div className="min-h-screen bg-surface font-body selection:bg-primary/10">
      <Navbar />
      <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Hero Section */}
      <section className="relative pt-24 pb-20 overflow-hidden">
        <div className="max-w-7xl mx-auto px-8 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 text-primary text-xs font-bold uppercase tracking-wider mb-8 animate-fade-up">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Multi-Modal Search Active
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold text-on-surface mb-6 tracking-tight leading-[1.1] animate-fade-up" style={{ animationDelay: '0.1s' }}>
            The Precision<br /> Price Ledger<span className="text-primary italic">Drop.</span>
          </h1>

          <p className="text-xl text-on-surface-variant max-w-2xl mx-auto mb-12 animate-fade-up" style={{ animationDelay: '0.2s' }}>
            DeltaDrop monitors millions of products across the web to secure the best entry points for your purchases.
          </p>

          <form onSubmit={handleTrack} className="max-w-2xl mx-auto relative animate-fade-up" style={{ animationDelay: '0.3s' }}>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
            <div className="flex items-center gap-3 p-2 bg-white rounded-2xl shadow-float border border-outline-variant/40">
              <div className="flex-1 flex items-center gap-3 px-4">
                <span className="material-symbols-outlined text-outline">search</span>
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Paste any Product URL or Product Name..."
                  value={heroInput}
                  onChange={e => setHeroInput(e.target.value)}
                  className="w-full py-3 bg-transparent text-on-surface font-medium focus:outline-none placeholder:text-outline/60"
                />
              </div>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="px-4 py-3.5 rounded-xl font-bold text-on-surface-variant hover:bg-surface transition-all active:scale-95"
                aria-label="Search by image"
              >
                <span className="material-symbols-outlined align-middle">image_search</span>
              </button>
              <button type="submit" className="bg-primary text-white px-8 py-3.5 rounded-xl font-bold hover:bg-primary-container transition-all active:scale-95 shadow-sm">
                Track
              </button>
            </div>
          </form>

        </div>
      </section>

      {/* Live Market Flux Section */}
      <section className="py-24 bg-white border-y border-outline-variant/40">
        <div className="max-w-7xl mx-auto px-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
            <div>
              <h2 className="text-3xl font-bold text-on-surface tracking-tight mb-2">Live Market Flux</h2>
              <p className="text-on-surface-variant">Real-time delta detections across indexed retailers.</p>
            </div>
            <button onClick={handleViewAllDrops} className="text-primary font-bold hover:underline flex items-center gap-1 group">
              View All Detections
              <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {liveProducts.map((p, i) => (
              <Link to={`/product?q=${encodeURIComponent(p.name)}`} key={i} className="glass-card p-6 flex flex-col h-full group hover:-translate-y-1 transition-all duration-300">
                <div className="flex items-start justify-between mb-6">
                  <div className="w-14 h-14 rounded-2xl bg-surface flex items-center justify-center text-3xl shadow-sm border border-outline-variant/20 overflow-hidden relative">
                    {p.image_url ? (
                      <img src={p.image_url} alt={p.name} className="w-full h-full object-contain p-2 mix-blend-multiply" />
                    ) : (
                      <span>{p.icon}</span>
                    )}
                  </div>
                  <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider ${p.badgeColor}`}>
                    {p.badge}
                  </span>
                </div>

                <h3 onClick={() => navigate(`/product?q=${encodeURIComponent(p.name)}`)} className="font-bold text-on-surface mb-1 group-hover:text-primary transition-colors line-clamp-1 cursor-pointer">{p.name}</h3>
                <div className="flex items-baseline gap-2 mb-6">
                  <span className="text-2xl font-black text-on-surface">{p.price}</span>
                  {p.mrp && <span className="text-sm text-outline line-through">{p.mrp}</span>}
                </div>

                <div className="mt-auto">
                  <div className="h-1.5 w-full bg-surface-container rounded-full overflow-hidden mb-4">
                    <div className={`h-full rounded-full ${p.barColor}`} style={{ width: p.barWidth }} />
                  </div>
                  <button onClick={() => navigate('/login')} className={`w-full py-3 rounded-xl text-sm font-bold transition-all ${p.ctaStyle === 'primary' ? 'bg-primary text-white shadow-sm hover:bg-primary-container' : 'bg-surface text-on-surface-variant hover:bg-surface-container'
                    }`}>
                    {p.cta}
                  </button>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Aggregate Data Section */}
      <section className="py-24 bg-surface overflow-hidden">
        <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 text-primary text-xs font-bold uppercase tracking-wider mb-6">
              Precision Intelligence
            </div>
            <h2 className="text-4xl font-extrabold text-on-surface mb-6 tracking-tight leading-tight">
              Aggregate Pricing Data<br />Across <span className="text-primary">5,000+ Retailers.</span>
            </h2>
            <p className="text-lg text-on-surface-variant mb-10 leading-relaxed">
              We leverage proprietary scrapers to index global inventories in 15-minute cycles, ensuring you never miss a delta in the market.
            </p>

            <ul className="space-y-4 mb-12">
              {[
                { icon: 'bolt', text: 'Real-time price drop notifications' },
                { icon: 'monitoring', text: 'Historical price performance charts' },
                { icon: 'verified', text: 'Verified retailer availability' }
              ].map((f, i) => (
                <li key={i} className="flex items-center gap-3 font-semibold text-on-surface">
                  <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                    <span className="material-symbols-outlined text-sm">{f.icon}</span>
                  </div>
                  {f.text}
                </li>
              ))}
            </ul>

            <div className="p-8 bg-white rounded-3xl border border-outline-variant/40 shadow-sm relative group overflow-hidden">
              <div className="relative z-10">
                <p className="font-bold text-on-surface mb-4 text-sm">Join the network for precision tracking.</p>
                <form onSubmit={handleSignup} className="flex flex-col sm:flex-row gap-3">
                  <input
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="flex-1 px-5 py-3 rounded-xl bg-surface border border-outline-variant/40 text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                  />
                  <button type="submit" className="bg-primary text-white px-8 py-3 rounded-xl font-bold hover:bg-primary-container transition-all shadow-sm">
                    Get Access
                  </button>
                </form>
              </div>
              <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-48 h-48 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-colors" />
            </div>
          </div>

          <div className="relative lg:h-[600px] flex items-center justify-center">
            <div className="absolute inset-0 bg-primary/5 rounded-[40px] rotate-3" />
            <div className="relative z-10 w-full bg-white rounded-[32px] p-8 shadow-float border border-outline-variant/40 transform -rotate-2 hover:rotate-0 transition-transform duration-500">
              <div className="flex items-center justify-between mb-8 pb-6 border-b border-outline-variant/20">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center text-white">
                    <span className="material-symbols-outlined">analytics</span>
                  </div>
                  <div>
                    <div className="font-bold text-on-surface">Precision Analytics</div>
                    <div className="text-xs text-on-surface-variant font-medium">Market Performance View</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-black text-primary">-12.4%</div>
                  <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Avg. Delta</div>
                </div>
              </div>

              <div className="space-y-6">
                {[
                  { label: 'Tracking Accuracy', val: '99.98%' },
                  { label: 'Price Anomalies', val: '432 Detected' },
                  { label: 'System Uptime', val: '100%' }
                ].map((s, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">
                      <span>{s.label}</span>
                      <span className="text-on-surface">{s.val}</span>
                    </div>
                    <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: '85%' }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-12 p-6 bg-surface rounded-2xl border border-outline-variant/20 text-center">
                <p className="text-sm font-medium text-on-surface-variant leading-relaxed">
                  "DeltaDrop changed how we manage our internal hardware procurement. Absolute game changer."
                </p>
                <div className="mt-4 font-bold text-on-surface text-xs">— CTO, TechFlow Systems</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />

      {imgLoading && (
        <div className="fixed inset-0 z-[100] bg-on-surface/40 backdrop-blur-md flex items-center justify-center">
          <div className="bg-white p-8 rounded-[32px] shadow-float border border-outline-variant/40 flex flex-col items-center gap-6 max-w-sm w-full mx-4">
            <div className="w-20 h-20 rounded-2xl border-4 border-primary border-t-transparent animate-spin" />
            <div className="text-center">
              <h4 className="font-bold text-on-surface uppercase tracking-widest mb-2 text-sm">AI Analyzing Image</h4>
              <p className="text-xs text-on-surface-variant font-medium">Extracting product data from your upload...</p>
            </div>
            {previewImg && (
              <div className="w-full aspect-video rounded-xl overflow-hidden border border-outline-variant/20">
                <img src={previewImg} alt="Preview" className="w-full h-full object-cover" />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
