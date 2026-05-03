import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { auth } from '../services/api'
import { toast } from '../components/ui/Toast'
import { useGoogleLogin } from '@react-oauth/google'

const INTERESTS = ['Electronics','Smartphones','Laptops','Fashion','Shoes','Appliances','Cameras','Gaming']

function GoogleLoginButton({ onSuccess, onError }) {
  const login = useGoogleLogin({ onSuccess, onError })
  return (
    <button onClick={() => login()} type="button"
      className="max-w-sm w-full flex items-center justify-center gap-3 py-2.5 mb-3 bg-surface-container-low rounded-md text-sm font-semibold text-on-surface hover:bg-surface-container-high transition-colors relative overflow-hidden">
      <svg className="w-4 h-4" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" /><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" /><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" /><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" /></svg>
      Continue with Google
    </button>
  )
}

export default function RegisterPage() {
  const [searchParams] = useSearchParams()
  const [form, setForm]           = useState({ first:'', last:'', email: searchParams.get('email') || '', password:'' })
  const [interests, setInterests] = useState(new Set())
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const { login }                 = useAuth()
  const navigate                  = useNavigate()

  const handleGoogleSuccess = async (tokenResponse) => {
    setLoading(true)
    try {
      const tokenPayload = tokenResponse?.credential
        ? { credential: tokenResponse.credential }
        : { token: tokenResponse?.access_token }
      if (!tokenPayload.token && !tokenPayload.credential) {
        throw new Error('Google sign-in returned no token.')
      }

      const data = await auth.googleLogin(tokenPayload)
      login(data.user, data.access_token, data.refresh_token)
      toast(`Welcome, ${data.user?.full_name || data.user?.username || 'User'}!`, 'success')
      navigate('/discover')
    } catch (err) {
      setError(err.message || 'Google Sign-Up failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleError = () => toast('Google Sign-Up failed or was cancelled.', 'error')

  const handleGoogleClick = () => {
    toast('Google OAuth not configured. Add VITE_GOOGLE_CLIENT_ID', 'error')
  }

  const handleAppleLogin = () => {
    toast('Apple Sign-In coming soon', 'info')
  }

  const toggleInterest = (tag) => setInterests(prev => {
    const n = new Set(prev); n.has(tag) ? n.delete(tag) : n.add(tag); return n
  })

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.first || !form.email || !form.password) { setError('Please fill in all fields.'); return }
    if (form.password.length < 8) { setError('Password must be at least 8 characters long.'); return }
    setLoading(true)
    setError('')

    const normalizedEmail = form.email.toLowerCase().trim()
    try {
      const data = await auth.register({
        email:     normalizedEmail,
        username:  normalizedEmail.split('@')[0],
        password:  form.password,
        full_name: `${form.first} ${form.last}`.trim(),
      })
      
      // Auto-login instantly
      const loginData = await auth.login({ email: normalizedEmail, password: form.password })
      login(loginData.user, loginData.access_token, loginData.refresh_token)
      
      if (interests.size > 0 && loginData.user?.id) {
        localStorage.setItem(`dd_preferences_${loginData.user.id}`, JSON.stringify(Array.from(interests)))
      }

      toast('Account created successfully! Welcome to DeltaDrop.', 'success')
      navigate('/discover')

    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-white font-body selection:bg-primary/10">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-[40%] bg-surface border-r border-outline-variant/40 p-16">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-base">bolt</span>
          </div>
          <div className="font-headline font-bold text-xl text-on-surface tracking-tight">DeltaDrop</div>
        </div>

        <div>
          <h1 className="text-4xl font-extrabold text-on-surface mb-6 tracking-tight leading-tight">
            Join the precision <span className="text-primary italic">market network.</span>
          </h1>
          <p className="text-on-surface-variant text-lg leading-relaxed max-w-xs mb-10">
            Establish your account to access real-time indexing and institutional-grade alerts.
          </p>
          
          <div className="space-y-4">
            {['Amazon.in','Flipkart','Reliance Digital','Myntra','Croma','Tata CLiQ'].map(r => (
              <div key={r} className="flex items-center gap-3 text-sm font-bold text-on-surface-variant">
                <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                {r}
              </div>
            ))}
          </div>
        </div>

        <div className="text-xs font-medium text-outline">
          Free forever. No credit card required. © 2026
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 bg-white overflow-y-auto py-12">
        <div className="w-full max-w-sm">
          <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-on-surface-variant hover:text-on-surface mb-12 transition-colors">
            <span className="material-symbols-outlined text-base">arrow_back</span>
            Back to home
          </Link>

          <h2 className="text-3xl font-extrabold text-on-surface mb-2 tracking-tight">Create account</h2>
          <p className="text-on-surface-variant mb-8 font-medium">Start tracking in less than 30 seconds.</p>

          {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl border border-red-100 mb-6 font-medium">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-5 animate-fade-up">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-2">First Name</label>
                <input name="firstName" autoComplete="given-name" value={form.first} onChange={e => setForm(f=>({...f,first:e.target.value}))} placeholder="Arjun"
                  className="w-full bg-surface border border-outline-variant/40 rounded-xl px-4 py-3 text-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all" />
              </div>
              <div>
                <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-2">Last Name</label>
                <input name="lastName" autoComplete="family-name" value={form.last} onChange={e => setForm(f=>({...f,last:e.target.value}))} placeholder="Sharma"
                  className="w-full bg-surface border border-outline-variant/40 rounded-xl px-4 py-3 text-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all" />
              </div>
            </div>
            <div>
              <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-2">Email Address</label>
              <input name="email" type="email" autoComplete="email" value={form.email} onChange={e => setForm(f=>({...f,email:e.target.value}))} placeholder="arjun@email.com"
                className="w-full bg-surface border border-outline-variant/40 rounded-xl px-4 py-3 text-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all" />
            </div>
            <div>
              <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-2">Password</label>
              <input name="newPassword" type="password" autoComplete="new-password" value={form.password} onChange={e => setForm(f=>({...f,password:e.target.value}))} placeholder="Min. 8 characters"
                className="w-full bg-surface border border-outline-variant/40 rounded-xl px-4 py-3 text-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all" />
            </div>
            
            <div>
              <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-3">Interests</label>
              <div className="flex flex-wrap gap-2">
                {INTERESTS.map(tag => (
                  <button key={tag} type="button" onClick={() => toggleInterest(tag)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border
                      ${interests.has(tag) ? 'bg-primary text-white border-primary shadow-sm' : 'bg-surface border-outline-variant/40 text-on-surface-variant hover:border-primary/40'}`}>
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-primary text-white py-3.5 rounded-xl font-bold text-sm hover:bg-primary-container active:scale-95 transition-all shadow-sm disabled:opacity-60">
              {loading ? 'Establishing account…' : 'Create Free Account'}
            </button>
          </form>

          <div className="flex items-center gap-3 my-8">
            <div className="flex-1 h-px bg-outline-variant/30" />
            <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-[0.2em]">OR</span>
            <div className="flex-1 h-px bg-outline-variant/30" />
          </div>

          <div className="space-y-3">
            {['Google', 'Apple ID'].map(provider => {
              if (provider === 'Google') {
                return import.meta.env.VITE_GOOGLE_CLIENT_ID ? (
                  <GoogleLoginButton key={provider} onSuccess={handleGoogleSuccess} onError={handleGoogleError} />
                ) : (
                  <button key={provider} onClick={handleGoogleClick} type="button"
                    className="w-full flex items-center justify-center gap-3 py-3 border border-outline-variant/40 rounded-xl text-sm font-bold text-on-surface hover:bg-surface transition-colors">
                    <svg className="w-4 h-4" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" /><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" /><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" /><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" /></svg>
                    Continue with Google
                  </button>
                )
              }
              return (
                <button key={provider} disabled type="button"
                  className="w-full flex items-center justify-center gap-3 py-3 border border-outline-variant/40 rounded-xl text-sm font-bold text-on-surface hover:bg-surface transition-colors opacity-50 cursor-not-allowed">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.04 2.26-.74 3.58-.71 1.73.11 2.87.68 3.75 1.7-3.08 1.95-2.58 5.75.52 7.02-.75 1.83-1.8 3.33-2.93 4.16zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/></svg>
                  Apple ID (Coming soon)
                </button>
              )
            })}
          </div>

          <p className="text-sm text-on-surface-variant mt-10 text-center font-medium">
            Already have an account?{' '}
            <Link to="/login" className="text-primary font-bold hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
