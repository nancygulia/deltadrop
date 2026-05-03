import { useState, useEffect } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { auth } from '../services/api'
import { toast } from '../components/ui/Toast'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [password, setPassword]   = useState('')
  const [confirm, setConfirm]     = useState('')
  const [showPw, setShowPw]       = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [success, setSuccess]     = useState(false)

  // If no token in URL, redirect to login
  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!password || !confirm) { setError('Please fill in all fields.'); return }
    if (password.length < 8)   { setError('Password must be at least 8 characters.'); return }
    if (password !== confirm)  { setError('Passwords do not match.'); return }

    setLoading(true)
    try {
      await auth.resetPassword(token, password)
      setSuccess(true)
      toast('Password reset! You can now sign in.', 'success')
    } catch (err) {
      setError(err.message || 'Reset link is invalid or has expired. Please request a new one.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center text-white mx-auto mb-4 shadow-lg">
            <span className="text-3xl font-black font-headline">D</span>
          </div>
          <h1 className="font-headline text-2xl font-extrabold text-on-surface">Reset your password</h1>
          <p className="text-on-surface-variant text-sm mt-1">Choose a new password for your DeltaDrop account.</p>
        </div>

        <div className="bg-white rounded-3xl shadow-ambient border border-outline-variant/40 p-10 animate-fade-up" style={{ animationDelay: '0.1s' }}>
          {success ? (
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="material-symbols-outlined text-green-600 text-3xl">check_circle</span>
              </div>
              <h2 className="font-bold text-xl text-on-surface mb-2">Password updated!</h2>
              <p className="text-on-surface-variant text-sm mb-6">Your password has been successfully reset. You can now sign in with your new password.</p>
              <Link to="/login"
                className="inline-block bg-primary text-white px-10 py-3.5 rounded-2xl font-bold text-sm hover:bg-primary-container transition-all shadow-md">
                Sign In
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex items-center gap-2">
                  <span className="material-symbols-outlined text-red-500 text-lg">error</span>
                  {error}
                </div>
              )}

              <div>
                <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block mb-1.5">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    autoFocus
                    className="w-full bg-white border border-outline-variant/40 rounded-2xl px-5 py-4 text-sm font-medium text-on-surface outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary pr-14 shadow-sm"
                  />
                  <button type="button" onClick={() => setShowPw(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-on-surface-variant font-semibold hover:text-on-surface">
                    {showPw ? 'Hide' : 'Show'}
                  </button>
                </div>
                {password.length > 0 && (
                  <div className="mt-2 flex gap-1">
                    {[...Array(4)].map((_, i) => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${
                        password.length >= [8, 10, 12, 16][i]
                          ? i < 2 ? 'bg-yellow-400' : i === 2 ? 'bg-green-400' : 'bg-green-600'
                          : 'bg-surface-container-high'
                      }`} />
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block mb-1.5">
                  Confirm New Password
                </label>
                <input
                  type={showPw ? 'text' : 'password'}
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  placeholder="Repeat password"
                  className={`w-full bg-white border border-outline-variant/40 rounded-2xl px-5 py-4 text-sm font-medium text-on-surface outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary shadow-sm ${
                    confirm && confirm !== password ? 'ring-2 ring-red-400/40 border-red-400' : ''
                  }`}
                />
                {confirm && confirm !== password && (
                  <p className="text-xs text-red-500 mt-1">Passwords don't match</p>
                )}
              </div>

              <button
                type="submit"
                disabled={loading || (confirm && confirm !== password)}
                className="w-full grad-primary text-on-primary py-3 rounded-xl font-bold text-sm hover:opacity-90 active:scale-95 transition-all disabled:opacity-60 mt-2"
              >
                {loading ? 'Resetting…' : 'Reset Password'}
              </button>

              <p className="text-center text-sm text-on-surface-variant pt-1">
                Remembered it?{' '}
                <Link to="/login" className="text-primary font-bold hover:underline">Sign in</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
