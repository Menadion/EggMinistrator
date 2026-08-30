import { Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import eggministratorLogo from '../assets/logo.svg'
import loginHero from '../assets/login-hero.jpg'

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
    <main className="relative min-h-screen overflow-hidden bg-[#0B5D3B]">
      <div
        className="absolute inset-x-0 top-0 h-[58%] bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: `linear-gradient(90deg, rgba(3, 48, 24, 0.78) 0%, rgba(8, 63, 42, 0.48) 44%, rgba(8, 63, 42, 0.02) 100%), url("${loginHero}")`,
        }}
      />
      <div className="absolute inset-x-0 bottom-0 top-[58%] bg-[#0B5D3B]" />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 left-0 h-56 w-56 opacity-25"
        style={{
          backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.62) 2px, transparent 2px)',
          backgroundSize: '12px 12px',
          maskImage: 'radial-gradient(circle at 0% 100%, black 0%, transparent 72%)',
          WebkitMaskImage: 'radial-gradient(circle at 0% 100%, black 0%, transparent 72%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 right-0 h-56 w-56 opacity-25"
        style={{
          backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.62) 2px, transparent 2px)',
          backgroundSize: '12px 12px',
          maskImage: 'radial-gradient(circle at 100% 100%, black 0%, transparent 72%)',
          WebkitMaskImage: 'radial-gradient(circle at 100% 100%, black 0%, transparent 72%)',
        }}
      />

      <div className="pointer-events-none absolute left-12 top-[28%] z-10 hidden max-w-[360px] text-white lg:block">
        <h1 className="text-5xl font-bold leading-tight tracking-tight">
          Quality insights
          <br />
          for every egg.
        </h1>
        <p className="mt-5 border-l-2 border-green-300 pl-4 text-base leading-6 text-green-50">
          Monitor egg inspections, quality results, reports, and analytics in one centralized
          system.
        </p>
      </div>

      <div className="relative z-20 flex min-h-screen flex-col px-6 py-7 sm:px-10 sm:py-8 lg:px-12 lg:py-10">
        <header className="flex items-center gap-4 text-xl font-bold text-white">
          <span className="grid h-14 w-14 place-items-center overflow-hidden">
            <img
              src={eggministratorLogo}
              alt="Eggministrator logo"
              className="h-full w-full object-contain"
            />
          </span>
          EggMinistrator
        </header>

        <div className="flex flex-1 items-center justify-center py-10 lg:py-14">
          <form
            onSubmit={submit}
            className="w-full max-w-sm rounded-2xl border border-white/80 bg-white p-6 shadow-2xl shadow-[#083F2A]/30 sm:p-7 lg:translate-y-8"
          >
            <div className="text-center">
              <p className="inline-flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-3 py-1 text-xs font-semibold text-[#0B5D3B]">
                <ShieldCheck size={15} />
                Smart egg inspection management
              </p>
              <h1 className="mt-4 text-2xl font-bold text-[#172033]">Welcome back</h1>
            </div>
            {location.state?.passwordChangeSuccess && (
              <p className="mt-5 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
                Password updated. Sign in with your new password.
              </p>
            )}
            {error && (
              <p
                role="alert"
                className="mt-5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {error}
              </p>
            )}
            <div className="mt-5 space-y-4 border-t border-slate-100 pt-5">
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#172033]">Username</span>
                <span className="flex items-center gap-2 rounded-lg border border-[#D9E0E7] px-3 py-3 focus-within:border-[#0B5D3B] focus-within:ring-2 focus-within:ring-[#0B5D3B]/15">
                  <Mail size={18} className="text-[#64748B]" />
                  <input
                    required
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    autoComplete="username"
                    placeholder="Enter your username"
                    className="w-full bg-transparent text-[#172033] outline-none placeholder:text-slate-400"
                  />
                </span>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#172033]">Password</span>
                <span className="flex items-center gap-2 rounded-lg border border-[#D9E0E7] px-3 py-3 focus-within:border-[#0B5D3B] focus-within:ring-2 focus-within:ring-[#0B5D3B]/15">
                  <LockKeyhole size={18} className="text-[#64748B]" />
                  <input
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    className="w-full bg-transparent text-[#172033] outline-none placeholder:text-slate-400"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    className="text-[#64748B] hover:text-[#0B5D3B]"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </span>
              </label>
            </div>
            <button
              disabled={isSubmitting || isLoading}
              className="mt-6 w-full rounded-lg bg-[#0B5D3B] px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-[#083F2A] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>

        <footer className="mb-1 text-xs text-white/75 sm:text-sm">
          EggMinistrator • Leong Hup PH Inspection System
        </footer>
      </div>
    </main>
  )
}
