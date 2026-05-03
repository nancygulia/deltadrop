import { useState } from 'react'
import PublicPageLayout from '../components/layout/PublicPageLayout'
import { toast } from '../components/ui/Toast'

const HELP_CATEGORIES = [
  { icon: 'rocket_launch', title: 'Getting Started',          sub: 'Quick setup guide for Precision Ledger and tracking your first merchant link.', links: ['Onboarding Guide','Connecting Accounts'] },
  { icon: 'manage_accounts', title: 'Account Management',    sub: 'Manage your subscription, security settings, and personal data exports.',         links: ['Billing Cycles','Two-Factor Auth'] },
  { icon: 'notifications_active', title: 'Alerts & Notifications', sub: 'Configuring high-signal drop alerts via Webhooks, Email, or Slack.',          links: ['Custom Thresholds','Push Settings'] },
  { icon: 'verified', title: 'Data Accuracy',                sub: 'Our methodology for price verification and historical data auditing.',               links: ['Validation Engine','Error Reporting'] },
]

const TERMS = [
  {
    title: '1. The Precision License',
    body:  'By utilizing DeltaDrop, you are granted a non-exclusive license to track and archive price data for personal or internal enterprise use. This data, referred to as the "Precision Ledger," is provided as a reference tool and does not constitute a financial guarantee of market behavior.',
    note:  'Note: Unauthorized scraping of the DeltaDrop aggregation layer is strictly prohibited under our fair use data policy.',
  },
]

const FAQ = [
  { q: 'How often is the data refreshed?',           a: 'Active products are refreshed every 2 minutes. Dormant products are checked every 15 minutes. Sale events trigger immediate re-indexing across all tracked retailers.' },
  { q: 'Can I export my tracking history?',          a: 'Yes. Navigate to Account Management → Data Export. You can download your full Precision Ledger history as JSON or CSV at any time, fully compliant with GDPR data portability.' },
  { q: 'What merchants are currently supported?',    a: 'We currently support 14 verified retailers including Amazon.in, Flipkart, Reliance Digital, Myntra, Croma, Tata CLiQ, Nykaa, Meesho, and more. Integrations are added monthly.' },
  { q: "How does the 'Price Drop' alert engine work?", a: 'Our ML model compares the current price against a 90-day rolling average, all-time low, and your custom threshold. When all conditions align, a high-signal alert is dispatched via your chosen channel.' },
]

function FaqItem({ q, a }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="py-4 border-b border-outline-variant/15 last:border-0">
      <button onClick={() => setOpen(v => !v)} className="w-full flex items-center justify-between gap-4 text-left">
        <span className="font-medium text-sm text-on-surface">{q}</span>
        <span className="material-symbols-outlined text-on-surface-variant flex-shrink-0 text-xl transition-transform"
          style={{ transform: open ? 'rotate(45deg)' : 'none' }}>add</span>
      </button>
      {open && <p className="text-xs text-on-surface-variant mt-3 leading-relaxed max-w-lg">{a}</p>}
    </div>
  )
}

export default function HelpPage() {
  const [searchQ, setSearchQ] = useState('')

  return (
    <PublicPageLayout>
      <div className="p-8 max-w-3xl mx-auto">

        {/* Hero */}
        <div className="text-center mb-10 animate-fade-up">
          <h1 className="font-headline text-5xl font-extrabold text-on-surface tracking-tight mb-6">How can we help?</h1>
          <div className="flex items-center gap-3 bg-surface-container-lowest rounded-xl px-5 py-3.5 shadow-ambient max-w-md mx-auto mb-5">
            <span className="material-symbols-outlined text-on-surface-variant text-lg">search</span>
            <input value={searchQ} onChange={e => setSearchQ(e.target.value)}
              placeholder="Search for tracking, alerts, data utility…"
              className="flex-1 bg-transparent border-none outline-none text-sm text-on-surface placeholder:text-on-surface-variant" />
          </div>
          <div className="flex items-center justify-center gap-2">
            <span className="text-xs text-on-surface-variant font-medium">Popular:</span>
            {['API Keys','Refund Tracking','Price History'].map(tag => (
              <button key={tag} onClick={() => setSearchQ(tag)}
                className="px-3 py-1 rounded-full bg-surface-container-lowest shadow-ambient text-xs font-semibold text-on-surface hover:bg-secondary-container hover:text-primary transition-colors">
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Help categories */}
        <div className="grid grid-cols-4 gap-4 mb-10 animate-fade-up" style={{ animationDelay: '.08s', opacity: 0 }}>
          {HELP_CATEGORIES.map(cat => (
            <div key={cat.title} className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient hover:shadow-float transition-shadow">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-primary text-base">{cat.icon}</span>
              </div>
              <div className="font-headline font-bold text-sm text-on-surface mb-2 leading-tight">{cat.title}</div>
              <p className="text-xs text-on-surface-variant leading-relaxed mb-3">{cat.sub}</p>
              <div className="space-y-1">
                {cat.links.map(l => (
                  <button key={l} onClick={() => toast(`Opening: ${l}`, 'info')}
                    className="block text-xs font-semibold text-primary hover:underline">{l}</button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Terms of Data Utility */}
        <div className="mb-8 animate-fade-up" style={{ animationDelay: '.14s', opacity: 0 }}>
          <div className="flex items-center gap-3 mb-5">
            <span className="material-symbols-outlined text-on-surface text-xl">gavel</span>
            <h2 className="font-headline text-2xl font-extrabold text-on-surface">Terms of Data Utility</h2>
          </div>

          <div className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient mb-4">
            <div className="font-headline font-bold text-base text-on-surface mb-3">1. The Precision License</div>
            <p className="text-sm text-on-surface-variant leading-relaxed mb-4">{TERMS[0].body}</p>
            <div className="border-l-2 border-primary pl-4 py-1">
              <p className="text-xs text-on-surface-variant leading-relaxed italic">{TERMS[0].note}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
              <div className="font-headline font-bold text-sm text-on-surface mb-3">Data Sourcing</div>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                We aggregate data from global retailers in 15-minute intervals. While we strive for absolute precision, merchant-side technical errors or regional price discrepancies may occur. DeltaDrop acts as an editorial lens, not a direct transaction facilitator.
              </p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
              <div className="font-headline font-bold text-sm text-on-surface mb-3">User Contributions</div>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Users may upload receipts or manually log pricing points. By contributing data, you warrant its accuracy and grant DeltaDrop an anonymous, irrevocable license to include these points in our global trend modeling.
              </p>
            </div>
          </div>

          <div className="rounded-xl p-6 relative overflow-hidden" style={{ background: '#111827' }}>
            <div className="absolute right-6 top-1/2 -translate-y-1/2 opacity-10">
              <span className="material-symbols-outlined fill-icon text-white" style={{ fontSize: '80px' }}>verified_user</span>
            </div>
            <div className="relative z-10">
              <div className="font-headline font-bold text-base text-white mb-2">Compliance &amp; Transparency</div>
              <p className="text-xs text-gray-400 leading-relaxed max-w-lg mb-4">
                DeltaDrop complies with GDPR and CCPA protocols regarding data portability. Your tracking history is your intellectual property; you may request a full JSON export of your Precision Ledger at any time through the Account Management dashboard.
              </p>
              <button onClick={() => toast('Downloading compliance PDF…', 'info')}
                className="px-4 py-2 grad-primary text-on-primary rounded-md font-bold text-xs hover:opacity-90 active:scale-95 transition-all">
                Download Compliance PDF
              </button>
            </div>
          </div>
        </div>

        {/* FAQ */}
        <div className="mb-10 animate-fade-up" style={{ animationDelay: '.20s', opacity: 0 }}>
          <h2 className="font-headline text-3xl font-extrabold text-on-surface text-center mb-8">Frequently Asked Questions</h2>
          <div className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient">
            {FAQ.map((item, i) => <FaqItem key={i} q={item.q} a={item.a} />)}
          </div>
        </div>

        {/* Still have questions CTA */}
        <div className="rounded-2xl p-12 text-center grad-primary animate-fade-up" style={{ animationDelay: '.26s', opacity: 0 }}>
          <h2 className="font-headline text-2xl font-extrabold text-on-primary mb-3">Still have questions?</h2>
          <p className="text-on-primary-container text-sm leading-relaxed mb-8 max-w-sm mx-auto">
            Our support team of data analysts is available 24/7 to help you optimize your tracking ledger.
          </p>
          <div className="flex gap-4 justify-center">
            <button onClick={() => toast('Opening support chat…', 'info')}
              className="px-6 py-3 bg-surface-container-lowest text-primary rounded-md font-bold text-sm hover:bg-white transition-colors active:scale-95">
              Contact Support
            </button>
            <button onClick={() => toast('Opening community forum…', 'info')}
              className="px-6 py-3 bg-white/10 text-on-primary rounded-md font-bold text-sm hover:bg-white/20 transition-colors"
              style={{ border: '1px solid rgba(255,255,255,.25)' }}>
              Visit Community Forum
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-10 pt-8 border-t border-outline-variant/15 pb-4">
          <div className="flex justify-center gap-6 mb-3">
            {['Privacy','Transparency','Terms','Help'].map(l => (
              <a key={l} href={`/${l.toLowerCase()}`} className="text-xs text-on-surface-variant hover:text-primary transition-colors">{l}</a>
            ))}
          </div>
          <div className="text-center font-headline font-black text-sm text-on-surface mb-1">DeltaDrop</div>
          <p className="text-[11px] text-on-surface-variant text-center uppercase tracking-widest">© 2024 DELTADROP EDITORIAL DATA EXPERIENCE. ALL RIGHTS RESERVED.</p>
        </footer>
      </div>
    </PublicPageLayout>
  )
}
