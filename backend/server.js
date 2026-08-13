import { createServer } from 'node:http'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createAnalyticsInsights } from './routes/analyticsRoutes.js'
import { handleAuthRoute } from './routes/authRoutes.js'
import { AuthError, getSessionUser } from './services/authService.js'
import { listInspections, overrideInspection } from './services/inspectionService.js'

const backendDirectory = fileURLToPath(new URL('.', import.meta.url))
const envPath = resolve(backendDirectory, '.env')

if (existsSync(envPath)) {
  readFileSync(envPath, 'utf8').split(/\r?\n/).forEach((line) => {
    const match = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/)
    if (match && !process.env[match[1]]) process.env[match[1]] = match[2].replace(/^['"]|['"]$/g, '')
  })
}

const isAllowedDashboardOrigin = (origin) => /^http:\/\/(localhost|127\.0\.0\.1):517[3-9]$/.test(origin)

const sendJson = (response, statusCode, body, origin = '') => {
  response.writeHead(statusCode, {
    'Access-Control-Allow-Origin': isAllowedDashboardOrigin(origin) ? origin : 'http://localhost:5173',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Content-Type': 'application/json; charset=utf-8',
  })
  response.end(body === null ? undefined : JSON.stringify(body))
}

const readJsonBody = (request) => new Promise((resolveBody, reject) => {
  let rawBody = ''
  request.on('data', (chunk) => {
    rawBody += chunk
    if (rawBody.length > 100_000) reject(new Error('Request body is too large.'))
  })
  request.on('end', () => {
    try { resolveBody(rawBody ? JSON.parse(rawBody) : {}) } catch { reject(new Error('Request body must be valid JSON.')) }
  })
  request.on('error', reject)
})

const server = createServer(async (request, response) => {
  const origin = request.headers.origin || ''
  if (request.method === 'OPTIONS') return sendJson(response, 204, {}, origin)

  try {
    const requestUrl = new URL(request.url || '/', 'http://localhost')
    const path = requestUrl.pathname
    const requestBody = ['POST', 'PUT', 'PATCH'].includes(request.method) ? await readJsonBody(request) : null
    const authResult = await handleAuthRoute({ method: request.method, path, query: Object.fromEntries(requestUrl.searchParams), headers: request.headers, body: requestBody })
    if (authResult) return sendJson(response, authResult.statusCode, authResult.body, origin)

    if (request.method === 'GET' && path === '/api/inspections') {
      const authorization = request.headers.authorization || ''
      const token = authorization.startsWith('Bearer ') ? authorization.slice(7) : null
      await getSessionUser(token)
      return sendJson(response, 200, await listInspections(), origin)
    }

    // FR-03: an authorized user replaces the model's verdict with their own.
    // Any signed-in account may do this -- an inspector correcting the machine
    // at the station is the workflow the requirement describes, not an admin
    // task. Who did it is recorded on the row.
    const overrideMatch = path.match(/^\/api\/inspections\/([^/]+)\/override$/)
    if (request.method === 'PATCH' && overrideMatch) {
      const authorization = request.headers.authorization || ''
      const token = authorization.startsWith('Bearer ') ? authorization.slice(7) : null
      const actor = await getSessionUser(token)
      const updated = await overrideInspection({
        inspectionCode: decodeURIComponent(overrideMatch[1]),
        label: requestBody?.label,
        actor,
      })
      return sendJson(response, 200, updated, origin)
    }

    if (request.method === 'POST' && path === '/api/analytics/insights') {
      const authorization = request.headers.authorization || ''
      const token = authorization.startsWith('Bearer ') ? authorization.slice(7) : null
      await getSessionUser(token)
      const result = await createAnalyticsInsights(requestBody)
      return sendJson(response, result.statusCode, result.body, origin)
    }

    return sendJson(response, 404, { error: 'Route not found.' }, origin)
  } catch (error) {
    if (error instanceof AuthError) return sendJson(response, error.statusCode, { error: error.message, code: error.code }, origin)
    return sendJson(response, 400, { error: error.message || 'Invalid request.', code: 'INVALID_REQUEST' }, origin)
  }
})

const port = Number(process.env.BACKEND_PORT) || 3001
server.listen(port, () => console.log(`Eggministrator backend listening at http://localhost:${port}`))
