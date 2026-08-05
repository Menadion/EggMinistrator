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
      assessments.result_label AS quality,
      inspections.station_name AS device
    FROM egg_inspections AS inspections
    LEFT JOIN size_grades ON size_grades.id = inspections.size_grade_id
    LEFT JOIN ai_assessments AS assessments ON assessments.inspection_id = inspections.id
    WHERE inspections.final_disposition <> 'no_egg'
    ORDER BY inspections.captured_at DESC, inspections.id DESC
  `)

  const inspections = rows.map(({ inspectionCode, batchId, sequenceNumber, ...inspection }) => ({
    ...inspection,
    eggId: formatEggId(inspectionCode, batchId, sequenceNumber),
    inspectionCode,
  }))

  return { inspections, dataSource: 'MariaDB' }
}
