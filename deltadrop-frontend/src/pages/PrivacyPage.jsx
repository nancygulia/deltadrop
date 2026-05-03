import PublicPageLayout from '../components/layout/PublicPageLayout'
import { toast } from '../components/ui/Toast'

const DATA_WE_COLLECT = [
  { title: 'Tracking Telemetry',   desc: 'We record item URLs and price history metadata specifically requested by your tracking profile. This data is isolated to your unique vault.' },
  { title: 'Account Identification', desc: 'Verified email addresses and notification preferences essential for delivering high-precision price drop alerts.' },
  { title: 'Technical Logs',       desc: 'Browser versions and IP headers are kept for 72 hours solely for DDoS mitigation and analytical performance tuning.' },
]

const YOUR_CHOICES = [
  { label: 'Export All Data',        icon: 'download' },
  { label: 'Purge History',          icon: 'delete' },
  { label: 'Opt-out of Analytics',   icon: 'visibility_off' },
]

const TRANSPARENCY = [
  { label: 'GOV REQUESTS',       value: '0',     sub: 'Total government or third-party data requests processed in Q3 2024.', icon: 'do_not_disturb_on', color: 'text-on-surface' },
  { label: 'SYSTEM LATENCY',     value: '14ms',  sub: 'Average global response time across all tracking nodes.',              icon: 'speed',              color: 'text-tertiary-container' },
  { label: 'UPTIME DISTRIBUTION',value: null,    sub: 'Reliability by region (Last 30 Days).',                                icon: 'pie_chart',          color: 'text-primary' },
]

export default function PrivacyPage() {
  return (
    <PublicPageLayout>
      <div className="p-8 max-w-4xl mx-auto">

        {/* Header */}
        <div className="mb-10 animate-fade-up">
          <div className="text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-3">Trust & Governance</div>
          <div className="flex items-start justify-between gap-6">
            <div className="flex-1">
              <h1 className="font-headline text-5xl font-extrabold text-on-surface tracking-tight mb-4">Privacy &amp; Transparency.</h1>
              <p className="text-on-surface-variant text-base leading-relaxed max-w-md">
                Our commitment to clarity means your data is never a product. Explore our ledger of privacy standards and real-time operational transparency.
              </p>
            </div>
            <div className="flex-shrink-0 bg-surface-container-lowest rounded-xl p-4 shadow-ambient text-right">
              <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1">Current Uptime</div>
              <div className="font-headline text-3xl font-extrabold text-on-surface flex items-center gap-2 justify-end">
                99.99%
                <div className="w-5 h-5 rounded-full bg-tertiary-container flex items-center justify-center">
                  <span className="material-symbols-outlined fill-icon text-on-tertiary-container text-sm">check</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Data We Collect + Your Choices */}
        <div className="grid grid-cols-5 gap-5 mb-5 animate-fade-up" style={{ animationDelay: '.08s', opacity: 0 }}>
          <div className="col-span-3 bg-surface-container-lowest rounded-xl p-6 shadow-ambient">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                <span className="material-symbols-outlined fill-icon text-primary text-base">database</span>
              </div>
              <h2 className="font-headline font-bold text-lg text-on-surface">Data We Collect</h2>
            </div>
            <div className="space-y-5">
              {DATA_WE_COLLECT.map((item, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/40 mt-2 flex-shrink-0"/>
                  <div>
                    <div className="font-semibold text-sm text-on-surface mb-1">{item.title}</div>
                    <p className="text-xs text-on-surface-variant leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-2 grad-primary rounded-xl p-6 text-on-primary">
            <h2 className="font-headline font-bold text-lg mb-2">Your Choices</h2>
            <p className="text-on-primary-container text-xs leading-relaxed mb-6">
              You maintain absolute sovereignty over your tracking footprint. Adjust your visibility settings at any time.
            </p>
            <div className="space-y-3">
              {YOUR_CHOICES.map(c => (
                <button key={c.label} onClick={() => toast(`${c.label} initiated`, 'info')}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-left">
                  <span className="font-semibold text-sm text-on-primary">{c.label}</span>
                  <span className="material-symbols-outlined fill-icon text-on-primary-container text-lg">{c.icon}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* How We Use It + Security Infrastructure */}
        <div className="grid grid-cols-5 gap-5 mb-8 animate-fade-up" style={{ animationDelay: '.14s', opacity: 0 }}>
          <div className="col-span-2 bg-surface-container-low rounded-xl p-6">
            <h3 className="font-headline font-bold text-base text-on-surface mb-3">How We Use It</h3>
            <p className="text-xs text-on-surface-variant leading-relaxed mb-4">
              Data is strictly utilized for the functional execution of price monitoring. We do not engage in behavioral advertising or data brokering.
            </p>
            <button className="text-xs font-bold text-primary flex items-center gap-1 hover:underline">
              READ POLICY
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
          </div>

          <div className="col-span-3 bg-surface-container-lowest rounded-xl p-6 shadow-ambient">
            <div className="flex items-start justify-between">
              <div className="flex-1 pr-4">
                <h3 className="font-headline font-bold text-base text-on-surface mb-3">Security Infrastructure</h3>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  Our ledger is protected by AES-256 encryption at rest and TLS 1.3 in transit. We conduct bi-annual third-party penetration tests to ensure the integrity of your monitored data.
                </p>
              </div>
              <div className="w-16 h-16 rounded-xl bg-surface-container-low flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined fill-icon text-on-surface-variant text-3xl">verified_user</span>
              </div>
            </div>
          </div>
        </div>

        {/* Transparency Report */}
        <div className="animate-fade-up" style={{ animationDelay: '.20s', opacity: 0 }}>
          <div className="text-center mb-8">
            <h2 className="font-headline text-3xl font-extrabold text-on-surface mb-2">Transparency Report</h2>
            <p className="text-on-surface-variant text-sm">Quarterly metrics on data stewardship and infrastructure performance.</p>
          </div>

          <div className="grid grid-cols-3 gap-5 mb-8">
            {TRANSPARENCY.map((item, i) => (
              <div key={i} className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
                <div className="flex items-center justify-between mb-4">
                  <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">{item.label}</div>
                  <span className={`material-symbols-outlined text-xl ${item.color}`}>{item.icon}</span>
                </div>
                {item.value
                  ? <div className={`font-headline text-4xl font-extrabold mb-2 ${item.color}`}>{item.value}</div>
                  : (
                    <div className="flex gap-1 mb-2 items-end h-10">
                      {[70,85,60,90,75,95,80,90].map((h, j) => (
                        <div key={j} className="flex-1 rounded-t-sm" style={{ height: `${h}%`, background: '#6bfe9c' }} />
                      ))}
                    </div>
                  )}
                <p className="text-xs text-on-surface-variant leading-relaxed">{item.sub}</p>
                <div className="mt-3 h-1 rounded-full bg-surface-container overflow-hidden">
                  <div className="h-full rounded-full bg-tertiary-container" style={{ width: i === 0 ? '5%' : i === 1 ? '82%' : '95%' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA dark section */}
        <div className="rounded-2xl p-12 text-center animate-fade-up" style={{ animationDelay: '.26s', opacity: 0, background: '#111827' }}>
          <h2 className="font-headline text-3xl font-extrabold text-white mb-3">Questions about your data?</h2>
          <p className="text-gray-400 text-sm leading-relaxed mb-8 max-w-md mx-auto">
            Our privacy officers are available for detailed inquiries regarding our encryption standards or data sovereignty protocols.
          </p>
          <div className="flex gap-4 justify-center">
            <button onClick={() => toast('Connecting to privacy officer…', 'info')}
              className="px-6 py-3 bg-surface-container-lowest text-on-surface rounded-md font-bold text-sm hover:bg-white transition-colors active:scale-95">
              Contact Privacy Officer
            </button>
            <button onClick={() => toast('Downloading audit PDF…', 'info')}
              className="px-6 py-3 bg-white/10 text-white rounded-md font-bold text-sm hover:bg-white/20 transition-colors"
              style={{ border: '1px solid rgba(255,255,255,.2)' }}>
              Download Audit PDF
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-10 pt-8 border-t border-outline-variant/15 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-headline font-black text-base text-on-surface">DeltaDrop</div>
              <div className="text-xs text-on-surface-variant">The Precision Ledger Editorial Experience</div>
            </div>
            <div className="flex gap-5">
              {['Privacy','Transparency','Terms','Help'].map(l => (
                <a key={l} href={`/${l.toLowerCase()}`} className="text-xs text-on-surface-variant hover:text-primary transition-colors">{l}</a>
              ))}
            </div>
          </div>
          <p className="text-[11px] text-on-surface-variant text-center mt-4">© 2026 DeltaDrop Editorial Data Experience. All rights reserved.</p>
        </footer>
      </div>
    </PublicPageLayout>
  )
}
