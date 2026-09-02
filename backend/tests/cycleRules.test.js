import test from 'node:test'
import assert from 'node:assert/strict'
import { parseCyclePost, sumTolerance, sumMismatch, parseCycleAssessment, parseCycleReject, MAX_SLOTS } from '../services/cycleRules.js'

const egg = (slot, extra = {}) => ({
  slot, image_path: `ai/captures/20260902/cycle_1_slot${slot}.jpg`, class: 'good', confidence: 0.9,
  model_name: 'candling-classifier', model_version: '0.3.0+test', inference_time_ms: 40,
  raw_result: JSON.stringify({ good: 0.9, defective: 0.05, not_an_egg: 0.05 }), ...extra,
})

test('parseCyclePost accepts 1..6 slot-ordered weights and a total', () => {
  const parsed = parseCyclePost({ station_name: 'Station 1', weights: [58.2, 61.0, 55.4], total_g: 174.6 })
  assert.deepEqual(parsed, { stationName: 'Station 1', weights: [58.2, 61, 55.4], totalG: 174.6 })
})

test('parseCyclePost defaults the station name', () => {
  assert.equal(parseCyclePost({ weights: [50], total_g: 50 }).stationName, 'Station 1')
})

test('parseCyclePost rejects empty, oversized, and non-numeric weights', () => {
  assert.throws(() => parseCyclePost({ weights: [], total_g: 0 }), { code: 'WEIGHTS_REQUIRED' })
  assert.throws(() => parseCyclePost({ total_g: 0 }), { code: 'WEIGHTS_REQUIRED' })
  assert.throws(() => parseCyclePost({ weights: [50, 50, 50, 50, 50, 50, 50], total_g: 350 }), { code: 'TOO_MANY_WEIGHTS' })
  assert.throws(() => parseCyclePost({ weights: [50, 'x'], total_g: 100 }), { code: 'INVALID_WEIGHT' })
  assert.throws(() => parseCyclePost({ weights: [50, 0], total_g: 50 }), { code: 'INVALID_WEIGHT' })
  assert.throws(() => parseCyclePost({ weights: [50], total_g: 'heavy' }), { code: 'INVALID_TOTAL' })
  assert.throws(() => parseCyclePost({ weights: [50], total_g: -1 }), { code: 'INVALID_TOTAL' })
})

test('MAX_SLOTS is six', () => assert.equal(MAX_SLOTS, 6))

test('sumTolerance reads the env and defaults to 3', () => {
  delete process.env.CYCLE_SUM_TOLERANCE_G
  assert.equal(sumTolerance(), 3)
  process.env.CYCLE_SUM_TOLERANCE_G = '1.5'
  assert.equal(sumTolerance(), 1.5)
  process.env.CYCLE_SUM_TOLERANCE_G = 'nonsense'
  assert.equal(sumTolerance(), 3)
  delete process.env.CYCLE_SUM_TOLERANCE_G
})

test('sumMismatch is null inside tolerance and a sentence outside it', () => {
  assert.equal(sumMismatch([58.2, 61.0], 119.2, 3), null)
  assert.equal(sumMismatch([58.2, 61.0], 122.1, 3), null)
  assert.equal(sumMismatch([58.2, 61.0], 122.3, 3), 'sum(weights) 119.2 g vs total_g 122.3 g, tolerance ±3 g')
})

test('parseCycleAssessment accepts a full prefix and sorts by slot', () => {
  const parsed = parseCycleAssessment({ frame_path: 'ai/captures/20260902/cycle_1.jpg', eggs: [egg(2), egg(1)] }, 2)
  assert.equal(parsed.framePath, 'ai/captures/20260902/cycle_1.jpg')
  assert.deepEqual(parsed.eggs.map((e) => e.slot), [1, 2])
  assert.equal(parsed.eggs[0].imagePath, 'ai/captures/20260902/cycle_1_slot1.jpg')
  assert.equal(parsed.eggs[0].confidence, 0.9)
  assert.equal(parsed.eggs[0].rawResult, egg(1).raw_result)
})

test('parseCycleAssessment enforces count and prefix', () => {
  const frame = 'ai/captures/20260902/cycle_1.jpg'
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(1)] }, 2), { code: 'EGG_COUNT_MISMATCH' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(1), egg(3)] }, 2), { code: 'SLOTS_NOT_PREFIX' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(1), egg(1)] }, 2), { code: 'SLOTS_NOT_PREFIX' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(0)] }, 1), { code: 'INVALID_SLOT' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(7)] }, 1), { code: 'INVALID_SLOT' })
  assert.throws(() => parseCycleAssessment({ frame_path: '', eggs: [egg(1)] }, 1), { code: 'FRAME_PATH_REQUIRED' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame }, 1), { code: 'EGGS_REQUIRED' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(1, { class: 'cracked' })] }, 1), { code: 'INVALID_RESULT_LABEL' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(1, { image_path: '' })] }, 1), { code: 'IMAGE_REQUIRED' })
  assert.throws(() => parseCycleAssessment({ frame_path: frame, eggs: [egg(1, { raw_result: '{not json' })] }, 1), { code: 'INVALID_RAW_RESULT' })
})

test('parseCycleReject accepts the two optical reasons only', () => {
  const parsed = parseCycleReject({ reason: 'not_prefix', detail: 'slot 2 empty, slot 3 occupied', occupied_slots: [1, 3], frame_path: 'ai/captures/20260902/cycle_1.jpg' })
  assert.deepEqual(parsed, { reason: 'not_prefix', detail: 'slot 2 empty, slot 3 occupied', occupiedSlots: [1, 3], framePath: 'ai/captures/20260902/cycle_1.jpg' })
  assert.equal(parseCycleReject({ reason: 'occupancy_mismatch' }).framePath, null)
  assert.throws(() => parseCycleReject({ reason: 'weights_sum_mismatch' }), { code: 'INVALID_REJECT_REASON' })
  assert.throws(() => parseCycleReject({}), { code: 'INVALID_REJECT_REASON' })
})
