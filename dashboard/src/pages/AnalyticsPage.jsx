import { AlertTriangle, BarChart3, CalendarDays, Egg, RefreshCw, RotateCcw, Scale, TrendingUp } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useMemo, useState } from 'react'
import { historyScans, reportingPeriod, sizeDistribution } from '../data/mockData'
import { ChartCard, PageHeader, StatCard } from '../components/Ui'

const sizes = ['All Sizes', 'Peewee', 'Small', 'Medium', 'Large', 'Extra Large', 'Jumbo']
const qualities = ['All Quality', 'Good', 'Spoiled']
const defaultFilters = { startDate: reportingPeriod.start, endDate: reportingPeriod.end, size: 'All Sizes', quality: 'All Quality' }

const shiftIsoDate = (isoDate, days) => {
  const date = new Date(`${isoDate}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

const daysInRange = (startDate, endDate) => Math.max(1, Math.round((new Date(`${endDate}T00:00:00Z`) - new Date(`${startDate}T00:00:00Z`)) / 86_400_000) + 1)
const shortDate = (isoDate) => new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(`${isoDate}T00:00:00Z`))
const shortMonth = (month) => new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${month}-01T00:00:00Z`))

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

const filterScans = (scans, filters) => scans.filter((scan) => scan.date >= filters.startDate && scan.date <= filters.endDate && (filters.size === 'All Sizes' || scan.size === filters.size) && (filters.quality === 'All Quality' || scan.quality === filters.quality))

const aggregateScans = (scans, aggregation) => {
  const groups = new Map()
  scans.forEach((scan) => {
    const key = aggregation === 'weekly' ? weekStart(scan.date) : aggregation === 'monthly' ? scan.date.slice(0, 7) : scan.date
    const label = aggregation === 'weekly' ? `Week of ${shortDate(key)}` : aggregation === 'monthly' ? shortMonth(key) : shortDate(key)
    groups.set(key, { label, count: (groups.get(key)?.count || 0) + 1 })
  })
  return [...groups.entries()].sort(([first], [second]) => first.localeCompare(second)).map(([, value]) => value)
}

export default function AnalyticsPage() {
  const [filters, setFilters] = useState(defaultFilters)
  const [aggregation, setAggregation] = useState('daily')
  const [preset, setPreset] = useState('last-7')
  const [lastRefreshed, setLastRefreshed] = useState(new Date())
  const updateFilter = (name, value) => { setFilters((current) => ({ ...current, [name]: value })); setPreset('custom') }
  const setDatePreset = (nextPreset) => {
    const endDate = reportingPeriod.end
    const startDate = nextPreset === 'today' ? endDate
      : nextPreset === 'last-7' ? shiftIsoDate(endDate, -6)
        : nextPreset === 'last-30' ? shiftIsoDate(endDate, -29)
          : nextPreset === 'this-month' ? `${endDate.slice(0, 7)}-01`
            : nextPreset === 'last-3-months' ? `${shiftIsoDate(`${endDate.slice(0, 7)}-01`, -62).slice(0, 7)}-01`
              : nextPreset === 'this-year' ? `${endDate.slice(0, 4)}-01-01`
                : filters.startDate
    setFilters((current) => ({ ...current, startDate, endDate }))
    setPreset(nextPreset)
  }
  const resetFilters = () => { setFilters(defaultFilters); setAggregation('daily'); setPreset('last-7') }
  const selectedScans = useMemo(() => filterScans(historyScans, filters), [filters])
  const periodDays = daysInRange(filters.startDate, filters.endDate)
  const previousFilters = useMemo(() => ({ ...filters, startDate: shiftIsoDate(filters.startDate, -periodDays), endDate: shiftIsoDate(filters.startDate, -1) }), [filters, periodDays])
  const previousScans = useMemo(() => filterScans(historyScans, previousFilters), [previousFilters])
  const volumeData = useMemo(() => aggregateScans(selectedScans, aggregation), [selectedScans, aggregation])
  const spoilageData = useMemo(() => aggregateScans(selectedScans, 'daily').map((point) => {
    const date = [...new Set(selectedScans.map((scan) => scan.date))].find((item) => shortDate(item) === point.label)
    const scans = selectedScans.filter((scan) => scan.date === date)
    const spoiled = scans.filter((scan) => scan.quality === 'Spoiled').length
    return { ...point, rate: scans.length ? Number(((spoiled / scans.length) * 100).toFixed(1)) : 0 }
  }), [selectedScans])
  const sizeData = useMemo(() => sizeDistribution.map((size) => ({ ...size, value: selectedScans.filter((scan) => scan.size === size.name).length })), [selectedScans])
  const weightData = useMemo(() => {
    const bands = [{ label: 'Under 40g', minimum: 0, maximum: 39.99 }, { label: '40–49g', minimum: 40, maximum: 49.99 }, { label: '50–59g', minimum: 50, maximum: 59.99 }, { label: '60–69g', minimum: 60, maximum: 69.99 }, { label: '70g and above', minimum: 70, maximum: Infinity }]
    return bands.map((band) => ({ name: band.label, count: selectedScans.filter((scan) => scan.weight >= band.minimum && scan.weight <= band.maximum).length }))
  }, [selectedScans])
  const qualityBySize = useMemo(() => sizeDistribution.map((size) => ({ name: size.name, Good: selectedScans.filter((scan) => scan.size === size.name && scan.quality === 'Good').length, Spoiled: selectedScans.filter((scan) => scan.size === size.name && scan.quality === 'Spoiled').length })), [selectedScans])
  const hourData = useMemo(() => Array.from({ length: 24 }, (_, hour) => ({ hour, label: `${hour % 12 || 12} ${hour < 12 ? 'AM' : 'PM'}`, count: selectedScans.filter((scan) => hourFromTime(scan.time) === hour).length })).filter((item) => item.count > 0), [selectedScans])
  const metrics = useMemo(() => {
    const total = selectedScans.length
    const good = selectedScans.filter((scan) => scan.quality === 'Good').length
    const spoiled = total - good
    const averageWeight = total ? Number((selectedScans.reduce((sum, scan) => sum + scan.weight, 0) / total).toFixed(1)) : 0
    const mostCommon = sizeData.reduce((largest, item) => item.value > largest.value ? item : largest, { name: 'No data', value: 0 })
    const previousTotal = previousScans.length
    const change = previousTotal ? Number((((total - previousTotal) / previousTotal) * 100).toFixed(1)) : null
    return { total, good, spoiled, averageWeight, spoilageRate: total ? Number(((spoiled / total) * 100).toFixed(1)) : 0, averagePerDay: Number((total / periodDays).toFixed(1)), mostCommon: mostCommon.name, previousTotal, change }
  }, [selectedScans, sizeData, previousScans, periodDays])
  const refreshedLabel = lastRefreshed.toLocaleTimeString('en-PH', { timeZone: 'Asia/Manila', hour: 'numeric', minute: '2-digit' })
  const presetClass = (name) => `rounded-full px-3 py-1.5 text-xs font-semibold ${preset === name ? 'bg-forest-800 text-white' : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`

  return (
    <div>
      <PageHeader title="Analytics" description={`${selectedScans.length.toLocaleString()} inspections selected • Refreshed ${refreshedLabel}`} />
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap gap-2"><span className="mr-1 self-center text-xs font-semibold text-slate-500">Date range</span><button onClick={() => setDatePreset('today')} className={presetClass('today')}>Today</button><button onClick={() => setDatePreset('last-7')} className={presetClass('last-7')}>Last 7 Days</button><button onClick={() => setDatePreset('last-30')} className={presetClass('last-30')}>Last 30 Days</button><button onClick={() => setDatePreset('this-month')} className={presetClass('this-month')}>This Month</button><button onClick={() => setDatePreset('last-3-months')} className={presetClass('last-3-months')}>Last 3 Months</button><button onClick={() => setDatePreset('this-year')} className={presetClass('this-year')}>This Year</button><button onClick={() => setPreset('custom')} className={presetClass('custom')}>Custom Range</button></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6"><label><span className="mb-1 block text-xs font-medium text-slate-500">Start date</span><input type="date" value={filters.startDate} onChange={(event) => updateFilter('startDate', event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" /></label><label><span className="mb-1 block text-xs font-medium text-slate-500">End date</span><input type="date" value={filters.endDate} onChange={(event) => updateFilter('endDate', event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" /></label><label><span className="mb-1 block text-xs font-medium text-slate-500">Aggregation</span><select value={aggregation} onChange={(event) => setAggregation(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label><label><span className="mb-1 block text-xs font-medium text-slate-500">Egg size</span><select value={filters.size} onChange={(event) => updateFilter('size', event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{sizes.map((size) => <option key={size}>{size}</option>)}</select></label><label><span className="mb-1 block text-xs font-medium text-slate-500">Quality</span><select value={filters.quality} onChange={(event) => updateFilter('quality', event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{qualities.map((quality) => <option key={quality}>{quality}</option>)}</select></label><label><span className="mb-1 block text-xs font-medium text-slate-500">Device</span><select disabled className="w-full cursor-not-allowed rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-sm text-slate-400"><option>Not Configured</option></select></label></div>
        <div className="mt-4 flex justify-end border-t border-slate-100 pt-4"><div className="flex gap-2"><button onClick={() => setLastRefreshed(new Date())} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><RefreshCw size={16} />Refresh</button><button onClick={resetFilters} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><RotateCcw size={16} />Reset filters</button></div></div>
      </section>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><StatCard label="Total inspections" value={metrics.total.toLocaleString()} detail={`${periodDays}-day period`} icon={Egg} tone="green" /><StatCard label="Average per day" value={metrics.averagePerDay} detail="Selected date range" icon={CalendarDays} tone="green" /><StatCard label="Spoilage rate" value={`${metrics.spoilageRate}%`} detail={`${metrics.spoiled} spoiled eggs`} icon={AlertTriangle} tone="red" /><StatCard label="Average weight" value={`${metrics.averageWeight}g`} detail="Filtered inspections" icon={Scale} tone="yellow" /><StatCard label="Most common size" value={metrics.mostCommon} detail="Highest inspection count" icon={BarChart3} tone="orange" /><StatCard label="Change vs previous" value={metrics.change !== null ? `${metrics.change > 0 ? '+' : ''}${metrics.change}%` : '—'} detail={metrics.change === null ? 'No previous sample data' : `${metrics.previousTotal} previous inspections`} icon={TrendingUp} tone="green" /></div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3"><ChartCard title="Inspection Volume Over Time" action={<span className="rounded-md bg-green-50 px-2 py-1 text-xs font-semibold text-green-800">{aggregation}</span>} className="lg:col-span-2"><ResponsiveContainer width="100%" height={310}><AreaChart data={volumeData} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}><defs><linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#227849" stopOpacity={0.3} /><stop offset="100%" stopColor="#227849" stopOpacity={0.02} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" /><XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip /><Area type="monotone" dataKey="count" stroke="#227849" fill="url(#volumeFill)" strokeWidth={2.5} /></AreaChart></ResponsiveContainer></ChartCard><ChartCard title="Analytics Insights"><div className="grid min-h-72 place-items-center rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6 text-center"><div><p className="font-semibold text-slate-700">No AI insights available</p><p className="mt-2 max-w-xs text-sm leading-6 text-slate-500">AI-generated observations will appear here after the analytics AI service is connected.</p></div></div></ChartCard></div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2"><ChartCard title="Spoilage Rate Over Time"><ResponsiveContainer width="100%" height={260}><LineChart data={spoilageData} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" /><XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis unit="%" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip /><Line type="monotone" dataKey="rate" stroke="#ef5350" strokeWidth={2.5} dot={{ r: 3, fill: '#ef5350' }} /></LineChart></ResponsiveContainer></ChartCard><ChartCard title="Egg Size Distribution"><ResponsiveContainer width="100%" height={260}><BarChart data={sizeData} layout="vertical" margin={{ top: 4, right: 16, left: 22, bottom: 0 }}><XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip /><Bar dataKey="value" radius={[0, 4, 4, 0]}>{sizeData.map((item) => <Cell key={item.name} fill={item.color} />)}</Bar></BarChart></ResponsiveContainer></ChartCard></div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3"><ChartCard title="Egg Weight Distribution"><ResponsiveContainer width="100%" height={250}><BarChart data={weightData} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}><XAxis dataKey="name" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip /><Bar dataKey="count" fill="#f7b73b" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></ChartCard><ChartCard title="Good vs Spoiled by Egg Size" className="lg:col-span-2"><ResponsiveContainer width="100%" height={250}><BarChart data={qualityBySize} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}><XAxis dataKey="name" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip /><Legend /><Bar dataKey="Good" fill="#58ad5c" radius={[4, 4, 0, 0]} /><Bar dataKey="Spoiled" fill="#ef5350" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></ChartCard></div>
      <div className="mt-4"><ChartCard title="Inspections by Hour of Day"><ResponsiveContainer width="100%" height={260}><BarChart data={hourData} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}><XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip /><Bar dataKey="count" fill="#9c78d3" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></ChartCard></div>
    </div>
  )
}
