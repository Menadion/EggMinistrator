import { ChevronLeft, ChevronRight, Filter, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'
import { historyScans } from '../data/mockData'
import { DemoBadge, PageHeader, QualityBadge, SearchInput, SizeBadge } from '../components/Ui'

const PAGE_SIZE = 5

export default function HistoryPage() {
  const [search, setSearch] = useState('')
  const [size, setSize] = useState('All Sizes')
  const [quality, setQuality] = useState('All Quality')
  const [page, setPage] = useState(1)
  const filtered = useMemo(() => historyScans.filter((scan) => (size === 'All Sizes' || scan.size === size) && (quality === 'All Quality' || scan.quality === quality) && Object.values(scan).join(' ').toLowerCase().includes(search.toLowerCase())), [search, size, quality])
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const changeFilter = (setter) => (event) => { setter(event.target.value); setPage(1) }

  return (
    <div>
      <PageHeader title="History" description="Browse all egg inspection records" actions={<DemoBadge />} />
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 lg:grid-cols-[170px_1fr_150px_150px_auto]">
          <input type="date" defaultValue="2026-07-25" className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600" />
          <SearchInput value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search Egg ID or device" />
          <select value={size} onChange={changeFilter(setSize)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"><option>All Sizes</option>{['Peewee', 'Small', 'Medium', 'Large', 'Extra Large', 'Jumbo'].map((item) => <option key={item}>{item}</option>)}</select>
          <select value={quality} onChange={changeFilter(setQuality)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"><option>All Quality</option><option>Good</option><option>Spoiled</option></select>
          <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-forest-800 px-4 py-2 text-sm font-semibold text-white hover:bg-forest-900"><Filter size={16} />Filters</button>
        </div>
        <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="border-y border-slate-100 bg-slate-50 text-xs text-slate-500"><tr><th className="px-3 py-3 font-semibold">Date</th><th className="px-3 py-3 font-semibold">Time</th><th className="px-3 py-3 font-semibold">Egg ID</th><th className="px-3 py-3 font-semibold">Weight (g)</th><th className="px-3 py-3 font-semibold">Size</th><th className="px-3 py-3 font-semibold">Quality</th><th className="px-3 py-3 font-semibold">Device</th></tr></thead><tbody>{visible.map((scan) => <tr key={scan.eggId} className="border-b border-slate-100 text-slate-600"><td className="px-3 py-3">{scan.date}</td><td className="px-3 py-3">{scan.time}</td><td className="px-3 py-3 font-semibold text-slate-800">{scan.eggId}</td><td className="px-3 py-3">{scan.weight}</td><td className="px-3 py-3"><SizeBadge size={scan.size} /></td><td className="px-3 py-3"><QualityBadge quality={scan.quality} /></td><td className="px-3 py-3">{scan.device}</td></tr>)}{visible.length === 0 && <tr><td colSpan="7" className="px-3 py-10 text-center text-slate-500">No inspections match your filters.</td></tr>}</tbody></table></div>
        <div className="mt-4 flex flex-col gap-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between"><span>Showing {visible.length ? (page - 1) * PAGE_SIZE + 1 : 0}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} records</span><div className="flex items-center gap-1"><button disabled={page === 1} onClick={() => setPage(page - 1)} className="rounded-md border border-slate-200 p-1.5 disabled:opacity-40"><ChevronLeft size={16} /></button>{Array.from({ length: pageCount }, (_, index) => <button key={index} onClick={() => setPage(index + 1)} className={`h-8 w-8 rounded-md text-xs font-semibold ${page === index + 1 ? 'bg-forest-800 text-white' : 'hover:bg-slate-100'}`}>{index + 1}</button>)}<button disabled={page === pageCount} onClick={() => setPage(page + 1)} className="rounded-md border border-slate-200 p-1.5 disabled:opacity-40"><ChevronRight size={16} /></button></div></div>
      </section>
    </div>
  )
}
