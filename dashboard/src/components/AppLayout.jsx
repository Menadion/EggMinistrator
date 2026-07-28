import { useState } from 'react'
import { BarChart3, ChevronLeft, Egg, History, LayoutDashboard, LogOut, Menu, ReceiptText, UserRound, X } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import humptyLogo from "../assets/Humpty_Dumpty.webp";
const navigation = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'History', to: '/history', icon: History },
  { label: 'Reports', to: '/reports', icon: ReceiptText },
  { label: 'Analytics', to: '/analytics', icon: BarChart3 },
]

export default function AppLayout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const width = collapsed ? 'lg:w-20' : 'lg:w-64'
  const close = () => setMobileOpen(false)

  return (
    <div className="min-h-screen bg-cream-100">
      {mobileOpen && <button aria-label="Close navigation" className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden" onClick={close} />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 -translate-x-full flex-col bg-gradient-to-b from-forest-900 to-forest-950 p-3 text-white transition-transform duration-200 lg:translate-x-0 ${width} ${mobileOpen ? 'translate-x-0' : ''}`}>
        <div className="flex h-14 items-center gap-2 px-2">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-amber-50 text-amber-500"><img src={humptyLogo} alt="Humpty Logo" className="h-full w-full object-contain" /></div>
          {!collapsed && <span className="text-lg font-bold tracking-tight">EggMinistrator</span>}
          <button onClick={() => setMobileOpen(false)} className="ml-auto rounded p-1 text-green-100 lg:hidden"><X size={20} /></button>
        </div>
        <nav className="mt-5 space-y-1">
          {navigation.map(({ label, to, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={close} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-green-700 text-white shadow-sm' : 'text-green-100 hover:bg-green-800'}`}>
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto space-y-3">
          <button onClick={() => setCollapsed(!collapsed)} className="hidden w-full items-center justify-center rounded-lg py-2 text-green-100 hover:bg-green-800 lg:flex"><ChevronLeft className={collapsed ? 'rotate-180' : ''} size={18} /></button>
          <div className="rounded-lg border border-green-700 bg-green-900/60 p-2">
            <div className="flex items-center gap-2">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-cream-50 text-forest-900"><UserRound size={17} /></div>
              {!collapsed && <div className="min-w-0 text-left"><p className="truncate text-xs font-semibold">Admin User</p><p className="text-[11px] text-green-200">Administrator</p></div>}
              {!collapsed && <button onClick={() => navigate('/')} className="ml-auto text-green-200 hover:text-white" title="Log out"><LogOut size={16} /></button>}
            </div>
          </div>
        </div>
      </aside>
      <div className={`min-h-screen transition-all ${collapsed ? 'lg:ml-20' : 'lg:ml-64'}`}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-cream-50/95 px-4 backdrop-blur lg:hidden">
          <button onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-forest-900 hover:bg-green-50"><Menu size={23} /></button>
          <div className="flex items-center gap-2 font-bold text-forest-900"><img src={humptyLogo} alt="Humpty Logo" className="h-full w-full object-contain" />EggMinistrator</div>
          <div className="w-9" />
        </header>
        <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  )
}
