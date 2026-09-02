import test, { after, before } from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { databaseReachable } from './loadEnv.js'
import database from '../db.js'

const PORT = 3111
const BASE = `http://127.0.0.1:${PORT}`
const backendDir = fileURLToPath(new URL('..', import.meta.url))
let server = null
let dbUp = false
const created = []

const startServer = () => new Promise((ready, fail) => {
  server = spawn(process.execPath, [resolve(backendDir, 'server.js')], { cwd: backendDir, env: { ...process.env, BACKEND_PORT: String(PORT) }, stdio: ['ignore', 'pipe', 'pipe'] })
  let output = ''
  server.stdout.on('data', (chunk) => { output += chunk; if (output.includes('listening')) { clearTimeout(timer); ready() } })
  server.stderr.on('data', (chunk) => { output += chunk })
  server.once('exit', (code) => { clearTimeout(timer); fail(new Error(`server exited early (${code}): ${output}`)) })
  const timer = setTimeout(() => fail(new Error(`server did not start: ${output}`)), 8000)
})

const api = async (method, path, body) => {
  const response = await fetch(BASE + path, {
    method,
    headers: { 'X-Device-Key': process.env.DEVICE_API_KEY, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return { status: response.status, body: await response.json() }
}

const egg = (slot, cls = 'good') => ({
  slot, image_path: `ai/captures/20260902/cycle_route_slot${slot}.jpg`, class: cls, confidence: 0.9,
  model_name: 'candling-classifier', model_version: '0.3.0+test', inference_time_ms: 40,
  raw_result: JSON.stringify({ good: 0.9, defective: 0.05, not_an_egg: 0.05 }),
})

before(async () => {
  dbUp = (await databaseReachable()) && Boolean(process.env.DEVICE_API_KEY)
  if (dbUp) {
    await database.query("UPDATE tray_cycles SET status='rejected', rejected_reason='test_drain' WHERE status='pending'")
    await startServer()
  }
})
after(async () => {
  if (server) server.kill()
  if (created.length) {
    await database.query('DELETE FROM egg_inspections WHERE cycle_id IN (?)', [created])
    await database.query('DELETE FROM tray_cycles WHERE id IN (?)', [created])
  }
  await database.end()
})

test('every cycle route needs the device key', async (t) => {
  if (!dbUp) return t.skip('MySQL is down or DEVICE_API_KEY is empty in backend/.env')
  const response = await fetch(`${BASE}/api/cycles/pending`)
  assert.equal(response.status, 401)
})

test('the five routes carry one cycle from lid-close to result', async (t) => {
  if (!dbUp) return t.skip('MySQL is down or DEVICE_API_KEY is empty in backend/.env')
  assert.equal((await api('GET', '/api/cycles/pending')).status, 404)

  const minted = await api('POST', '/api/cycles', { station_name: 'Route Test', weights: [58.2, 61.0], total_g: 119.2 })
  assert.equal(minted.status, 201)
  created.push(minted.body.id)

  const pending = await api('GET', '/api/cycles/pending')
  assert.equal(pending.status, 200)
  assert.equal(pending.body.id, minted.body.id)
  assert.deepEqual(pending.body.weights, [58.2, 61])

  assert.deepEqual((await api('GET', `/api/cycles/${minted.body.id}/result`)).body, { status: 'pending' })

  const saved = await api('POST', `/api/cycles/${minted.body.id}/assessment`, { frame_path: 'ai/captures/20260902/cycle_route.jpg', eggs: [egg(1), egg(2, 'defective')] })
  assert.equal(saved.status, 201)
  assert.deepEqual(saved.body.inspections.map((e) => e.slot), [1, 2])

  const result = await api('GET', `/api/cycles/${minted.body.id}/result`)
  assert.equal(result.body.status, 'done')
  assert.equal(result.body.any_defective, true)
  assert.equal(result.body.eggs[1].label, 'defective')

  assert.equal((await api('GET', '/api/cycles/pending')).status, 404)
})

test('a sum mismatch is rejected at birth and the reject route handles optics', async (t) => {
  if (!dbUp) return t.skip('MySQL is down or DEVICE_API_KEY is empty in backend/.env')
  const bad = await api('POST', '/api/cycles', { weights: [58.2, 61.0], total_g: 140 })
  assert.equal(bad.status, 201)
  created.push(bad.body.id)
  assert.deepEqual((await api('GET', `/api/cycles/${bad.body.id}/result`)).body, { status: 'rejected', reason: 'weights_sum_mismatch' })

  const ok = await api('POST', '/api/cycles', { weights: [58.2], total_g: 58.2 })
  created.push(ok.body.id)
  const rejected = await api('POST', `/api/cycles/${ok.body.id}/reject`, { reason: 'occupancy_mismatch', detail: '1 weight, 2 occupied slots', occupied_slots: [1, 2], frame_path: 'ai/captures/20260902/cycle_route_reject.jpg' })
  assert.equal(rejected.status, 200)
  assert.deepEqual((await api('GET', `/api/cycles/${ok.body.id}/result`)).body, { status: 'rejected', reason: 'occupancy_mismatch' })

  const malformed = await api('POST', '/api/cycles', { weights: 'six', total_g: 1 })
  assert.equal(malformed.status, 400)
  assert.equal(malformed.body.code, 'WEIGHTS_REQUIRED')
})
