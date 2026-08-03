import { Egg, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import humptyLogo from '../assets/Humpty_Dumpty.webp'

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { login, user, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  if (!isLoading && user) return <Navigate to="/dashboard" replace />

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const result = await login({ username: username.trim().toLowerCase(), password })
      if (result.requiresPasswordChange) navigate('/change-temporary-password', { replace: true })
      else navigate('/dashboard', { replace: true })
    } catch (requestError) {
      setError(requestError.message || 'Unable to sign in.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="grid min-h-screen bg-cream-100 lg:grid-cols-2">
      <section className="hidden bg-gradient-to-br from-forest-950 via-forest-900 to-forest-700 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3 text-xl font-bold"><span className="grid h-11 w-11 place-items-center rounded-xl bg-cream-50 text-amber-500"><img src={humptyLogo} alt="Humpty Logo" className="h-full w-full object-contain" /></span>EggMinistrator</div>
        <div className="max-w-lg"><p className="mb-5 inline-flex items-center gap-2 rounded-full border border-green-500/40 bg-green-800/50 px-3 py-1 text-sm text-green-100"><ShieldCheck size={16} />Smart egg inspection management</p><h1 className="text-5xl font-bold leading-tight">Quality insights for every egg.</h1></div>
        <p className="text-sm text-green-200">EggMinistrator • LH Deli inspection system</p>
      </section>
      <section className="flex items-center justify-center p-5 sm:p-10">
        <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-green-950/8 sm:p-8">
          <div className="mb-8 lg:hidden"><div className="flex items-center gap-2 text-xl font-bold text-forest-900"><span className="grid h-9 w-9 place-items-center rounded-lg bg-green-50 text-amber-500"><img src={humptyLogo} alt="Humpty Logo" className="h-full w-full object-contain" /></span>EggMinistrator</div></div>
          <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1><p className="mt-1 text-sm text-slate-500">Sign in to access the inspection dashboard.</p>
          {location.state?.passwordChangeSuccess && <p className="mt-5 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">Password updated. Sign in with your new password.</p>}
          {error && <p role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <div className="mt-7 space-y-4">
            <label className="block"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Username</span><span className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-3 focus-within:border-green-600 focus-within:ring-2 focus-within:ring-green-100"><Mail size={18} className="text-slate-400" /><input required value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" className="w-full outline-none" /></span></label>
            <label className="block"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Password</span><span className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-3 focus-within:border-green-600 focus-within:ring-2 focus-within:ring-green-100"><LockKeyhole size={18} className="text-slate-400" /><input required value={password} onChange={(event) => setPassword(event.target.value)} type={showPassword ? 'text' : 'password'} autoComplete="current-password" className="w-full outline-none" /><button type="button" onClick={() => setShowPassword((current) => !current)} className="text-slate-400 hover:text-slate-700" aria-label="Show or hide password">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></span></label>
          </div>
          <button disabled={isSubmitting || isLoading} className="mt-6 w-full rounded-lg bg-forest-800 px-4 py-3 font-semibold text-white shadow-sm hover:bg-forest-900 disabled:cursor-not-allowed disabled:opacity-60">{isSubmitting ? 'Signing in…' : 'Sign in'}</button>
        </form>
      </section>
    </main>
  )
}
