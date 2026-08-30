import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Egg,
  RefreshCw,
  RotateCcw,
  Scale,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useEffect, useMemo, useState } from 'react'
import { reportingPeriod, sizeDistribution } from '../data/mockData'
import { ChartCard, PageHeader, StatCard } from '../components/Ui'
import { useAuth } from '../auth/AuthContext'
import { useDatabaseInspections } from '../hooks/useDatabaseInspections'

const sizes = ['All Sizes', 'Peewee', 'Small', 'Medium', 'Large', 'Extra Large', 'Jumbo']
const qualities = ['All Quality', 'good', 'defective']
const qualityLabel = (quality) =>
  ({ good: 'Good', defective: 'Defective', not_an_egg: 'Not an Egg' })[quality] || quality
const defaultFilters = {
  startDate: reportingPeriod.start,
  endDate: reportingPeriod.end,
  size: 'All Sizes',
  quality: 'All Quality',
}

const shiftIsoDate = (isoDate, days) => {
  const date = new Date(`${isoDate}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

const monthStart = (isoDate, monthsBefore = 0) => {
  const date = new Date(`${isoDate}T00:00:00Z`)
  date.setUTCMonth(date.getUTCMonth() - monthsBefore, 1)
  return date.toISOString().slice(0, 10)
}

const daysInRange = (startDate, endDate) =>
  Math.max(
    1,
    Math.round(
      (new Date(`${endDate}T00:00:00Z`) - new Date(`${startDate}T00:00:00Z`)) / 86_400_000
    ) + 1
  )
const recommendedAggregation = (startDate, endDate) => {
  const totalDays = daysInRange(startDate, endDate)
  return totalDays > 120 ? 'monthly' : totalDays > 45 ? 'weekly' : 'daily'
}
const shortDate = (isoDate) =>
  new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${isoDate}T00:00:00Z`)
  )
const shortMonth = (month) =>
  new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${month}-01T00:00:00Z`)
  )
const formatGeneratedAt = (value) =>
  new Intl.DateTimeFormat('en-PH', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Manila',
  }).format(new Date(value))

const weekStart = (isoDate) => {
  const date = new Date(`${isoDate}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7))
  return date.toISOString().slice(0, 10)
}

const hourFromTime = (time) => {
  const [clock, period] = time.split(' ')
  let hour = Number(clock.split(':')[0])
  if (period === 'PM' && hour !== 12) hour += 12
  if (period === 'AM' && hour === 12) hour = 0
  return hour
}

const filterScans = (scans, filters) =>
  scans.filter(
    (scan) =>
      scan.date >= filters.startDate &&
      scan.date <= filters.endDate &&
      (filters.size === 'All Sizes' || scan.size === filters.size) &&
      (filters.quality === 'All Quality' || scan.quality === filters.quality)
  )

const timeGroup = (isoDate, aggregation) => {
  const key =
    aggregation === 'weekly'
      ? weekStart(isoDate)
      : aggregation === 'monthly'
        ? isoDate.slice(0, 7)
        : isoDate
  const label = aggregation === 'monthly' ? shortMonth(key) : shortDate(key)
  return { key, label }
}

const aggregateScans = (scans, aggregation) => {
  const groups = new Map()
  scans.forEach((scan) => {
    const { key, label } = timeGroup(scan.date, aggregation)
    groups.set(key, { key, label, count: (groups.get(key)?.count || 0) + 1 })
  })
  return [...groups.entries()]
    .sort(([first], [second]) => first.localeCompare(second))
    .map(([, value]) => value)
}

export default function AnalyticsPage() {
  const { authenticatedFetch } = useAuth()
  const { inspections, error: databaseError, refresh: refreshDatabase } = useDatabaseInspections()
  const [filters, setFilters] = useState(defaultFilters)
  const [aggregation, setAggregation] = useState('daily')
  const [preset, setPreset] = useState('last-7')
  const [aiState, setAiState] = useState({ status: 'idle', data: null, error: '' })

  useEffect(() => {
    if (!inspections.length) return
    const dates = inspections.map((scan) => scan.date).sort()
    const firstDate = dates[0]
    const lastDate = dates[dates.length - 1]
    setFilters((current) => ({ ...current, startDate: firstDate, endDate: lastDate }))
    setAggregation(recommendedAggregation(firstDate, lastDate))
    setPreset('custom')
  }, [inspections])

  const updateFilter = (name, value) => {
    setFilters((current) => ({ ...current, [name]: value }))
    setPreset('custom')
  }
  const setDatePreset = (nextPreset) => {
    const endDate = inspections[0]?.date || reportingPeriod.end
    const startDate =
      nextPreset === 'today'
        ? endDate
        : nextPreset === 'last-7'
          ? shiftIsoDate(endDate, -6)
          : nextPreset === 'this-month'
            ? monthStart(endDate)
            : nextPreset === 'last-3-months'
              ? monthStart(endDate, 2)
              : nextPreset === 'this-year'
                ? `${endDate.slice(0, 4)}-01-01`
                : filters.startDate
    setFilters((current) => ({ ...current, startDate, endDate }))
    setAggregation(
      nextPreset === 'last-3-months' || nextPreset === 'this-year' ? 'monthly' : 'daily'
    )
    setPreset(nextPreset)
  }
  const resetFilters = () => {
    const dates = inspections.map((scan) => scan.date).sort()
    setFilters({
      ...defaultFilters,
      startDate: dates[0] || defaultFilters.startDate,
      endDate: dates.at(-1) || defaultFilters.endDate,
    })
    setAggregation(
      recommendedAggregation(
        dates[0] || defaultFilters.startDate,
        dates[dates.length - 1] || defaultFilters.endDate
      )
    )
    setPreset('custom')
  }

  const selectedScans = useMemo(() => filterScans(inspections, filters), [filters, inspections])
  const periodDays = daysInRange(filters.startDate, filters.endDate)
  const previousFilters = useMemo(
    () => ({
      ...filters,
      startDate: shiftIsoDate(filters.startDate, -periodDays),
      endDate: shiftIsoDate(filters.startDate, -1),
    }),
    [filters, periodDays]
  )
  const previousScans = useMemo(
    () => filterScans(inspections, previousFilters),
    [previousFilters, inspections]
  )
  const volumeData = useMemo(
    () => aggregateScans(selectedScans, aggregation),
    [selectedScans, aggregation]
  )
  const defectData = useMemo(() => {
    const groups = new Map()
    selectedScans.forEach((scan) => {
      const { key, label } = timeGroup(scan.date, aggregation)
      const current = groups.get(key) || { key, label, eggs: 0, defective: 0 }
      if (scan.quality !== 'not_an_egg') {
        current.eggs += 1
        if (scan.quality === 'defective') current.defective += 1
      }
      groups.set(key, current)
    })
    return [...groups.entries()]
      .sort(([first], [second]) => first.localeCompare(second))
      .map(([, group]) => ({
        ...group,
        rate: group.eggs ? Number(((group.defective / group.eggs) * 100).toFixed(1)) : 0,
      }))
  }, [selectedScans, aggregation])
  const sizeData = useMemo(
    () =>
      sizeDistribution.map((size) => ({
        ...size,
        value: selectedScans.filter((scan) => scan.size === size.name).length,
      })),
    [selectedScans]
  )
  const weightData = useMemo(() => {
    const bands = [
      { label: 'Under 40g', minimum: 0, maximum: 39.99 },
      { label: '40-49g', minimum: 40, maximum: 49.99 },
      { label: '50-59g', minimum: 50, maximum: 59.99 },
      { label: '60-69g', minimum: 60, maximum: 69.99 },
      { label: '70g and above', minimum: 70, maximum: Infinity },
    ]
    return bands.map((band) => ({
      name: band.label,
      count: selectedScans.filter(
        (scan) =>
          Number.isFinite(Number(scan.weight)) &&
          Number(scan.weight) >= band.minimum &&
          Number(scan.weight) <= band.maximum
      ).length,
    }))
  }, [selectedScans])
  const qualityBySize = useMemo(
    () =>
      sizeDistribution.map((size) => ({
        name: size.name,
        Good: selectedScans.filter((scan) => scan.size === size.name && scan.quality === 'good')
          .length,
        Defective: selectedScans.filter(
          (scan) => scan.size === size.name && scan.quality === 'defective'
        ).length,
      })),
    [selectedScans]
  )
  const hourData = useMemo(
    () =>
      Array.from({ length: 24 }, (_, hour) => ({
        hour,
        label: `${hour % 12 || 12} ${hour < 12 ? 'AM' : 'PM'}`,
        count: selectedScans.filter((scan) => hourFromTime(scan.time) === hour).length,
      })).filter((item) => item.count > 0),
    [selectedScans]
  )
  const metrics = useMemo(() => {
    const total = selectedScans.length
    const good = selectedScans.filter((scan) => scan.quality === 'good').length
    const defective = selectedScans.filter((scan) => scan.quality === 'defective').length
    const eggScans = selectedScans.filter((scan) => scan.quality !== 'not_an_egg')
    const notAnEgg = selectedScans.filter((scan) => scan.quality === 'not_an_egg').length
    const averageWeight = eggScans.length
      ? Number(
          (eggScans.reduce((sum, scan) => sum + Number(scan.weight), 0) / eggScans.length).toFixed(
            1
          )
        )
      : 0
    const mostCommon = sizeData.reduce(
      (largest, item) => (item.value > largest.value ? item : largest),
      { name: 'No data', value: 0 }
    )
    const previousTotal = previousScans.length
    const change = previousTotal
      ? Number((((total - previousTotal) / previousTotal) * 100).toFixed(1))
      : null
    return {
      total,
      good,
      defective,
      notAnEgg,
      averageWeight,
      defectRate: eggScans.length ? Number(((defective / eggScans.length) * 100).toFixed(1)) : 0,
      averagePerDay: Number((total / periodDays).toFixed(1)),
      mostCommon: mostCommon.name,
      previousTotal,
      change,
    }
  }, [selectedScans, sizeData, previousScans, periodDays])
  const analyticsSummary = useMemo(() => {
    const peakHour = hourData.reduce(
      (highest, item) => (item.count > highest.count ? item : highest),
      { label: 'No scans', count: 0 }
    )
    return {
      dateRange: {
        start: filters.startDate,
        end: filters.endDate,
        label: `${shortDate(filters.startDate)} - ${shortDate(filters.endDate)}`,
      },
      totalInspections: metrics.total,
      averageInspectionsPerDay: metrics.averagePerDay,
      defectRate: metrics.defectRate,
      averageWeight: metrics.averageWeight,
      mostCommonSize: metrics.mostCommon,
      classificationCounts: {
        good: metrics.good,
        defective: metrics.defective,
        not_an_egg: metrics.notAnEgg,
      },
      sizeCounts: sizeData.map(({ name, value }) => ({ name, count: value })),
      volumeSeries: volumeData,
      defectSeries: defectData.map(({ label, rate }) => ({ label, rate })),
      peakHour: { label: peakHour.label, count: peakHour.count },
      previousPeriod: { totalInspections: metrics.previousTotal, changePercent: metrics.change },
      dataSource: 'MariaDB',
    }
  }, [filters, metrics, sizeData, volumeData, defectData, hourData])

  useEffect(() => {
    setAiState({ status: 'idle', data: null, error: '' })
  }, [filters, aggregation])

  const generateInsights = async () => {
    if (!metrics.total) return
    setAiState({ status: 'loading', data: null, error: '' })
    try {
      const response = await authenticatedFetch('/api/analytics/insights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analytics: analyticsSummary }),
      })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.error || 'Unable to generate insights right now.')
      setAiState({ status: 'success', data: result, error: '' })
    } catch (error) {
      setAiState({
        status: 'error',
        data: null,
        error: error.message || 'Unable to generate insights right now.',
      })
    }
  }

  const presetClass = (name) =>
    name === 'last-30'
      ? 'hidden'
      : `min-h-11 rounded-full px-3 py-1.5 text-xs font-semibold ${preset === name ? 'bg-forest-800 text-white' : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`
  const insightTone = {
    positive: 'border-green-200 bg-green-50 text-green-800',
    warning: 'border-amber-200 bg-amber-50 text-amber-900',
    neutral: 'border-slate-200 bg-slate-50 text-slate-700',
  }

  return (
    <div>
      <PageHeader title="Analytics" />
      {databaseError && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {databaseError}
        </p>
      )}
      <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
        <div className="flex flex-wrap gap-2">
          <span className="mr-1 self-center text-xs font-semibold text-slate-500">Date range</span>
          <button onClick={() => setDatePreset('today')} className={presetClass('today')}>
            Today
          </button>
          <button onClick={() => setDatePreset('last-7')} className={presetClass('last-7')}>
            Last 7 Days
          </button>
          <button onClick={() => setDatePreset('last-30')} className={presetClass('last-30')}>
            Last 30 Days
          </button>
          <button onClick={() => setDatePreset('this-month')} className={presetClass('this-month')}>
            This Month
          </button>
          <button
            onClick={() => setDatePreset('last-3-months')}
            className={presetClass('last-3-months')}
          >
            Last 3 Months
          </button>
          <button onClick={() => setDatePreset('this-year')} className={presetClass('this-year')}>
            This Year
          </button>
          <button onClick={() => setPreset('custom')} className={presetClass('custom')}>
            Custom Range
          </button>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-500">Start date</span>
            <input
              type="date"
              value={filters.startDate}
              onChange={(event) => updateFilter('startDate', event.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-500">End date</span>
            <input
              type="date"
              value={filters.endDate}
              onChange={(event) => updateFilter('endDate', event.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-500">Aggregation</span>
            <select
              value={aggregation}
              onChange={(event) => setAggregation(event.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-500">Egg size</span>
            <select
              value={filters.size}
              onChange={(event) => updateFilter('size', event.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              {sizes.map((size) => (
                <option key={size}>{size}</option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-500">Quality</span>
            <select
              value={filters.quality}
              onChange={(event) => updateFilter('quality', event.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              {qualities.map((quality) => (
                <option key={quality}>
                  {quality === 'All Quality' ? 'All Quality Results' : qualityLabel(quality)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-500">Device</span>
            <select
              disabled
              className="w-full cursor-not-allowed rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-sm text-slate-400"
            >
              <option>Not Configured</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex justify-end border-t border-slate-100 pt-4">
          <div className="flex gap-2">
            <button
              onClick={refreshDatabase}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
            <button
              onClick={resetFilters}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <RotateCcw size={16} />
              Reset filters
            </button>
          </div>
        </div>
      </section>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Total inspections"
          value={metrics.total.toLocaleString()}
          detail={`${periodDays}-day period`}
          icon={Egg}
          tone="green"
        />
        <StatCard
          label="Average per day"
          value={metrics.averagePerDay}
          detail="Selected date range"
          icon={CalendarDays}
          tone="green"
        />
        <StatCard
          label="Defect rate"
          value={`${metrics.defectRate}%`}
          detail={`${metrics.defective} defective eggs`}
          icon={AlertTriangle}
          tone="red"
        />
        <StatCard
          label="Average weight"
          value={`${metrics.averageWeight}g`}
          detail="Filtered inspections"
          icon={Scale}
          tone="yellow"
        />
        <StatCard
          label="Most common size"
          value={metrics.mostCommon}
          detail="Highest inspection count"
          icon={BarChart3}
          tone="orange"
        />
        <StatCard
          label="Change vs previous"
          value={
            metrics.change !== null ? `${metrics.change > 0 ? '+' : ''}${metrics.change}%` : '—'
          }
          detail={
            metrics.change === null
              ? 'No previous sample data'
              : `${metrics.previousTotal} previous inspections`
          }
          icon={TrendingUp}
          tone="green"
        />
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <ChartCard
          title="Inspection Volume Over Time"
          action={
            <span className="rounded-md bg-green-50 px-2 py-1 text-xs font-semibold text-green-800">
              {aggregation}
            </span>
          }
          className="lg:col-span-2"
        >
          <ResponsiveContainer width="100%" height={310}>
            <AreaChart data={volumeData} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#227849" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#227849" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#227849"
                fill="url(#volumeFill)"
                strokeWidth={2.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="AI Insights">
          <div className="min-h-72 space-y-3">
            <p className="text-xs text-slate-500">
              Selected range: {analyticsSummary.dateRange.label} · Sample Data
            </p>
            {aiState.status === 'idle' && (
              <div className="grid min-h-52 place-items-center rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                <div>
                  <p className="font-semibold text-slate-700">Ready to analyze this selection</p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Gemini will receive only the summarized metrics and chart totals.
                  </p>
                  <button
                    onClick={generateInsights}
                    disabled={!metrics.total}
                    className="mt-4 inline-flex items-center gap-2 rounded-lg bg-forest-800 px-3 py-2 text-sm font-semibold text-white hover:bg-forest-900 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Sparkles size={16} />
                    Generate Insights
                  </button>
                </div>
              </div>
            )}
            {aiState.status === 'loading' && (
              <div className="grid min-h-52 place-items-center rounded-lg border border-dashed border-green-200 bg-green-50 p-6 text-center">
                <div>
                  <RefreshCw className="mx-auto animate-spin text-green-700" size={22} />
                  <p className="mt-3 font-semibold text-green-900">Generating AI insights…</p>
                  <p className="mt-1 text-sm text-green-800">
                    Analyzing the selected Sample Data summary.
                  </p>
                </div>
              </div>
            )}
            {aiState.status === 'error' && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                <p className="font-semibold text-red-800">Insights could not be generated</p>
                <p className="mt-1 text-sm leading-6 text-red-700">{aiState.error}</p>
                <button
                  onClick={generateInsights}
                  className="mt-3 inline-flex items-center gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
                >
                  <RefreshCw size={16} />
                  Try again
                </button>
              </div>
            )}
            {aiState.status === 'success' && (
              <div className="space-y-3">
                <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                  <p className="font-semibold text-green-900">{aiState.data.summary}</p>
                  <p className="mt-2 text-xs text-green-800">
                    Generated by {aiState.data.provider} on{' '}
                    {formatGeneratedAt(aiState.data.generatedAt)} from the selected Sample Data
                    summary.
                  </p>
                </div>
                {aiState.data.insights.slice(0, 4).map((insight, index) => (
                  <article
                    key={`${insight.title}-${index}`}
                    className={`rounded-lg border p-3 ${insightTone[insight.type] || insightTone.neutral}`}
                  >
                    <p className="font-semibold">{insight.title}</p>
                    <p className="mt-1 text-sm leading-5">{insight.message}</p>
                  </article>
                ))}
                {aiState.data.recommendations?.length > 0 && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                      Recommendations
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-600">
                      {aiState.data.recommendations.map((recommendation, index) => (
                        <li key={`${recommendation}-${index}`}>• {recommendation}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <button
                  onClick={generateInsights}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  <RefreshCw size={16} />
                  Regenerate Insights
                </button>
              </div>
            )}
          </div>
        </ChartCard>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <ChartCard title="Defect Rate Over Time">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={defectData} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis unit="%" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="rate"
                stroke="#ef5350"
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#ef5350' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Egg Size Distribution">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={sizeData}
              layout="vertical"
              margin={{ top: 4, right: 16, left: 22, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis
                type="category"
                dataKey="name"
                width={80}
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {sizeData.map((item) => (
                  <Cell key={item.name} fill={item.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <ChartCard title="Egg Weight Distribution">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={weightData} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#f7b73b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Quality Results by Egg Size" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={qualityBySize} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="Good" fill="#58ad5c" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Defective" fill="#ef5350" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="mt-4">
        <ChartCard title="Inspections by Hour of Day">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={hourData} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#9c78d3" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}
