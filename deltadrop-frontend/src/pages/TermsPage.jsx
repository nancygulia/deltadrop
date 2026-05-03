import { useState } from 'react'
import PublicPageLayout from '../components/layout/PublicPageLayout'
import { toast } from '../components/ui/Toast'

const SECTIONS = [
  {
    id: '1', title: 'The Precision License',
    body: `By utilizing DeltaDrop, you are granted a non-exclusive, non-transferable license to track and archive price data for personal or internal enterprise use. This data, referred to as the "Precision Ledger," is provided as a reference tool and does not constitute a financial guarantee of market behavior.`,
    note: 'Unauthorized scraping of the DeltaDrop aggregation layer is strictly prohibited under our fair use data policy. Violations may result in permanent account termination.',
  },
  {
    id: '2', title: 'Data Sourcing & Accuracy',
    body: `We aggregate retail pricing data from public-facing merchant pages in 15-minute cycles. While we strive for absolute precision, merchant-side technical errors, regional price discrepancies, or delivery surcharges may cause deviations. DeltaDrop acts as an editorial intelligence lens — not a direct transaction facilitator or price guarantor.`,
    note: null,
  },
  {
    id: '3', title: 'User Contributions',
    body: `Users may upload receipts or manually log pricing data points. By contributing data, you warrant its accuracy to the best of your knowledge and grant DeltaDrop an anonymous, irrevocable, royalty-free license to include these price points in our global trend modeling algorithms. Contributed data is never personally identifiable in our public outputs.`,
    note: null,
  },
  {
    id: '4', title: 'Account Termination',
    body: `DeltaDrop reserves the right to suspend or permanently terminate accounts that (a) attempt to circumvent our rate limiting systems, (b) use automated tools to bulk-download ledger data, or (c) violate any provision of this agreement. Account holders will be notified via registered email prior to termination except in cases of severe abuse.`,
    note: null,
  },
  {
    id: '5', title: 'Limitation of Liability',
    body: `DeltaDrop's total cumulative liability to you for any cause of action arising out of or related to this agreement shall not exceed the amount you paid for premium services in the 12 months preceding the claim. DeltaDrop is not liable for any indirect, incidental, special, consequential, or punitive damages, including lost profits from purchasing decisions made using ledger data.`,
    note: null,
  },
  {
    id: '6', title: 'Governing Law & Dispute Resolution',
    body: `This agreement is governed by the laws of India. Any dispute arising under this agreement shall be subject to the exclusive jurisdiction of the courts of Bengaluru, Karnataka. We encourage all disputes to first be raised with our compliance team at privacy@deltadrop.in for resolution within 30 days prior to legal proceedings.`,
    note: null,
  },
]

export default function TermsPage() {
  const [activeSection, setActiveSection] = useState(null)

  return (
    <PublicPageLayout>
      <div className="p-8 max-w-4xl mx-auto">

        {/* Header */}
        <div className="mb-10 animate-fade-up">
          <div className="text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-3">Legal</div>
          <h1 className="font-headline text-5xl font-extrabold text-on-surface tracking-tight mb-4">Terms of Data Utility.</h1>
          <div className="flex items-center gap-4">
            <p className="text-on-surface-variant text-base leading-relaxed max-w-lg">
              These terms govern your use of the DeltaDrop Precision Ledger platform, including all price tracking, alert, and analytics features.
            </p>
            <div className="flex-shrink-0 bg-surface-container-low rounded-xl px-4 py-3 text-right">
              <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Last Updated</div>
              <div className="font-headline font-extrabold text-on-surface">Oct 1, 2024</div>
            </div>
          </div>
        </div>

        {/* Quick nav */}
        <div className="flex flex-wrap gap-2 mb-8 animate-fade-up" style={{ animationDelay: '.06s', opacity: 0 }}>
          {SECTIONS.map(s => (
            <button key={s.id} onClick={() => { setActiveSection(s.id); document.getElementById(`section-${s.id}`)?.scrollIntoView({ behavior: 'smooth' }) }}
              className="px-3 py-1.5 rounded-full text-xs font-semibold bg-surface-container-lowest shadow-ambient text-on-surface-variant hover:text-primary hover:bg-secondary-container/40 transition-colors">
              {s.id}. {s.title}
            </button>
          ))}
        </div>

        {/* Terms sections */}
        <div className="space-y-4 animate-fade-up" style={{ animationDelay: '.10s', opacity: 0 }}>
          {SECTIONS.map((s, i) => (
            <div key={s.id} id={`section-${s.id}`}
              className={`bg-surface-container-lowest rounded-xl p-6 shadow-ambient transition-all ${activeSection === s.id ? 'ring-2 ring-primary/20' : ''}`}>
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-lg grad-primary flex items-center justify-center text-on-primary font-bold text-sm flex-shrink-0 mt-0.5">
                  {s.id}
                </div>
                <div className="flex-1">
                  <h3 className="font-headline font-bold text-base text-on-surface mb-3">{s.title}</h3>
                  <p className="text-sm text-on-surface-variant leading-relaxed">{s.body}</p>
                  {s.note && (
                    <div className="mt-4 pl-4 border-l-2 border-primary/40">
                      <p className="text-xs text-on-surface-variant leading-relaxed italic">{s.note}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Compliance block */}
        <div className="mt-8 rounded-2xl overflow-hidden animate-fade-up" style={{ animationDelay: '.18s', opacity: 0, background: '#111827' }}>
          <div className="p-8 flex items-center justify-between gap-8">
            <div>
              <div className="font-headline font-bold text-base text-white mb-2">Compliance & Data Portability</div>
              <p className="text-gray-400 text-sm leading-relaxed max-w-md">
                DeltaDrop complies with GDPR and CCPA data portability protocols. You may request a full JSON export of your Precision Ledger at any time through Account Management. Requests are processed within 72 hours.
              </p>
            </div>
            <div className="flex gap-3 flex-shrink-0">
              <button onClick={() => toast('Downloading compliance PDF…', 'info')}
                className="px-5 py-2.5 grad-primary text-on-primary rounded-md font-bold text-sm hover:opacity-90 active:scale-95 transition-all">
                Download Compliance PDF
              </button>
              <button onClick={() => toast('Opening compliance portal…', 'info')}
                className="px-5 py-2.5 bg-white/10 text-white rounded-md font-bold text-sm hover:bg-white/20 transition-colors"
                style={{ border: '1px solid rgba(255,255,255,.2)' }}>
                GDPR Portal
              </button>
            </div>
          </div>
        </div>

        {/* Contact CTA */}
        <div className="mt-6 bg-surface-container-lowest rounded-xl p-6 shadow-ambient flex items-center gap-6 animate-fade-up" style={{ animationDelay: '.22s', opacity: 0 }}>
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-primary text-xl">gavel</span>
          </div>
          <div className="flex-1">
            <div className="font-headline font-bold text-base text-on-surface mb-1">Questions about these terms?</div>
            <p className="text-sm text-on-surface-variant">Our legal team is available at <span className="text-primary font-semibold">legal@deltadrop.in</span> for clarification on any provision.</p>
          </div>
          <button onClick={() => toast('Opening legal contact form…', 'info')}
            className="px-5 py-2.5 bg-surface-container text-on-surface rounded-md font-bold text-sm hover:bg-surface-container-high transition-colors flex-shrink-0">
            Contact Legal
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
