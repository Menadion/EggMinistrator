import database from '../db.js'
import { randomUUID, timingSafeEqual } from 'node:crypto'

export class InspectionError extends Error {
  constructor(message, statusCode = 400, code = 'INSPECTION_ERROR') {
    super(message)
    this.statusCode = statusCode
    this.code = code
  }
}

const classificationDispositions = {
  good: 'accepted',
  defective: 'rejected',
  not_an_egg: 'no_egg',
}

const isSafeInteger = (value) => Number.isInteger(value) && value >= 0
const hasText = (value) => typeof value === 'string' && value.trim().length > 0

const parseRawResult = (value) => {
  if (!hasText(value)) {
    throw new InspectionError('raw_result must contain the classifier JSON line exactly as emitted.', 400, 'RAW_RESULT_REQUIRED')
  }

  try {
    JSON.parse(value)
  } catch {
    throw new InspectionError('raw_result must be valid JSON from the classifier.', 400, 'INVALID_RAW_RESULT')
  }

  return value
}

const parseWeight = (value) => {
  const weight = Number(value)
  if (!Number.isFinite(weight) || weight <= 0 || weight > 1000) throw new InspectionError('weight_g must be a number between 0 and 1000.', 400, 'INVALID_WEIGHT')
  return Number(weight.toFixed(2))
}

const parseConfidence = (value) => {
  const confidence = Number(value)
  if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) throw new InspectionError('confidence must be a number from 0 to 1.', 400, 'INVALID_CONFIDENCE')
  return Number(confidence.toFixed(4))
}

const parseInferenceTime = (value) => {
  const time = Number(value)
  if (!isSafeInteger(time)) throw new InspectionError('inference_time_ms must be a non-negative whole number.', 400, 'INVALID_INFERENCE_TIME')
  return time
}

const findSizeGrade = async (connection, weight) => {
  const [rows] = await connection.execute(`
    SELECT id, label
    FROM size_grades
    WHERE is_active = 1
      AND minimum_weight_g <= ?
      AND (maximum_weight_g IS NULL OR ? < maximum_weight_g)
    ORDER BY minimum_weight_g DESC
    LIMIT 1
  `, [weight, weight])

  if (!rows[0]) throw new InspectionError('No active size grade matches this weight.', 422, 'SIZE_GRADE_NOT_FOUND')
  return rows[0]
}

export function requireDeviceKey(headers) {
  const configuredKey = process.env.DEVICE_API_KEY
  if (!hasText(configuredKey)) throw new InspectionError('Device authentication is not configured. Add DEVICE_API_KEY to backend/.env.', 503, 'DEVICE_AUTH_NOT_CONFIGURED')

  const receivedKey = headers['x-device-key']
  if (!hasText(receivedKey)) throw new InspectionError('A valid X-Device-Key header is required.', 401, 'DEVICE_KEY_REQUIRED')

  const expected = Buffer.from(configuredKey)
  const received = Buffer.from(receivedKey)
  if (expected.length !== received.length || !timingSafeEqual(expected, received)) throw new InspectionError('The supplied device key is invalid.', 401, 'DEVICE_KEY_INVALID')
}

// A batch is one day's inspection run at one station. Decided 2026-08-15.
// The station has no operator screen to open and close a batch by hand, so the
// day is the unit that needs nobody to remember anything: the first egg of the
// day opens the batch and the rest join it.
//
// The date comes from CURDATE() rather than from JavaScript so that it agrees
// with captured_at, which defaults to the database clock. Deriving it in Node
// puts the batch a day out whenever UTC and local time fall either side of
// midnight, which in Manila is every evening.
async function findOrCreateDailyBatch(connection, stationName) {
  const [result] = await connection.execute(`
    INSERT INTO inspection_batches (batch_code, source_name, notes, started_at)
    VALUES (CONCAT(?, ' ', CURDATE()), ?, 'Daily inspection run, opened automatically by the station.', CURRENT_TIMESTAMP)
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
  `, [stationName, stationName])
  return result.insertId
}

// sequence_number counts within its own batch, so it restarts at 1 each day.
// The batch row is locked first: two eggs arriving together would otherwise
// read the same MAX and both claim the same number.
async function nextSequenceNumber(connection, batchId) {
  await connection.execute('SELECT id FROM inspection_batches WHERE id = ? FOR UPDATE', [batchId])
  const [rows] = await connection.execute(
    'SELECT COALESCE(MAX(sequence_number), 0) + 1 AS nextNumber FROM egg_inspections WHERE batch_id = ?',
    [batchId],
  )
  return Number(rows[0].nextNumber)
}

export async function createInspection({ weight_g: weightValue }) {
  const weight = parseWeight(weightValue)
  const connection = await database.getConnection()

  try {
    await connection.beginTransaction()
    const stationName = process.env.STATION_NAME || 'Station 1'
    const sizeGrade = await findSizeGrade(connection, weight)
    const batchId = await findOrCreateDailyBatch(connection, stationName)
    const sequenceNumber = await nextSequenceNumber(connection, batchId)
    const [result] = await connection.execute(`
      INSERT INTO egg_inspections (
        inspection_code, batch_id, sequence_number, station_name, weight_g, size_grade_id, ai_disposition, final_disposition, final_grade
      ) VALUES (?, ?, ?, ?, ?, ?, 'review', 'review', ?)
    `, [randomUUID(), batchId, sequenceNumber, stationName, weight, sizeGrade.id, sizeGrade.label])
    await connection.commit()
    return { id: result.insertId }
  } catch (error) {
    await connection.rollback()
    throw error
  } finally {
    connection.release()
  }
}

export async function saveAssessment(inspectionId, assessment) {
  if (!isSafeInteger(inspectionId) || inspectionId === 0) throw new InspectionError('Inspection id must be a positive whole number.', 400, 'INVALID_INSPECTION_ID')

  const resultLabel = assessment.class
  if (!Object.hasOwn(classificationDispositions, resultLabel)) throw new InspectionError('class must be good, defective, or not_an_egg.', 400, 'INVALID_RESULT_LABEL')
  if (!hasText(assessment.image)) throw new InspectionError('image is required.', 400, 'IMAGE_REQUIRED')
  if (!hasText(assessment.model_name)) throw new InspectionError('model_name is required.', 400, 'MODEL_NAME_REQUIRED')
  if (!hasText(assessment.model_version)) throw new InspectionError('model_version is required.', 400, 'MODEL_VERSION_REQUIRED')

  const confidence = parseConfidence(assessment.confidence)
  const inferenceTime = parseInferenceTime(assessment.inference_time_ms)
  const rawResult = parseRawResult(assessment.raw_result)
  const disposition = classificationDispositions[resultLabel]
  const connection = await database.getConnection()

  try {
    await connection.beginTransaction()
    const [inspections] = await connection.execute('SELECT id FROM egg_inspections WHERE id = ? FOR UPDATE', [inspectionId])
    if (!inspections[0]) throw new InspectionError('Inspection not found.', 404, 'INSPECTION_NOT_FOUND')

    const [existingAssessments] = await connection.execute('SELECT id FROM ai_assessments WHERE inspection_id = ? LIMIT 1', [inspectionId])
    if (existingAssessments[0]) throw new InspectionError('This inspection already has an assessment.', 409, 'ASSESSMENT_ALREADY_EXISTS')

    await connection.execute(`
      INSERT INTO ai_assessments (
        inspection_id, assessment_type, result_label, confidence_score, is_defect_detected,
        model_name, model_version, inference_time_ms, raw_result
      ) VALUES (?, 'candling', ?, ?, ?, ?, ?, ?, ?)
    `, [inspectionId, resultLabel, confidence, resultLabel === 'defective' ? 1 : 0, assessment.model_name.trim(), assessment.model_version.trim(), inferenceTime, rawResult])

    await connection.execute(`
      INSERT INTO inspection_images (inspection_id, image_type, file_path)
      VALUES (?, 'candling', ?)
    `, [inspectionId, assessment.image.trim()])

    if (resultLabel === 'not_an_egg') {
      await connection.execute(`
        UPDATE egg_inspections
        SET ai_disposition = ?, final_disposition = ?, size_grade_id = NULL, final_grade = NULL
        WHERE id = ?
      `, [disposition, disposition, inspectionId])
    } else {
      await connection.execute(`
        UPDATE egg_inspections
        SET ai_disposition = ?, final_disposition = ?
        WHERE id = ?
      `, [disposition, disposition, inspectionId])
    }

    await connection.commit()
    return { id: inspectionId, label: resultLabel, confidence }
  } catch (error) {
    await connection.rollback()
    throw error
  } finally {
    connection.release()
  }
}

export async function getInspectionResult(inspectionId) {
  if (!isSafeInteger(inspectionId) || inspectionId === 0) throw new InspectionError('Inspection id must be a positive whole number.', 400, 'INVALID_INSPECTION_ID')

  const [rows] = await database.execute(`
    SELECT assessments.result_label AS label, assessments.confidence_score AS confidence
    FROM egg_inspections AS inspections
    LEFT JOIN ai_assessments AS assessments ON assessments.inspection_id = inspections.id
    WHERE inspections.id = ?
    LIMIT 1
  `, [inspectionId])

  if (!rows[0]) throw new InspectionError('Inspection not found.', 404, 'INSPECTION_NOT_FOUND')
  if (!rows[0].label) return { status: 'pending' }
  return { label: rows[0].label, confidence: Number(rows[0].confidence) }
}

// Section 4.1 step 2: the classifier asks whether an egg is waiting for a verdict.
//
// The waiting state was never missing -- an egg_inspections row with no matching
// ai_assessments row IS an egg waiting. What was missing is a way to ask about it
// from outside this process. ai/listen_station.py is a CLIENT: it holds no port
// and nothing can call it, so it can only poll a URL the server recognises.
//
// Oldest first, so a backlog drains in the order the eggs were weighed rather
// than newest-first, which would strand the earliest egg forever.
export async function findPendingInspection() {
  const [rows] = await database.execute(`
    SELECT inspections.id, inspections.inspection_code, inspections.weight_g
    FROM egg_inspections AS inspections
    LEFT JOIN ai_assessments AS assessments ON assessments.inspection_id = inspections.id
    WHERE assessments.id IS NULL
    ORDER BY inspections.id ASC
    LIMIT 1
  `)

  if (!rows[0]) return null
  return { id: rows[0].id, inspection_code: rows[0].inspection_code, weight_g: rows[0].weight_g }
}

function formatEggId(inspectionCode, batchId, sequenceNumber) {
  const hasBatchId = batchId !== null && batchId !== undefined && String(batchId).trim() !== ''
  const hasSequenceNumber = sequenceNumber !== null && sequenceNumber !== undefined && String(sequenceNumber).trim() !== ''
  const batch = Number(batchId)
  const sequence = Number(sequenceNumber)

  if (hasBatchId && hasSequenceNumber && Number.isInteger(batch) && batch >= 0 && Number.isInteger(sequence) && sequence >= 0) {
    return `B${String(batch).padStart(3, '0')}-EGG-${String(sequence).padStart(3, '0')}`
  }

  const code = typeof inspectionCode === 'string' ? inspectionCode.trim() : ''
  return code ? `${code.slice(0, 8)}…` : '—'
}

// A deliberately tiny companion to listInspections(). The dashboard polls this
// every few seconds so it can notice a new egg without refetching every row.
//
// listInspections() has no LIMIT: it returns every non-'no_egg' inspection,
// which is over five thousand rows on a seeded database. Polling THAT would
// move about a megabyte every few seconds and re-render the charts each time,
// which is visible jank during a live demo.
//
// Three signals, because one is not enough:
//   total       a new inspection arrives, or a row leaves via 'no_egg'
//   latestId    a new row, even if another left in the same window
//   lastChange  an assessment or an override edits a row IN PLACE, so neither
//               of the above moves, but updated_at does
export async function getInspectionsRevision() {
  const [rows] = await database.execute(`
    SELECT
      COUNT(*) AS total,
      COALESCE(MAX(id), 0) AS latestId,
      COALESCE(MAX(updated_at), '1970-01-01') AS lastChange
    FROM egg_inspections
    WHERE final_disposition <> 'no_egg'
  `)
  return {
    total: Number(rows[0].total),
    latestId: Number(rows[0].latestId),
    lastChange: String(rows[0].lastChange),
  }
}

export async function listInspections() {
  const [rows] = await database.execute(`
    SELECT
      inspections.inspection_code AS inspectionCode,
      inspections.batch_id AS batchId,
      inspections.sequence_number AS sequenceNumber,
      DATE_FORMAT(inspections.captured_at, '%Y-%m-%d') AS date,
      DATE_FORMAT(inspections.captured_at, '%m/%d/%Y') AS displayDate,
      DATE_FORMAT(inspections.captured_at, '%l:%i:%s %p') AS time,
      inspections.weight_g AS weight,
      size_grades.label AS size,
      assessments.result_label AS aiQuality,
      inspections.is_overridden AS isOverridden,
      inspections.final_disposition AS finalDisposition,
      inspections.station_name AS device
    FROM egg_inspections AS inspections
    LEFT JOIN size_grades ON size_grades.id = inspections.size_grade_id
    LEFT JOIN ai_assessments AS assessments ON assessments.inspection_id = inspections.id
    WHERE inspections.final_disposition <> 'no_egg'
    ORDER BY inspections.captured_at DESC, inspections.id DESC
  `)

  const inspections = rows.map(({ inspectionCode, batchId, sequenceNumber, aiQuality, isOverridden, finalDisposition, ...inspection }) => {
    const overridden = Number(isOverridden) === 1
    const overriddenLabel = DISPOSITION_TO_LABEL[finalDisposition]
    return {
      ...inspection,
      // `quality` stays the field every page already reads, so nothing downstream
      // changes. What moves is where it comes from: a human's override wins over
      // the model's label, which is the whole point of FR-03.
      quality: overridden && overriddenLabel ? overriddenLabel : aiQuality,
      aiQuality,
      isOverridden: overridden,
      eggId: formatEggId(inspectionCode, batchId, sequenceNumber),
      inspectionCode,
    }
  })

  return { inspections, dataSource: 'MariaDB' }
}

// FR-03: allow authorized personnel to override an AI classification result.
//
// The schema was built for this and nothing had ever used it: `ai_disposition`
// keeps what the model said, `final_disposition` is what stands, and
// `is_overridden` records that the two differ by human decision rather than by
// accident. We never touch `ai_disposition` -- overwriting what the model said
// would destroy the only evidence that an override happened.
//
// ⚠️ `final_grade` is NOT this column. The sample data puts size labels in it
// ("Medium", "Large"), so it is the final *size* grade, not the final verdict.
// Writing a quality label there corrupts the size shown on every page.
const OVERRIDE_LABELS = {
  good: 'accepted',
  defective: 'rejected',
  not_an_egg: 'no_egg',
}

const DISPOSITION_TO_LABEL = Object.fromEntries(
  Object.entries(OVERRIDE_LABELS).map(([label, disposition]) => [disposition, label]),
)

export async function overrideInspection({ inspectionCode, label, actor }) {
  const code = typeof inspectionCode === 'string' ? inspectionCode.trim() : ''
  if (!code) throw new Error('An inspection code is required.')

  const disposition = OVERRIDE_LABELS[label]
  if (!disposition) {
    throw new Error(`Result must be one of: ${Object.keys(OVERRIDE_LABELS).join(', ')}.`)
  }

  // There is no `overridden_by` column, so the audit trail goes in `notes`.
  // Worth a real column eventually -- see CONTRACT.md section 7.
  const who = actor?.username || 'unknown'
  const stamp = new Date().toISOString()
  const note = `Overridden to "${label}" by ${who} at ${stamp}.`

  const [result] = await database.execute(
    `UPDATE egg_inspections
        SET is_overridden = 1,
            final_disposition = ?,
            notes = CONCAT(COALESCE(notes, ''), IF(notes IS NULL OR notes = '', '', '\n'), ?)
      WHERE inspection_code = ?`,
    [disposition, note, code],
  )

  if (result.affectedRows === 0) throw new Error('No inspection found with that code.')

  return { inspectionCode: code, quality: label, isOverridden: true, disposition }
}
