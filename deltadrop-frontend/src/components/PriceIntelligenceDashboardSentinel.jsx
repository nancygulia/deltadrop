/**
 * PriceIntelligenceDashboardSentinel.jsx
 *
 * AI Price Sentinel + Price Trajectory Chart dashboard for DeltaDrop.
 * Works with Indian e-commerce products — no crypto/CoinGecko dependency.
 * Shows realistic price history (past) + AI 7-day forward prediction.
 *
 * Props:
 *   productId    {number|string}  Real DB product ID (or search_ mock)
 *   productName  {string}         Product name for display and AI prompt
 *   currentPrice {number}         Current price in INR
 *   days         {number}         Days of history to show (default 90)
 */

import React, { useState, useEffect, useCallback } from 'react'
import { fetchPriceHistoryWithPrediction, TIME_PERIODS } from '../services/priceService'
import PriceTrajectoryChart from './PriceTrajectoryChart'
import AIPriceSentinel from './AIPriceSentinel'
import { getPricePrediction, generateFallbackPrediction } from '../services/aiSentinelService'

const LoadingSkeleton = () => (
  <div className="animate-pulse space-y-4">
    <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg" />
    <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg" />
  </div>
)

const ErrorComponent = ({ error, onRetry }) => (
  <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800">
    <p className="text-sm text-red-700 dark:text-red-300 mb-3">{error}</p>
    <button onClick={onRetry} className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700">
      Retry
    </button>
  </div>
)

export default function PriceIntelligenceDashboardSentinel({
  productId   = null,
  productName = 'Product',
  currentPrice = 0,
  days: initialDays = 90,
}) {
  const [loading,        setLoading]        = useState(true)
  const [error,          setError]          = useState(null)
  const [historicalData, setHistoricalData] = useState([])
  const [predictedData,  setPredictedData]  = useState([])
  const [aiPrediction,   setAiPrediction]   = useState(null)
  const [selectedDays,   setSelectedDays]   = useState(initialDays)
  const [isSimulated,    setIsSimulated]    = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // ── Step 1: fetch price history (real DB or deterministic simulation) ──
      const {
        historicalData: hist,
        predictedData:  pred,
        simulated,
        trend,
        summary,
      } = await fetchPriceHistoryWithPrediction(productId, productName, currentPrice, selectedDays)

      setHistoricalData(hist)
      setPredictedData(pred)
      setIsSimulated(simulated)

      // ── Step 2: AI Sentinel analysis ──────────────────────────────────────
      let prediction
      if (hist.length > 0) {
        prediction = await getPricePrediction(hist, productName, selectedDays)
        if (prediction?.error) {
          prediction = generateFallbackPrediction(hist)
        }
        // Inject trend from price service if Gemini didn't provide one
        if (!prediction?.trend && trend) prediction = { ...prediction, trend }
        if (!prediction?.summary && summary) prediction = { ...prediction, summary }
      } else {
        prediction = generateFallbackPrediction([{ date: new Date().toISOString().split('T')[0], price: currentPrice }])
      }

      setAiPrediction(prediction)

    } catch (err) {
      console.error('[PriceIntelligenceDashboardSentinel] Error:', err)
      setError(err.message || 'Failed to load price data')
    } finally {
      setLoading(false)
    }
  }, [productId, productName, currentPrice, selectedDays])

  useEffect(() => { fetchData() }, [fetchData])

  if (loading && historicalData.length === 0) {
    return (
      <div className="max-w-5xl mx-auto p-4">
        <LoadingSkeleton />
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            AI Price Sentinel
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {productName}
            {isSimulated && (
              <span className="ml-2 px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 rounded">
                Simulated history
              </span>
            )}
          </p>
        </div>

        {/* Period selector */}
        <div className="flex gap-2 flex-wrap">
          {TIME_PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setSelectedDays(p.value)}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                selectedDays === p.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorComponent error={error} onRetry={fetchData} />}

      {/* Price trajectory chart */}
      {historicalData.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Price History &amp; Prediction
            </h3>
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {historicalData.length} historical &bull; {predictedData.length} predicted
            </span>
          </div>
          <PriceTrajectoryChart
            historicalData={historicalData}
            predictedData={predictedData}
            productName={productName}
            currency="inr"
          />
        </div>
      )}

      {/* AI Sentinel badge */}
      {aiPrediction && (
        <AIPriceSentinel
          prediction={aiPrediction}
          productName={productName}
          currentPrice={currentPrice}
        />
      )}

    </div>
  )
}
