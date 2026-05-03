/**
 * AIPredictionBadge.jsx — Small badge/card component for AI predictions
 * 
 * Displays trend direction, risk level, support/resistance levels, and insights.
 * Follows existing DeltaDrop component styling patterns.
 */

import React from 'react'

/**
 * Trend icon component
 */
const TrendIcon = ({ trend, className = '' }) => {
  const iconClass = `w-5 h-5 ${className}`
  
  if (trend === 'bullish') {
    return (
      <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    )
  }
  
  if (trend === 'bearish') {
    return (
      <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
      </svg>
    )
  }
  
  // sideways
  return (
    <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
    </svg>
  )
}

/**
 * Risk level badge component
 */
const RiskBadge = ({ riskLevel }) => {
  const colors = {
    low: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    high: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
  }
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[riskLevel] || colors.medium}`}>
      {riskLevel?.toUpperCase() || 'MEDIUM'} RISK
    </span>
  )
}

/**
 * Trend strength badge component
 */
const TrendStrengthBadge = ({ strength }) => {
  const colors = {
    weak: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    moderate: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    strong: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
  }
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[strength] || colors.moderate}`}>
      {strength?.toUpperCase() || 'MODERATE'} TREND
    </span>
  )
}

export default function AIPredictionBadge({ prediction, className = '' }) {
  if (!prediction) {
    return (
      <div className={`bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 ${className}`}>
        <p className="text-gray-500 dark:text-gray-400 text-center">No prediction data available</p>
      </div>
    )
  }

  if (prediction.error) {
    return (
      <div className={`bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800 ${className}`}>
        <div className="flex items-center space-x-2 mb-2">
          <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">AI Prediction Unavailable</h3>
        </div>
        <p className="text-sm text-yellow-700 dark:text-yellow-300">{prediction.message}</p>
        {prediction.summary && (
          <div className="mt-2 p-2 bg-yellow-100 dark:bg-yellow-900/40 rounded">
            <p className="text-xs text-yellow-800 dark:text-yellow-200">{prediction.summary}</p>
          </div>
        )}
        {prediction.isFallback && (
          <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-2 italic">
            Showing fallback analysis based on price trends
          </p>
        )}
      </div>
    )
  }

  const trendColors = {
    bullish: 'text-green-600 dark:text-green-400',
    bearish: 'text-red-600 dark:text-red-400',
    sideways: 'text-gray-600 dark:text-gray-400'
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 shadow-sm ${className}`}>
      {/* Header with trend and risk */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`flex items-center space-x-1 ${trendColors[prediction.trend]}`}>
            <TrendIcon trend={prediction.trend} />
            <span className="font-semibold capitalize">{prediction.trend}</span>
          </div>
          <TrendStrengthBadge strength={prediction.trendStrength} />
        </div>
        <RiskBadge riskLevel={prediction.riskLevel} />
      </div>

      {/* Support and Resistance Levels */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
          <p className="text-xs text-green-600 dark:text-green-400 font-medium">Support Level</p>
          <p className="text-lg font-bold text-green-800 dark:text-green-200">
            ${prediction.supportLevel?.toLocaleString()}
          </p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
          <p className="text-xs text-red-600 dark:text-red-400 font-medium">Resistance Level</p>
          <p className="text-lg font-bold text-red-800 dark:text-red-200">
            ${prediction.resistanceLevel?.toLocaleString()}
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">AI Analysis</h4>
        <p className="text-sm text-gray-600 dark:text-gray-400">{prediction.summary}</p>
      </div>

      {/* Key Insights */}
      {prediction.keyInsights && prediction.keyInsights.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Key Insights</h4>
          <ul className="space-y-1">
            {prediction.keyInsights.map((insight, index) => (
              <li key={index} className="text-sm text-gray-600 dark:text-gray-400 flex items-start">
                <span className="text-blue-500 dark:text-blue-400 mr-2">•</span>
                {insight}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Predicted Prices Summary */}
      {prediction.predictedPrices && prediction.predictedPrices.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">7-Day Forecast</h4>
          <div className="grid grid-cols-3 gap-2 text-xs">
            {prediction.predictedPrices.slice(0, 3).map((pred, index) => (
              <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded p-2 text-center">
                <p className="text-gray-500 dark:text-gray-400">{new Date(pred.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</p>
                <p className="font-semibold text-gray-900 dark:text-gray-100">${pred.price?.toLocaleString()}</p>
                <p className="text-gray-500 dark:text-gray-400">{pred.confidence}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mt-4">
        <p className="text-xs text-gray-500 dark:text-gray-400 italic">
          AI predictions are speculative. Not financial advice.
        </p>
        {prediction.isFallback && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            This is a fallback analysis based on historical price trends.
          </p>
        )}
      </div>
    </div>
  )
}
