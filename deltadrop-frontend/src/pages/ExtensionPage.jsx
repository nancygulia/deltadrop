import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import { toast } from '../components/ui/Toast'

export default function ExtensionPage() {
  const navigate = useNavigate()

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-8 py-12">
        {/* Hero Section */}
        <div className="relative mb-24 animate-fade-up">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
            <div className="lg:col-span-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 text-primary text-xs font-bold uppercase tracking-wider mb-8">
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                Browser Protocol v2.0
              </div>
              <h1 className="text-5xl lg:text-6xl font-black text-on-surface tracking-tight leading-[1.1] mb-6">
                Market Intelligence,<br />
                <span className="text-primary">Directly in Chrome.</span>
              </h1>
              <p className="text-lg text-on-surface-variant leading-relaxed mb-10 max-w-lg font-medium">
                Execute every purchase with absolute certainty. Access sub-millisecond price indexing and AI insights without leaving your favorite store.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <button onClick={() => toast('Redirecting to Chrome Web Store...', 'info')}
                  className="px-8 py-4 bg-primary text-white rounded-2xl font-bold text-base flex items-center justify-center gap-3 hover:bg-primary-container active:scale-95 transition-all shadow-lg shadow-primary/20">
                  <span className="material-symbols-outlined text-xl">extension_add</span>
                  Install Extension — Free
                </button>
                <div className="flex items-center gap-4 px-6 py-4 bg-white border border-outline-variant/40 rounded-2xl shadow-sm">
                  <div className="flex -space-x-3">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="w-8 h-8 rounded-full border-2 border-white bg-surface flex items-center justify-center text-[10px] font-black text-on-surface-variant ring-1 ring-outline-variant/20">
                        {['A', 'R', 'M'][i-1]}
                      </div>
                    ))}
                  </div>
                  <div>
                    <div className="text-sm font-black text-on-surface">4.9/5</div>
                    <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">50k+ Users</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-6 relative">
              <div className="absolute inset-0 bg-primary/5 rounded-[40px] blur-3xl -z-10 transform rotate-3" />
              <BrowserMockup />
            </div>
          </div>
        </div>

        {/* Intelligence Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-24">
          <div className="md:col-span-8 bg-white rounded-[32px] p-10 border border-outline-variant/40 shadow-sm group hover:border-primary/20 transition-all">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-8 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-2xl">dataset</span>
            </div>
            <h3 className="text-2xl font-bold text-on-surface mb-4 tracking-tight">Real-Time Index Parity</h3>
            <p className="text-on-surface-variant font-medium leading-relaxed max-w-lg mb-10">
              Our neural network automatically reconciles product identities across 1,000+ retail platforms, ensuring you see the global best price instantly.
            </p>
            <FluxChart />
          </div>

          <div className="md:col-span-4 bg-primary text-white rounded-[32px] p-10 shadow-lg relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full -mr-24 -mt-24 blur-3xl group-hover:scale-110 transition-transform" />
            <div className="relative z-10 flex flex-col h-full">
              <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center mb-8">
                <span className="material-symbols-outlined text-2xl text-white">notifications_active</span>
              </div>
              <h3 className="text-2xl font-bold mb-4 tracking-tight">Zero-Latency Alerts</h3>
              <p className="text-white/80 font-medium leading-relaxed mb-10">
                Establish target thresholds directly on the product page. We execute the notification the moment the ledger shifts.
              </p>
              <div className="mt-auto">
                <button onClick={() => navigate('/alerts')} className="w-full py-4 bg-white text-primary rounded-2xl font-bold text-sm hover:bg-primary-container hover:text-white transition-all active:scale-95 shadow-sm">
                  Configure Alerts
                </button>
              </div>
            </div>
          </div>

          <div className="md:col-span-5 bg-white rounded-[32px] p-10 border border-outline-variant/40 shadow-sm group hover:border-primary/20 transition-all">
            <div className="w-12 h-12 rounded-2xl bg-tertiary-container/10 flex items-center justify-center text-tertiary-container mb-8 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-2xl">psychology</span>
            </div>
            <h3 className="text-2xl font-bold text-on-surface mb-4 tracking-tight">Algorithmic Verdicts</h3>
            <p className="text-on-surface-variant font-medium leading-relaxed mb-10">
              Data-backed 'Buy vs Wait' indicator integrated directly into every price tag on the web.
            </p>
            <div className="p-6 bg-surface/50 rounded-2xl border border-outline-variant/10 flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-tertiary-container/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-tertiary-container text-2xl">verified</span>
              </div>
              <div>
                <div className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Buy Confidence</div>
                <div className="text-xl font-black text-tertiary-container">94% PROBABILITY</div>
              </div>
            </div>
          </div>

          <div className="md:col-span-7 bg-white rounded-[32px] p-10 border border-outline-variant/40 shadow-sm group hover:border-primary/20 transition-all overflow-hidden relative">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-8 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-2xl">compare_arrows</span>
            </div>
            <h3 className="text-2xl font-bold text-on-surface mb-4 tracking-tight">Cross-Market Parity</h3>
            <p className="text-on-surface-variant font-medium leading-relaxed mb-10">
              Instantly verify if a competitor is offering a lower entry point while you're browsing.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-6 bg-white border border-outline-variant/40 rounded-2xl shadow-sm">
                <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Market A</div>
                <div className="text-xl font-black text-on-surface">₹44,990</div>
              </div>
              <div className="p-6 bg-primary/5 border border-primary/20 rounded-2xl shadow-sm">
                <div className="text-[10px] font-bold text-primary uppercase tracking-widest mb-2">Market B</div>
                <div className="text-xl font-black text-primary">₹41,200</div>
              </div>
            </div>
          </div>
        </div>

        {/* Integration Steps */}
        <div className="mb-24 text-center">
          <h2 className="text-3xl font-bold text-on-surface mb-16 tracking-tight">Strategic Implementation</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {[
              { n: '01', title: 'Initialization', desc: 'Add DeltaDrop to your browser via the Chrome Web Store in a single operation.' },
              { n: '02', title: 'Data Ingestion', desc: 'Browse normally. Our engine identifies value streams in the background.' },
              { n: '03', title: 'Execution', desc: 'Receive instant alerts when the market hits your designated target.' }
            ].map(step => (
              <div key={step.n} className="flex flex-col items-center group">
                <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center text-primary text-2xl font-black mb-8 group-hover:bg-primary group-hover:text-white transition-all">
                  {step.n}
                </div>
                <h3 className="text-xl font-bold text-on-surface mb-4">{step.title}</h3>
                <p className="text-on-surface-variant font-medium leading-relaxed max-w-xs">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ Section */}
        <div className="bg-white border border-outline-variant/40 rounded-[32px] p-12 shadow-sm">
          <h2 className="text-3xl font-bold text-on-surface mb-10 tracking-tight text-center">Protocol FAQ</h2>
          <div className="max-w-3xl mx-auto divide-y divide-outline-variant/20">
            <FaqItem defaultOpen question="Is the browser extension free to use?"
              answer="Yes, our core tracking engine and alert system are entirely free. We sustain the network through institutional data analytics partnerships." />
            <FaqItem question="Which browsers are officially supported?"
              answer="DeltaDrop v2.0 is verified for Chrome, Microsoft Edge, Brave, and Arc. Safari support is currently in restricted beta." />
            <FaqItem question="How does the AI determine the 'Buy' verdict?"
              answer="We analyze historical volatility, regional demand spikes, and upcoming retail event windows to determine the probability of a future price decrease." />
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

function BrowserMockup() {
  const [popupVisible, setPopupVisible] = useState(true)
  const sparkRef = useRef(null)

  useEffect(() => {
    if (popupVisible && sparkRef.current) {
      setTimeout(() => sparkRef.current?.classList.add('drawn'), 300)
    }
  }, [popupVisible])

  return (
    <div className="rounded-3xl overflow-hidden shadow-2xl border border-outline-variant/40 bg-white group">
      {/* Browser Bar */}
      <div className="bg-[#f8fafc] px-6 py-4 flex items-center gap-4 border-b border-outline-variant/40">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#ef4444]/20 border border-[#ef4444]/40" />
          <div className="w-3 h-3 rounded-full bg-[#f59e0b]/20 border border-[#f59e0b]/40" />
          <div className="w-3 h-3 rounded-full bg-[#10b981]/20 border border-[#10b981]/40" />
        </div>
        <div className="flex-1 bg-white border border-outline-variant/40 rounded-xl px-4 py-2 text-[10px] text-on-surface-variant font-bold flex items-center gap-2">
          <span className="material-symbols-outlined text-[10px] text-[#10b981] fill-icon">lock</span>
          amazon.in/Sony-WH-1000XM5/dp/B0CH...
        </div>
        <button onClick={() => setPopupVisible(!popupVisible)} className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-white shadow-lg shadow-primary/20 hover:scale-110 transition-transform">
          <span className="material-symbols-outlined text-lg">bolt</span>
        </button>
      </div>

      {/* Main Content Area */}
      <div className="p-8 relative min-h-[440px] bg-white">
        <div className="grid grid-cols-12 gap-8 mb-8">
          <div className="col-span-5 aspect-square bg-[#f8fafc] rounded-[32px] border border-outline-variant/20 flex items-center justify-center text-7xl shadow-inner">
            🎧
          </div>
          <div className="col-span-7 flex flex-col justify-center">
            <div className="h-4 bg-[#f1f5f9] rounded-full w-full mb-3" />
            <div className="h-4 bg-[#f1f5f9] rounded-full w-4/5 mb-8" />
            <div className="text-3xl font-black text-on-surface mb-1">₹24,990</div>
            <div className="text-sm font-bold text-on-surface-variant mb-8 line-through opacity-50">₹34,990</div>
            <div className="h-12 bg-[#f1f5f9] rounded-2xl w-full" />
          </div>
        </div>
        <div className="space-y-4">
          <div className="h-2 bg-[#f8fafc] rounded-full w-full" />
          <div className="h-2 bg-[#f8fafc] rounded-full w-11/12" />
        </div>

        {/* Floating Extension Popup */}
        <div className={`absolute top-6 right-6 w-[320px] bg-white rounded-[32px] shadow-2xl border border-outline-variant/40 overflow-hidden transition-all duration-500 ${popupVisible ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-4 scale-95 pointer-events-none'}`}>
          <div className="bg-primary p-6 text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-lg">bolt</span>
              <span className="text-[10px] font-black uppercase tracking-[0.2em]">Live Intelligence</span>
            </div>
            <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full text-[9px] font-black">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              SYNCED
            </div>
          </div>
          
          <div className="p-6 space-y-6">
            <div>
              <div className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-2">Market Floor</div>
              <div className="flex items-baseline gap-3">
                <span className="text-3xl font-black text-on-surface">₹24,990</span>
                <span className="text-sm font-bold text-on-surface-variant line-through opacity-40">₹34,990</span>
              </div>
            </div>

            <div className="bg-tertiary-container/10 p-4 rounded-2xl border border-tertiary-container/20 flex items-center gap-3">
              <span className="material-symbols-outlined text-tertiary-container">verified</span>
              <div>
                <div className="text-[10px] font-black text-tertiary-container uppercase tracking-widest">AI Verdict</div>
                <div className="text-sm font-bold text-on-surface">Strong Buy Signal</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                <span>Volatility Chart</span>
                <span>Best: Amazon</span>
              </div>
              <div className="h-16 bg-primary/5 rounded-2xl border border-outline-variant/20 flex items-center justify-center">
                 <svg viewBox="0 0 240 56" className="w-full h-12 px-4">
                  <path ref={sparkRef} className="sparkline-path"
                    d="M0,40 C20,38 30,44 50,36 C70,28 80,42 100,32 C120,22 130,38 150,28 C170,18 180,34 200,22 C215,14 225,18 240,14"
                    fill="none" stroke="#2563eb" strokeWidth="3" strokeLinecap="round" />
                </svg>
              </div>
            </div>

            <button className="w-full py-4 bg-primary text-white rounded-2xl font-bold text-sm shadow-lg shadow-primary/20">
              Set Price Alert
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function FluxChart() {
  const bars = [45, 65, 55, 90, 40, 70, 55, 80]
  return (
    <div className="h-32 flex items-end gap-2 px-4 bg-[#f8fafc] rounded-3xl overflow-hidden border border-outline-variant/20">
      {bars.map((h, i) => (
        <div key={i} className="flex-1 bg-primary/20 rounded-t-xl group hover:bg-primary transition-all cursor-pointer relative"
          style={{ height: `${h}%` }}>
          <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-on-surface text-white text-[9px] px-2 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            ₹{h*1000}
          </div>
        </div>
      ))}
    </div>
  )
}

function FaqItem({ question, answer, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="py-6">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between gap-4 text-left group">
        <span className="text-lg font-bold text-on-surface group-hover:text-primary transition-colors">{question}</span>
        <span className={`material-symbols-outlined text-outline group-hover:text-primary transition-transform ${open ? 'rotate-180' : ''}`}>
          expand_more
        </span>
      </button>
      <div className={`overflow-hidden transition-all duration-300 ${open ? 'max-h-40 mt-4' : 'max-h-0'}`}>
        <p className="text-on-surface-variant font-medium leading-relaxed">
          {answer}
        </p>
      </div>
    </div>
  )
}
