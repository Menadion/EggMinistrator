import { CheckCircle2, Eye, EyeOff, LockKeyhole } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const apiBaseUrl = 'http://localhost:3001'

const passwordChecks = (password) => [
  { label: 'At least 8 characters', passed: password.length >= 8 },
  { label: 'One uppercase letter', passed: /[A-Z]/.test(password) },
  { label: 'One lowercase letter', passed: /[a-z]/.test(password) },
  { label: 'One number', passed: /\d/.test(password) },
  { label: 'One special character', passed: /[^A-Za-z0-9]/.test(password) },
]

export default function ChangeTemporaryPasswordPage() {
  const { passwordChangeTokenKey } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const passwordChangeToken =
    location.state?.passwordChangeToken || sessionStorage.getItem(passwordChangeTokenKey)
  const checks = useMemo(() => passwordChecks(newPassword), [newPassword])
  const strength = checks.filter((check) => check.passed).length

  if (!passwordChangeToken) return <Navigate to="/" replace />

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }
    if (strength !== checks.length) {
      setError('Your new password does not meet all requirements.')
      return
    }
    setIsSubmitting(true)
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/change-temporary-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passwordChangeToken, newPassword, confirmPassword }),
      })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.error || 'Unable to change your password.')
      sessionStorage.removeItem(passwordChangeTokenKey)
      navigate('/', { replace: true, state: { passwordChangeSuccess: true } })
    } catch (requestError) {
      setError(requestError.message || 'Unable to change your password.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const fieldClass =
    'w-full rounded-lg border border-slate-200 py-3 pl-10 pr-11 text-slate-800 outline-none focus:border-forest-600 focus:ring-2 focus:ring-forest-100'

  return (
    <main className="grid min-h-screen place-items-center bg-cream-100 p-5">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-forest-950/8 sm:p-8"
      >
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-forest-100 text-forest-800">
          <LockKeyhole size={22} />
        </div>
        <h1 className="mt-5 text-2xl font-bold text-slate-900">Set a new password</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Your temporary password is valid only for this first sign-in. Create a new password to
          continue.
        </p>
        {error && (
          <p
            role="alert"
            className="mt-5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </p>
        )}
        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">New password</span>
            <span className="relative block">
              <LockKeyhole className="absolute left-3 top-3.5 text-slate-400" size={18} />
              <input
                required
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                type={showNewPassword ? 'text' : 'password'}
                autoComplete="new-password"
                className={fieldClass}
              />
              <button
                type="button"
                onClick={() => setShowNewPassword((current) => !current)}
                className="absolute right-3 top-3 text-slate-400 hover:text-slate-700"
                aria-label="Show or hide new password"
              >
                {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </span>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">
              Confirm new password
            </span>
            <span className="relative block">
              <LockKeyhole className="absolute left-3 top-3.5 text-slate-400" size={18} />
              <input
                required
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                className={fieldClass}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword((current) => !current)}
                className="absolute right-3 top-3 text-slate-400 hover:text-slate-700"
                aria-label="Show or hide confirmation password"
              >
                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </span>
          </label>
        </div>
        <section className="mt-5 rounded-lg bg-slate-50 p-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-700">Password strength</p>
            <p className="text-xs font-semibold text-slate-500">{strength}/5</p>
          </div>
          <div className="mt-2 flex gap-1">
            {checks.map((check) => (
              <span
                key={check.label}
                className={`h-1.5 flex-1 rounded-full ${check.passed ? 'bg-forest-600' : 'bg-slate-200'}`}
              />
            ))}
          </div>
          <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
            {checks.map((check) => (
              <li key={check.label} className="flex items-center gap-2">
                <CheckCircle2
                  size={14}
                  className={check.passed ? 'text-forest-600' : 'text-slate-300'}
                />
                {check.label}
              </li>
            ))}
          </ul>
        </section>
        <button
          disabled={isSubmitting}
          className="mt-6 w-full rounded-lg bg-forest-800 px-4 py-3 font-semibold text-white shadow-sm hover:bg-forest-900 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? 'Updating password…' : 'Update password'}
        </button>
      </form>
    </main>
  )
}
