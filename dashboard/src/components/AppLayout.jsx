import { useEffect, useState } from 'react'
import { BarChart3, History, LayoutDashboard, LogOut, Menu, ReceiptText, UserRound, UsersRound, X } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import eggministratorLogo from '../assets/eggministrator logo.png'
const navigation = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'History', to: '/history', icon: History },
  { label: 'Reports', to: '/reports', icon: ReceiptText },
  { label: 'Analytics', to: '/analytics', icon: BarChart3 },
]

export default function AppLayout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [desktopExpanded, setDesktopExpanded] = useState(false)
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const width = desktopExpanded ? 'lg:w-64' : 'lg:w-20'
  const close = () => setMobileOpen(false)
  const signOut = async () => { await logout(); navigate('/') }

  useEffect(() => {
    if (!mobileOpen) return undefined

    const previousOverflow = document.body.style.overflow
    const closeWithEscape = (event) => {
      if (event.key === 'Escape') close()
    }

    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', closeWithEscape)

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', closeWithEscape)
    }
  }, [mobileOpen])

  return (
    <div className="min-h-screen bg-cream-100">
      {mobileOpen && <button aria-label="Close navigation" className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden" onClick={close} />}
      <aside onMouseEnter={() => setDesktopExpanded(true)} onMouseLeave={() => setDesktopExpanded(false)} onFocusCapture={() => setDesktopExpanded(true)} className={`fixed inset-y-0 left-0 z-40 flex w-64 -translate-x-full flex-col bg-gradient-to-b from-forest-900 to-forest-950 p-3 text-white transition-[transform,width] duration-200 lg:translate-x-0 ${width} ${mobileOpen ? 'translate-x-0' : ''}`}>
        <div className="flex h-14 items-center gap-2 px-2">
          <div className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-lg"><img src={eggministratorLogo} alt="Eggministrator logo" className="h-full w-full translate-y-2 scale-[2.5] object-cover" /></div>
          <span className={`text-lg font-bold tracking-tight ${desktopExpanded ? '' : 'lg:hidden'}`}>EggMinistrator</span>
          <button onClick={close} aria-label="Close navigation" className="ml-auto grid min-h-11 min-w-11 place-items-center rounded-lg text-green-100 hover:bg-green-800 lg:hidden"><X size={20} /></button>
        </div>
        <nav className="mt-5 space-y-1">
          {navigation.map(({ label, to, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={close} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${desktopExpanded ? '' : 'lg:justify-center lg:px-0'} ${isActive ? 'bg-green-700 text-white shadow-sm' : 'text-green-100 hover:bg-green-800'}`}>
              <Icon size={18} className="shrink-0" />
              <span className={desktopExpanded ? '' : 'lg:hidden'}>{label}</span>
            </NavLink>
          ))}
        </nav>
        {user?.role === 'admin' && <nav className="mt-6 space-y-1"><p className={`px-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-green-300 ${desktopExpanded ? '' : 'lg:sr-only'}`}>Administration</p><NavLink to="/accounts" onClick={close} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${desktopExpanded ? '' : 'lg:justify-center lg:px-0'} ${isActive ? 'bg-green-700 text-white shadow-sm' : 'text-green-100 hover:bg-green-800'}`}><UsersRound size={18} className="shrink-0" /><span className={desktopExpanded ? '' : 'lg:hidden'}>Accounts</span></NavLink></nav>}
        <div className="mt-auto space-y-3">
          <div className={`rounded-lg border border-green-700 bg-green-900/60 p-2 ${desktopExpanded ? '' : 'lg:grid lg:place-items-center'}`}>
            <div className="flex items-center gap-2">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-cream-50 text-forest-900"><UserRound size={17} /></div>
              <div className={`min-w-0 text-left ${desktopExpanded ? '' : 'lg:hidden'}`}><p className="truncate text-xs font-semibold">{user?.fullName}</p><p className="text-[11px] capitalize text-green-200">{user?.role}</p></div>
              <button onClick={signOut} aria-label="Log out" className={`ml-auto grid min-h-11 min-w-11 place-items-center rounded-lg text-green-200 hover:bg-green-800 hover:text-white ${desktopExpanded ? '' : 'lg:hidden'}`} title="Log out"><LogOut size={16} /></button>
            </div>
          </div>
        </div>
      </aside>
      <div className={`min-h-screen transition-all duration-200 ${desktopExpanded ? 'lg:ml-64' : 'lg:ml-20'}`}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-cream-50/95 px-4 backdrop-blur lg:hidden">
          <button onClick={() => setMobileOpen(true)} aria-label="Open navigation" className="grid min-h-11 min-w-11 place-items-center rounded-lg text-forest-900 hover:bg-green-50"><Menu size={23} /></button>
          <div className="flex min-w-0 items-center gap-2 font-bold text-forest-900"><span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-md"><img src={eggministratorLogo} alt="Eggministrator logo" className="h-full w-full translate-y-1.5 scale-[2.5] object-cover" /></span><span className="truncate">EggMinistrator</span></div>
          <div className="min-w-11" />
        </header>
        <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  )
}
