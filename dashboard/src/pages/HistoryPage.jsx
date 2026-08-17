import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { PageHeader, QualityBadge, SearchInput, SizeBadge } from '../components/Ui'

const PAGE_SIZE = 10

function paginationItems(currentPage, pageCount) {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, index) => index + 1)

  const items = [1]
  const nearbyPages = [currentPage - 1, currentPage, currentPage + 1].filter((item) => item > 1 && item < pageCount)
  if (nearbyPages[0] > 2) items.push('start-ellipsis')
  items.push(...nearbyPages)
  if (nearbyPages.at(-1) < pageCount - 1) items.push('end-ellipsis')
  items.push(pageCount)
  return items
}

export default function HistoryPage() {
  const { authenticatedFetch } = useAuth()
  const [historyScans, setHistoryScans] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [search, setSearch] = useState('')
  const [size, setSize] = useState('All Sizes')
  const [quality, setQuality] = useState('All Quality')
  const [page, setPage] = useState(1)
  const [selectedDate, setSelectedDate] = useState('')
  useEffect(() => {
    const loadHistory = async () => {
      setIsLoading(true)
      setLoadError('')
      try {
        const response = await authenticatedFetch('/api/inspections')
        const result = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(result.error || 'Unable to load inspection records from MariaDB.')
        setHistoryScans(result.inspections || [])
      } catch (error) {
        setLoadError(error.message || 'Unable to load inspection records from MariaDB.')
      } finally {
        setIsLoading(false)
      }
    }

    loadHistory()
  }, [authenticatedFetch])
  const filtered = useMemo(() => historyScans.filter((scan) => (!selectedDate || scan.date === selectedDate) && (size === 'All Sizes' || scan.size === size) && (quality === 'All Quality' || scan.quality === quality) && Object.values(scan).join(' ').toLowerCase().includes(search.toLowerCase())), [historyScans, search, size, quality, selectedDate])
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const pages = paginationItems(page, pageCount)
  const changeFilter = (setter) => (event) => { setter(event.target.value); setPage(1) }

  return (
    <div>
      <PageHeader title="History" />
      <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
        {loadError && <p role="alert" className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{loadError}</p>}
        <div className="grid gap-3 lg:grid-cols-[170px_minmax(0,1fr)_150px_150px]">
          <input type="date" value={selectedDate} onChange={(event) => { setSelectedDate(event.target.value); setPage(1) }} className="min-h-11 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600" />
          <SearchInput value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search Egg ID or device" />
          <select value={size} onChange={changeFilter(setSize)} className="min-h-11 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"><option>All Sizes</option>{['Peewee', 'Small', 'Medium', 'Large', 'Extra Large', 'Jumbo'].map((item) => <option key={item}>{item}</option>)}</select>
          <select value={quality} onChange={changeFilter(setQuality)} className="min-h-11 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"><option value="All Quality">All Quality Results</option><option value="good">Good</option><option value="defective">Defective</option></select>
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="border-y border-slate-100 bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="px-3 py-3 font-semibold">Date</th>
                <th className="px-3 py-3 font-semibold">Time</th>
                <th className="px-3 py-3 font-semibold">Egg ID</th>
                <th className="px-3 py-3 font-semibold">Weight (g)</th>
                <th className="px-3 py-3 font-semibold">Size</th>
                <th className="px-3 py-3 font-semibold">Quality</th>
                <th className="px-3 py-3 font-semibold">Device</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && <tr><td colSpan="7" className="px-3 py-10 text-center text-slate-500">Loading MariaDB records...</td></tr>}
              {!isLoading && visible.map((scan) => (
                <tr key={scan.eggId} className="border-b border-slate-100 text-slate-600">
                  <td className="px-3 py-3">{scan.displayDate}</td>
                  <td className="px-3 py-3">{scan.time}</td>
                  <td className="px-3 py-3 font-semibold text-slate-800">{scan.eggId}</td>
                  <td className="px-3 py-3">{scan.weight ?? '—'}</td>
                  <td className="px-3 py-3"><SizeBadge size={scan.size} /></td>
                  <td className="px-3 py-3"><QualityBadge quality={scan.quality} /></td>
                  <td className="px-3 py-3">{scan.device}</td>
                </tr>
              ))}
              {!isLoading && visible.length === 0 && <tr><td colSpan="7" className="px-3 py-10 text-center text-slate-500">No inspections match your filters.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-col gap-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between"><span>Showing {visible.length ? (page - 1) * PAGE_SIZE + 1 : 0}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} records</span><div className="flex flex-wrap items-center gap-1"><button disabled={page === 1} onClick={() => setPage(page - 1)} aria-label="Previous page" className="rounded-md border border-slate-200 p-1.5 disabled:opacity-40"><ChevronLeft size={16} /></button>{pages.map((item) => typeof item === 'string' ? <span key={item} className="grid h-8 w-6 place-items-center text-slate-400">…</span> : <button key={item} onClick={() => setPage(item)} aria-label={`Page ${item}`} aria-current={page === item ? 'page' : undefined} className={`h-8 w-8 rounded-md text-xs font-semibold ${page === item ? 'bg-forest-800 text-white' : 'hover:bg-slate-100'}`}>{item}</button>)}<button disabled={page === pageCount} onClick={() => setPage(page + 1)} aria-label="Next page" className="rounded-md border border-slate-200 p-1.5 disabled:opacity-40"><ChevronRight size={16} /></button></div></div>
      </section>
    </div>
  )
}
