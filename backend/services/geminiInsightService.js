import { GoogleGenAI } from '@google/genai'

const insightTypes = new Set(['positive', 'warning', 'neutral'])

export class GeminiInsightError extends Error {
  constructor(message, statusCode = 502, code = 'GEMINI_REQUEST_FAILED') {
    super(message)
    this.statusCode = statusCode
    this.code = code
  }
}

const responseSchema = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    insights: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['positive', 'warning', 'neutral'] },
          title: { type: 'string' },
          message: { type: 'string' },
        },
        required: ['type', 'title', 'message'],
      },
    },
    recommendations: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'insights', 'recommendations'],
}

const removeCodeFence = (text) => text.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')

const parseResponse = (text) => {
  if (!text) throw new GeminiInsightError('Gemini returned an empty response.', 502, 'GEMINI_EMPTY_RESPONSE')

  let data
  try {
    data = JSON.parse(removeCodeFence(text))
  } catch (error) {
    throw new GeminiInsightError('Gemini returned malformed JSON.', 502, 'GEMINI_MALFORMED_RESPONSE')
  }

  if (!data || typeof data.summary !== 'string' || !Array.isArray(data.insights) || !Array.isArray(data.recommendations)) {
    throw new GeminiInsightError('Gemini returned an incomplete insight response.', 502, 'GEMINI_MALFORMED_RESPONSE')
  }

  const insights = data.insights
    .filter((insight) => insight && insightTypes.has(insight.type) && typeof insight.title === 'string' && typeof insight.message === 'string')
    .slice(0, 4)

  if (!insights.length) throw new GeminiInsightError('Gemini returned no usable insights.', 502, 'GEMINI_EMPTY_RESPONSE')

  return {
    summary: data.summary.trim(),
    insights,
    recommendations: data.recommendations.filter((item) => typeof item === 'string' && item.trim()).slice(0, 4),
    provider: 'Google Gemini',
    generatedAt: new Date().toISOString(),
  }
}

const buildPrompt = (analytics) => `You are an operations analyst for Eggministrator, an egg-inspection dashboard. Analyze only the aggregate sample-data summary below. Do not invent facts, do not mention raw records, and keep the language clear for a farm operator. Return 2 to 4 concise insights.

Analytics summary:\n${JSON.stringify(analytics)}

Return JSON only with this exact structure:
{
  "summary": "one concise overall summary",
  "insights": [
    { "type": "positive|warning|neutral", "title": "short title", "message": "one concise evidence-based observation" }
  ],
  "recommendations": ["up to four practical next steps"]
}`

export async function generateGeminiInsights(analytics) {
  const apiKey = process.env.GEMINI_API_KEY?.trim()
  const model = process.env.GEMINI_MODEL?.trim()

  if (!apiKey || !model) {
    throw new GeminiInsightError('Gemini is not configured. Add GEMINI_API_KEY and GEMINI_MODEL to backend/.env.', 503, 'GEMINI_CONFIG_MISSING')
  }

  const client = new GoogleGenAI({ apiKey })

  try {
    const response = await client.models.generateContent({
      model,
      contents: buildPrompt(analytics),
      config: {
        responseMimeType: 'application/json',
        responseSchema,
        temperature: 0.3,
      },
    })
    return parseResponse(response.text)
  } catch (error) {
    const statusCode = Number(error?.status || error?.statusCode || error?.response?.status)
    if (error instanceof GeminiInsightError) throw error
    if (statusCode === 429) throw new GeminiInsightError('Gemini rate limit reached. Please wait a moment and try again.', 429, 'GEMINI_RATE_LIMITED')
    if (statusCode === 401 || statusCode === 403) throw new GeminiInsightError('Gemini rejected the backend credentials. Check backend/.env.', 502, 'GEMINI_AUTH_ERROR')
    if (error?.cause?.code || error?.code === 'ENOTFOUND') throw new GeminiInsightError('Unable to reach Gemini. Check your internet connection and try again.', 503, 'GEMINI_NETWORK_ERROR')
    throw new GeminiInsightError('Gemini could not generate insights right now. Check the backend configuration and try again.', 502, 'GEMINI_UPSTREAM_ERROR')
  }
}
