/**
 * api.js — DeltaDrop Frontend API Service
 *
 * Wraps every backend endpoint with auth token injection,
 * error handling, and typed responses.
 *
 * Backend base: /api/v1  (set VITE_API_BASE in .env if needed)
 */

const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api/v1'
const BACKEND_COOLDOWN_MS = 1500
let backendOfflineUntil = 0

function isBackendOffline() {
  return Date.now() < backendOfflineUntil
}

function markBackendOffline() {
  backendOfflineUntil = Date.now() + BACKEND_COOLDOWN_MS
}

function clearBackendOffline() {
  backendOfflineUntil = 0
}

function isNetworkFailure(err) {
  const msg = String(err?.message || err || '').toLowerCase()
  return (
    msg.includes('failed to fetch') ||
    msg.includes('networkerror') ||
    msg.includes('ecconnreset') ||
    msg.includes('econnreset') ||
    msg.includes('econnrefused') ||
    msg.includes('load failed') ||
    msg.includes('aborted')
  )
}

async function fetchWithBackendGuard(url, options = {}) {
  if (isBackendOffline()) {
    throw new Error('Backend temporarily unavailable')
  }

  const timeoutMs = options.timeoutMs ?? 15000
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  const mergedSignal = options.signal

  const onAbort = () => controller.abort()
  if (mergedSignal) mergedSignal.addEventListener('abort', onAbort, { once: true })

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearBackendOffline()
    return res
  } catch (err) {
    if (isNetworkFailure(err)) {
      markBackendOffline()
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
    if (mergedSignal) mergedSignal.removeEventListener('abort', onAbort)
  }
}

// ── Auth token helpers ────────────────────────────────────────────────────────

function getToken() {
  const token = localStorage.getItem('dd_token')
  const refresh = localStorage.getItem('dd_refresh')

  // Only return token if both tokens exist and token format is valid
  if (!token || !refresh) {
    if (token && !refresh) {
      addToBlacklist(token)
      clearTokens()
    }
    return null
  }

  // Check if token is blacklisted
  if (isTokenBlacklisted(token)) {
    clearTokens()
    return null
  }

  // Basic JWT format validation (header.payload.signature)
  const parts = token.split('.')
  if (parts.length !== 3) {
    addToBlacklist(token)
    clearTokens()
    return null
  }

  // Check if token is expired by decoding payload
  try {
    const payload = JSON.parse(atob(parts[1]))
    const now = Math.floor(Date.now() / 1000)
    if (payload.exp && payload.exp < now) {
      addToBlacklist(token)
      clearTokens()
      return null
    }
  } catch (e) {
    addToBlacklist(token)
    clearTokens()
    return null
  }

  return token
}

function isTokenExpired(token) {
  if (!token) return true
  
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return true
    
    const payload = JSON.parse(atob(parts[1]))
    const now = Math.floor(Date.now() / 1000)
    return payload.exp && payload.exp < now
  } catch (e) {
    return true
  }
}

function validateTokenPair() {
  const token = localStorage.getItem('dd_token')
  const refresh = localStorage.getItem('dd_refresh')
  
  // Check if we have both tokens
  if (!token || !refresh) {
    clearTokens()
    return false
  }
  
  // Check token format
  const tokenParts = token.split('.')
  if (tokenParts.length !== 3) {
    clearTokens()
    return false
  }
  
  // Check if token is expired
  if (isTokenExpired(token)) {
    // Don't clear here - let refresh mechanism handle it
    return false
  }
  
  return true
}

let onAuthChange = null
let refreshPromise = null
export function setAuthChangeCallback(cb) {
  onAuthChange = cb
}

function saveTokens(access, refresh, user) {
  localStorage.setItem('dd_token',   access)
  localStorage.setItem('dd_refresh', refresh)
  if (user) localStorage.setItem('dd_user', JSON.stringify(user))
  if (onAuthChange) onAuthChange({ token: access, user })
}

function clearTokens() {
  localStorage.removeItem('dd_token')
  localStorage.removeItem('dd_refresh')
  localStorage.removeItem('dd_user')
  if (onAuthChange) onAuthChange({ token: null, user: null })
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

export async function apiFetch(path, options = {}) {
  if (isBackendOffline()) {
    throw new Error('Backend temporarily unavailable')
  }
  
  // Skip auth for public endpoints
  const publicEndpoints = ['/auth/login', '/auth/register', '/auth/refresh', '/products/public-search', '/products/public-recent', '/products/public-trending', '/products/search', '/api/search']
  const isPublicEndpoint = publicEndpoints.some(endpoint => path.startsWith(endpoint))
  
  // Get token for authenticated endpoints
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token && !isPublicEndpoint ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const res = await fetchWithBackendGuard(`${BASE}${path}`, { ...options, headers })

  // Handle 401 gracefully
  if (res.status === 401 && !isPublicEndpoint && token) {
    console.log('[AUTH] 401 received - attempting token refresh')
    const refreshed = await tryRefresh()
    if (refreshed) {
      // Retry with fresh token
      const freshToken = getToken()
      const retryHeaders = {
        'Content-Type': 'application/json',
        ...(freshToken ? { Authorization: `Bearer ${freshToken}` } : {}),
        ...options.headers,
      }
      const retryRes = await fetchWithBackendGuard(`${BASE}${path}`, { ...options, headers: retryHeaders })
      if (retryRes.ok) {
        return await retryRes.json().catch(() => ({}))
      }
    }
    // If refresh failed, clear tokens and throw error
    clearTokens()
    throw new Error('Session expired - please log in again')
  }

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    const msg = data.detail || data.message || `API error ${res.status}`
    throw new Error(msg)
  }

  return data
}

async function tryRefresh() {
  const refresh = localStorage.getItem('dd_refresh')
  if (!refresh) return false
  if (refreshPromise) return refreshPromise

  const maxRetries = 3
  const baseDelayMs = 250
  refreshPromise = (async () => {
    try {
      for (let attempt = 0; attempt < maxRetries; attempt += 1) {
        try {
          const res = await fetch(`${BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refresh }),
          })
          if (!res.ok) {
            if (res.status === 401) {
              // Refresh token is invalid, clear everything
              clearTokens()
              return false
            }
            return false
          }
          const data = await res.json()
          saveTokens(data.access_token, data.refresh_token, data.user)
          console.log('Token refresh successful')
          return true
        } catch (err) {
          if (attempt === maxRetries - 1) {
            // Final attempt failed, clear tokens
            clearTokens()
            return false
          }
          const backoff = baseDelayMs * (2 ** attempt)
          await new Promise(resolve => setTimeout(resolve, backoff))
        }
      }
      return false
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

// Add cleanup function to be called periodically
function cleanupExpiredTokens() {
  const token = localStorage.getItem('dd_token')
  if (token && isTokenExpired(token)) {
    console.log('Cleaning up expired token')
    clearTokens()
  }
}

// Token blacklist to prevent reuse of invalid tokens
const tokenBlacklist = new Set()

function addToBlacklist(token) {
  if (token) tokenBlacklist.add(token)
}

function isTokenBlacklisted(token) {
  return tokenBlacklist.has(token)
}

// Run cleanup every 5 minutes
if (typeof window !== 'undefined') {
  setInterval(cleanupExpiredTokens, 5 * 60 * 1000)
  
  // Immediate cleanup on page load to prevent any 401 errors
  cleanupExpiredTokens()
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const auth = {
  async register({ email, username, password, full_name }) {
    return apiFetch('/auth/register', {
      method: 'POST',
      body:   JSON.stringify({ email, username, password, full_name }),
    })
  },

  async login({ email, password }) {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body:   JSON.stringify({ email, password }),
    })
    saveTokens(data.access_token, data.refresh_token, data.user)
    return data
  },

  async googleLogin(payload) {
    const body = typeof payload === 'string'
      ? { token: payload }
      : payload

    const data = await apiFetch('/auth/google-login', {
      method: 'POST',
      body:   JSON.stringify(body),
    })
    saveTokens(data.access_token, data.refresh_token, data.user)
    return data
  },

  async logout() {
    const refresh = localStorage.getItem('dd_refresh')
    if (refresh) {
      await apiFetch('/auth/logout', {
        method: 'POST',
        body:   JSON.stringify({ refresh_token: refresh }),
      }).catch(() => {})
    }
    clearTokens()
  },

  async me() {
    return apiFetch('/auth/me')
  },

  async updateMe(data) {
    const res = await apiFetch('/auth/me', {
      method: 'PATCH',
      body:   JSON.stringify(data),
    })
    if (res.user) {
      // Access/Refresh tokens remain same, just update user
      saveTokens(localStorage.getItem('dd_token'), localStorage.getItem('dd_refresh'), res.user)
    }
    return res
  },

  async changePassword({ old_password, new_password }) {
    return apiFetch('/auth/me/password', {
      method: 'PATCH',
      body:   JSON.stringify({ old_password, new_password }),
    })
  },

  async forgotPassword(email) {
    return apiFetch('/auth/forgot-password', {
      method: 'POST',
      body:   JSON.stringify({ email }),
    })
  },

  async resetPassword(token, new_password) {
    return apiFetch('/auth/reset-password', {
      method: 'POST',
      body:   JSON.stringify({ token, new_password }),
    })
  },
}

// ── Products ──────────────────────────────────────────────────────────────────

export const products = {
  /**
   * List all tracked products with optional filters.
   * @param {Object} opts - { category, search, page, limit, sort, order }
   */
  async list(opts = {}) {
    const params = new URLSearchParams()
    if (opts.category) params.set('category', opts.category)
    if (opts.search)   params.set('search',   opts.search)
    if (opts.page)     params.set('page',      opts.page)
    if (opts.limit)    params.set('limit',     opts.limit)
    if (opts.sort)     params.set('sort',      opts.sort)
    if (opts.order)    params.set('order',     opts.order)
    return apiFetch(`/products?${params}`)
  },

  /**
   * Add a product URL to track. Triggers immediate scrape.
   * @param {string} url      - Amazon.in / Flipkart / etc. product URL
   * @param {string} retailer - "Amazon.in" | "Flipkart" | "Myntra" | ...
   */
  async track(url, retailer) {
    return apiFetch('/products/track', {
      method: 'POST',
      body:   JSON.stringify({ url, retailer }),
    })
  },

  /**
   * Live search across all retailers via Playwright scraping.
   * @param {string}   query    - product name or keyword
   * @param {string[]} retailers - optional retailer filter
   */
  async search(query, retailers = null, category = null) {
    return apiFetch('/products/search', {
      method: 'POST',
      body:   JSON.stringify({ query, retailers, category }),
    })
  },

  /** Public search - no login req */
  async publicSearch(query, retailers = null, category = null) {
    return apiFetch('/products/public-search', {
      method:  'POST',
      body:   JSON.stringify({ query, retailers, category }),
    })
  },

  /** Compare search - uses /api/v1/compare/search unified endpoint */
  async compareSearch(query, { signal } = {}) {
    return apiFetch('/compare/search', {
      method: 'POST',
      body: JSON.stringify({ query }),
      signal
    })
  },

  /** Extract title from URL */
  async extractUrl(url) {
    return apiFetch('/compare/extract-url', {
      method: 'POST',
      body: JSON.stringify({ url })
    })
  },

  /** Compare by exact URL */
  async compareUrl(url, { signal } = {}) {
    return apiFetch('/compare/url', {
      method: 'POST',
      body: JSON.stringify({ url }),
      signal
    })
  },

  /** Accurate Search - uses /api/search unified endpoint */
  async accurateSearch(query, { signal } = {}) {
    const normalize = (data) => {
      if (Array.isArray(data)) {
        return { results: data, retailers_scanned: data.length, query }
      }
      return {
        results:           data.results           || [],
        retailers_scanned: data.retailers_scanned || 0,
        query:             data.query             || query,
        diagnosis:         data.diagnosis || data.message || null,
        category:          data.category,
        identity:          data.identity,
        message:           data.message,
      }
    }

    let primaryDiagnosis = null

    try {
      console.log('[api.accurateSearch] request start', { query })
      const res = await fetchWithBackendGuard(`/api/search?q=${encodeURIComponent(query)}`, { signal })
      console.log('[api.accurateSearch] response received', { ok: res.ok, status: res.status })
      if (!res.ok) throw new Error(`Search error ${res.status}`)
      const data = await res.json()
      console.log('[api.accurateSearch] parsed response', {
        resultCount: Array.isArray(data?.results) ? data.results.length : (Array.isArray(data) ? data.length : 0),
        keys: data && !Array.isArray(data) ? Object.keys(data) : [],
      })
      const normalized = normalize(data)
      primaryDiagnosis = normalized.diagnosis || null
      if (normalized.results.length > 0) return normalized
    } catch (err) {
      console.error('[accurateSearch] Fetch error:', err)
      if (isNetworkFailure(err) || isBackendOffline()) {
        return { results: [], retailers_scanned: 0, query, diagnosis: primaryDiagnosis }
      }
    }

    if (isBackendOffline()) {
      return { results: [], retailers_scanned: 0, query, diagnosis: primaryDiagnosis }
    }

    try {
      const fallback = await apiFetch('/products/public-search', {
        method: 'POST',
        body: JSON.stringify({ query, retailers: null, category: null }),
      })
      const normalizedFallback = normalize(fallback)
      if (normalizedFallback.results.length > 0) return normalizedFallback
      return {
        ...normalizedFallback,
        diagnosis: normalizedFallback.diagnosis || primaryDiagnosis || null,
      }
    } catch (err) {
      console.error('[accurateSearch] Public fallback failed:', err)
      return { results: [], retailers_scanned: 0, query, diagnosis: primaryDiagnosis }
    }
  },

  async get(id, { signal } = {}) {
    if (id && String(id).startsWith('search_')) {
      return { id, retailers: [], name: '', brand: '', image_url: null }
    }
    return apiFetch(`/products/${id}`, { signal })
  },

  /**
   * Get price history for Chart.js rendering.
   * @param {number} id      - product ID
   * @param {number} days    - 7 | 30 | 90 | 365
   * @param {string} retailer - optional retailer filter
   */
  /**
   * Get price history for Chart.js rendering.
   * Uses the /api/price-history endpoint (not authenticated, proxied via Vite).
   */
  async priceHistory(id, days = 90, { signal } = {}) {
    // Skip API call for mock search result IDs
    if (id && id.startsWith('search_')) {
      throw new Error('Mock product ID - using demo data')
    }
    
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 20000)
    const onAbort = () => controller.abort()
    if (signal) signal.addEventListener('abort', onAbort, { once: true })

    const normalizePriceHistory = (data) => {
      if (data && Array.isArray(data.aggregated) && data.retailers && typeof data.retailers === 'object') {
        return {
          aggregated: data.aggregated,
          retailers: data.retailers,
        }
      }

      if (Array.isArray(data?.data)) {
        const aggregatedMap = new Map()
        const retailers = {}

        data.data.forEach(point => {
          if (!point || !point.recorded_at) return
          const date = String(point.recorded_at).slice(0, 10)
          const price = Number(point.price)
          if (!Number.isFinite(price)) return
          aggregatedMap.set(date, aggregatedMap.has(date) ? Math.min(aggregatedMap.get(date), price) : price)
          const retailer = point.retailer || 'Unknown'
          if (!retailers[retailer]) retailers[retailer] = []
          retailers[retailer].push({ date, price })
        })

        return {
          aggregated: Array.from(aggregatedMap.entries())
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([date, price]) => ({ date, price })),
          retailers,
        }
      }

      return {
        aggregated: [],
        retailers: {},
      }
    }

    try {
      console.log('[api.priceHistory] request start', { id, days })
      const res = await fetchWithBackendGuard(`${BASE.replace('/api/v1', '')}/api/price-history?product_id=${id}&days=${days}`, {
        signal: controller.signal,
      })
      console.log('[api.priceHistory] response received', { ok: res.ok, status: res.status })
      if (!res.ok) throw new Error('Price history unavailable')
      const data = await res.json()
      console.log('[api.priceHistory] parsed response', {
        aggregated: Array.isArray(data.aggregated) ? data.aggregated.length : null,
        retailerKeys: data.retailers ? Object.keys(data.retailers).length : 0,
      })
      return normalizePriceHistory(data)
    } finally {
      clearTimeout(timeoutId)
      if (signal) signal.removeEventListener('abort', onAbort)
    }
  },

  async imageSearch(file) {
    const token = getToken()
    const formData = new FormData()
    formData.append('image', file)

    const res = await fetch(`${BASE}/products/image-search`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })

    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(data.detail || data.message || `API error ${res.status}`)
    }

    return data
  },

  async recommendation(id) {
    if (id && String(id).startsWith('search_')) {
      return {
        verdict: 'NEUTRAL',
        confidence: null,
        reasoning: 'AI analysis will be available after this search result is saved as a tracked product.',
        method: 'search_result_fallback',
        insights: {
          price_comparison: 'Current search result',
          trend_analysis: 'Live trend data pending',
          smart_recommendation: 'Monitor for price changes',
          suggested_alert_price: null,
        }
      }
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 20000)
    try {
      console.log('[api.recommendation] request start', { id })
      const res = await fetchWithBackendGuard(`${BASE.replace('/api/v1', '')}/api/recommendation?product_id=${id}`, {
        signal: controller.signal,
      })
      console.log('[api.recommendation] response received', { ok: res.ok, status: res.status })
      if (!res.ok) throw new Error('Recommendation load failed')
      const data = await res.json()
      console.log('[api.recommendation] parsed response', {
        verdict: data?.verdict,
        method: data?.method,
        confidence: data?.confidence,
      })
      return data
    } catch (err) {
      console.warn('[api.recommendation] error:', err)
      // Return fallback recommendation on error
      return {
        verdict: 'NEUTRAL',
        confidence: null,
        reasoning: 'AI analysis is temporarily unavailable. Please check back later.',
        method: 'fallback_error',
        insights: {
          price_comparison: 'Current price unavailable',
          trend_analysis: 'Trend data pending',
          smart_recommendation: 'Monitor for price changes',
          suggested_alert_price: null,
        }
      }
    } finally {
      clearTimeout(timeoutId)
    }
  },

  /** Get latest ML prediction for a product */
  async getPrediction(id) {
    // Skip API call for mock search result IDs
    if (id && id.startsWith('search_')) {
      throw new Error('Mock product ID - using demo data')
    }
    return apiFetch(`/products/${id}/prediction`)
  },

  /** Trigger a fresh ML prediction in the background */
  async triggerPrediction(id) {
    // Skip API call for mock search result IDs
    if (id && id.startsWith('search_')) {
      throw new Error('Mock product ID - using demo data')
    }
    return apiFetch(`/products/${id}/predict`, { method: 'POST' })
  },

  /** Get AI price recommendation for a product */
  async getRecommendation(product_id) {
    // Skip API call for mock search result IDs
    if (product_id && product_id.startsWith('search_')) {
      throw new Error('Mock product ID - using demo data')
    }
    return apiFetch(`/ai/recommendation?product_id=${product_id}`)
  },

  /** Get recently tracked products with highest drops for landing/discover pages */
  async publicRecent() {
    return apiFetch('/products/public-recent')
  },

  /** Get trending products for landing/discover pages */
  async publicTrending() {
    return apiFetch('/products/public-trending')
  },

  /** Autocomplete suggestions from existing database */
  async suggestions(q) {
    return apiFetch(`/products/suggestions?q=${encodeURIComponent(q)}`)
  },
}

// ── Watchlist ─────────────────────────────────────────────────────────────────

export const watchlist = {
  async get() {
    return apiFetch('/watchlist')
  },

  async add(product_id) {
    return apiFetch('/watchlist', {
      method: 'POST',
      body:   JSON.stringify({ product_id }),
    })
  },

  async remove(product_id) {
    return apiFetch(`/watchlist/${product_id}`, { method: 'DELETE' })
  },
}

// ── Price Alerts ──────────────────────────────────────────────────────────────

export const alerts = {
  async list() {
    return apiFetch('/alerts')
  },

  /**
   * Create a price alert.
   * @param {Object} opts - { product_id, target_price, threshold_pct?, retailer? }
   */
  async create({ product_id, target_price, threshold_pct, retailer }) {
    return apiFetch('/alerts', {
      method: 'POST',
      body:   JSON.stringify({ product_id, target_price, threshold_pct, retailer }),
    })
  },

  async delete(alert_id) {
    return apiFetch(`/alerts/${alert_id}`, { method: 'DELETE' })
  },

  async toggle(alert_id) {
    return apiFetch(`/alerts/${alert_id}/toggle`, { method: 'PATCH' })
  },
}

// ── AI Price Intelligence ─────────────────────────────────────────────────────

export const ai = {
  /**
   * Ask the AI a question grounded in live product data.
   * @param {string} product_context - from buildProductContext()
   * @param {string} question        - user's question
   * @returns {Promise<{answer: string, timestamp: string}>}
   */
  async ask(product_context, question) {
    return apiFetch('/ai/ask', {
      method: 'POST',
      body:   JSON.stringify({ product_context, question }),
    })
  },

  async status() {
    return apiFetch('/ai/status')
  },

  async analyze(product_name, price, min_price, max_price) {
    return apiFetch('/ai/analyze', {
      method: 'POST',
      body: JSON.stringify({ product_name, price, min_price, max_price }),
    })
  },
}

export const simple_alerts = {
  async create(email, product, target_price) {
    return apiFetch('/alerts', {
      method: 'POST',
      body: JSON.stringify({ email, product, target_price })
    })
  }
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export const admin = {
  async stats() {
    return apiFetch('/admin/stats')
  },

  async trigger(job) {
    return apiFetch('/admin/trigger', {
      method: 'POST',
      body:   JSON.stringify({ job }),
    })
  },

  async listUsers() {
    return apiFetch('/admin/users')
  },

  async toggleUser(user_id) {
    return apiFetch(`/admin/users/${user_id}/toggle`, { method: 'PATCH' })
  },
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function healthCheck() {
  const res = await fetch(`${BASE.replace('/api/v1', '')}/api/health`)
  return res.json()
}

// ── Polling helper ────────────────────────────────────────────────────────────

/**
 * Poll an endpoint until a condition is met or timeout.
 * Used to wait for background scrape/prediction tasks.
 *
 * @param {Function} fn         - async function to call
 * @param {Function} isDone     - predicate on the result
 * @param {number}   intervalMs - polling interval
 * @param {number}   timeoutMs  - max wait
 */
export async function pollUntil(fn, isDone, intervalMs = 2000, timeoutMs = 30000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    const result = await fn()
    if (isDone(result)) return result
    await new Promise(r => setTimeout(r, intervalMs))
  }
  throw new Error('Poll timeout')
}

// ── Price formatters ──────────────────────────────────────────────────────────

export function formatPrice(n) {
  if (n === null || n === undefined) return 'Not Available'
  if (Number(n) === 0) return '₹0'
  return '₹' + Number(n).toLocaleString('en-IN')
}


export function formatDiscount(n) {
  if (!n) return null
  return `-${Math.round(n)}%`
}

export function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

export function formatDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60000)
  if (mins < 1)   return 'just now'
  if (mins < 60)  return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
