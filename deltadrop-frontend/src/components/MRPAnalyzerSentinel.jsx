/**
 * MRPAnalyzerSentinel.jsx — Standalone AI-powered MRP analysis component for Indian retail market
 * 
 * Standalone AI-powered MRP analysis form.
 * Data source: Gemini API ONLY.
 * NOT connected to any existing product form, admin panel, or pricing logic.
 */

import React, { useState } from 'react'

/**
 * Loading skeleton component for MRP Analyzer Sentinel
 */
const LoadingSkeleton = () => (
  <div className="animate-pulse space-y-4">
    <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
    <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
    <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
  </div>
)

/**
 * Error component with retry button for MRP Analyzer Sentinel
 */
const ErrorComponent = ({ error, onRetry }) => (
  <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800">
    <div className="flex items-center space-x-2 mb-2">
      <svg className="w-5 h-5 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Analysis Error</h3>
    </div>
    <p className="text-sm text-red-700 dark:text-red-300 mb-3">{error}</p>
    <button
      onClick={onRetry}
      className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
    >
      Retry Analysis
    </button>
  </div>
)

export default function MRPAnalyzerSentinel({ className = '' }) {
  // Form state
  const [formData, setFormData] = useState({
    productName: '',
    category: '',
    costOfProduction: '',
    targetMarket: '',
    brandTier: '',
    keyFeatures: '',
    competitorPrices: ''
  })

  // UI state
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [analysis, setAnalysis] = useState(null)

  // Handle form input changes
  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  // Form validation
  const validateForm = () => {
    const required = ['productName', 'category', 'costOfProduction', 'targetMarket', 'brandTier']
    const missing = required.filter(field => !formData[field].trim())
    
    if (missing.length > 0) {
      setError(`Please fill in: ${missing.join(', ')}`)
      return false
    }
    
    const cost = parseFloat(formData.costOfProduction)
    if (isNaN(cost) || cost <= 0) {
      setError('Please enter a valid cost of production')
      return false
    }
    
    return true
  }

  // Analyze MRP using backend AI endpoint (Gemini stays server-side)
  const analyzeMRP = async () => {
    if (!validateForm()) return

    setLoading(true)
    setError(null)
    setAnalysis(null)

    try {
      const { apiFetch } = await import('../services/api')
      
      const result = await apiFetch('/ai/mrp-analyze', {
        method: 'POST',
        body: JSON.stringify({
          product_name: formData.productName,
          category: formData.category,
          cost_of_production: parseFloat(formData.costOfProduction),
          target_market: formData.targetMarket,
          brand_tier: formData.brandTier,
          key_features: formData.keyFeatures,
          competitor_prices: formData.competitorPrices,
        }),
      })

      setAnalysis(result)

    } catch (err) {
      console.error('MRP Analysis error:', err)
      setError(err.message || 'Analysis service unavailable')
    } finally {
      setLoading(false)
    }
  }

  // Reset form
  const resetForm = () => {
    setFormData({
      productName: '',
      category: '',
      costOfProduction: '',
      targetMarket: '',
      brandTier: '',
      keyFeatures: '',
      competitorPrices: ''
    })
    setAnalysis(null)
    setError(null)
  }

  return (
    <div className={`max-w-4xl mx-auto p-4 space-y-6 ${className}`}>
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          MRP Analyzer for Indian Market
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          AI-powered pricing strategy recommendations for your products
        </p>
      </div>

      {/* Form */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Product Information
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Product Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Product Name *
            </label>
            <input
              type="text"
              value={formData.productName}
              onChange={(e) => handleInputChange('productName', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter product name"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Category *
            </label>
            <select
              value={formData.category}
              onChange={(e) => handleInputChange('category', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select category</option>
              <option value="Electronics">Electronics</option>
              <option value="Clothing">Clothing</option>
              <option value="Food & Beverages">Food & Beverages</option>
              <option value="Home & Kitchen">Home & Kitchen</option>
              <option value="Beauty & Personal Care">Beauty & Personal Care</option>
              <option value="Sports & Fitness">Sports & Fitness</option>
              <option value="Books & Media">Books & Media</option>
              <option value="Toys & Games">Toys & Games</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* Cost of Production */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Cost of Production (₹) *
            </label>
            <input
              type="number"
              value={formData.costOfProduction}
              onChange={(e) => handleInputChange('costOfProduction', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter production cost"
              min="0"
              step="0.01"
            />
          </div>

          {/* Target Market */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Target Market *
            </label>
            <select
              value={formData.targetMarket}
              onChange={(e) => handleInputChange('targetMarket', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select market</option>
              <option value="Premium">Premium</option>
              <option value="Mid-range">Mid-range</option>
              <option value="Budget">Budget</option>
              <option value="Mass Market">Mass Market</option>
              <option value="Niche">Niche</option>
            </select>
          </div>

          {/* Brand Tier */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Brand Tier *
            </label>
            <select
              value={formData.brandTier}
              onChange={(e) => handleInputChange('brandTier', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select brand tier</option>
              <option value="Luxury">Luxury</option>
              <option value="Premium">Premium</option>
              <option value="Established">Established</option>
              <option value="Mid-tier">Mid-tier</option>
              <option value="Budget">Budget</option>
              <option value="New">New</option>
            </select>
          </div>

          {/* Key Features */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Key Features
            </label>
            <input
              type="text"
              value={formData.keyFeatures}
              onChange={(e) => handleInputChange('keyFeatures', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., Organic, Handmade, Premium materials"
            />
          </div>

          {/* Competitor Prices */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Competitor Prices
            </label>
            <textarea
              value={formData.competitorPrices}
              onChange={(e) => handleInputChange('competitorPrices', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., Brand A: ₹999, Brand B: ₹1299, Brand C: ₹799"
              rows={3}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-4 mt-6">
          <button
            onClick={analyzeMRP}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Analyzing...' : 'Analyze MRP'}
          </button>
          <button
            onClick={resetForm}
            disabled={loading}
            className="px-6 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <ErrorComponent error={error} onRetry={analyzeMRP} />
      )}

      {/* Loading State */}
      {loading && !error && (
        <LoadingSkeleton />
      )}

      {/* Analysis Results */}
      {analysis && !error && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Pricing Analysis Results
          </h2>

          {/* MRP Range */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 text-center">
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">Minimum MRP</p>
              <p className="text-2xl font-bold text-green-800 dark:text-green-200">
                ₹{analysis.mrpRange?.min?.toLocaleString()}
              </p>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-center">
              <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">Optimal MRP</p>
              <p className="text-2xl font-bold text-blue-800 dark:text-blue-200">
                ₹{analysis.mrpRange?.optimal?.toLocaleString()}
              </p>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 text-center">
              <p className="text-sm text-purple-600 dark:text-purple-400 font-medium">Maximum MRP</p>
              <p className="text-2xl font-bold text-purple-800 dark:text-purple-200">
                ₹{analysis.mrpRange?.max?.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Analysis Details */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                Pricing Strategy
              </h3>
              <p className="text-gray-600 dark:text-gray-400">{analysis.pricingStrategy}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Gross Margin at Optimal
                </h3>
                <p className="text-gray-600 dark:text-gray-400">{analysis.grossMarginAtOptimal}</p>
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  GST Slab
                </h3>
                <p className="text-gray-600 dark:text-gray-400">{analysis.gstSlab}</p>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                Market Positioning
              </h3>
              <p className="text-gray-600 dark:text-gray-400">{analysis.marketPositioning}</p>
            </div>

            {analysis.implementationTips && analysis.implementationTips.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Implementation Tips
                </h3>
                <ul className="space-y-2">
                  {analysis.implementationTips.map((tip, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-blue-500 dark:text-blue-400 mr-2">•</span>
                      <span className="text-gray-600 dark:text-gray-400">{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Required Disclaimer - Always Visible */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-6">
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">
              MRP recommendations are AI-generated estimates. Verify with market research.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
