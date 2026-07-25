import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import ReportsPage from './pages/ReportsPage'
import AnalyticsPage from './pages/AnalyticsPage'

function ProtectedPage({ children }) {
  return <AppLayout>{children}</AppLayout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/dashboard" element={<ProtectedPage><DashboardPage /></ProtectedPage>} />
      <Route path="/history" element={<ProtectedPage><HistoryPage /></ProtectedPage>} />
      <Route path="/reports" element={<ProtectedPage><ReportsPage /></ProtectedPage>} />
      <Route path="/analytics" element={<ProtectedPage><AnalyticsPage /></ProtectedPage>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
