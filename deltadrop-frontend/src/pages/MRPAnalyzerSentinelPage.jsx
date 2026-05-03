/**
 * MRPAnalyzerSentinelPage.jsx — New page for MRP analysis tool
 * 
 * This is a standalone page that provides AI-powered MRP analysis
 * for the Indian retail market.
 */

import React from 'react'
import MRPAnalyzerSentinel from '../components/MRPAnalyzerSentinel'

export default function MRPAnalyzerSentinelPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <MRPAnalyzerSentinel />
    </div>
  )
}
