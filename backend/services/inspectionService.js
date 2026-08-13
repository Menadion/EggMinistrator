import database from '../db.js'

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
      inspections.final_grade AS finalGrade,
      inspections.station_name AS device
    FROM egg_inspections AS inspections
    LEFT JOIN size_grades ON size_grades.id = inspections.size_grade_id
    LEFT JOIN ai_assessments AS assessments ON assessments.inspection_id = inspections.id
    WHERE inspections.final_disposition <> 'no_egg'
    ORDER BY inspections.captured_at DESC, inspections.id DESC
  `)

  const inspections = rows.map(({ inspectionCode, batchId, sequenceNumber, aiQuality, isOverridden, finalGrade, ...inspection }) => {
    const overridden = Number(isOverridden) === 1
    return {
      ...inspection,
      // `quality` stays the field every page already reads, so nothing downstream
      // changes. What moves is where it comes from: a human's override wins over
      // the model's label, which is the whole point of FR-03.
      quality: overridden && finalGrade ? finalGrade : aiQuality,
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
const OVERRIDE_LABELS = {
  good: 'accepted',
  defective: 'rejected',
  not_an_egg: 'no_egg',
}

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
            final_grade = ?,
            notes = CONCAT(COALESCE(notes, ''), IF(notes IS NULL OR notes = '', '', '\n'), ?)
      WHERE inspection_code = ?`,
    [disposition, label, note, code],
  )

  if (result.affectedRows === 0) throw new Error('No inspection found with that code.')

  return { inspectionCode: code, quality: label, isOverridden: true, disposition }
}
