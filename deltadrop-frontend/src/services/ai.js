/**
 * ai.js — DeltaDrop AI Price Intelligence Service
 *
 * Builds a structured product context block from live product data
 * and sends it to the backend /api/v1/ai/ask endpoint.
 * The backend calls Gemini with the DeltaDrop system prompt.
 */

import { apiFetch } from './api'

// ── Context builder ──────────────────────────────────────────────────────────

/**
 * Builds a rich, structured context block from a product object.
 * This is what gets injected into the Claude prompt alongside the user's question.
 *
 * @param {Object} product   — product from mockData.js or API
 * @param {Array}  history   — [{date, price}] price history points
 * @returns {string}         — formatted context block
 */
export function buildProductContext(product, history = []) {
  if (!product) return ''

  // Compute price analytics
  const prices    = product.retailers.map(r => r.price || r.current_price).filter(Boolean)
  const bestRetailer = product.retailers.reduce((best, r) => {
    const p = parsePrice(r.price || r.current_price)
    const b = parsePrice(best?.price || best?.current_price)
    return (!b || (p && p < b)) ? r : best
  }, product.retailers[0])

  const currentPrice  = parsePrice(product.price || product.best_price)
  const mrp           = parsePrice(product.mrp)
  const discountPct   = mrp && currentPrice ? (((mrp - currentPrice) / mrp) * 100).toFixed(1) : null
  const allTimeLow    = history.length > 0 ? Math.min(...history.map(h => h.price)) : null
  const allTimeHigh   = history.length > 0 ? Math.max(...history.map(h => h.price)) : null
  const pctFromATL    = allTimeLow && currentPrice
    ? (((currentPrice - allTimeLow) / allTimeLow) * 100).toFixed(1)
    : null

  // Trend: compare current price to 30-day-ago price
  const thirtyDaysAgo = history.length >= 5
    ? history[Math.max(0, history.length - 30)]?.price
    : null
  const trendPct = thirtyDaysAgo && currentPrice
    ? (((currentPrice - thirtyDaysAgo) / thirtyDaysAgo) * 100).toFixed(1)
    : null

  // AI Verdict from product data
  const verdict = product.aiVerdict || product.ai_verdict || 'UNKNOWN'

  return `=== DELTADROP PRODUCT DATA ===

PRODUCT: ${product.name}
CATEGORY: ${product.category}
BRAND: ${product.brand || 'Unknown'}
SPECS: ${product.spec || product.specs || 'N/A'}

--- PRICING ---
Current Best Price: ₹${currentPrice?.toLocaleString('en-IN') || 'N/A'}
MRP: ₹${mrp?.toLocaleString('en-IN') || 'N/A'}
Discount from MRP: ${discountPct ? discountPct + '%' : 'N/A'}
Best Retailer: ${bestRetailer?.name || bestRetailer?.retailer || 'N/A'}

--- RETAILER COMPARISON ---
${product.retailers.map(r => {
  const p  = parsePrice(r.price || r.current_price)
  const nm = r.name || r.retailer
  const stk = r.in_stock !== false ? 'In Stock' : 'Out of Stock'
  return `  ${nm}: ₹${p?.toLocaleString('en-IN') || 'N/A'} [${stk}]`
}).join('\n')}

--- PRICE HISTORY (last 90 days) ---
${allTimeLow    ? `All-Time Low: ₹${allTimeLow.toLocaleString('en-IN')}` : 'All-Time Low: Insufficient data'}
${allTimeHigh   ? `All-Time High: ₹${allTimeHigh.toLocaleString('en-IN')}` : ''}
${pctFromATL    ? `Current Price vs ATL: +${pctFromATL}% above all-time low` : ''}
${trendPct      ? `30-Day Trend: ${Number(trendPct) > 0 ? '+' : ''}${trendPct}% (${Number(trendPct) < 0 ? 'dropping' : 'rising'})` : '30-Day Trend: Insufficient data'}
${history.length > 0 ? `Data Points: ${history.length} price records` : 'No historical data available'}

--- ML PREDICTION ---
${product.aiScore        ? `AI Confidence Score: ${product.aiScore}%` : ''}
${verdict !== 'UNKNOWN'  ? `Current Verdict: ${verdict}` : ''}
${product.projSaving     ? `Projected Savings: ${product.projSaving}` : ''}
${product.aiDesc         ? `Model Reasoning: ${product.aiDesc}` : ''}
${product.target         ? `Target Price Signal: ${product.target}` : ''}

=== END PRODUCT DATA ===`
}


/**
 * Builds context from raw search results (multiple products across retailers)
 */
export function buildSearchContext(query, results = []) {
  if (!results.length) return `Search query: "${query}" — No results found.`

  const sorted = [...results].sort((a, b) => (a.current_price || 0) - (b.current_price || 0))

  return `=== DELTADROP SEARCH RESULTS ===

SEARCH QUERY: "${query}"
RESULTS FOUND: ${results.length} across ${new Set(results.map(r => r.retailer)).size} retailers

--- RETAILER PRICES (sorted lowest to highest) ---
${sorted.map((r, i) => `  ${i + 1}. ${r.retailer}: ₹${Number(r.current_price).toLocaleString('en-IN')}${r.mrp ? ` (MRP ₹${Number(r.mrp).toLocaleString('en-IN')})` : ''}${r.discount_pct ? ` — ${Number(r.discount_pct).toFixed(0)}% off` : ''} ${r.in_stock ? '[In Stock]' : '[Out of Stock]'}`).join('\n')}

PRICE SPREAD: ₹${Math.min(...results.map(r => r.current_price || 0)).toLocaleString('en-IN')} – ₹${Math.max(...results.map(r => r.current_price || 0)).toLocaleString('en-IN')}
BEST DEAL: ${sorted[0]?.retailer} at ₹${Number(sorted[0]?.current_price).toLocaleString('en-IN')}

=== END SEARCH DATA ===`
}


// ── API call ─────────────────────────────────────────────────────────────────

/**
 * Ask the DeltaDrop AI a question grounded in product context.
 *
 * @param {string} productContext — from buildProductContext()
 * @param {string} question       — user's free-text question
 * @returns {Promise<string>}     — AI answer text
 */
export async function askDeltaDropAI(productContext, question) {
  const data = await apiFetch('/ai/ask', {
    method: 'POST',
    body: JSON.stringify({
      product_context: productContext,
      question,
    }),
  })
  return data.answer
}


// ── Suggested questions per context ──────────────────────────────────────────

export function getSuggestedQuestions(product) {
  if (!product) return []
  const name = product.name || 'this product'
  return [
    `Should I buy ${name} now or wait?`,
    `Is this the lowest price ${name} has ever been?`,
    `Which retailer gives the best deal on ${name}?`,
    `Will the price drop further in the next 2 weeks?`,
    `Is this a good time to buy given the festive season?`,
    `What's the historical price trend for ${name}?`,
  ]
}


// ── Format AI verdict from response text ─────────────────────────────────────

export function parseVerdictFromAnswer(answer) {
  if (!answer) return null
  if (answer.includes('BUY NOW'))  return 'BUY_NOW'
  if (answer.includes('WAIT'))     return 'WAIT'
  if (answer.includes('NEUTRAL'))  return 'NEUTRAL'
  return null
}


// ── Helper ────────────────────────────────────────────────────────────────────

function parsePrice(raw) {
  if (!raw) return null
  if (typeof raw === 'number') return raw
  const cleaned = String(raw).replace(/[^\d.]/g, '').replace(',', '')
  const n = parseFloat(cleaned)
  return isNaN(n) ? null : n
}
