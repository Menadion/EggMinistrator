import bcrypt from 'bcryptjs'
import { createHash, randomBytes } from 'node:crypto'
import database from '../db.js'

const BCRYPT_ROUNDS = 12
const MAX_FAILED_LOGIN_ATTEMPTS = 5
const LOCK_DURATION_MINUTES = 15
const SESSION_DURATION_HOURS = 8
const PASSWORD_CHANGE_TOKEN_MINUTES = 15
const TEMPORARY_PASSWORD_HOURS = 24
const temporaryPasswordCharacters = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*'
const allowedRoles = ['admin', 'inspector']
const usernamePattern = /^[A-Za-z0-9._-]{4,50}$/

export class AuthError extends Error {
  constructor(message, statusCode = 400, code = 'AUTH_ERROR') {
    super(message)
    this.statusCode = statusCode
    this.code = code
  }
}

const tokenHash = (token) => createHash('sha256').update(token).digest('hex')
const createToken = () => randomBytes(48).toString('base64url')
const createExpiration = (minutes) => new Date(Date.now() + (minutes * 60_000))
const composeFullName = ({ first_name: firstName, middle_initial: middleInitial, last_name: lastName, full_name: fullName }) => {
  const nameParts = [firstName, middleInitial ? `${middleInitial}.` : null, lastName].filter(Boolean)
  return nameParts.length ? nameParts.join(' ') : fullName
}

const mapUser = (user) => ({
  id: user.id,
  fullName: composeFullName(user),
  username: user.username,
  role: user.role,
  isActive: Boolean(user.is_active),
  mustChangePassword: Boolean(user.must_change_password),
})
const mapAccount = (user) => ({
  id: user.id,
  fullName: composeFullName(user),
  firstName: user.first_name,
  middleInitial: user.middle_initial,
  lastName: user.last_name,
  username: user.username,
  role: user.role,
  isActive: Boolean(user.is_active),
  lastLoginAt: user.last_login_at,
  createdAt: user.created_at,
  updatedAt: user.updated_at,
})

export const validatePassword = (password) => {
  if (typeof password !== 'string' || password.length < 8) return 'Password must be at least 8 characters.'
  if (!/[A-Z]/.test(password)) return 'Password must include an uppercase letter.'
  if (!/[a-z]/.test(password)) return 'Password must include a lowercase letter.'
  if (!/\d/.test(password)) return 'Password must include a number.'
  if (!/[^A-Za-z0-9]/.test(password)) return 'Password must include a special character.'
  return null
}

const generateTemporaryPassword = () => {
  const required = ['ABCDEFGHJKLMNPQRSTUVWXYZ', 'abcdefghijkmnopqrstuvwxyz', '23456789', '!@#$%^&*']
  const characters = [...required.map((group) => group[randomBytes(1)[0] % group.length])]
  while (characters.length < 16) characters.push(temporaryPasswordCharacters[randomBytes(1)[0] % temporaryPasswordCharacters.length])
  return characters.sort(() => randomBytes(1)[0] - 128).join('')
}

const normalizeUsername = (username) => typeof username === 'string' ? username.trim().toLowerCase() : ''
const normalizeName = (name) => typeof name === 'string' ? name.trim().replace(/\s+/g, ' ') : ''
const normalizeMiddleInitial = (initial) => {
  if (initial === undefined || initial === null || initial === '') return null
  const normalized = String(initial).trim().replace(/\.$/, '')
  if (!/^[A-Za-z]$/.test(normalized)) throw new AuthError('Middle initial must contain one alphabetic character.', 400, 'INVALID_MIDDLE_INITIAL')
  return normalized.toUpperCase()
}

const findUserByUsername = async (username) => {
  const [rows] = await database.execute('SELECT * FROM users WHERE username = ? LIMIT 1', [normalizeUsername(username)])
  return rows[0] || null
}

const findUserById = async (userId) => {
  const [rows] = await database.execute('SELECT * FROM users WHERE id = ? LIMIT 1', [userId])
  return rows[0] || null
}

const validateAccountInput = ({ firstName, middleInitial, lastName, username, role, isActive }, isUpdate = false) => {
  const normalized = {}
  if (!isUpdate || firstName !== undefined) {
    normalized.firstName = normalizeName(firstName)
    if (!normalized.firstName || normalized.firstName.length > 100) throw new AuthError('First name is required and must be 100 characters or fewer.', 400, 'INVALID_FIRST_NAME')
  }
  if (!isUpdate || lastName !== undefined) {
    normalized.lastName = normalizeName(lastName)
    if (!normalized.lastName || normalized.lastName.length > 100) throw new AuthError('Last name is required and must be 100 characters or fewer.', 400, 'INVALID_LAST_NAME')
  }
  if (!isUpdate || middleInitial !== undefined) {
    normalized.middleInitial = normalizeMiddleInitial(middleInitial)
  }
  if (!isUpdate || username !== undefined) {
    normalized.username = normalizeUsername(username)
    if (!usernamePattern.test(normalized.username)) throw new AuthError('Username must contain 4 to 50 letters, numbers, periods, hyphens, or underscores.', 400, 'INVALID_USERNAME')
  }
  if (!isUpdate || role !== undefined) {
    if (!allowedRoles.includes(role)) throw new AuthError('Role must be admin or inspector.', 400, 'INVALID_ROLE')
    normalized.role = role
  }
  if (isActive !== undefined && typeof isActive !== 'boolean') throw new AuthError('Account status must be active or inactive.', 400, 'INVALID_ACCOUNT_STATUS')
  if (isActive !== undefined) normalized.isActive = isActive
  return normalized
}

const assertAdminSafeguards = async (actor, target, nextRole, nextIsActive) => {
  const removesActiveAdmin = target.role === 'admin' && target.is_active && (nextRole !== 'admin' || !nextIsActive)
  if (!removesActiveAdmin) return
  if (actor.id === target.id) throw new AuthError('You cannot deactivate or demote your own administrator account.', 400, 'SELF_LOCKOUT_PREVENTED')
  const [rows] = await database.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND is_active = 1")
  if (rows[0].count <= 1) throw new AuthError('The final active administrator cannot be deactivated or changed to another role.', 400, 'FINAL_ADMIN_PROTECTED')
}

const invalidateUserSessions = async (userId) => {
  await database.execute('UPDATE auth_sessions SET invalidated_at = NOW() WHERE user_id = ? AND invalidated_at IS NULL', [userId])
}

const invalidatePasswordChangeTokens = async (userId) => {
  await database.execute('UPDATE password_change_tokens SET used_at = NOW() WHERE user_id = ? AND used_at IS NULL', [userId])
}

const createSession = async (userId) => {
  const token = createToken()
  const expiresAt = createExpiration(SESSION_DURATION_HOURS * 60)
  await database.execute('INSERT INTO auth_sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)', [userId, tokenHash(token), expiresAt])
  return { token, expiresAt: expiresAt.toISOString() }
}

const createPasswordChangeToken = async (userId) => {
  const token = createToken()
  const expiresAt = createExpiration(PASSWORD_CHANGE_TOKEN_MINUTES)
  await invalidatePasswordChangeTokens(userId)
  await database.execute('INSERT INTO password_change_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)', [userId, tokenHash(token), expiresAt])
  return { token, expiresAt: expiresAt.toISOString() }
}

const registerFailedLogin = async (user) => {
  const attempts = user.failed_login_attempts + 1
  const lockedUntil = attempts >= MAX_FAILED_LOGIN_ATTEMPTS ? createExpiration(LOCK_DURATION_MINUTES) : null
  await database.execute('UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?', [attempts, lockedUntil, user.id])
}

export async function login({ username, password }) {
  if (typeof username !== 'string' || typeof password !== 'string' || !username.trim() || !password) {
    throw new AuthError('Username and password are required.', 400, 'INVALID_LOGIN_REQUEST')
  }

  const user = await findUserByUsername(normalizeUsername(username))
  if (!user) throw new AuthError('Invalid username or password.', 401, 'INVALID_CREDENTIALS')
  if (!user.is_active) throw new AuthError('This account is inactive. Contact an administrator.', 403, 'ACCOUNT_INACTIVE')
  if (user.locked_until && new Date(user.locked_until) > new Date()) throw new AuthError('This account is temporarily locked. Please try again later.', 423, 'ACCOUNT_LOCKED')

  const matches = await bcrypt.compare(password, user.password_hash)
  if (!matches) {
    await registerFailedLogin(user)
    throw new AuthError('Invalid username or password.', 401, 'INVALID_CREDENTIALS')
  }

  await database.execute('UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login_at = NOW() WHERE id = ?', [user.id])

  if (user.must_change_password) {
    if (!user.temporary_password_expires_at || new Date(user.temporary_password_expires_at) <= new Date()) {
      throw new AuthError('This temporary password has expired. Contact an administrator for a reset.', 403, 'TEMPORARY_PASSWORD_EXPIRED')
    }
    const passwordChange = await createPasswordChangeToken(user.id)
    return { requiresPasswordChange: true, passwordChangeToken: passwordChange.token, passwordChangeTokenExpiresAt: passwordChange.expiresAt }
  }

  const session = await createSession(user.id)
  return { requiresPasswordChange: false, sessionToken: session.token, expiresAt: session.expiresAt, user: mapUser(user) }
}

export async function getSessionUser(token) {
  if (!token) throw new AuthError('Authentication is required.', 401, 'AUTH_REQUIRED')
  const [rows] = await database.execute(
    `SELECT users.* FROM auth_sessions
     INNER JOIN users ON users.id = auth_sessions.user_id
     WHERE auth_sessions.token_hash = ?
       AND auth_sessions.invalidated_at IS NULL
       AND auth_sessions.expires_at > NOW()
     LIMIT 1`,
    [tokenHash(token)],
  )
  const user = rows[0]
  if (!user || !user.is_active) throw new AuthError('Your session is no longer valid. Please sign in again.', 401, 'SESSION_INVALID')
  if (user.must_change_password) throw new AuthError('A password change is required before accessing the application.', 403, 'PASSWORD_CHANGE_REQUIRED')
  return mapUser(user)
}

export async function logout(token) {
  if (token) await database.execute('UPDATE auth_sessions SET invalidated_at = NOW() WHERE token_hash = ? AND invalidated_at IS NULL', [tokenHash(token)])
}

export async function createEmployee({ firstName, middleInitial, lastName, username, role }) {
  const account = validateAccountInput({ firstName, middleInitial, lastName, username, role })

  const temporaryPassword = generateTemporaryPassword()
  const passwordHash = await bcrypt.hash(temporaryPassword, BCRYPT_ROUNDS)
  const expiresAt = createExpiration(TEMPORARY_PASSWORD_HOURS * 60)
  try {
    const [result] = await database.execute(
      `INSERT INTO users (full_name, first_name, middle_initial, last_name, username, password_hash, role, is_active, must_change_password, temporary_password_expires_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?)`,
      [composeFullName({ first_name: account.firstName, middle_initial: account.middleInitial, last_name: account.lastName }), account.firstName, account.middleInitial, account.lastName, account.username, passwordHash, account.role, expiresAt],
    )
    const user = await findUserById(result.insertId)
    return { user: mapAccount(user), temporaryPassword, temporaryPasswordExpiresAt: expiresAt.toISOString() }
  } catch (error) {
    if (error.code === 'ER_DUP_ENTRY') throw new AuthError('That username is already in use.', 409, 'USERNAME_EXISTS')
    throw error
  }
}

export async function resetEmployeePassword(userId) {
  const user = await findUserById(userId)
  if (!user) throw new AuthError('Employee account not found.', 404, 'USER_NOT_FOUND')
  const temporaryPassword = generateTemporaryPassword()
  const passwordHash = await bcrypt.hash(temporaryPassword, BCRYPT_ROUNDS)
  const expiresAt = createExpiration(TEMPORARY_PASSWORD_HOURS * 60)
  await database.execute(
    `UPDATE users
     SET password_hash = ?, must_change_password = 1, temporary_password_expires_at = ?,
         password_changed_at = NULL, failed_login_attempts = 0, locked_until = NULL
     WHERE id = ?`,
    [passwordHash, expiresAt, user.id],
  )
  await invalidateUserSessions(user.id)
  await invalidatePasswordChangeTokens(user.id)
  return { user: { ...mapAccount(user), mustChangePassword: true }, temporaryPassword, temporaryPasswordExpiresAt: expiresAt.toISOString() }
}

export async function listAccounts({ search = '', role = '', status = '', page = 1, pageSize = 10 } = {}) {
  const safePage = Math.max(1, Number(page) || 1)
  const safePageSize = Math.min(50, Math.max(1, Number(pageSize) || 10))
  const conditions = []
  const values = []
  if (search.trim()) {
    conditions.push("(CONCAT_WS(' ', first_name, middle_initial, last_name) LIKE ? OR full_name LIKE ? OR username LIKE ?)")
    values.push(`%${search.trim()}%`, `%${search.trim()}%`, `%${normalizeUsername(search)}%`)
  }
  if (allowedRoles.includes(role)) {
    conditions.push('role = ?')
    values.push(role)
  }
  if (status === 'active' || status === 'inactive') {
    conditions.push('is_active = ?')
    values.push(status === 'active' ? 1 : 0)
  }
  const whereClause = conditions.length ? `WHERE ${conditions.join(' AND ')}` : ''
  const [countRows] = await database.execute(`SELECT COUNT(*) AS total FROM users ${whereClause}`, values)
  const [rows] = await database.execute(
    `SELECT id, full_name, first_name, middle_initial, last_name, username, role, is_active, last_login_at, created_at, updated_at
     FROM users ${whereClause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?`,
    [...values, safePageSize, (safePage - 1) * safePageSize],
  )
  const [summaryRows] = await database.execute(
    `SELECT COUNT(*) AS total, SUM(is_active = 1) AS active, SUM(is_active = 0) AS inactive
     FROM users`,
  )
  return { accounts: rows.map(mapAccount), total: countRows[0].total, page: safePage, pageSize: safePageSize, summary: summaryRows[0] }
}

export async function getAccount(userId) {
  const user = await findUserById(userId)
  if (!user) throw new AuthError('Employee account not found.', 404, 'USER_NOT_FOUND')
  return mapAccount(user)
}

export async function updateAccount(actor, userId, { firstName, middleInitial, lastName, username, role, isActive }) {
  const target = await findUserById(userId)
  if (!target) throw new AuthError('Employee account not found.', 404, 'USER_NOT_FOUND')
  const isStatusOnlyUpdate = isActive !== undefined && [firstName, middleInitial, lastName, username, role].every((value) => value === undefined)
  const legacyNameFieldsAreBlank = !target.first_name && !target.last_name
  const submittedNamesAreBlank = [firstName, middleInitial, lastName].every((value) => value === undefined || value === null || String(value).trim() === '')
  const preserveLegacyName = legacyNameFieldsAreBlank && submittedNamesAreBlank
  const account = validateAccountInput(
    preserveLegacyName ? { username, role, isActive } : { firstName, middleInitial, lastName, username, role, isActive },
    isStatusOnlyUpdate || preserveLegacyName,
  )
  const nextFirstName = account.firstName ?? target.first_name
  const nextMiddleInitial = account.middleInitial === undefined ? target.middle_initial : account.middleInitial
  const nextLastName = account.lastName ?? target.last_name
  const nextUsername = account.username ?? target.username
  const nextRole = account.role ?? target.role
  const nextIsActive = account.isActive ?? Boolean(target.is_active)
  await assertAdminSafeguards(actor, target, nextRole, nextIsActive)
  try {
    await database.execute(
      `UPDATE users SET full_name = ?, first_name = ?, middle_initial = ?, last_name = ?, username = ?, role = ?, is_active = ? WHERE id = ?`,
      [composeFullName({ first_name: nextFirstName, middle_initial: nextMiddleInitial, last_name: nextLastName, full_name: target.full_name }), nextFirstName, nextMiddleInitial, nextLastName, nextUsername, nextRole, Number(nextIsActive), target.id],
    )
  } catch (error) {
    if (error.code === 'ER_DUP_ENTRY') throw new AuthError('That username is already in use.', 409, 'USERNAME_EXISTS')
    throw error
  }
  if (!nextIsActive) {
    await invalidateUserSessions(target.id)
    await invalidatePasswordChangeTokens(target.id)
  }
  return getAccount(target.id)
}

export async function updateAccountStatus(actor, userId, isActive) {
  if (typeof isActive !== 'boolean') throw new AuthError('Account status must be active or inactive.', 400, 'INVALID_ACCOUNT_STATUS')
  return updateAccount(actor, userId, { isActive })
}

export async function changeTemporaryPassword({ passwordChangeToken, newPassword, confirmPassword }) {
  if (typeof passwordChangeToken !== 'string' || !passwordChangeToken) throw new AuthError('A valid password-change token is required.', 401, 'PASSWORD_CHANGE_TOKEN_REQUIRED')
  if (newPassword !== confirmPassword) throw new AuthError('New password and confirmation do not match.', 400, 'PASSWORD_MISMATCH')
  const validationError = validatePassword(newPassword)
  if (validationError) throw new AuthError(validationError, 400, 'WEAK_PASSWORD')

  const [rows] = await database.execute(
    `SELECT password_change_tokens.id AS token_id, users.* FROM password_change_tokens
     INNER JOIN users ON users.id = password_change_tokens.user_id
     WHERE password_change_tokens.token_hash = ?
       AND password_change_tokens.used_at IS NULL
       AND password_change_tokens.expires_at > NOW()
     LIMIT 1`,
    [tokenHash(passwordChangeToken)],
  )
  const user = rows[0]
  if (!user || !user.must_change_password) throw new AuthError('This password-change link is invalid or expired.', 401, 'PASSWORD_CHANGE_TOKEN_INVALID')
  if (await bcrypt.compare(newPassword, user.password_hash)) throw new AuthError('Your new password cannot match the temporary password.', 400, 'PASSWORD_REUSES_TEMPORARY')

  const passwordHash = await bcrypt.hash(newPassword, BCRYPT_ROUNDS)
  await database.execute(
    `UPDATE users
     SET password_hash = ?, must_change_password = 0, password_changed_at = NOW(),
         temporary_password_expires_at = NULL, failed_login_attempts = 0, locked_until = NULL
     WHERE id = ?`,
    [passwordHash, user.id],
  )
  await invalidateUserSessions(user.id)
  await database.execute('UPDATE password_change_tokens SET used_at = NOW() WHERE user_id = ? AND used_at IS NULL', [user.id])
}
