/**
 * aiSentinelService.js — Standalone service for AI Price Sentinel predictions
 * 
 * SECURITY FIX: All Gemini API calls now go through the backend.
 * No API keys are stored or used in the frontend.
 */

import { apiFetch } from './api'

/**
 * Generates AI Price Sentinel prediction via backend endpoint
 * @param {Array<{date: string, price: number}>} priceHistory - Historical price data array
 * @param {string} productName - Name of the product/asset
 * @param {number} period - Number of days of historical data provided
 * @returns {Promise<Object>} AI prediction object or error object
 */
export async function getPricePrediction(priceHistory, productName, period = 30) {
  if (!Array.isArray(priceHistory) || priceHistory.length === 0) {
    return {
      error: true,
      message: 'Invalid price history data provided'
    }
  }

  if (!productName || typeof productName !== 'string') {
    return {
      error: true,
      message: 'Invalid product name provided'
    }
  }

  try {
    // Call the backend /api/v1/ai/predict endpoint (Gemini stays server-side)
    const currentPrice = priceHistory[priceHistory.length - 1]?.price || 0
    const prediction = await apiFetch('/ai/predict', {
      method: 'POST',
      body: JSON.stringify({
        product_name: productName,
        current_price: currentPrice,
        price_history: priceHistory.map(p => ({ date: p.date, price: p.price })),
        period,
        category: 'General',
      }),
    })

    // Validate required fields
    const requiredFields = ['trend', 'trendStrength', 'supportLevel', 'resistanceLevel', 'predictedPrices', 'summary', 'riskLevel', 'keyInsights']
    const missingFields = requiredFields.filter(field => !(field in prediction))

    if (missingFields.length > 0) {
      console.warn('Backend AI response missing fields:', missingFields)
      // Still return what we got — backend may have returned a partial fallback
      return {
        ...prediction,
        // Fill in missing fields with defaults
        trend: prediction.trend || 'sideways',
        trendStrength: prediction.trendStrength || 'moderate',
        supportLevel: prediction.supportLevel || Math.min(...priceHistory.map(p => p.price)),
        resistanceLevel: prediction.resistanceLevel || Math.max(...priceHistory.map(p => p.price)),
        predictedPrices: prediction.predictedPrices || [],
        summary: prediction.summary || 'Analysis in progress.',
        riskLevel: prediction.riskLevel || 'medium',
        keyInsights: prediction.keyInsights || [],
      }
    }

    return prediction

  } catch (error) {
    console.warn('[aiSentinelService] Backend prediction failed, using local fallback:', error.message)
    // Fall back to local calculation if backend is unavailable
    return generateFallbackPrediction(priceHistory)
  }
}

/**
 * Generates a simple fallback prediction based on price history trend
 * Used when backend AI endpoint is unavailable
 * @param {Array<{date: string, price: number}>} priceHistory - Historical price data
 * @returns {Object} Simple fallback prediction
 */
export function generateFallbackPrediction(priceHistory) {
  if (!Array.isArray(priceHistory) || priceHistory.length < 2) {
    return {
      error: true,
      message: 'Insufficient data for prediction'
    }
  }

  const prices = priceHistory.map(p => p.price)
  const currentPrice = prices[prices.length - 1]
  const oldestPrice = prices[0]
  
  // Calculate simple trend
  const priceChange = ((currentPrice - oldestPrice) / oldestPrice) * 100
  const trend = priceChange > 5 ? 'bullish' : priceChange < -5 ? 'bearish' : 'sideways'
  const trendStrength = Math.abs(priceChange) > 15 ? 'strong' : Math.abs(priceChange) > 8 ? 'moderate' : 'weak'
  
  // Calculate support and resistance (simple min/max)
  const supportLevel = Math.min(...prices)
  const resistanceLevel = Math.max(...prices)
  
  // Generate simple predicted prices for next 7 days
  const dailyChange = priceChange / priceHistory.length
  const predictedPrices = []
  const today = new Date()
  
  for (let i = 1; i <= 7; i++) {
    const futureDate = new Date(today)
    futureDate.setDate(today.getDate() + i)
    const predictedPrice = currentPrice * (1 + (dailyChange * i / 100))
    
    predictedPrices.push({
      date: futureDate.toISOString().split('T')[0],
      price: Number(predictedPrice.toFixed(2)),
      confidence: trendStrength === 'strong' ? 'medium' : 'low'
    })
  }

  return {
    trend,
    trendStrength,
    supportLevel: Number(supportLevel.toFixed(2)),
    resistanceLevel: Number(resistanceLevel.toFixed(2)),
    predictedPrices,
    summary: `Based on ${priceHistory.length} days of data, the price trend is ${trend} with ${trendStrength} momentum.`,
    riskLevel: trendStrength === 'strong' ? 'high' : 'medium',
    keyInsights: [
      `Price has ${priceChange > 0 ? 'increased' : 'decreased'} by ${Math.abs(priceChange).toFixed(1)}% over the period`,
      `Current support level: ${supportLevel.toFixed(2)}`,
      `Current resistance level: ${resistanceLevel.toFixed(2)}`
    ],
    isFallback: true
  }
}
