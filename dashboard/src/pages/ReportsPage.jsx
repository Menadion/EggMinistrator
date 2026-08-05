import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Database, Download, FileBarChart, FileText, Printer, RotateCcw, Save } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { reportingPeriod } from '../data/mockData'
import { PageHeader, downloadCsv } from '../components/Ui'
import { useDatabaseInspections } from '../hooks/useDatabaseInspections'

const sizes = ['All Sizes', 'Peewee', 'Small', 'Medium', 'Large', 'Extra Large', 'Jumbo']
const qualities = ['All Quality', 'good', 'defective']
const reportTypes = ['Inspection Summary', 'Detailed Records', 'AI Classification Report', 'Size Report']
const groupOptions = ['Day', 'Week', 'Month', 'Size', 'AI Result']
const defaultBuilder = { reportType: 'Inspection Summary', startDate: reportingPeriod.start, endDate: reportingPeriod.end, size: 'All Sizes', quality: 'All Quality', groupBy: 'Day', includeCharts: false, includeDetails: false }

const formatDate = (value) => new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
const formatMonth = (value) => new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}-01T00:00:00Z`))
const classificationLabel = (value) => ({ good: 'Good', defective: 'Defective' }[value] || value || '—')
const validWeight = (value) => typeof value !== 'boolean' && value !== null && value !== undefined && String(value).trim() !== '' && Number.isFinite(Number(value))
const weightLabel = (value) => validWeight(value) ? `${Number(value).toFixed(1)} g` : '—'
const rate = (part, total) => total ? Number(((part / total) * 100).toFixed(1)) : 0
const weekStart = (value) => { const date = new Date(`${value}T00:00:00Z`); date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7)); return date.toISOString().slice(0, 10) }
const filterScans = (scans, filters) => scans.filter((scan) => scan.date >= filters.startDate && scan.date <= filters.endDate && (filters.size === 'All Sizes' || scan.size === filters.size) && (filters.quality === 'All Quality' || scan.quality === filters.quality))

const groupDetails = (scan, groupBy) => {
  if (groupBy === 'Week') { const key = weekStart(scan.date); return { key, label: `Week of ${formatDate(key)}`, sort: key } }
  if (groupBy === 'Month') return { key: scan.date.slice(0, 7), label: formatMonth(scan.date.slice(0, 7)), sort: scan.date.slice(0, 7) }
  if (groupBy === 'Size') return { key: scan.size || 'Not graded', label: scan.size || 'Not graded', sort: sizes.indexOf(scan.size) }
  if (groupBy === 'AI Result') return { key: scan.quality, label: classificationLabel(scan.quality), sort: qualities.indexOf(scan.quality) }
  return { key: scan.date, label: scan.displayDate, sort: scan.date }
}

const buildGroups = (scans, groupBy) => {
  const groups = new Map()
  scans.forEach((scan) => {
    const group = groupDetails(scan, groupBy)
    const current = groups.get(group.key) || { ...group, inspections: 0, good: 0, defective: 0, weights: [] }
    current.inspections += 1
    current.good += scan.quality === 'good' ? 1 : 0
    current.defective += scan.quality === 'defective' ? 1 : 0
    if (validWeight(scan.weight)) current.weights.push(Number(scan.weight))
    groups.set(group.key, current)
  })
  return [...groups.values()].sort((first, second) => String(first.sort).localeCompare(String(second.sort), undefined, { numeric: true })).map((group) => ({ ...group, averageWeight: group.weights.length ? Number((group.weights.reduce((sum, value) => sum + value, 0) / group.weights.length).toFixed(1)) : null, defectRate: rate(group.defective, group.inspections) }))
}

export default function ReportsPage() {
  const { inspections, isLoading, error } = useDatabaseInspections()
  const [builder, setBuilder] = useState(defaultBuilder)
  const [report, setReport] = useState(null)
  useEffect(() => { if (inspections.length) { const dates = inspections.map((scan) => scan.date).sort(); setBuilder((current) => ({ ...current, startDate: dates[0], endDate: dates[dates.length - 1] })) } }, [inspections])
  const updateBuilder = (key, value) => setBuilder((current) => ({ ...current, [key]: value }))
  const resetBuilder = () => { setBuilder(defaultBuilder); setReport(null) }
  const reportScans = useMemo(() => report ? filterScans(inspections, report) : [], [report, inspections])
  const groups = useMemo(() => report ? buildGroups(reportScans, report.groupBy) : [], [report, reportScans])
  const summary = useMemo(() => {
    const good = reportScans.filter((scan) => scan.quality === 'good').length
    const defective = reportScans.filter((scan) => scan.quality === 'defective').length
    const weights = reportScans.filter((scan) => validWeight(scan.weight)).map((scan) => Number(scan.weight))
    const sizeCounts = new Map()
    reportScans.filter((scan) => scan.size).forEach((scan) => sizeCounts.set(scan.size, (sizeCounts.get(scan.size) || 0) + 1))
    const rankedSizes = [...sizeCounts.entries()].sort((first, second) => second[1] - first[1])
    const highestSizeCount = rankedSizes[0]?.[1]
    const mostCommonSize = highestSizeCount && rankedSizes.filter(([, count]) => count === highestSizeCount).length === 1 ? rankedSizes[0][0] : null
    return { total: reportScans.length, good, defective, averageWeight: weights.length ? Number((weights.reduce((sum, value) => sum + value, 0) / weights.length).toFixed(1)) : null, defectRate: rate(defective, reportScans.length), mostCommonSize, missingData: reportScans.some((scan) => !validWeight(scan.weight) || !scan.size) }
  }, [reportScans])
  const showGrouped = groups.length >= 2
  const showDetails = Boolean(report?.includeDetails) || groups.length <= 1
  const groupMetricLabel = ({ Day: 'Highest Inspection Day', Week: 'Highest Inspection Week', Month: 'Highest Inspection Month' }[report?.groupBy] || 'Highest Inspection Group')
  const highestGroup = showGrouped ? [...groups].sort((first, second) => second.inspections - first.inspections)[0] : null
  const dateCovered = !report ? '' : report.startDate === report.endDate ? formatDate(report.startDate) : `${formatDate(report.startDate)} – ${formatDate(report.endDate)}`
  const findings = report ? [`${summary.total} ${summary.total === 1 ? 'egg was' : 'eggs were'} inspected during the selected period.`, `${summary.good} ${summary.good === 1 ? 'egg was' : 'eggs were'} classified as good.`, `${summary.defective} ${summary.defective === 1 ? 'egg was' : 'eggs were'} classified as defective.`, `The defect rate was ${summary.defectRate.toFixed(1)}%.`, summary.averageWeight === null ? 'Average weight could not be calculated because valid weight data was unavailable.' : `Average weight was ${summary.averageWeight.toFixed(1)} g.`] : []
  const exportCsv = () => downloadCsv([['Date', 'Time', 'Egg ID', 'Weight (g)', 'Size', 'Result'], ...reportScans.map((scan) => [scan.displayDate, scan.time, scan.eggId, validWeight(scan.weight) ? Number(scan.weight).toFixed(1) : '—', scan.size || '—', classificationLabel(scan.quality)])], 'eggministrator-report.csv')

  return (
    <div className="reports-page">
      <PageHeader title="Reports" description={isLoading ? 'Loading MariaDB inspection records…' : 'Build a formal report from MariaDB inspection records.'} />
      {error && <p role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <section className="reports-builder rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
        <div className="mb-5 flex items-center gap-2"><FileText size={19} className="text-forest-800" /><h2 className="font-bold text-slate-900">Report Builder</h2></div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Report Type</span><select value={builder.reportType} onChange={(event) => updateBuilder('reportType', event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm">{reportTypes.map((type) => <option key={type}>{type}</option>)}</select></label>
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Start Date</span><input type="date" value={builder.startDate} onChange={(event) => updateBuilder('startDate', event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm" /></label>
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">End Date</span><input type="date" value={builder.endDate} onChange={(event) => updateBuilder('endDate', event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm" /></label>
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Group By</span><select value={builder.groupBy} onChange={(event) => updateBuilder('groupBy', event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm">{groupOptions.map((option) => <option key={option}>{option}</option>)}</select></label>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Egg Size</span><select value={builder.size} onChange={(event) => updateBuilder('size', event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm">{sizes.map((size) => <option key={size}>{size}</option>)}</select></label>
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">AI Result</span><select value={builder.quality} onChange={(event) => updateBuilder('quality', event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm">{qualities.map((quality) => <option key={quality}>{quality === 'All Quality' ? 'All AI Results' : classificationLabel(quality)}</option>)}</select></label>
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Device</span><select disabled className="w-full cursor-not-allowed rounded-lg border border-slate-200 bg-slate-100 px-3 py-2.5 text-sm text-slate-400"><option>Not Configured</option></select></label>
        </div>
        <div className="mt-5 flex flex-col gap-4 border-t border-slate-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-5">
            <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-700"><input type="checkbox" checked={builder.includeCharts} onChange={(event) => updateBuilder('includeCharts', event.target.checked)} />Include charts</label>
            <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-700"><input type="checkbox" checked={builder.includeDetails} onChange={(event) => updateBuilder('includeDetails', event.target.checked)} />Include detailed records</label>
          </div>
          <div className="flex gap-2"><button onClick={resetBuilder} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700"><RotateCcw size={16} />Reset</button><button onClick={() => setReport({ ...builder, generatedAt: new Date() })} className="inline-flex items-center gap-2 rounded-lg bg-forest-800 px-4 py-2.5 text-sm font-semibold text-white"><FileBarChart size={16} />Generate Report</button></div>
        </div>
      </section>

      {!report && <section className="mt-5 rounded-xl border border-dashed border-slate-300 bg-white/60 p-10 text-center"><FileText className="mx-auto text-slate-400" size={30} /><h2 className="mt-3 font-bold text-slate-700">Your report preview will appear here</h2></section>}

      {report && <section className="report-preview mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <div className="report-actions mb-6 flex flex-wrap gap-2 border-b border-slate-100 pb-5">
          <button onClick={exportCsv} className="inline-flex items-center gap-2 rounded-lg border border-green-700 px-3 py-2 text-sm font-semibold text-green-800"><Download size={16} />Export CSV</button>
          <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700"><FileText size={16} />Export PDF</button>
          <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700"><Printer size={16} />Print</button>
          <button disabled className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-400"><Save size={16} />Save Report</button>
        </div>
        <header className="border-b-2 border-forest-800 pb-5"><p className="text-sm font-bold uppercase tracking-[0.2em] text-forest-800">Eggministrator</p><h1 className="mt-1 text-2xl font-bold text-slate-900">{report.reportType}</h1><p className="mt-1 text-sm text-slate-500">Egg inspection monitoring and quality report</p></header>
        <section className="my-6 grid gap-4 border-b border-slate-100 pb-6 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><p className="text-slate-500">Date Covered</p><p className="mt-1 font-semibold">{dateCovered}</p></div>
          <div><p className="text-slate-500">Generated At</p><p className="mt-1 font-semibold">{report.generatedAt.toLocaleString('en-PH', { timeZone: 'Asia/Manila' })}</p></div>
          <div><p className="text-slate-500">Grouped By</p><p className="mt-1 font-semibold">{report.groupBy}</p></div>
          <div><p className="text-slate-500">Data Source</p><p className="mt-1 inline-flex items-center gap-1 font-semibold"><Database size={14} />MariaDB</p></div>
        </section>
        {summary.missingData && <p className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">Weight information is unavailable for some or all selected inspections. Average weight and weight-based analysis may be incomplete.</p>}
        <section><h2 className="mb-3 text-base font-bold">Executive Summary</h2><dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3"><div className="rounded-lg bg-slate-50 p-3"><dt>Total Inspections</dt><dd className="mt-1 text-lg font-bold">{summary.total}</dd></div><div className="rounded-lg bg-slate-50 p-3"><dt>Good Eggs</dt><dd className="mt-1 text-lg font-bold text-green-700">{summary.good}</dd></div><div className="rounded-lg bg-slate-50 p-3"><dt>Defective Eggs</dt><dd className="mt-1 text-lg font-bold text-red-600">{summary.defective}</dd></div><div className="rounded-lg bg-slate-50 p-3"><dt>Defect Rate</dt><dd className="mt-1 text-lg font-bold">{summary.defectRate.toFixed(1)}%</dd></div><div className="rounded-lg bg-slate-50 p-3"><dt>Average Weight</dt><dd className="mt-1 text-lg font-bold">{summary.averageWeight === null ? 'Not available' : `${summary.averageWeight.toFixed(1)} g`}</dd></div>{summary.mostCommonSize && <div className="rounded-lg bg-slate-50 p-3"><dt>Most Common Size</dt><dd className="mt-1 text-lg font-bold">{summary.mostCommonSize}</dd></div>}{highestGroup && <div className="rounded-lg bg-slate-50 p-3"><dt>{groupMetricLabel}</dt><dd className="mt-1 text-lg font-bold">{highestGroup.label}</dd></div>}</dl></section>
        {showGrouped && <section className="mt-7"><h2 className="mb-3 text-base font-bold">Grouped Report</h2><div className="overflow-x-auto"><table className="w-full min-w-[700px] text-sm"><thead className="border-y bg-slate-50 text-left text-xs text-slate-600"><tr><th className="px-3 py-2.5">{report.groupBy}</th><th className="px-3 py-2.5 text-right">Inspections</th><th className="px-3 py-2.5 text-right">Good Eggs</th><th className="px-3 py-2.5 text-right">Defective Eggs</th><th className="px-3 py-2.5 text-right">Average Weight</th><th className="px-3 py-2.5 text-right">Defect Rate</th></tr></thead><tbody>{groups.map((group) => <tr key={group.key} className="border-b"><td className="px-3 py-2.5 font-medium">{group.label}</td><td className="px-3 py-2.5 text-right">{group.inspections}</td><td className="px-3 py-2.5 text-right">{group.good}</td><td className="px-3 py-2.5 text-right">{group.defective}</td><td className="px-3 py-2.5 text-right">{group.averageWeight === null ? 'Not available' : `${group.averageWeight.toFixed(1)} g`}</td><td className="px-3 py-2.5 text-right">{group.defectRate.toFixed(1)}%</td></tr>)}</tbody></table></div></section>}
        {report.includeCharts && showGrouped && <section className="mt-7"><h2 className="mb-3 text-base font-bold">Charts</h2><ResponsiveContainer width="100%" height={260}><BarChart data={groups}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" /><YAxis /><Tooltip /><Bar dataKey="inspections" fill="#227849" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></section>}
        {showDetails && <section className="mt-7"><h2 className="mb-3 text-base font-bold">Detailed Inspection Records</h2><div className="overflow-x-auto"><table className="w-full min-w-[650px] text-sm"><thead className="border-y bg-slate-50 text-left text-xs text-slate-600"><tr><th className="px-3 py-2.5">Egg ID</th><th className="px-3 py-2.5">Date</th><th className="px-3 py-2.5">Time</th><th className="px-3 py-2.5">Weight</th><th className="px-3 py-2.5">Size</th><th className="px-3 py-2.5">Result</th></tr></thead><tbody>{reportScans.map((scan) => <tr key={scan.eggId} className="border-b"><td className="px-3 py-2.5 font-medium">{scan.eggId}</td><td className="px-3 py-2.5">{scan.displayDate || '—'}</td><td className="px-3 py-2.5">{scan.time || '—'}</td><td className="px-3 py-2.5">{weightLabel(scan.weight)}</td><td className="px-3 py-2.5">{scan.size || '—'}</td><td className="px-3 py-2.5">{classificationLabel(scan.quality)}</td></tr>)}{reportScans.length === 0 && <tr><td colSpan="6" className="px-3 py-8 text-center text-slate-500">No inspections match the selected criteria.</td></tr>}</tbody></table></div></section>}
        <section className="mt-7 border-t pt-6"><h2 className="mb-3 text-base font-bold">Key Findings</h2><ul className="space-y-2 text-sm text-slate-700">{findings.map((finding) => <li key={finding}>• {finding}</li>)}</ul></section>
      </section>}
    </div>
  )
}
