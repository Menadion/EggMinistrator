import test, { after, before } from 'node:test'
import assert from 'node:assert/strict'
import { databaseReachable } from './loadEnv.js'
import database from '../db.js'
import { createCycle, findPendingCycle, getCycleResult, weightsOf } from '../services/cycleService.js'

let dbUp = false
const created = []   // cycle ids to delete afterwards

before(async () => { dbUp = await databaseReachable() })
after(async () => {
  if (created.length) {
    await database.query('DELETE FROM egg_inspections WHERE cycle_id IN (?)', [created])
    await database.query('DELETE FROM tray_cycles WHERE id IN (?)', [created])
  }
  await database.end()
})

// Drain any pending cycles left by an earlier crashed run so "oldest pending"
// is deterministic for this file.
const drainPending = async () => { await database.query("UPDATE tray_cycles SET status='rejected', rejected_reason='test_drain' WHERE status='pending'") }

test('weightsOf re-parses the stored body', () => {
  assert.deepEqual(weightsOf(JSON.stringify({ weights: [58.2, 61], total_g: 119.2 })), [58.2, 61])
})

test('createCycle mints a pending row when the sum agrees', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  await drainPending()
  const made = await createCycle({ station_name: 'Test Station', weights: [58.2, 61.0, 55.4], total_g: 174.6 })
  created.push(made.id)
  assert.equal(made.status, 'pending')
  const [rows] = await database.query('SELECT status, station_name, raw_weights, rejected_reason FROM tray_cycles WHERE id = ?', [made.id])
  assert.equal(rows[0].status, 'pending')
  assert.equal(rows[0].station_name, 'Test Station')
  assert.deepEqual(JSON.parse(rows[0].raw_weights).weights, [58.2, 61.0, 55.4])
  assert.equal(rows[0].rejected_reason, null)
})

test('createCycle mints a rejected row when the sum disagrees, and still answers with an id', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  const made = await createCycle({ weights: [58.2, 61.0], total_g: 130.0 })
  created.push(made.id)
  assert.equal(made.status, 'rejected')
  assert.deepEqual(await getCycleResult(made.id), { status: 'rejected', reason: 'weights_sum_mismatch' })
})

test('findPendingCycle returns the oldest pending cycle with its weights, or null', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  await drainPending()
  assert.equal(await findPendingCycle(), null)
  const first = await createCycle({ weights: [50], total_g: 50 })
  const second = await createCycle({ weights: [60, 61], total_g: 121 })
  created.push(first.id, second.id)
  const waiting = await findPendingCycle()
  assert.equal(waiting.id, first.id)
  assert.deepEqual(waiting.weights, [50])
  assert.ok(waiting.created_at)
  assert.deepEqual(await getCycleResult(second.id), { status: 'pending' })
  await drainPending()
})

test('getCycleResult rejects a bad id and a missing cycle', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  await assert.rejects(() => getCycleResult(0), { code: 'INVALID_CYCLE_ID' })
  await assert.rejects(() => getCycleResult(999999999), { code: 'CYCLE_NOT_FOUND' })
})
