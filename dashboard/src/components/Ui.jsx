import { ArrowDownToLine, CheckCircle2, Download, FileText, Search, XCircle } from 'lucide-react'

const sizeStyles = {
  Peewee: 'bg-teal-100 text-teal-800',
  Small: 'bg-sky-100 text-sky-800',
  Medium: 'bg-amber-100 text-amber-800',
  Large: 'bg-orange-100 text-orange-800',
  'Extra Large': 'bg-violet-100 text-violet-800',
  Jumbo: 'bg-rose-100 text-rose-800',
}

export function SizeBadge({ size }) {
  if (!size)
    return (
      <span className="whitespace-nowrap rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
        Not graded
      </span>
    )
  return (
    <span
      className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ${sizeStyles[size]}`}
    >
      {size}
    </span>
  )
}

export function QualityBadge({ quality }) {
  const labels = { good: 'Good', defective: 'Defective', not_an_egg: 'Not an Egg' }
  const good = quality === 'good'
  const notAnEgg = quality === 'not_an_egg'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${good ? 'bg-green-100 text-green-800' : notAnEgg ? 'bg-slate-200 text-slate-700' : 'bg-red-100 text-red-700'}`}
    >
      {good ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
      {labels[quality] || quality}
    </span>
  )
}

export function PageHeader({ title, description, actions }) {
  return (
    <div className="mb-4 flex flex-col gap-4 sm:mb-6 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-[28px]">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2 [&>button]:min-h-11">{actions}</div>
      )}
    </div>
  )
}

export function ChartCard({ title, children, action, className = '' }) {
  return (
    <section
      className={`min-w-0 rounded-xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4 ${className}`}
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="min-w-0 text-sm font-bold text-slate-800">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

export function StatCard({ label, value, detail, icon: Icon, tone = 'green' }) {
  const tones = {
    green: 'bg-green-100 text-green-700',
    red: 'bg-red-100 text-red-600',
    yellow: 'bg-amber-100 text-amber-600',
    orange: 'bg-orange-100 text-orange-600',
  }
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
        </div>
        <div className={`grid h-11 w-11 place-items-center rounded-full ${tones[tone]}`}>
          <Icon size={22} strokeWidth={2.5} />
        </div>
      </div>
      <p className="mt-2 text-xs text-slate-500">{detail}</p>
    </section>
  )
}

export function SearchInput({ value, onChange, placeholder = 'Search' }) {
  return (
    <label className="flex min-h-11 min-w-0 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-400 focus-within:border-green-600 focus-within:ring-2 focus-within:ring-green-100">
      <Search size={16} />
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="min-w-0 w-full border-0 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
      />
    </label>
  )
}

export function ExportButtons({ onCsv, onPdf }) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={onCsv}
        className="inline-flex items-center gap-2 rounded-lg border border-green-700 bg-white px-3 py-2 text-sm font-semibold text-green-800 hover:bg-green-50"
      >
        <Download size={16} />
        Export CSV
      </button>
      <button
        onClick={onPdf}
        className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
      >
        <FileText size={16} />
        Export PDF
      </button>
    </div>
  )
}

export function downloadCsv(rows, fileName = 'egg-report.csv') {
  const csv = rows
    .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(','))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

export const reportRows = [['Egg ID', 'Weight (g)', 'Size', 'Quality', 'Device']]
