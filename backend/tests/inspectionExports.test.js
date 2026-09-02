import test from 'node:test'
import assert from 'node:assert/strict'
import * as inspections from '../services/inspectionService.js'

test('the helpers the cycle path reuses are exported', () => {
  for (const name of ['classificationDispositions', 'hasText', 'isSafeInteger', 'parseWeight', 'parseConfidence', 'parseInferenceTime', 'parseRawResult', 'findSizeGrade', 'findOrCreateDailyBatch', 'nextSequenceNumber']) {
    assert.ok(name in inspections, `${name} is not exported`)
  }
})

test('parseWeight keeps its v1 behaviour', () => {
  assert.equal(inspections.parseWeight('58.236'), 58.24)
  assert.throws(() => inspections.parseWeight(0), { code: 'INVALID_WEIGHT' })
  assert.throws(() => inspections.parseWeight(1001), { code: 'INVALID_WEIGHT' })
})

test('the disposition map is the Decision G one', () => {
  assert.deepEqual(inspections.classificationDispositions, { good: 'accepted', defective: 'rejected', not_an_egg: 'no_egg' })
})
