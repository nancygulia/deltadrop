import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { auth } from '../services/api'
import { toast } from '../components/ui/Toast'
import { useGoogleLogin } from '@react-oauth/google'

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

export default function LoginPage() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [forgotMode, setForgotMode]   = useState(false)
  const [forgotSent, setForgotSent]   = useState(false)

  const { login, isLoggedIn } = useAuth()
  const navigate = useNavigate()

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
      toast(`Welcome back, ${data.user?.full_name || data.user?.username || 'User'}!`, 'success')
      navigate('/discover')
    } catch (err) {
      setError(err.message || 'Google Sign-In failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleError = () => toast('Google Sign-In failed or was cancelled.', 'error')

  const handleGoogleClick = () => {
    toast('Google OAuth not configured. Add VITE_GOOGLE_CLIENT_ID', 'error')
  }

  const handleAppleLogin = () => {
    toast('Apple Sign-In coming soon', 'info')
  }

  if (isLoggedIn) { navigate('/discover'); return null }

  // ── Forgot Password (real API call) ────────────────────────────────────────
  async function handleForgot(e) {
    e.preventDefault()
    setError('')
    if (!email) { setError('Please enter your email address.'); return }
    setLoading(true)
    try {
      await auth.forgotPassword(email.toLowerCase().trim())
      setForgotSent(true)
      toast('Reset link sent to your email.', 'success')
    } catch (err) {
      setError(err.message || 'Failed to send reset link. Try again.')
    } finally {
      setLoading(false)
    }
  }

  // ── Real Login (via api.js with token refresh support) ─────────────────────
  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!email || !password) { setError('Please fill in all fields.'); return }
    setLoading(true)
    try {
      const normalizedEmail = email.toLowerCase().trim()
      const data = await auth.login({ email: normalizedEmail, password })
      login(data.user, data.access_token, data.refresh_token)
      toast(`Welcome back, ${data.user.full_name || data.user.username}!`, 'success')
      navigate('/discover')
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.')
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
            Institutional tracking for the <span className="text-primary italic">modern consumer.</span>
          </h1>
          <p className="text-on-surface-variant text-lg leading-relaxed max-w-xs mb-10">
            Secure the best entry points across 5,000+ Indian retailers with precision indexing.
          </p>
          
          <div className="space-y-6">
            {[
              { label: 'Avg savings/month', val: '₹4,200' },
              { label: 'Retailers tracked', val: '5,000+' },
              { label: 'Products in ledger', val: '2M+' }
            ].map(s => (
              <div key={s.label} className="flex items-center gap-4">
                <div className="w-px h-10 bg-outline-variant/60" />
                <div>
                  <div className="text-2xl font-bold text-on-surface">{s.val}</div>
                  <div className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">{s.label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="text-xs font-medium text-outline">
          Intelligence Provided by Precision Ledger Protocols © 2026
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 bg-white">
        <div className="w-full max-w-sm">
          <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-on-surface-variant hover:text-on-surface mb-12 transition-colors">
            <span className="material-symbols-outlined text-base">arrow_back</span>
            Back to home
          </Link>

          <h2 className="text-3xl font-extrabold text-on-surface mb-2 tracking-tight">Welcome back</h2>
          <p className="text-on-surface-variant mb-8">Sign in to your DeltaDrop account.</p>

          {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl border border-red-100 mb-6 font-medium">{error}</div>}

          {forgotMode ? (
            forgotSent ? (
              <div className="animate-fade-up">
                <div className="bg-primary/5 border border-primary/10 rounded-2xl p-6 mb-6 text-center">
                  <span className="material-symbols-outlined text-primary text-4xl mb-4 block">mark_email_read</span>
                  <p className="font-bold text-on-surface mb-2">Check your inbox</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed">
                    We sent a reset link to <strong className="text-on-surface">{email}</strong>.
                  </p>
                </div>
                <button onClick={() => { setForgotMode(false); setForgotSent(false); setError('') }}
                  className="w-full py-3 text-sm font-bold text-primary hover:bg-primary/5 rounded-xl transition-all">
                  Return to Sign In
                </button>
              </div>
            ) : (
              <form onSubmit={handleForgot} className="space-y-5 animate-fade-up">
                <div>
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-2">Account Email</label>
                  <input name="email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="name@email.com" autoFocus
                    className="w-full bg-surface border border-outline-variant/40 rounded-xl px-4 py-3 text-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all" />
                </div>
                <button type="submit" disabled={loading}
                  className="w-full bg-primary text-white py-3.5 rounded-xl font-bold text-sm hover:bg-primary-container active:scale-95 transition-all shadow-sm disabled:opacity-60">
                  {loading ? 'Sending link…' : 'Send Reset Link'}
                </button>
                <p className="text-sm text-center text-on-surface-variant mt-4 cursor-pointer font-semibold hover:text-on-surface"
                  onClick={() => { setForgotMode(false); setError('') }}>
                  Return to Sign In
                </p>
              </form>
            )
          ) : (
            <div className="animate-fade-up">
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest block mb-2">Email Address</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="name@email.com" autoFocus
                    className="w-full bg-surface border border-outline-variant/40 rounded-xl px-4 py-3 text-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all" />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <label className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">Password</label>
                    <span className="text-xs text-primary font-bold cursor-pointer hover:underline"
                      onClick={() => { setForgotMode(true); setError('') }}>Forgot password?</span>
                  </div>
                  <div className="relative">
                    <input name="password" type={showPw ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-surface border border-outline-variant/40 rounded-xl px-4 py-3 text-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 outline-none transition-all pr-14" />
                    <button type="button" onClick={() => setShowPw(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-on-surface-variant font-bold hover:text-on-surface">
                      {showPw ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>
                <button type="submit" disabled={loading}
                  className="w-full bg-primary text-white py-3.5 rounded-xl font-bold text-sm hover:bg-primary-container active:scale-95 transition-all shadow-sm disabled:opacity-60">
                  {loading ? 'Signing in…' : 'Sign In'}
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
                Don't have an account?{' '}
                <Link to="/register" className="text-primary font-bold hover:underline">Create one free</Link>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
