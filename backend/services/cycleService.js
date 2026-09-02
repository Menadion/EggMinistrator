// The database half of the fan-out (spec sections 3 and 4). cycleRules.js has
// already decided what is well-formed; this file decides what exists.
//
// Only one function in here mints eggs: saveCycleAssessment (Task 5), and it
// does so inside one transaction, so six rows are born together or not at
// all. createCycle mints a *cycle*, which is the parent, never an egg.
import database from '../db.js'
import { randomUUID } from 'node:crypto'
import { InspectionError, classificationDispositions, findOrCreateDailyBatch, findSizeGrade, isSafeInteger, nextSequenceNumber } from './inspectionService.js'
import { SUM_MISMATCH_REASON, parseCycleAssessment, parseCyclePost, parseCycleReject, sumMismatch, sumTolerance } from './cycleRules.js'

const requireCycleId = (cycleId) => {
  if (!isSafeInteger(cycleId) || cycleId === 0) throw new InspectionError('Cycle id must be a positive whole number.', 400, 'INVALID_CYCLE_ID')
}

// raw_weights is the board's body as received. Re-parsing it through the same
// validator is how the weights come back out, so there is one reading of the
// body, not two that can drift.
export const weightsOf = (rawWeights) => parseCyclePost(JSON.parse(rawWeights)).weights

// D2 + D3: one POST at lid-close. The sum check is the one thing the server
// can verify without eyes; failing it mints the cycle already rejected so the
// audit row exists and the board learns through the result poll.
export async function createCycle(body) {
  const { stationName, weights, totalG } = parseCyclePost(body)
  const mismatch = sumMismatch(weights, totalG, sumTolerance())
  const status = mismatch ? 'rejected' : 'pending'
  const rejectedReason = mismatch ? `${SUM_MISMATCH_REASON}: ${mismatch}`.slice(0, 200) : null
  const [result] = await database.execute(
    'INSERT INTO tray_cycles (station_name, status, raw_weights, rejected_reason) VALUES (?, ?, ?, ?)',
    [stationName, status, JSON.stringify(body), rejectedReason],
  )
  return { id: result.insertId, status }
}

// Oldest pending first, same reasoning as findPendingInspection: a backlog
// drains in lid-close order. Weights ride along so the listener can check
// occupancy without a second call.
export async function findPendingCycle() {
  const [rows] = await database.execute(
    "SELECT id, raw_weights, created_at FROM tray_cycles WHERE status = 'pending' ORDER BY created_at ASC, id ASC LIMIT 1",
  )
  if (!rows[0]) return null
  return { id: rows[0].id, weights: weightsOf(rows[0].raw_weights), created_at: rows[0].created_at }
}

const reasonCode = (storedReason) => String(storedReason || '').split(':')[0].trim()

export async function getCycleResult(cycleId) {
  requireCycleId(cycleId)
  const [cycles] = await database.execute('SELECT status, rejected_reason FROM tray_cycles WHERE id = ? LIMIT 1', [cycleId])
  if (!cycles[0]) throw new InspectionError('Cycle not found.', 404, 'CYCLE_NOT_FOUND')
  const { status, rejected_reason: rejectedReason } = cycles[0]
  if (status === 'pending') return { status: 'pending' }
  if (status === 'rejected') return { status: 'rejected', reason: reasonCode(rejectedReason) }

  const [rows] = await database.execute(`
    SELECT inspections.tray_slot AS slot, assessments.result_label AS label,
           inspections.final_disposition AS disposition, size_grades.label AS size
    FROM egg_inspections AS inspections
    LEFT JOIN ai_assessments AS assessments ON assessments.inspection_id = inspections.id
    LEFT JOIN size_grades ON size_grades.id = inspections.size_grade_id
    WHERE inspections.cycle_id = ?
    ORDER BY inspections.tray_slot ASC
  `, [cycleId])
  const eggs = rows.map((row) => ({ slot: Number(row.slot), label: row.label, disposition: row.disposition, size: row.size ?? null }))
  return { status: 'done', eggs, any_defective: eggs.some((egg) => egg.label === 'defective') }
}

// THE FAN-OUT. One cycle in, k eggs out, in one transaction. Everything here
// reuses v1's own service functions so an egg born from a tray is
// indistinguishable from an egg born from the single-egg station: same daily
// batch, same sequence numbers, same size-grade lookup, same disposition map,
// same not_an_egg handling (no size). The only new facts are cycle_id and
// tray_slot.
//
// Gated on status = 'pending' under FOR UPDATE: a listener that crashed after
// saving crops and re-picked the cycle cannot mint twice, and two listeners
// cannot race.
export async function saveCycleAssessment(cycleId, body) {
  requireCycleId(cycleId)
  const connection = await database.getConnection()
  try {
    await connection.beginTransaction()
    const [cycles] = await connection.execute('SELECT id, station_name, status, raw_weights FROM tray_cycles WHERE id = ? FOR UPDATE', [cycleId])
    const cycle = cycles[0]
    if (!cycle) throw new InspectionError('Cycle not found.', 404, 'CYCLE_NOT_FOUND')
    if (cycle.status !== 'pending') throw new InspectionError(`Cycle is already ${cycle.status}.`, 409, 'CYCLE_NOT_PENDING')

    const weights = weightsOf(cycle.raw_weights)
    const { framePath, eggs } = parseCycleAssessment(body, weights.length)
    const batchId = await findOrCreateDailyBatch(connection, cycle.station_name)
    const inspections = []

    for (const egg of eggs) {
      const weight = weights[egg.slot - 1]
      const disposition = classificationDispositions[egg.class]
      const sizeGrade = egg.class === 'not_an_egg' ? null : await findSizeGrade(connection, weight)
      const sequenceNumber = await nextSequenceNumber(connection, batchId)

      const [inserted] = await connection.execute(`
        INSERT INTO egg_inspections (
          inspection_code, batch_id, sequence_number, station_name, weight_g, size_grade_id,
          ai_disposition, final_disposition, final_grade, cycle_id, tray_slot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [randomUUID(), batchId, sequenceNumber, cycle.station_name, weight, sizeGrade ? sizeGrade.id : null, disposition, disposition, sizeGrade ? sizeGrade.label : null, cycleId, egg.slot])
      const inspectionId = inserted.insertId

      await connection.execute(`
        INSERT INTO ai_assessments (
          inspection_id, assessment_type, result_label, confidence_score, is_defect_detected,
          model_name, model_version, inference_time_ms, raw_result
        ) VALUES (?, 'candling', ?, ?, ?, ?, ?, ?, ?)
      `, [inspectionId, egg.class, egg.confidence, egg.class === 'defective' ? 1 : 0, egg.modelName, egg.modelVersion, egg.inferenceTimeMs, egg.rawResult])

      await connection.execute(
        "INSERT INTO inspection_images (inspection_id, image_type, file_path) VALUES (?, 'candling', ?)",
        [inspectionId, egg.imagePath],
      )
      inspections.push({ slot: egg.slot, id: inspectionId })
    }

    await connection.execute(
      "UPDATE tray_cycles SET status = 'done', frame_path = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
      [framePath, cycleId],
    )
    await connection.commit()
    return { id: cycleId, status: 'done', inspections }
  } catch (error) {
    await connection.rollback()
    throw error
  } finally {
    connection.release()
  }
}

// The listener's refusal (optics: occupancy or prefix). The frame is kept as
// evidence of what the refused tray looked like. No egg rows ever exist.
export async function rejectCycle(cycleId, body) {
  requireCycleId(cycleId)
  const { reason, detail, occupiedSlots, framePath } = parseCycleReject(body)
  const suffix = occupiedSlots.length ? ` (occupied ${occupiedSlots.join(',')})` : ''
  const stored = (detail || suffix) ? `${reason}: ${detail}${suffix}`.slice(0, 200) : reason

  const [result] = await database.execute(
    "UPDATE tray_cycles SET status = 'rejected', rejected_reason = ?, frame_path = COALESCE(?, frame_path) WHERE id = ? AND status = 'pending'",
    [stored, framePath, cycleId],
  )
  if (result.affectedRows === 0) {
    const [rows] = await database.execute('SELECT status FROM tray_cycles WHERE id = ? LIMIT 1', [cycleId])
    if (!rows[0]) throw new InspectionError('Cycle not found.', 404, 'CYCLE_NOT_FOUND')
    throw new InspectionError(`Cycle is already ${rows[0].status}.`, 409, 'CYCLE_NOT_PENDING')
  }
  return { id: cycleId, status: 'rejected', reason }
}
