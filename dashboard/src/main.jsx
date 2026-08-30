import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
// Self-hosted, not a Google Fonts <link>. The station and server run on a LAN
// (firmware/secrets.h.example pins SERVER_HOST to a local IP), so a CDN font
// would silently fall back to Segoe UI in any room without internet.
import '@fontsource-variable/ibm-plex-sans'
// Mono is only for machine identifiers (EGG-000123). There is no variable
// build of Plex Mono, so these are static weights -- just the two the app
// actually uses, font-medium and font-semibold.
import '@fontsource/ibm-plex-mono/500.css'
import '@fontsource/ibm-plex-mono/600.css'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HashRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </HashRouter>
  </StrictMode>
)
