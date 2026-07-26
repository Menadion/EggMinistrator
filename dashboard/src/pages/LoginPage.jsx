import { Egg, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import humptyLogo from "../assets/Humpty_Dumpty.webp";

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const navigate = useNavigate()
  const submit = (event) => {
    event.preventDefault()
    navigate('/dashboard')
  }

  return (
    <main className="grid min-h-screen bg-cream-100 lg:grid-cols-2">
      <section className="hidden bg-gradient-to-br from-forest-950 via-forest-900 to-forest-700 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3 text-xl font-bold"><span className="grid h-11 w-11 place-items-center rounded-xl bg-cream-50 text-amber-500"><img src={humptyLogo} alt="Humpty Logo" className="h-full w-full object-contain" /></span>EggMinistrator</div>
        <div className="max-w-lg"><p className="mb-5 inline-flex items-center gap-2 rounded-full border border-green-500/40 bg-green-800/50 px-3 py-1 text-sm text-green-100"><ShieldCheck size={16} />Smart egg inspection management</p><h1 className="text-5xl font-bold leading-tight">Quality insights for every egg.</h1><p className="mt-5 text-lg leading-8 text-green-100"></p></div>
        <p className="text-sm text-green-200">EggMinistrator • LH Deli inspection system</p>
      </section>
      <section className="flex items-center justify-center p-5 sm:p-10">
        <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-green-950/8 sm:p-8">
          <div className="mb-8 lg:hidden"><div className="flex items-center gap-2 text-xl font-bold text-forest-900"><span className="grid h-9 w-9 place-items-center rounded-lg bg-green-50 text-amber-500"><img src={humptyLogo} alt="Humpty Logo" className="h-full w-full object-contain" /></span>EggMinistrator</div></div>
          <h2 className="text-2xl font-bold text-slate-900">Welcome back</h2><p className="mt-1 text-sm text-slate-500">Sign in to access the inspection dashboard.</p>
          <div className="mt-7 space-y-4">
            <label className="block"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Email or username</span><span className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-3 focus-within:border-green-600 focus-within:ring-2 focus-within:ring-green-100"><Mail size={18} className="text-slate-400" /><input required defaultValue="admin" className="w-full outline-none" /></span></label>
            <label className="block"><span className="mb-1.5 block text-sm font-semibold text-slate-700">Password</span><span className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-3 focus-within:border-green-600 focus-within:ring-2 focus-within:ring-green-100"><LockKeyhole size={18} className="text-slate-400" /><input required type={showPassword ? 'text' : 'password'} defaultValue="password" className="w-full outline-none" /><button type="button" onClick={() => setShowPassword(!showPassword)} className="text-slate-400 hover:text-slate-700">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></span></label>
          </div>
          <button className="mt-6 w-full rounded-lg bg-forest-800 px-4 py-3 font-semibold text-white shadow-sm hover:bg-forest-900">Sign in</button>
        </form>
      </section>
    </main>
  )
}
