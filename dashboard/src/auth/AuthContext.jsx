import { createContext, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null)
const apiBaseUrl = 'http://localhost:3001'
const sessionTokenKey = 'eggministrator_session_token'
const passwordChangeTokenKey = 'eggministrator_password_change_token'

const readResponse = async (response) => {
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(body.error || 'Unable to complete the request.')
    error.code = body.code
    throw error
  }
  return body
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = () => {
    sessionStorage.removeItem(sessionTokenKey)
    setUser(null)
  }

  const restoreSession = async () => {
    const token = sessionStorage.getItem(sessionTokenKey)
    if (!token) {
      setIsLoading(false)
      return
    }
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/session`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const result = await readResponse(response)
      setUser(result.user)
    } catch {
      clearSession()
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    restoreSession()
  }, [])

  const login = async (credentials) => {
    const response = await fetch(`${apiBaseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    })
    const result = await readResponse(response)
    if (result.requiresPasswordChange) {
      sessionStorage.setItem(passwordChangeTokenKey, result.passwordChangeToken)
      return { requiresPasswordChange: true }
    }
    sessionStorage.setItem(sessionTokenKey, result.sessionToken)
    setUser(result.user)
    return { requiresPasswordChange: false }
  }

  const logout = async () => {
    const token = sessionStorage.getItem(sessionTokenKey)
    try {
      if (token)
        await fetch(`${apiBaseUrl}/api/auth/session`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        })
    } finally {
      clearSession()
    }
  }

  const authenticatedFetch = async (path, options = {}) => {
    const token = sessionStorage.getItem(sessionTokenKey)
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${token}` },
    })
    if (response.status === 401) clearSession()
    return response
  }

  return (
    <AuthContext.Provider
      value={{ user, isLoading, login, logout, authenticatedFetch, passwordChangeTokenKey }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider.')
  return context
}
