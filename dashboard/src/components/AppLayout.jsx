import { useEffect, useRef, useState } from 'react'
import {
  BarChart3,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  ReceiptText,
  UserRound,
  UsersRound,
  X,
} from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import eggministratorLogo from '../assets/logo.svg'
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
  // The rail overlays the content instead of pushing it, so expanding never
  // resizes <main> and the 23 recharts ResponsiveContainers never re-measure.
  // The shadow is what tells the eye it is floating above rather than inline.
  const width = desktopExpanded ? 'lg:w-64 lg:shadow-2xl' : 'lg:w-20'
  const asideRef = useRef(null)
  const close = () => setMobileOpen(false)
  // Opening on click meant the only way back was clicking the logo again.
  // Navigating away, Escape, or a click anywhere else should all settle it.
  const closeAll = () => {
    setMobileOpen(false)
    setDesktopExpanded(false)
  }
  const signOut = async () => {
    await logout()
    navigate('/')
  }

  useEffect(() => {
    if (!desktopExpanded) return undefined

    const collapseOnOutsideClick = (event) => {
      if (!asideRef.current?.contains(event.target)) setDesktopExpanded(false)
    }
    const collapseOnEscape = (event) => {
      if (event.key === 'Escape') setDesktopExpanded(false)
    }

    // mousedown rather than an overlay element, so the click still lands on
    // whatever is underneath instead of being swallowed to close the rail.
    document.addEventListener('mousedown', collapseOnOutsideClick)
    document.addEventListener('keydown', collapseOnEscape)

    return () => {
      document.removeEventListener('mousedown', collapseOnOutsideClick)
      document.removeEventListener('keydown', collapseOnEscape)
    }
  }, [desktopExpanded])

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
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
          onClick={closeAll}
        />
      )}
      <aside
        ref={asideRef}
        className={`fixed inset-y-0 left-0 z-40 flex w-64 -translate-x-full flex-col bg-gradient-to-b from-forest-900 to-forest-950 p-3 text-white transition-[transform,width] duration-200 lg:translate-x-0 ${width} ${mobileOpen ? 'translate-x-0' : ''}`}
      >
        <div className="flex h-14 items-center gap-2 px-2">
          <button
            type="button"
            onClick={() => setDesktopExpanded((open) => !open)}
            aria-expanded={desktopExpanded}
            aria-label={desktopExpanded ? 'Collapse navigation' : 'Expand navigation'}
            className="grid h-11 w-11 shrink-0 cursor-default place-items-center overflow-hidden rounded-lg lg:cursor-pointer lg:hover:ring-2 lg:hover:ring-forest-500"
          >
            <img
              src={eggministratorLogo}
              alt="Eggministrator logo"
              className="h-full w-full object-contain"
            />
          </button>
          <span
            className={`text-lg font-bold tracking-tight ${desktopExpanded ? '' : 'lg:hidden'}`}
          >
            EggMinistrator
          </span>
          <button
            onClick={closeAll}
            aria-label="Close navigation"
            className="ml-auto grid min-h-11 min-w-11 place-items-center rounded-lg text-forest-100 hover:bg-forest-800 lg:hidden"
          >
            <X size={20} />
          </button>
        </div>
        <nav className="mt-5 space-y-1">
          {navigation.map(({ label, to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={closeAll}
              // the visible label is display:none while collapsed, which takes
              // it out of the accessibility tree along with the link's name
              aria-label={label}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${desktopExpanded ? '' : 'lg:justify-center lg:px-0'} ${isActive ? 'bg-forest-700 text-white shadow-sm' : 'text-forest-100 hover:bg-forest-800'}`
              }
            >
              <Icon size={18} className="shrink-0" />
              <span className={desktopExpanded ? '' : 'lg:hidden'}>{label}</span>
            </NavLink>
          ))}
        </nav>
        {user?.role === 'admin' && (
          <nav className="mt-6 space-y-1">
            <p
              className={`px-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-forest-300 ${desktopExpanded ? '' : 'lg:sr-only'}`}
            >
              Administration
            </p>
            <NavLink
              to="/accounts"
              onClick={closeAll}
              aria-label="Accounts"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${desktopExpanded ? '' : 'lg:justify-center lg:px-0'} ${isActive ? 'bg-forest-700 text-white shadow-sm' : 'text-forest-100 hover:bg-forest-800'}`
              }
            >
              <UsersRound size={18} className="shrink-0" />
              <span className={desktopExpanded ? '' : 'lg:hidden'}>Accounts</span>
            </NavLink>
          </nav>
        )}
        <div className="mt-auto space-y-3">
          <div
            className={`rounded-lg border border-forest-700 bg-forest-900/60 p-2 ${desktopExpanded ? '' : 'lg:grid lg:place-items-center'}`}
          >
            <div className="flex items-center gap-2">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-cream-50 text-forest-900">
                <UserRound size={17} />
              </div>
              <div className={`min-w-0 text-left ${desktopExpanded ? '' : 'lg:hidden'}`}>
                <p className="truncate text-xs font-semibold">{user?.fullName}</p>
                <p className="text-[11px] capitalize text-forest-200">{user?.role}</p>
              </div>
              <button
                onClick={signOut}
                aria-label="Log out"
                className={`ml-auto grid min-h-11 min-w-11 place-items-center rounded-lg text-forest-200 hover:bg-forest-800 hover:text-white ${desktopExpanded ? '' : 'lg:hidden'}`}
                title="Log out"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </aside>
      <div className="min-h-screen lg:ml-20">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-cream-50/95 px-4 backdrop-blur lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
            className="grid min-h-11 min-w-11 place-items-center rounded-lg text-forest-900 hover:bg-forest-50"
          >
            <Menu size={23} />
          </button>
          <div className="flex min-w-0 items-center gap-2 font-bold text-forest-900">
            <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-md">
              <img
                src={eggministratorLogo}
                alt="Eggministrator logo"
                className="h-full w-full object-contain"
              />
            </span>
            <span className="truncate">EggMinistrator</span>
          </div>
          <div className="min-w-11" />
        </header>
        <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  )
}
