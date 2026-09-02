// The arithmetic half of the fan-out's division of labour (spec section 4):
// the server checks what it can check without eyes -- the weights add up, the
// slots are a prefix, the counts agree -- and only the transaction in
// cycleService.js mints eggs. Nothing in this file touches the database, which
// is what makes it unit-testable with MySQL down.
import { InspectionError, classificationDispositions, hasText, parseConfidence, parseInferenceTime, parseRawResult, parseWeight } from './inspectionService.js'

export const MAX_SLOTS = 6
export const REJECT_REASONS = ['occupancy_mismatch', 'not_prefix']
export const SUM_MISMATCH_REASON = 'weights_sum_mismatch'
const DEFAULT_TOLERANCE_G = 3

const round2 = (value) => Number(Number(value).toFixed(2))

// D2: one POST at lid-close. `weights` is slot-ordered, 1..6 entries, and the
// board's prompt flow is what guarantees the order -- the server cannot see it.
export function parseCyclePost(body) {
  const weights = body?.weights
  if (!Array.isArray(weights) || weights.length === 0) throw new InspectionError('weights must be a non-empty array of grams in slot order.', 400, 'WEIGHTS_REQUIRED')
  if (weights.length > MAX_SLOTS) throw new InspectionError(`weights may hold at most ${MAX_SLOTS} entries.`, 400, 'TOO_MANY_WEIGHTS')
  const parsedWeights = weights.map(parseWeight)   // 0 < w <= 1000, two decimals, INVALID_WEIGHT otherwise
  const totalG = Number(body.total_g)
  if (!Number.isFinite(totalG) || totalG < 0 || totalG > 6000) throw new InspectionError('total_g must be a non-negative number of grams.', 400, 'INVALID_TOTAL')
  const stationName = hasText(body.station_name) ? body.station_name.trim() : (process.env.STATION_NAME || 'Station 1')
  return { stationName, weights: parsedWeights, totalG: round2(totalG) }
}

export function sumTolerance() {
  const configured = Number(process.env.CYCLE_SUM_TOLERANCE_G)
  return Number.isFinite(configured) && configured >= 0 ? configured : DEFAULT_TOLERANCE_G
}

// null when the board's own total agrees with its steps; otherwise the detail
// the board reads back through the result poll. Open item 2 in the spec: ±3 g
// is a placeholder until the real cell's noise is measured.
export function sumMismatch(weights, totalG, tolerance) {
  const sum = round2(weights.reduce((acc, w) => acc + w, 0))
  if (Math.abs(sum - totalG) <= tolerance + 1e-9) return null
  return `sum(weights) ${sum} g vs total_g ${totalG} g, tolerance ±${tolerance} g`
}

const isPrefix = (slots, k) => slots.length === k && slots.every((slot, index) => slot === index + 1)

export function parseCycleAssessment(body, weightCount) {
  if (!hasText(body?.frame_path)) throw new InspectionError('frame_path is required.', 400, 'FRAME_PATH_REQUIRED')
  const eggs = body.eggs
  if (!Array.isArray(eggs) || eggs.length === 0) throw new InspectionError('eggs must be a non-empty array.', 400, 'EGGS_REQUIRED')
  if (eggs.length !== weightCount) throw new InspectionError(`eggs has ${eggs.length} entries but the cycle has ${weightCount} weights.`, 400, 'EGG_COUNT_MISMATCH')

  const parsed = eggs.map((item) => {
    const slot = Number(item?.slot)
    if (!Number.isInteger(slot) || slot < 1 || slot > MAX_SLOTS) throw new InspectionError(`slot must be a whole number from 1 to ${MAX_SLOTS}.`, 400, 'INVALID_SLOT')
    if (!Object.hasOwn(classificationDispositions, item.class)) throw new InspectionError('class must be good, defective, or not_an_egg.', 400, 'INVALID_RESULT_LABEL')
    if (!hasText(item.image_path)) throw new InspectionError('image_path is required on every egg.', 400, 'IMAGE_REQUIRED')
    if (!hasText(item.model_name)) throw new InspectionError('model_name is required.', 400, 'MODEL_NAME_REQUIRED')
    if (!hasText(item.model_version)) throw new InspectionError('model_version is required.', 400, 'MODEL_VERSION_REQUIRED')
    return {
      slot,
      class: item.class,
      imagePath: item.image_path.trim(),
      confidence: parseConfidence(item.confidence),
      modelName: item.model_name.trim(),
      modelVersion: item.model_version.trim(),
      inferenceTimeMs: parseInferenceTime(item.inference_time_ms),
      rawResult: parseRawResult(item.raw_result),
    }
  }).sort((a, b) => a.slot - b.slot)

  if (!isPrefix(parsed.map((e) => e.slot), weightCount)) throw new InspectionError(`slots must be exactly 1..${weightCount}, each once.`, 400, 'SLOTS_NOT_PREFIX')
  return { framePath: body.frame_path.trim(), eggs: parsed }
}

export function parseCycleReject(body) {
  const reason = body?.reason
  if (!REJECT_REASONS.includes(reason)) throw new InspectionError(`reason must be one of: ${REJECT_REASONS.join(', ')}.`, 400, 'INVALID_REJECT_REASON')
  const occupiedSlots = Array.isArray(body.occupied_slots) ? body.occupied_slots.map(Number).filter((n) => Number.isInteger(n) && n >= 1 && n <= MAX_SLOTS) : []
  return {
    reason,
    detail: hasText(body.detail) ? body.detail.trim().slice(0, 200) : '',
    occupiedSlots,
    framePath: hasText(body.frame_path) ? body.frame_path.trim() : null,
  }
}
