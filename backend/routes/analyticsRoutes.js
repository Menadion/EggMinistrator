import { GeminiInsightError, generateGeminiInsights } from '../services/geminiInsightService.js'

const isNumber = (value) => typeof value === 'number' && Number.isFinite(value)
const isString = (value) => typeof value === 'string' && value.trim().length > 0

const validateAnalyticsSummary = (analytics) => {
  if (!analytics || typeof analytics !== 'object' || Array.isArray(analytics)) return 'A prepared analytics summary is required.'

  const { dateRange, totalInspections, averageInspectionsPerDay, defectRate, averageWeight, mostCommonSize, classificationCounts, sizeCounts, volumeSeries, defectSeries, peakHour, dataSource } = analytics
  if (!dateRange || !isString(dateRange.start) || !isString(dateRange.end) || !isString(dateRange.label)) return 'The selected date range is invalid.'
  if (![totalInspections, averageInspectionsPerDay, defectRate, averageWeight].every(isNumber) || !isString(mostCommonSize)) return 'The summary metrics are invalid.'
  if (!classificationCounts || !isNumber(classificationCounts.good) || !isNumber(classificationCounts.defective) || !isNumber(classificationCounts.not_an_egg)) return 'The classification totals are invalid.'
  if (!Array.isArray(sizeCounts) || !Array.isArray(volumeSeries) || !Array.isArray(defectSeries)) return 'The chart summaries are invalid.'
  if (!peakHour || !isString(peakHour.label) || !isNumber(peakHour.count) || !isString(dataSource)) return 'The analytics summary is incomplete.'
  return null
}

export async function createAnalyticsInsights(requestBody) {
  const analytics = requestBody?.analytics
  const validationError = validateAnalyticsSummary(analytics)
  if (validationError) {
    return { statusCode: 400, body: { error: validationError, code: 'INVALID_ANALYTICS_SUMMARY' } }
  }

  try {
    return { statusCode: 200, body: await generateGeminiInsights(analytics) }
  } catch (error) {
    if (error instanceof GeminiInsightError) {
      return { statusCode: error.statusCode, body: { error: error.message, code: error.code } }
    }
    return { statusCode: 500, body: { error: 'Unable to generate insights right now.', code: 'INTERNAL_ERROR' } }
  }
}
