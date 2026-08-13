import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import { useAuth } from './auth/AuthContext'
import LoginPage from './pages/LoginPage'
import ChangeTemporaryPasswordPage from './pages/ChangeTemporaryPasswordPage'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import ReportsPage from './pages/ReportsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import AccountsPage from './pages/AccountsPage'

function ProtectedPage({ children }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <main className="grid min-h-screen place-items-center bg-cream-100 text-sm font-semibold text-slate-600">Checking your session…</main>
  if (!user || user.mustChangePassword) return <Navigate to="/" replace />
  return <AppLayout>{children}</AppLayout>
}

function AdminPage({ children }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <main className="grid min-h-screen place-items-center bg-cream-100 text-sm font-semibold text-slate-600">Checking your session…</main>
  if (!user) return <Navigate to="/" replace />
  if (user.role !== 'admin') return <main className="grid min-h-screen place-items-center bg-cream-100 p-6 text-center"><div><h1 className="text-2xl font-bold text-slate-900">Unauthorized</h1><p className="mt-2 text-sm text-slate-600">Only administrators can access account management.</p></div></main>
  return <AppLayout>{children}</AppLayout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/change-temporary-password" element={<ChangeTemporaryPasswordPage />} />
      <Route path="/dashboard" element={<ProtectedPage><DashboardPage /></ProtectedPage>} />
      <Route path="/history" element={<ProtectedPage><HistoryPage /></ProtectedPage>} />
      <Route path="/reports" element={<ProtectedPage><ReportsPage /></ProtectedPage>} />
      <Route path="/analytics" element={<ProtectedPage><AnalyticsPage /></ProtectedPage>} />
      <Route path="/accounts" element={<AdminPage><AccountsPage /></AdminPage>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
