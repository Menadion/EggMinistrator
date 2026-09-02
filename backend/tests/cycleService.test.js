import test, { after, before } from 'node:test'
import assert from 'node:assert/strict'
import { databaseReachable } from './loadEnv.js'
import database from '../db.js'
import { createCycle, findPendingCycle, getCycleResult, weightsOf, saveCycleAssessment, rejectCycle } from '../services/cycleService.js'

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

const eggBody = (slot, cls = 'good') => ({
  slot, image_path: `ai/captures/20260902/cycle_test_slot${slot}.jpg`, class: cls, confidence: 0.91,
  model_name: 'candling-classifier', model_version: '0.3.0+test', inference_time_ms: 40,
  raw_result: JSON.stringify({ good: 0.91, defective: 0.05, not_an_egg: 0.04 }),
})

test('saveCycleAssessment mints k eggs, k images, k assessments and closes the cycle', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  const made = await createCycle({ station_name: 'Test Station', weights: [58.2, 47.0, 71.5], total_g: 176.7 })
  created.push(made.id)
  const saved = await saveCycleAssessment(made.id, {
    frame_path: 'ai/captures/20260902/cycle_test.jpg',
    eggs: [eggBody(3, 'defective'), eggBody(1), eggBody(2, 'not_an_egg')],
  })
  assert.equal(saved.status, 'done')
  assert.deepEqual(saved.inspections.map((e) => e.slot), [1, 2, 3])

  const [eggs] = await database.query(`
    SELECT i.tray_slot, i.weight_g, i.ai_disposition, i.final_disposition, i.final_grade, i.size_grade_id, i.batch_id, i.sequence_number, i.station_name,
           a.result_label, a.raw_result, im.file_path
    FROM egg_inspections i
    JOIN ai_assessments a ON a.inspection_id = i.id
    JOIN inspection_images im ON im.inspection_id = i.id
    WHERE i.cycle_id = ? ORDER BY i.tray_slot`, [made.id])
  assert.equal(eggs.length, 3)
  assert.deepEqual(eggs.map((e) => Number(e.weight_g)), [58.2, 47.0, 71.5])
  assert.deepEqual(eggs.map((e) => e.ai_disposition), ['accepted', 'no_egg', 'rejected'])
  assert.deepEqual(eggs.map((e) => e.final_disposition), ['accepted', 'no_egg', 'rejected'])
  assert.equal(eggs[0].final_grade, 'Medium')          // 58.2 g under PNS
  assert.equal(eggs[1].final_grade, null)              // not_an_egg carries no size, as v1
  assert.equal(eggs[1].size_grade_id, null)
  assert.equal(eggs[2].final_grade, 'Jumbo')           // 71.5 g
  assert.equal(eggs[0].station_name, 'Test Station')
  assert.ok(eggs.every((e) => e.batch_id === eggs[0].batch_id))
  assert.deepEqual(eggs.map((e) => e.sequence_number), [eggs[0].sequence_number, eggs[0].sequence_number + 1, eggs[0].sequence_number + 2])
  assert.equal(eggs[0].raw_result, eggBody(1).raw_result)
  assert.equal(eggs[2].file_path, 'ai/captures/20260902/cycle_test_slot3.jpg')

  const [cycle] = await database.query('SELECT status, frame_path, completed_at FROM tray_cycles WHERE id = ?', [made.id])
  assert.equal(cycle[0].status, 'done')
  assert.equal(cycle[0].frame_path, 'ai/captures/20260902/cycle_test.jpg')
  assert.ok(cycle[0].completed_at)

  const result = await getCycleResult(made.id)
  assert.equal(result.status, 'done')
  assert.equal(result.any_defective, true)
  assert.deepEqual(result.eggs, [
    { slot: 1, label: 'good', disposition: 'accepted', size: 'Medium' },
    { slot: 2, label: 'not_an_egg', disposition: 'no_egg', size: null },
    { slot: 3, label: 'defective', disposition: 'rejected', size: 'Jumbo' },
  ])
})

test('saveCycleAssessment is all-or-nothing: a bad egg in the bundle leaves zero rows', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  const made = await createCycle({ weights: [58.2, 61.0], total_g: 119.2 })
  created.push(made.id)
  await assert.rejects(
    () => saveCycleAssessment(made.id, { frame_path: 'ai/captures/x.jpg', eggs: [eggBody(1), { ...eggBody(2), raw_result: 'not json' }] }),
    { code: 'INVALID_RAW_RESULT' },
  )
  const [rows] = await database.query('SELECT COUNT(*) AS n FROM egg_inspections WHERE cycle_id = ?', [made.id])
  assert.equal(Number(rows[0].n), 0)
  assert.deepEqual(await getCycleResult(made.id), { status: 'pending' })
})

test('saveCycleAssessment refuses a count or prefix mismatch and a non-pending cycle', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  const made = await createCycle({ weights: [58.2, 61.0], total_g: 119.2 })
  created.push(made.id)
  await assert.rejects(() => saveCycleAssessment(made.id, { frame_path: 'ai/captures/x.jpg', eggs: [eggBody(1)] }), { code: 'EGG_COUNT_MISMATCH' })
  await assert.rejects(() => saveCycleAssessment(made.id, { frame_path: 'ai/captures/x.jpg', eggs: [eggBody(1), eggBody(3)] }), { code: 'SLOTS_NOT_PREFIX' })
  await saveCycleAssessment(made.id, { frame_path: 'ai/captures/x.jpg', eggs: [eggBody(1), eggBody(2)] })
  await assert.rejects(() => saveCycleAssessment(made.id, { frame_path: 'ai/captures/x.jpg', eggs: [eggBody(1), eggBody(2)] }), { code: 'CYCLE_NOT_PENDING' })
  await assert.rejects(() => saveCycleAssessment(999999999, { frame_path: 'ai/captures/x.jpg', eggs: [eggBody(1)] }), { code: 'CYCLE_NOT_FOUND' })
})

test('rejectCycle marks a pending cycle rejected with the reason and keeps the frame, and never mints eggs', async (t) => {
  if (!dbUp) return t.skip('MySQL is not running on 3306')
  const made = await createCycle({ weights: [58.2, 61.0], total_g: 119.2 })
  created.push(made.id)
  const rejected = await rejectCycle(made.id, { reason: 'not_prefix', detail: 'slot 1 empty, slot 2 occupied', occupied_slots: [2], frame_path: 'ai/captures/20260902/cycle_test_reject.jpg' })
  assert.deepEqual(rejected, { id: made.id, status: 'rejected', reason: 'not_prefix' })
  const [cycle] = await database.query('SELECT status, rejected_reason, frame_path FROM tray_cycles WHERE id = ?', [made.id])
  assert.equal(cycle[0].status, 'rejected')
  assert.equal(cycle[0].rejected_reason, 'not_prefix: slot 1 empty, slot 2 occupied (occupied 2)')
  assert.equal(cycle[0].frame_path, 'ai/captures/20260902/cycle_test_reject.jpg')
  const [rows] = await database.query('SELECT COUNT(*) AS n FROM egg_inspections WHERE cycle_id = ?', [made.id])
  assert.equal(Number(rows[0].n), 0)
  assert.deepEqual(await getCycleResult(made.id), { status: 'rejected', reason: 'not_prefix' })
  await assert.rejects(() => rejectCycle(made.id, { reason: 'occupancy_mismatch' }), { code: 'CYCLE_NOT_PENDING' })
  await assert.rejects(() => rejectCycle(999999999, { reason: 'occupancy_mismatch' }), { code: 'CYCLE_NOT_FOUND' })
})
