import { createServer } from 'node:http'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createAnalyticsInsights } from './routes/analyticsRoutes.js'

const backendDirectory = fileURLToPath(new URL('.', import.meta.url))
const envPath = resolve(backendDirectory, '.env')

if (existsSync(envPath)) {
  readFileSync(envPath, 'utf8').split(/\r?\n/).forEach((line) => {
    const match = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/)
    if (match && !process.env[match[1]]) process.env[match[1]] = match[2].replace(/^['"]|['"]$/g, '')
  })
}

const sendJson = (response, statusCode, body) => {
  response.writeHead(statusCode, {
    'Access-Control-Allow-Origin': 'http://localhost:5173',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json; charset=utf-8',
  })
  response.end(JSON.stringify(body))
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
  if (request.method === 'OPTIONS') return sendJson(response, 204, {})
  if (request.method !== 'POST' || request.url !== '/api/analytics/insights') return sendJson(response, 404, { error: 'Route not found.' })

  try {
    const requestBody = await readJsonBody(request)
    const result = await createAnalyticsInsights(requestBody)
    return sendJson(response, result.statusCode, result.body)
  } catch (error) {
    return sendJson(response, 400, { error: error.message || 'Invalid request.', code: 'INVALID_REQUEST' })
  }
})

const port = Number(process.env.BACKEND_PORT) || 3001
server.listen(port, () => console.log(`Eggministrator backend listening at http://localhost:${port}`))
