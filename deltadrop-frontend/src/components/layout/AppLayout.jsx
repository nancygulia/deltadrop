import { useState } from 'react'
import { Link } from 'react-router-dom'
import SearchOverlay from '../ui/SearchOverlay'
import DashboardHeader from './DashboardHeader'
import Footer from './Footer'

export default function AppLayout({ children, tabs = [] }) {
  const [searchOpen, setSearchOpen] = useState(false)

  return (
    <div className="min-h-screen bg-surface flex flex-col font-body">
      <DashboardHeader tabs={tabs} />

      <main className="flex-1 flex flex-col">
        <div className="flex-1 max-w-[1200px] mx-auto w-full">
          {children}
        </div>
        <Footer />
      </main>

      <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  )
}
