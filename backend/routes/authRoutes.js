import { AuthError, changeTemporaryPassword, createEmployee, getAccount, getSessionUser, listAccounts, login, logout, resetEmployeePassword, updateAccount, updateAccountStatus } from '../services/authService.js'

const getBearerToken = (headers) => {
  const authorization = headers.authorization || ''
  return authorization.startsWith('Bearer ') ? authorization.slice(7) : null
}

const requireAdmin = async (headers) => {
  const user = await getSessionUser(getBearerToken(headers))
  if (user.role !== 'admin') throw new AuthError('Administrator access is required.', 403, 'ADMIN_REQUIRED')
  return user
}

const success = (body, statusCode = 200) => ({ statusCode, body })
const failure = (error) => error instanceof AuthError
  ? { statusCode: error.statusCode, body: { error: error.message, code: error.code } }
  : { statusCode: 500, body: { error: 'Authentication service is unavailable.', code: 'AUTH_SERVICE_ERROR' } }

export async function handleAuthRoute(request) {
  try {
    const token = getBearerToken(request.headers)
    if (request.method === 'POST' && request.path === '/api/auth/login') return success(await login(request.body || {}))
    if (request.method === 'GET' && request.path === '/api/auth/session') return success({ user: await getSessionUser(token) })
    if (request.method === 'DELETE' && request.path === '/api/auth/session') {
      await logout(token)
      return { statusCode: 204, body: null }
    }
    if (request.method === 'POST' && request.path === '/api/auth/change-temporary-password') {
      await changeTemporaryPassword(request.body || {})
      return success({ message: 'Password changed successfully. Please sign in again.' })
    }
    if (request.method === 'POST' && request.path === '/api/users') {
      await requireAdmin(request.headers)
      return success(await createEmployee(request.body || {}), 201)
    }
    if (request.method === 'GET' && request.path === '/api/admin/accounts') {
      await requireAdmin(request.headers)
      return success(await listAccounts(request.query))
    }
    if (request.method === 'POST' && request.path === '/api/admin/accounts') {
      await requireAdmin(request.headers)
      return success(await createEmployee(request.body || {}), 201)
    }
    const accountMatch = request.path.match(/^\/api\/admin\/accounts\/(\d+)$/)
    if (request.method === 'GET' && accountMatch) {
      await requireAdmin(request.headers)
      return success({ account: await getAccount(Number(accountMatch[1])) })
    }
    if (request.method === 'PUT' && accountMatch) {
      const admin = await requireAdmin(request.headers)
      return success({ account: await updateAccount(admin, Number(accountMatch[1]), request.body || {}) })
    }
    const statusMatch = request.path.match(/^\/api\/admin\/accounts\/(\d+)\/status$/)
    if (request.method === 'PATCH' && statusMatch) {
      const admin = await requireAdmin(request.headers)
      return success({ account: await updateAccountStatus(admin, Number(statusMatch[1]), request.body?.isActive) })
    }
    const adminResetMatch = request.path.match(/^\/api\/admin\/accounts\/(\d+)\/reset-password$/)
    if (request.method === 'POST' && adminResetMatch) {
      const admin = await requireAdmin(request.headers)
      const targetId = Number(adminResetMatch[1])
      if (admin.id === targetId) throw new AuthError('Use the password-change process for your own account. An administrator cannot reset their own account here.', 400, 'SELF_RESET_PREVENTED')
      return success(await resetEmployeePassword(targetId))
    }
    const resetMatch = request.path.match(/^\/api\/users\/(\d+)\/reset-password$/)
    if (request.method === 'POST' && resetMatch) {
      const admin = await requireAdmin(request.headers)
      const targetId = Number(resetMatch[1])
      if (admin.id === targetId) throw new AuthError('Use the password-change process for your own account. An administrator cannot reset their own account here.', 400, 'SELF_RESET_PREVENTED')
      return success(await resetEmployeePassword(targetId))
    }
    return null
  } catch (error) {
    return failure(error)
  }
}
