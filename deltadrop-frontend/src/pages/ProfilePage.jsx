import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import AppLayout from '../components/layout/AppLayout'
import AIButton from '../components/ui/AIButton'
import { toast } from '../components/ui/Toast'
import { auth } from '../services/api'


export default function ProfilePage() {
  const { user, logout, updateUser } = useAuth()
  const u = user || {}
  
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading]     = useState(false)
  const [name, setName]           = useState(u.full_name || u.username || '')
  const [email, setEmail]         = useState(u.email || '')

  async function handleSaveProfile() {
    setLoading(true)
    try {
      const res = await auth.updateMe({ full_name: name, email })
      updateUser(res.user)
      setIsEditing(false)
      toast('Profile updated successfully!', 'success')
    } catch (err) {
      toast(err.message || 'Failed to update profile', 'error')
    } finally {
      setLoading(false)
    }
  }

  function handleShareLedger() {
    toast('Ledger link copied to clipboard!', 'success')
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-8 py-12 bg-white min-h-screen selection:bg-primary/10">
        {/* Profile Header */}
        <div className="mb-12 animate-fade-up">
          <div className="bg-white rounded-[32px] border border-outline-variant/40 p-10 flex flex-col md:flex-row items-center gap-10 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -mr-32 -mt-32" />
            
            <div className="relative z-10">
              <div className="w-32 h-32 rounded-3xl overflow-hidden ring-4 ring-primary/5 shadow-md">
                {u.avatar ? (
                  <img src={u.avatar} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full bg-primary flex items-center justify-center text-4xl font-black text-white">
                    {(u.full_name || u.username || u.name || 'U')[0].toUpperCase()}
                  </div>
                )}
              </div>
              <button className="absolute -bottom-2 -right-2 w-10 h-10 bg-primary text-white rounded-xl shadow-lg border-2 border-white flex items-center justify-center hover:scale-110 transition-transform">
                <span className="material-symbols-outlined text-sm">photo_camera</span>
              </button>
            </div>

            <div className="flex-1 text-center md:text-left relative z-10">
              <h1 className="text-4xl font-black text-on-surface tracking-tight mb-2">
                {u.full_name || u.username || 'DeltaDrop User'}
              </h1>
              <div className="flex flex-wrap justify-center md:justify-start gap-3 items-center">
                <span className="text-sm font-bold text-on-surface-variant flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  Personal Index Protocol
                </span>
                <span className="w-1 h-1 rounded-full bg-outline-variant" />
                <span className="text-sm font-bold text-primary">Pro Account Activated</span>
              </div>
            </div>

            <div className="flex flex-wrap justify-center gap-3 relative z-10">
              <button onClick={handleShareLedger} className="px-6 py-3.5 bg-surface border border-outline-variant/40 rounded-2xl text-sm font-bold text-on-surface hover:bg-surface-container transition-all active:scale-95 shadow-sm">
                Share My Ledger
              </button>
              <button onClick={async () => { setLoading(true); try { await logout() } finally { setLoading(false) } }} disabled={loading} className="px-6 py-3.5 bg-white border border-red-100 rounded-2xl text-sm font-bold text-red-600 hover:bg-red-50 transition-all active:scale-95 disabled:opacity-50">
                Sign Out
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Account Settings */}
          <div className="lg:col-span-2 space-y-8">
            <div className="bg-white rounded-3xl border border-outline-variant/40 p-10 shadow-sm animate-fade-up">
              <div className="flex items-center justify-between mb-10">
                <h2 className="text-2xl font-bold text-on-surface tracking-tight">Account Information</h2>
                {isEditing ? (
                  <div className="flex gap-2">
                    <button onClick={() => setIsEditing(false)} className="px-5 py-2 text-sm font-bold text-on-surface-variant hover:text-on-surface">Cancel</button>
                    <button onClick={handleSaveProfile} disabled={loading} className="px-6 py-2 bg-primary text-white rounded-xl text-sm font-bold shadow-sm hover:bg-primary-container transition-all">
                      {loading ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                ) : (
                  <button onClick={() => setIsEditing(true)} className="px-6 py-2 bg-primary/10 text-primary rounded-xl text-sm font-bold hover:bg-primary/20 transition-all">
                    Edit Profile
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                <div className="space-y-3">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block">Legal Full Name</label>
                  {isEditing ? (
                    <input value={name} onChange={e => setName(e.target.value)}
                      className="w-full bg-white border border-primary/20 rounded-2xl px-5 py-4 text-sm font-bold text-on-surface focus:ring-4 focus:ring-primary/5 focus:border-primary outline-none transition-all shadow-inner" />
                  ) : (
                    <div className="w-full bg-surface/50 border border-transparent rounded-2xl px-5 py-4 text-sm font-bold text-on-surface">
                      {name}
                    </div>
                  )}
                </div>
                <div className="space-y-3">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block">Primary Sync Email</label>
                  {isEditing ? (
                    <input value={email} onChange={e => setEmail(e.target.value)} type="email"
                      className="w-full bg-white border border-primary/20 rounded-2xl px-5 py-4 text-sm font-bold text-on-surface focus:ring-4 focus:ring-primary/5 focus:border-primary outline-none transition-all shadow-inner" />
                  ) : (
                    <div className="w-full bg-surface/50 border border-transparent rounded-2xl px-5 py-4 text-sm font-bold text-on-surface">
                      {email}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Notification Control */}
            <div className="bg-white rounded-3xl border border-outline-variant/40 p-10 shadow-sm animate-fade-up" style={{ animationDelay: '0.1s' }}>
              <h2 className="text-2xl font-bold text-on-surface tracking-tight mb-8">Intelligence Preferences</h2>
              <div className="space-y-6">
                {[
                  { label: 'Real-time Price Indexing', desc: 'Instant push notifications for tracked retailers', on: true },
                  { label: 'Market Volatility Reports', desc: 'Weekly deep-dive into regional price swings', on: true },
                  { label: 'Network Data Contribution', desc: 'Contribute anonymized data to global liquidity ledger', on: false },
                ].map((p, i) => (
                  <div key={i} className="flex items-center justify-between p-6 bg-surface/30 rounded-2xl border border-outline-variant/10 group hover:border-primary/20 transition-all">
                    <div>
                      <div className="font-bold text-on-surface mb-1">{p.label}</div>
                      <div className="text-sm text-on-surface-variant font-medium">{p.desc}</div>
                    </div>
                    <div className={`w-12 h-6 rounded-full flex items-center px-1 cursor-pointer transition-all ${p.on ? 'bg-primary' : 'bg-outline-variant/40'}`}>
                      <div className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${p.on ? 'translate-x-6' : ''}`}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Connected Services */}
          <div className="space-y-8 animate-fade-up" style={{ animationDelay: '0.2s' }}>
            <div className="bg-white rounded-3xl border border-outline-variant/40 p-10 shadow-sm h-full">
              <h2 className="text-2xl font-bold text-on-surface tracking-tight mb-8">Sync Services</h2>
              <div className="space-y-4">
                <div className="p-6 bg-white border border-[#4285F4]/20 rounded-2xl relative overflow-hidden group shadow-sm">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-[#4285F4]" />
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-white border border-outline-variant/40 flex items-center justify-center font-black text-[#4285F4] shadow-inner text-lg">G</div>
                      <div>
                        <div className="font-bold text-sm text-on-surface">Google Account</div>
                        <div className="text-xs font-bold text-on-surface-variant uppercase tracking-widest mt-0.5">Active Sync</div>
                      </div>
                    </div>
                    <button className="text-xs font-black text-[#ea4335] uppercase tracking-widest hover:underline opacity-0 group-hover:opacity-100 transition-opacity">De-sync</button>
                  </div>
                </div>

                <div className="p-6 bg-white border border-outline-variant/40 rounded-2xl relative overflow-hidden group shadow-sm opacity-60">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-black flex items-center justify-center text-white shadow-inner">
                        <span className="material-symbols-outlined text-xl">apple</span>
                      </div>
                      <div>
                        <div className="font-bold text-sm text-on-surface">Apple ID</div>
                        <div className="text-xs font-bold text-outline uppercase tracking-widest mt-0.5">Offline</div>
                      </div>
                    </div>
                    <button className="text-xs font-black text-primary uppercase tracking-widest hover:underline">Link</button>
                  </div>
                </div>
              </div>

              <div className="mt-12 p-6 bg-primary/5 rounded-2xl border border-primary/10">
                <div className="flex items-center gap-3 mb-4">
                  <span className="material-symbols-outlined text-primary">security</span>
                  <span className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">Protocol Integrity</span>
                </div>
                <p className="text-sm font-medium text-on-surface-variant leading-relaxed">
                  Your biometric and credential data is encrypted at rest using AES-256 protocols.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <AIButton position="fixed" />
    </AppLayout>
  )
}
