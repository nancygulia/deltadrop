/**
 * debugHelper.js - Debug utility to check if fixes are working
 *
 * SECURITY FIX: Removed all VITE_GEMINI_API_KEY references.
 * AI features are now proxied through the backend.
 */

// Check if environment variables are loaded
export function checkEnvironmentVariables() {
  const apiBase = import.meta.env.VITE_API_BASE
  
  console.log('🔍 Environment Variables Check:')
  console.log('VITE_API_BASE:', apiBase ? '✅ Loaded' : '⚠️ Using default')
  
  return {
    apiBase: !!apiBase,
  }
}

// Test AI Price Sentinel service (via backend)
export async function testAIPriceSentinel() {
  console.log('🤖 Testing AI Price Sentinel (via backend)...')
  
  try {
    const { getPricePrediction } = await import('../services/aiSentinelService.js')
    
    // Test with demo data
    const demoData = [
      { date: '2026-04-20', price: 45000 },
      { date: '2026-04-21', price: 45500 },
      { date: '2026-04-22', price: 45200 },
      { date: '2026-04-23', price: 45800 },
      { date: '2026-04-24', price: 46100 }
    ]
    
    const result = await getPricePrediction(demoData, 'Test Product', 5)
    
    console.log('AI Price Sentinel Result:', result)
    
    if (result.error) {
      console.log('❌ AI Price Sentinel failed:', result.message)
    } else {
      console.log('✅ AI Price Sentinel working!')
      console.log('Trend:', result.trend)
      console.log('Predictions:', result.predictedPrices?.length, 'days')
    }
    
    return result
  } catch (error) {
    console.error('❌ AI Price Sentinel test failed:', error)
    return null
  }
}

// Test Price Trajectory Chart service
export async function testPriceTrajectoryChart() {
  console.log('📈 Testing Price Trajectory Chart...')
  
  try {
    const { getPricePrediction } = await import('../services/aiSentinelService.js')
    
    // Test with sample price history data
    const samplePriceHistory = [
      { date: '2024-01-01', price: 1500 },
      { date: '2024-01-02', price: 1450 },
      { date: '2024-01-03', price: 1400 },
      { date: '2024-01-04', price: 1350 },
      { date: '2024-01-05', price: 1299 }
    ]
    
    const result = await getPricePrediction(samplePriceHistory, 'H&M Jeans', 5)
    
    console.log('AI Price Prediction Result:', result)
    
    if (result && (result.predictedPrices || result.trend)) {
      console.log('✅ AI Price Prediction working!')
      console.log('Trend:', result.trend)
      console.log('Predictions:', result.predictedPrices?.length || 0)
    } else {
      console.log('❌ AI Price Prediction failed: No data returned')
    }
    
    return result.predictedPrices || []
  } catch (error) {
    console.error('❌ AI Price Prediction test failed:', error)
    return null
  }
}

// Test price formatting
export function testPriceFormatting() {
  console.log('💰 Testing Price Formatting...')
  
  try {
    const { formatPrice } = require('../services/api.js')
    
    const tests = [
      { input: null, expected: 'Not Available' },
      { input: undefined, expected: 'Not Available' },
      { input: 0, expected: '₹0' },
      { input: 1234.56, expected: '₹1,235' }
    ]
    
    let allPassed = true
    
    tests.forEach(({ input, expected }) => {
      const result = formatPrice(input)
      const passed = result === expected
      console.log(`${passed ? '✅' : '❌'} formatPrice(${input}) = "${result}" (expected: "${expected}")`)
      if (!passed) allPassed = false
    })
    
    console.log(allPassed ? '✅ Price formatting working!' : '❌ Price formatting has issues')
    return allPassed
  } catch (error) {
    console.error('❌ Price formatting test failed:', error)
    return false
  }
}

// Run all diagnostic tests
export async function runDiagnostics() {
  console.log('🚀 Running DeltaDrop Frontend Diagnostics...')
  console.log('=' .repeat(50))
  
  const envCheck = checkEnvironmentVariables()
  const aiTest = await testAIPriceSentinel()
  const chartTest = await testPriceTrajectoryChart()
  const formatTest = testPriceFormatting()
  
  console.log('=' .repeat(50))
  console.log('📊 Diagnostic Summary:')
  console.log('Environment Variables:', envCheck.apiBase ? '✅' : '⚠️')
  console.log('AI Price Sentinel:', aiTest && !aiTest.error ? '✅' : '❌')
  console.log('Price Trajectory Chart:', Array.isArray(chartTest) && chartTest.length > 0 ? '✅' : '❌')
  console.log('Price Formatting:', formatTest ? '✅' : '❌')
  
  return {
    environment: envCheck,
    aiSentinel: aiTest,
    priceChart: chartTest,
    priceFormatting: formatTest
  }
}

// Make it available globally for console debugging
if (typeof window !== 'undefined') {
  window.deltaDropDebug = {
    runDiagnostics,
    checkEnvironmentVariables,
    testAIPriceSentinel,
    testPriceTrajectoryChart,
    testPriceFormatting
  }
  
  console.log('🔧 Debug tools loaded! Run: window.deltaDropDebug.runDiagnostics()')
}
