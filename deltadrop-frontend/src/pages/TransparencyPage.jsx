import { useState } from 'react'
import PublicPageLayout from '../components/layout/PublicPageLayout'
import { toast } from '../components/ui/Toast'

const METRICS = [
  { label: 'Government Data Requests', value: '0',      unit: '',    desc: 'Total requests from government or third-party agencies in Q3 2024. We have never complied with a bulk data request.', icon: 'do_not_disturb_on', color: 'text-on-surface' },
  { label: 'System Latency',           value: '14',     unit: 'ms',  desc: 'Average API response time across all global tracking nodes in the last 30 days.', icon: 'speed',             color: 'text-tertiary-container' },
  { label: 'Uptime',                   value: '99.99',  unit: '%',   desc: 'Precision Ledger infrastructure availability over the trailing 12 months.', icon: 'verified',           color: 'text-primary' },
  { label: 'Data Sources Verified',    value: '1,400+', unit: '',    desc: 'Retail merchant data streams verified for accuracy every 2-minute cycle.', icon: 'fact_check',         color: 'text-primary' },
  { label: 'Price Points Indexed',     value: '5.4M',   unit: '',    desc: 'Unique price swing events captured and committed to the ledger in Q3 2024.', icon: 'analytics',          color: 'text-tertiary-container' },
  { label: 'Encryption Standard',      value: 'AES-256',unit: '',    desc: 'Military-grade encryption for all data at rest. TLS 1.3 for all data in transit.', icon: 'lock',              color: 'text-on-surface' },
]

const CHANGELOGS = [
  { date: 'Oct 15, 2024', version: 'v4.2.1', title: 'Subscription data scraper timeout fix', type: 'fix' },
  { date: 'Sep 28, 2024', version: 'v4.2.0', title: 'Added Tata CLiQ and Croma to retailer ledger', type: 'feature' },
  { date: 'Sep 12, 2024', version: 'v4.1.3', title: 'GMP history sparkline performance improvement', type: 'perf' },
  { date: 'Aug 30, 2024', version: 'v4.1.0', title: 'Introduced Neural Price Prediction Engine', type: 'feature' },
  { date: 'Aug 14, 2024', version: 'v4.0.5', title: 'APScheduler cron job stability patches', type: 'fix' },
]

const typeStyle = {
  feature: 'bg-primary/10 text-primary',
  fix:     'bg-orange-100 text-orange-700',
  perf:    'bg-tertiary-container/15 text-tertiary-container',
}

export default function TransparencyPage() {
  const [activeQ, setActiveQ] = useState('Q3 2024')

  return (
    <PublicPageLayout>
      <div className="p-8 max-w-4xl mx-auto">

        {/* Header */}
        <div className="mb-10 animate-fade-up">
          <div className="text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-3">Transparency</div>
          <h1 className="font-headline text-5xl font-extrabold text-on-surface tracking-tight mb-4">Open by Design.</h1>
          <p className="text-on-surface-variant text-base leading-relaxed max-w-md">
            Every engineering decision, data source, and infrastructure metric is documented here. We believe that a precision tool demands a transparent operator.
          </p>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-3 gap-4 mb-10 animate-fade-up" style={{ animationDelay: '.07s', opacity: 0 }}>
          {METRICS.map(m => (
            <div key={m.label} className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
              <div className="flex items-center justify-between mb-3">
                <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider leading-tight">{m.label}</div>
                <span className={`material-symbols-outlined fill-icon text-lg ${m.color}`}>{m.icon}</span>
              </div>
              <div className={`font-headline text-3xl font-extrabold mb-1 ${m.color}`}>
                {m.value}<span className="text-lg">{m.unit}</span>
              </div>
              <p className="text-xs text-on-surface-variant leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>

        {/* Infrastructure section */}
        <div className="bg-surface-container-lowest rounded-xl p-7 shadow-ambient mb-6 animate-fade-up" style={{ animationDelay: '.12s', opacity: 0 }}>
          <h2 className="font-headline text-xl font-extrabold text-on-surface mb-6">Infrastructure Architecture</h2>
          <div className="grid grid-cols-3 gap-5">
            {[
              { icon: 'cloud',       title: 'Hosting',      detail: 'AWS Mumbai Region (ap-south-1) with multi-AZ redundancy. Zero data stored outside India.' },
              { icon: 'database',    title: 'Database',     detail: 'PostgreSQL 16 with read replicas. All price history is append-only — we never mutate historical data.' },
              { icon: 'vpn_lock',    title: 'Security',     detail: 'Bi-annual third-party penetration tests. GDPR and CCPA compliant. SOC 2 Type II audit in progress.' },
            ].map(item => (
              <div key={item.title} className="bg-surface-container-low rounded-xl p-4">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
                  <span className="material-symbols-outlined text-primary text-base">{item.icon}</span>
                </div>
                <div className="font-headline font-bold text-sm text-on-surface mb-2">{item.title}</div>
                <p className="text-xs text-on-surface-variant leading-relaxed">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Uptime by region */}
        <div className="bg-surface-container-lowest rounded-xl p-7 shadow-ambient mb-6 animate-fade-up" style={{ animationDelay: '.16s', opacity: 0 }}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-headline text-xl font-extrabold text-on-surface">Uptime Distribution</h2>
            <div className="flex gap-1">
              {['Q3 2024','Q2 2024','Q1 2024'].map(q => (
                <button key={q} onClick={() => setActiveQ(q)}
                  className={`px-3 py-1 rounded-md text-xs font-bold transition-colors
                    ${activeQ === q ? 'bg-on-surface text-inverse-on-surface' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'}`}>
                  {q}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-5 gap-3">
            {[['Mumbai','99.99%'],['Delhi','99.97%'],['Bengaluru','99.98%'],['Chennai','99.96%'],['Kolkata','99.95%']].map(([city, uptime]) => (
              <div key={city} className="text-center">
                <div className="h-28 rounded-xl bg-surface-container-low flex flex-col justify-end p-2 mb-2 overflow-hidden relative">
                  <div className="rounded-t-lg bg-tertiary-container absolute bottom-0 left-2 right-2"
                    style={{ height: `${90 + Math.random() * 9}%` }} />
                </div>
                <div className="font-semibold text-xs text-on-surface">{city}</div>
                <div className="text-[10px] font-bold text-tertiary-container">{uptime}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Changelog */}
        <div className="animate-fade-up" style={{ animationDelay: '.20s', opacity: 0 }}>
          <h2 className="font-headline text-xl font-extrabold text-on-surface mb-4">Public Changelog</h2>
          <div className="bg-surface-container-lowest rounded-xl shadow-ambient overflow-hidden">
            {CHANGELOGS.map((log, i) => (
              <div key={i} className={`flex items-center gap-4 px-6 py-4 border-b border-outline-variant/10 last:border-0 ${i % 2 === 1 ? 'bg-surface-container-low/40' : ''}`}>
                <div className="text-xs text-on-surface-variant w-24 flex-shrink-0">{log.date}</div>
                <div className="text-xs font-mono font-bold text-on-surface-variant w-14 flex-shrink-0">{log.version}</div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase flex-shrink-0 ${typeStyle[log.type]}`}>{log.type}</span>
                <div className="text-sm text-on-surface">{log.title}</div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="mt-8 rounded-2xl p-10 text-center animate-fade-up" style={{ animationDelay: '.24s', opacity: 0, background: '#111827' }}>
          <h2 className="font-headline text-2xl font-extrabold text-white mb-3">Request a Full Audit Report</h2>
          <p className="text-gray-400 text-sm mb-6 max-w-sm mx-auto leading-relaxed">
            Enterprise users can request a comprehensive audit PDF including penetration test results and compliance certifications.
          </p>
          <button onClick={() => toast('Audit request submitted!', 'success')}
            className="px-6 py-3 bg-surface-container-lowest text-on-surface rounded-md font-bold text-sm hover:bg-white transition-colors">
            Download Audit PDF
          </button>
        </div>

        {/* Footer */}
        <footer className="mt-10 pt-8 border-t border-outline-variant/15 pb-4 flex items-center justify-between">
          <div className="font-headline font-black text-on-surface">DeltaDrop</div>
          <div className="flex gap-5">
            {['Privacy','Transparency','Terms','Help'].map(l => (
              <a key={l} href={`/${l.toLowerCase()}`} className="text-xs text-on-surface-variant hover:text-primary transition-colors">{l}</a>
            ))}
          </div>
          <p className="text-[11px] text-on-surface-variant">© 2024 DeltaDrop. All rights reserved.</p>
        </footer>
      </div>
    </PublicPageLayout>
  )
}
