/**
 * PriceChart.jsx — Self-contained price history and prediction chart component
 * 
 * Uses Recharts to display historical prices and AI predictions.
 * Fully responsive and follows existing DeltaDrop styling patterns.
 */

import React from 'react'
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'

/**
 * Custom tooltip for the price chart
 */
const CustomTooltip = ({ active, payload, currency = 'USD' }) => {
  if (active && payload && payload.length) {
    const data = payload[0]
    const isPredicted = data.dataKey === 'predictedPrice'
    
    return (
      <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {data.payload.date}
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {isPredicted ? 'Predicted' : 'Historical'}: {currency === 'inr' ? '₹' : currency === 'eur' ? '€' : '$'}{data.value?.toLocaleString()}
        </p>
        {data.payload.confidence && (
          <p className="text-xs text-gray-500 dark:text-gray-500">
            Confidence: {data.payload.confidence}
          </p>
        )}
      </div>
    )
  }
  return null
}

/**
 * Custom formatter for Y-axis to show currency symbols
 */
const formatYAxis = (value, currency = 'USD') => {
  const symbol = currency === 'inr' ? '₹' : currency === 'eur' ? '€' : '$'
  return `${symbol}${value.toLocaleString()}`
}

/**
 * Custom formatter for X-axis to show formatted dates
 */
const formatXAxis = (value) => {
  if (!value) return ''
  const date = new Date(value)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function PriceChart({ 
  historicalData = [], 
  predictedData = [], 
  coinName = '', 
  currency = 'USD',
  className = ''
}) {
  // Combine historical and predicted data
  const allData = React.useMemo(() => {
    const combined = []
    
    // Add historical data
    historicalData.forEach(item => {
      combined.push({
        date: item.date,
        price: item.price,
        historicalPrice: item.price,
        type: 'historical'
      })
    })
    
    // Add predicted data
    predictedData.forEach(item => {
      combined.push({
        date: item.date,
        predictedPrice: item.price,
        confidence: item.confidence,
        type: 'predicted'
      })
    })
    
    // Sort by date
    return combined.sort((a, b) => new Date(a.date) - new Date(b.date))
  }, [historicalData, predictedData])

  // Find today's date to add reference line
  const today = new Date().toISOString().split('T')[0]
  const todayIndex = allData.findIndex(item => item.date === today)
  
  // Calculate Y-axis domain with some padding
  const allPrices = allData.flatMap(item => 
    item.price ? [item.price] : item.predictedPrice ? [item.predictedPrice] : []
  )
  
  const minPrice = allPrices.length > 0 ? Math.min(...allPrices) : 0
  const maxPrice = allPrices.length > 0 ? Math.max(...allPrices) : 100
  const padding = (maxPrice - minPrice) * 0.1

  if (allData.length === 0) {
    return (
      <div className={`flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
        <p className="text-gray-500 dark:text-gray-400">No price data available</p>
      </div>
    )
  }

  return (
    <div className={`w-full ${className}`}>
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart
          data={allData}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 60
          }}
        >
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="#e5e7eb" 
            className="dark:stroke-gray-600"
          />
          
          <XAxis
            dataKey="date"
            tickFormatter={formatXAxis}
            angle={-45}
            textAnchor="end"
            height={60}
            tick={{ fontSize: 12, fill: '#6b7280' }}
            className="dark:fill-gray-400"
          />
          
          <YAxis
            tickFormatter={(value) => formatYAxis(value, currency)}
            tick={{ fontSize: 12, fill: '#6b7280' }}
            className="dark:fill-gray-400"
            domain={[minPrice - padding, maxPrice + padding]}
          />
          
          <Tooltip content={<CustomTooltip currency={currency} />} />
          
          <Legend 
            verticalAlign="bottom" 
            height={36}
            iconType="line"
            wrapperStyle={{ paddingTop: '20px' }}
          />
          
          {/* Reference line for "Today" if we have data around today */}
          {todayIndex >= 0 && (
            <ReferenceLine
              x={today}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label="Today"
            />
          )}
          
          {/* Historical prices as solid blue area */}
          <Area
            type="monotone"
            dataKey="historicalPrice"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.3}
            strokeWidth={2}
            name="Historical Price"
            connectNulls={false}
          />
          
          {/* Predicted prices as dashed orange line */}
          <Line
            type="monotone"
            dataKey="predictedPrice"
            stroke="#f97316"
            strokeWidth={2}
            strokeDasharray="5 5"
            name="Predicted Price"
            dot={{ fill: '#f97316', r: 4 }}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      
      {/* Chart footer */}
      <div className="mt-4 text-center">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {coinName && `${coinName} • `}
          {historicalData.length} historical points • {predictedData.length} predicted points
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
          Historical data: Solid blue area | Predictions: Dashed orange line
        </p>
      </div>
    </div>
  )
}
