import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import AIButton from '../components/ui/AIButton'
import { toast } from '../components/ui/Toast'

function getRetailerName(product) {
  return product?.retailers?.[0]?.retailer || 'Retailer'
}

function getPrimaryMrp(product) {
  return product?.retailers?.find(r => r?.mrp)?.mrp || null
}

function formatCurrency(value) {
  return value ? `₹${Number(value).toLocaleString('en-IN')}` : 'N/A'
}

function iconForProduct(name = '', category = '') {
  const value = `${name} ${category}`.toLowerCase()
  if (value.includes('laptop') || value.includes('macbook')) return '💻'
  if (value.includes('headphone') || value.includes('earbud') || value.includes('audio')) return '🎧'
  if (value.includes('phone') || value.includes('iphone') || value.includes('smartphone')) return '📱'
  if (value.includes('shoe') || value.includes('fashion')) return '👟'
  if (value.includes('watch')) return '⌚'
  if (value.includes('tv') || value.includes('television')) return '📺'
  if (value.includes('camera')) return '📷'
  if (value.includes('gaming') || value.includes('console')) return '🎮'
  return '🛍️'
}

function escapeCsv(value) {
  const stringValue = String(value ?? '')
  return `"${stringValue.replace(/"/g, '""')}"`
}

function buildNeutralPulse() {
  return [
    { sector: 'ELECTRONICS PULSE', status: 'Stable', delta: '0.0%', up: null, desc: 'No sufficient data tracked currently.' },
    { sector: 'FASHION PULSE', status: 'Stable', delta: '0.0%', up: null, desc: 'No sufficient data tracked currently.' },
    { sector: 'HOME & LIVING', status: 'Stable', delta: '0.0%', up: null, desc: 'No sufficient data tracked currently.' },
  ]
}

function buildPulse(list, sector) {
  if (!list || list.length < 2) {
    return { sector, status: 'Stable', delta: '0.0%', up: null, desc: 'No sufficient data tracked currently.' }
  }

  const avgDrop = list.reduce((acc, product) => acc + (product.drop_pct || 0), 0) / list.length
  const status = avgDrop >= 10 ? 'Hot' : avgDrop > 0 ? 'Stable' : 'Neutral'
  const delta = `${avgDrop > 0 ? '-' : ''}${Math.abs(avgDrop).toFixed(1)}%`
  const up = avgDrop < 0
  const desc = avgDrop >= 10
    ? 'High volatility and notable savings are showing up in this sector.'
    : 'Movement is limited right now, so there is no strong sector-wide signal yet.'

  return { sector, status, delta, up, desc }
}

export default function TrendsPage() {
  const navigate = useNavigate()
  const [downloading, setDownloading] = useState(false)
  const [recentProducts, setRecentProducts] = useState([])
  const [popularDrops, setPopularDrops] = useState([])
  const [biggestDrops, setBiggestDrops] = useState([])
  const [pulse, setPulse] = useState(buildNeutralPulse())
  const [volatilityLeader, setVolatilityLeader] = useState(null)
  const [dataLoading, setDataLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    const loadRecentProducts = async () => {
      setDataLoading(true)
      try {
        const response = await fetch('/api/v1/products/public-recent')
        const payload = await response.json().catch(() => ({}))
        const products = Array.isArray(payload.data) ? payload.data : []

        if (!isMounted) return

        setRecentProducts(products)

        if (!products.length) {
          setPopularDrops([])
          setBiggestDrops([])
          setVolatilityLeader(null)
          setPulse(buildNeutralPulse())
          return
        }

        const sortedByDrop = [...products].sort((a, b) => (b.drop_pct || 0) - (a.drop_pct || 0))
        const sortedByDelta = [...products].sort((a, b) => {
          const aDelta = (getPrimaryMrp(a) || 0) - (a.best_price || 0)
          const bDelta = (getPrimaryMrp(b) || 0) - (b.best_price || 0)
          return bDelta - aDelta
        })

        setPopularDrops(
          sortedByDrop.slice(0, 5).map(product => {
            const mrp = getPrimaryMrp(product)
            return {
              id: product.id,
              icon: iconForProduct(product.name, product.category),
              image_url: product.image_url,
              name: product.name,
              category: product.category || 'Products',
              store: getRetailerName(product),
              price: formatCurrency(product.best_price),
              mrp: mrp ? formatCurrency(mrp) : null,
              drop_pct: product.drop_pct || 0,
            }
          })
        )

        setBiggestDrops(
          sortedByDelta.slice(0, 5).map(product => {
            const mrp = getPrimaryMrp(product)
            const delta = mrp && product.best_price ? mrp - product.best_price : 0
            return {
              id: product.id,
              icon: iconForProduct(product.name, product.category),
              image_url: product.image_url,
              name: product.name,
              category: product.category || 'Products',
              price: formatCurrency(product.best_price),
              drop_amt: delta > 0 ? `₹${delta.toLocaleString('en-IN')}` : '—',
              merchant: getRetailerName(product),
            }
          })
        )

        const leader = sortedByDrop[0] || null
        setVolatilityLeader(
          leader
            ? {
                drop_pct: leader.drop_pct || 0,
                name: leader.name,
                category: leader.category || 'Products',
                store: getRetailerName(leader),
              }
            : null
        )

        const electronics = products.filter(product => product.category?.toLowerCase().includes('elec') || product.name?.toLowerCase().includes('laptop') || product.name?.toLowerCase().includes('phone'))
        const fashion = products.filter(product => product.category?.toLowerCase().includes('fashion') || product.name?.toLowerCase().includes('shoes') || product.name?.toLowerCase().includes('watch'))
        const home = products.filter(product => product.category?.toLowerCase().includes('home') || product.category?.toLowerCase().includes('living'))

        setPulse([
          buildPulse(electronics, 'ELECTRONICS PULSE'),
          buildPulse(fashion, 'FASHION PULSE'),
          buildPulse(home, 'HOME & LIVING'),
        ])
      } catch (error) {
        if (!isMounted) return
        console.warn('[TrendsPage] Failed to load recent products', error)
        setRecentProducts([])
        setPopularDrops([])
        setBiggestDrops([])
        setVolatilityLeader(null)
        setPulse(buildNeutralPulse())
      } finally {
        if (isMounted) setDataLoading(false)
      }
    }

    loadRecentProducts()
    return () => { isMounted = false }
  }, [])

  function handleDownload() {
    setDownloading(true)
    try {
      const csvRows = [
        ['Product ID', 'Name', 'Category', 'Retailer', 'Current Price', 'MRP', 'Drop Percent']
      ]

      recentProducts.forEach(product => {
        csvRows.push([
          product.id || '',
          escapeCsv(product.name),
          escapeCsv(product.category || 'Products'),
          escapeCsv(getRetailerName(product)),
          product.best_price ?? '',
          getPrimaryMrp(product) ?? '',
          product.drop_pct ?? 0,
        ])
      })

      const csvString = csvRows.map(row => row.join(',')).join('\n')
      const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `deltadrop_market_pulse_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      toast('Report downloaded as CSV', 'success')
    } catch (error) {
      toast('Export failed', 'error')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-8 py-12">
        <div className="mb-12 animate-fade-up">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 text-primary text-xs font-bold uppercase tracking-wider mb-6">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Live Market Detections
          </div>
          <h1 className="text-4xl font-extrabold text-on-surface tracking-tight mb-4">
            Today's Market Drops
          </h1>
          <p className="text-lg text-on-surface-variant max-w-2xl leading-relaxed">
            High-fidelity analysis of price fluctuations across 5,000+ Indian retailers. We track the numbers to secure your entry points.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {pulse.map((item, index) => (
            <div key={item.sector} className="bg-white rounded-2xl p-6 border border-outline-variant/40 shadow-sm animate-fade-up" style={{ animationDelay: `${index * 0.1}s` }}>
              <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">{item.sector}</div>
              <div className="flex items-center justify-between mb-4">
                <div className="text-2xl font-black text-on-surface">{item.status}</div>
                <div className={`px-2.5 py-1 rounded-lg text-xs font-bold ${item.up === false ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-surface-container text-on-surface-variant'}`}>
                  {item.delta}
                </div>
              </div>
              <p className="text-sm text-on-surface-variant leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-16">
          <div className="lg:col-span-2 bg-white rounded-3xl border border-outline-variant/40 shadow-sm overflow-hidden animate-fade-up">
            <div className="p-8 border-b border-outline-variant/40 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-on-surface">Popular Price Drops</h2>
                <p className="text-sm text-on-surface-variant">High-demand deals across the network.</p>
              </div>
              <button className="w-10 h-10 rounded-xl bg-surface flex items-center justify-center text-outline hover:text-primary transition-colors">
                <span className="material-symbols-outlined">auto_graph</span>
              </button>
            </div>

            <div className="divide-y divide-outline-variant/20">
              {dataLoading ? (
                [...Array(5)].map((_, index) => (
                  <div key={index} className="p-6 flex items-center gap-4 animate-pulse">
                    <div className="w-12 h-12 rounded-xl bg-surface" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-surface rounded w-1/3" />
                      <div className="h-3 bg-surface rounded w-1/4" />
                    </div>
                  </div>
                ))
              ) : popularDrops.length ? (
                popularDrops.map(item => (
                  <div key={item.id} onClick={() => navigate(`/product?q=${encodeURIComponent(item.name)}`)} className="flex items-center gap-5 p-4 rounded-2xl hover:bg-surface transition-all cursor-pointer group">
                    <div className="w-14 h-14 rounded-2xl bg-surface flex items-center justify-center text-2xl flex-shrink-0 overflow-hidden border border-outline-variant/20">
                      {item.image_url ? (
                        <img src={item.image_url} alt="" className="w-full h-full object-contain p-2 mix-blend-multiply" />
                      ) : (
                        <span>{item.icon}</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-on-surface group-hover:text-primary transition-colors line-clamp-1">{item.name}</div>
                      <div className="text-sm text-on-surface-variant mt-1">{item.category} · {item.store}</div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-lg font-black text-primary">{item.price}</div>
                      {item.mrp && <div className="text-xs text-outline line-through">{item.mrp}</div>}
                      <div className="text-[10px] font-black text-tertiary-container uppercase tracking-wider mt-1">-{item.drop_pct}% DROP</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-10 text-center text-sm text-on-surface-variant">
                  No live drop data is available yet.
                </div>
              )}
            </div>
          </div>

          <div className="bg-primary text-white rounded-3xl p-8 flex flex-col animate-fade-up" style={{ animationDelay: '0.2s' }}>
            <div className="text-xs font-bold uppercase tracking-widest opacity-60 mb-2">Volatility Leader</div>
            <h3 className="text-2xl font-bold mb-8">Highest Relative Drop</h3>

            <div className="flex-1 flex flex-col justify-center text-center">
              <div className="text-8xl font-black mb-4">{volatilityLeader ? `${volatilityLeader.drop_pct}%` : '0%'}</div>
              <div className="text-xl font-bold mb-1">{volatilityLeader?.name || 'No leader yet'}</div>
              <div className="text-sm opacity-60">
                {volatilityLeader ? `${volatilityLeader.category} · ${volatilityLeader.store}` : 'Waiting for more live pricing data'}
              </div>
            </div>

            <button onClick={() => navigate('/discover')} className="mt-8 w-full py-4 bg-white text-primary rounded-2xl font-bold text-sm hover:bg-primary-container hover:text-white transition-all active:scale-95 shadow-sm">
              View Detailed Volatility
            </button>
          </div>
        </div>

        <div className="animate-fade-up">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl font-bold text-on-surface tracking-tight">Biggest Value Fluctuations</h2>
            <button onClick={handleDownload} className="text-sm font-bold text-primary flex items-center gap-2 hover:underline">
              <span className="material-symbols-outlined text-base">download</span>
              {downloading ? 'Downloading…' : 'Export Data (.CSV)'}
            </button>
          </div>

          <div className="bg-white rounded-3xl border border-outline-variant/40 shadow-sm overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface border-b border-outline-variant/40">
                  <th className="px-8 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Product</th>
                  <th className="px-8 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Category</th>
                  <th className="px-8 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Current Price</th>
                  <th className="px-8 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Net Delta</th>
                  <th className="px-8 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest text-right">Merchant</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20">
                {dataLoading ? (
                  [...Array(5)].map((_, index) => (
                    <tr key={index} className="animate-pulse">
                      <td colSpan={5} className="px-8 py-6"><div className="h-4 bg-surface rounded w-full" /></td>
                    </tr>
                  ))
                ) : biggestDrops.length ? (
                  biggestDrops.map((row, index) => (
                    <tr key={index} onClick={() => navigate(`/product?q=${encodeURIComponent(row.name)}`)} className="hover:bg-surface transition-colors cursor-pointer group">
                      <td className="px-8 py-6">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-xl bg-surface flex items-center justify-center text-lg flex-shrink-0 border border-outline-variant/20 overflow-hidden">
                            {row.image_url ? (
                              <img src={row.image_url} alt="" className="w-full h-full object-contain p-1.5 mix-blend-multiply" />
                            ) : (
                              <span>{row.icon}</span>
                            )}
                          </div>
                          <span className="font-bold text-on-surface group-hover:text-primary transition-colors">{row.name}</span>
                        </div>
                      </td>
                      <td className="px-8 py-6 text-sm font-medium text-on-surface-variant">{row.category}</td>
                      <td className="px-8 py-6 font-black text-on-surface">{row.price}</td>
                      <td className="px-8 py-6">
                        <span className="px-2.5 py-1 rounded-lg bg-tertiary-container text-on-tertiary-container text-[10px] font-black">
                          - {row.drop_amt}
                        </span>
                      </td>
                      <td className="px-8 py-6 text-right">
                        <span className="text-xs font-bold text-on-surface-variant">{row.merchant}</span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-8 py-10 text-center text-sm text-on-surface-variant">
                      No value fluctuation data is available yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {popularDrops[0] && (
        <AIButton
          product={{
            id: popularDrops[0].id,
            name: popularDrops[0].name,
            price: popularDrops[0].price,
            category: popularDrops[0].category,
            retailers: [{ name: popularDrops[0].store, price: popularDrops[0].price }]
          }}
          position="fixed"
        />
      )}
    </AppLayout>
  )
}
