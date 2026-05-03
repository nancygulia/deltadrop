/**
 * PriceIntelligenceSentinelPage.jsx — New page for AI Price Sentinel dashboard
 * 
 * This is a standalone page that provides AI Price Sentinel and
 * Price Trajectory Chart features.
 */

import React from 'react'
import PriceIntelligenceDashboardSentinel from '../components/PriceIntelligenceDashboardSentinel'

export default function PriceIntelligenceSentinelPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PriceIntelligenceDashboardSentinel />
    </div>
  )
}
