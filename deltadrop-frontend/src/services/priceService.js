/**
 * priceService.js — DeltaDrop Price History Service
 *
 * Fetches price history from the DeltaDrop backend /api/price-history endpoint.
 * Works for ANY product by name or DB ID — no database records required.
 * When no real history exists the backend returns a realistic deterministic
 * simulation based on the product's current price (seeded by product_id so
 * the chart is stable across page reloads).
 *
 * SECURITY FIX: All AI/Gemini predictions are now routed through the backend.
 * No API keys are used in the frontend.
 */

import { apiFetch } from './api'

const BACKEND_BASE = import.meta.env.VITE_API_BASE?.replace('/api/v1', '') || 'http://127.0.0.1:8000'

export async function fetchProductPriceHistory(productId, days = 90) {
  if (!productId || String(productId).startsWith('search_')) {
    throw new Error('No real DB product ID available yet.')
  }
  const url = `${BACKEND_BASE}/api/price-history?product_id=${productId}&days=${days}`
  const res = await fetch(url, { signal: AbortSignal.timeout(15000) })
  if (!res.ok) throw new Error(`Price history API returned ${res.status}`)
  const data = await res.json()
  if (!data.aggregated || data.aggregated.length === 0) throw new Error('No price history returned.')
  return data
}

export async function fetchPriceHistoryWithPrediction(productId, productName, currentPrice, days = 90) {
  let historyData
  try {
    historyData = await fetchProductPriceHistory(productId, days)
  } catch {
    historyData = {
      aggregated: _clientSideSimulation(currentPrice, productName, days),
      retailers:  {},
      simulated:  true,
    }
  }

  const historicalData = historyData.aggregated || []
  let predictedData = []
  let trend = 'sideways'
  let summary = ''

  // Use backend AI prediction endpoint instead of direct Gemini call
  if (historicalData.length >= 7) {
    try {
      const recentSlice = historicalData.slice(-14)
      const prediction = await _callBackendPrediction(recentSlice, productName, currentPrice)
      predictedData = prediction.predictedPrices || []
      trend         = prediction.trend || 'sideways'
      summary       = prediction.summary || ''
    } catch (e) {
      console.warn('[priceService] Backend prediction failed, using math fallback:', e.message)
      predictedData = _mathPrediction(historicalData, 7)
      trend = _detectTrend(historicalData)
    }
  } else {
    predictedData = _mathPrediction(historicalData, 7)
    trend = _detectTrend(historicalData)
  }

  return { historicalData, predictedData, retailers: historyData.retailers || {}, simulated: historyData.simulated || false, trend, summary }
}

function _clientSideSimulation(basePrice, productName, days) {
  let seed = [...productName].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 1) + Math.round(basePrice)
  const rand = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 0x100000000 }
  const startMult = 1.08 + rand() * 0.10
  const events = {}
  for (let i = 0; i < 3; i++) {
    const s = Math.floor(rand() * (days - 6)); const dur = Math.floor(rand() * 4) + 2
    const mult = 0.72 + rand() * 0.20
    for (let d = s; d < Math.min(s + dur, days); d++) events[d] = Math.min(events[d] ?? 1, mult)
  }
  for (let i = 0; i < 2; i++) {
    const s = Math.floor(rand() * (days - 8)); const dur = Math.floor(rand() * 5) + 3
    const mult = 1.05 + rand() * 0.10
    for (let d = s; d < Math.min(s + dur, days); d++) if (!events[d]) events[d] = mult
  }
  const today = new Date(); today.setHours(0, 0, 0, 0)
  return Array.from({ length: days }, (_, i) => {
    const date = new Date(today); date.setDate(date.getDate() - (days - 1 - i))
    const progress = i / Math.max(days - 1, 1)
    let price = basePrice * (startMult + (1.0 - startMult) * progress)
    if (events[i]) price *= events[i]
    price *= 1.0 + (rand() - 0.5) * 0.03
    price = Math.max(basePrice * 0.55, Math.min(basePrice * 2.0, price))
    return { date: date.toISOString().split('T')[0], price: Math.round(price) }
  })
}

function _mathPrediction(history, forecastDays = 7) {
  const n = Math.min(history.length, 14)
  const slice = history.slice(-n)
  const prices = slice.map(p => p.price)
  const mean = prices.reduce((a, b) => a + b, 0) / n
  const slope = prices.reduce((a, p, i) => a + (p - mean) * (i - (n-1)/2), 0) /
                prices.reduce((a, _, i) => a + (i - (n-1)/2)**2, 0)
  const last = prices[prices.length - 1]
  const today = new Date(); today.setHours(0,0,0,0)
  return Array.from({ length: forecastDays }, (_, j) => {
    const date = new Date(today); date.setDate(date.getDate() + j + 1)
    return { date: date.toISOString().split('T')[0], price: Math.max(Math.round(last * 0.7), Math.round(last + slope * (j+1))), confidence: j < 3 ? 'high' : j < 5 ? 'medium' : 'low' }
  })
}

function _detectTrend(history) {
  if (history.length < 7) return 'sideways'
  const first = history[Math.max(0, history.length - 7)].price
  const last  = history[history.length - 1].price
  const diff  = (last - first) / first
  return diff > 0.03 ? 'bullish' : diff < -0.03 ? 'bearish' : 'sideways'
}

/**
 * Calls the backend /api/v1/ai/predict endpoint for secure server-side Gemini prediction.
 * No API keys needed in the frontend.
 */
async function _callBackendPrediction(recentHistory, productName, currentPrice) {
  return apiFetch('/ai/predict', {
    method: 'POST',
    body: JSON.stringify({
      product_name: productName,
      current_price: currentPrice,
      price_history: recentHistory.map(p => ({ date: p.date, price: p.price })),
      period: recentHistory.length,
      category: 'General',
    }),
  })
}

export const TIME_PERIODS = [
  { value: 7,   label: '7 Days'   },
  { value: 30,  label: '30 Days'  },
  { value: 90,  label: '90 Days'  },
  { value: 180, label: '6 Months' },
]
