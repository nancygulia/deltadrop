/**
 * AIButton.jsx — Floating AI trigger button.
 * Renders a persistent pill button that opens the AI drawer.
 * Shows the current product's verdict as a badge.
 */
import { useState } from 'react'
import AIDrawer from './AIDrawer'

export default function AIButton({ product, searchResults, position = 'fixed' }) {
  const [open, setOpen] = useState(false)

  const verdictColor = {
    'BUY NOW': 'bg-tertiary-fixed text-on-surface',
    'WAIT':    'bg-on-primary-container text-primary',
    'NEUTRAL': 'bg-surface-container-highest text-on-surface-variant',
  }
  const verdict = product?.aiVerdict

  return (
    <>
      {/* Floating trigger */}
      <button
        onClick={() => setOpen(true)}
        className={`${position === 'fixed' ? 'fixed bottom-6 right-6 z-[80]' : 'relative'} flex items-center gap-3 grad-primary text-on-primary px-5 py-3 rounded-full shadow-float hover:opacity-95 hover:scale-105 active:scale-95 transition-all font-headline`}
        title="Ask AI about this product's price">

        {/* Pulse ring */}
        <span className="absolute inset-0 rounded-full ring-2 ring-primary/30 animate-ping opacity-40" />

        <span className="material-symbols-outlined fill-icon text-xl relative z-10">psychology</span>

        <div className="relative z-10 text-left">
          <div className="text-xs font-black leading-none">Ask AI</div>
          <div className="text-[10px] text-on-primary-container leading-none mt-0.5">Price Intelligence</div>
        </div>

        {/* Verdict badge */}
        {verdict && (
          <span className={`relative z-10 text-[9px] font-black px-2 py-0.5 rounded-full uppercase tracking-wide ${verdictColor[verdict] || verdictColor['NEUTRAL']}`}>
            {verdict}
          </span>
        )}
      </button>

      {/* Drawer */}
      <AIDrawer
        product={product}
        searchResults={searchResults}
        isOpen={open}
        onClose={() => setOpen(false)}
      />
    </>
  )
}
