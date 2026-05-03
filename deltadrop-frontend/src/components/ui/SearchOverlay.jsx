import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { products } from '../../services/api'

export default function SearchOverlay({ open, onClose }) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedCat, setSelectedCat] = useState(null)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  const CATEGORIES = [
    { id: 'Shoes', icon: 'steps', label: 'Shoes' },
    { id: 'Electronics', icon: 'devices', label: 'Electronics' },
    { id: 'Clothing', icon: 'apparel', label: 'Fashion' },
    { id: 'Home', icon: 'home', label: 'Home' },
  ]

  // Reset on open
  useEffect(() => {
    if (open) {
      setQuery('')
      setSuggestions([])
    }
  }, [open])

  // Focus input
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
  }, [open])

  // Fetch suggestions with debounce
  useEffect(() => {
    if (!query || query.length < 2) {
      setSuggestions([])
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const res = await products.suggestions(query)
        setSuggestions(res.suggestions || [])
      } catch (err) {
        console.warn("Suggestions fetch failed")
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query])

  // Keyboard controls
  const handlerRef = useRef(null)
  handlerRef.current = e => {
    if (e.key === 'Escape') onClose()
    if (e.key === 'Enter') {
      if (query.trim()) goToTrack(query)
    }
  }

  useEffect(() => {
    const listen = e => handlerRef.current(e)
    if (open) document.addEventListener('keydown', listen)
    return () => document.removeEventListener('keydown', listen)
  }, [open])

  function goToTrack(queryString) {
    onClose()
    let url = `/product?q=${encodeURIComponent(queryString)}`
    if (selectedCat) url += `&cat=${encodeURIComponent(selectedCat)}`
    navigate(url)
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[300] flex items-start justify-center pt-16 px-4"
      style={{ background: 'rgba(24,28,30,0.55)', backdropFilter: 'blur(4px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}>

      <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl shadow-float overflow-hidden animate-fade-up">

        {/* Search input */}
        <div className="flex items-center gap-3 px-5 py-4" style={{ borderBottom: '1px solid rgba(195,198,214,0.12)' }}>
          <span className="material-symbols-outlined text-primary text-xl flex-shrink-0">
            {isSearching ? 'rotate_right animate-spin' : 'troubleshoot'}
          </span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Paste product URL or type an item name..."
            className="flex-1 bg-transparent border-none outline-none text-base text-on-surface placeholder:text-on-surface-variant font-headline font-bold"
          />
          <div className="flex items-center gap-2">
            {query && (
              <button onClick={() => { setQuery(''); inputRef.current?.focus() }}
                className="text-on-surface-variant hover:text-on-surface transition-colors flex items-center">
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            )}
            <button onClick={onClose}
              className="text-xs text-on-surface-variant bg-surface-container px-2 py-1 rounded font-mono hover:bg-surface-container-high transition-colors">
              ESC
            </button>
          </div>
        </div>

        {/* Interactive Query State */}
        <div className="max-h-[460px] overflow-y-auto">
          {!query.trim() ? (
            <div className="py-16 text-center">
              <div className="text-4xl mb-3 opacity-60">🔎</div>
              <div className="font-semibold text-on-surface mb-1">Global Neural Search</div>
              <div className="text-sm text-on-surface-variant max-w-sm mx-auto">
                DeltaDrop will dynamically scan verified retailers to compare prices for your request.
              </div>
            </div>
          ) : (
            <div className="flex flex-col">
              {/* Autocomplete List */}
              {suggestions.length > 0 && (
                <div className="py-2 border-b border-outline-variant/5">
                  <div className="px-5 py-2 text-[10px] font-bold text-primary uppercase tracking-widest">Database Matches</div>
                  {suggestions.map(s => (
                    <button key={s.id || s.name} onClick={() => goToTrack(s.name)}
                      className="w-full text-left px-5 py-3 hover:bg-surface-container-high flex items-center gap-3 transition-colors">
                      <span className="material-symbols-outlined text-on-surface-variant text-lg">history</span>
                      <span className="text-sm text-on-surface font-medium">{s.name}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Direct Search / Track Action */}
              <button onClick={() => goToTrack(query)}
                className="w-full text-left px-5 py-4 hover:bg-primary/5 flex items-center justify-between group transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                    <span className="material-symbols-outlined text-xl">analytics</span>
                  </div>
                  <div>
                    <div className="text-sm font-bold text-on-surface group-hover:text-primary transition-colors">Launch Market Scan</div>
                    <div className="text-[11px] text-on-surface-variant truncate max-w-[300px]">Deep analysis for "{query}"</div>
                  </div>
                </div>
                <span className="material-symbols-outlined text-primary opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0">arrow_forward</span>
              </button>
            </div>
          )}
        </div>

        {/* Category Picker (Quick Actions) */}
        {!query && (
          <div className="px-5 py-6 bg-surface-container-low flex flex-col gap-4">
              <h3 className="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest px-1">Strict Category Filter (Optional)</h3>
              <div className="grid grid-cols-4 gap-2">
                  {CATEGORIES.map(cat => (
                      <button 
                          key={cat.id}
                          onClick={() => setSelectedCat(selectedCat === cat.id ? null : cat.id)}
                          className={`flex flex-col items-center gap-2 p-3 rounded-2xl transition-all border ${selectedCat === cat.id ? 'bg-primary/10 border-primary text-primary shadow-sm' : 'bg-surface-container-highest border-outline-variant/10 text-on-surface-variant hover:border-outline-variant/30 hover:bg-surface-container-high'}`}
                      >
                          <span className="material-symbols-outlined">{cat.icon}</span>
                          <span className="text-[10px] font-black uppercase tracking-tight">{cat.label}</span>
                      </button>
                  ))}
              </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-5 py-3 flex items-center justify-between text-[11px] text-on-surface-variant bg-surface-container-low/30"
          style={{ borderTop: '1px solid rgba(195,198,214,0.12)' }}>
          <div className="flex gap-4">
            <span>↵ launch analysis</span>
            <span>ESC close prompt</span>
          </div>
          <span className="text-primary font-semibold tracking-wider">DeltaDrop Engine Ready</span>
        </div>
      </div>
    </div>
  )
}
