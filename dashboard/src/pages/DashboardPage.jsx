import { AlertTriangle, CalendarDays, CheckCircle2, ChevronRight, Egg, Scale, Settings2, TrendingUp } from 'lucide-react'
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useNavigate } from 'react-router-dom'
import { dailyInspections, qualityDistribution, scans, sizeDistribution } from '../data/mockData'
import { ChartCard, PageHeader, QualityBadge, SizeBadge, StatCard } from '../components/Ui'

function ScanTable({ rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[630px] text-left text-xs">
        <thead className="border-y border-slate-100 bg-slate-50 text-slate-500"><tr><th className="px-3 py-2.5 font-semibold">Time</th><th className="px-3 py-2.5 font-semibold">Egg ID</th><th className="px-3 py-2.5 font-semibold">Weight (g)</th><th className="px-3 py-2.5 font-semibold">Size</th><th className="px-3 py-2.5 font-semibold">Quality</th><th className="px-3 py-2.5 font-semibold">Device</th></tr></thead>
        <tbody>{rows.map((scan) => <tr key={scan[1]} className="border-b border-slate-100 text-slate-600"><td className="px-3 py-3">{scan[0]}</td><td className="px-3 py-3 font-semibold text-slate-800">{scan[1]}</td><td className="px-3 py-3">{scan[2]}</td><td className="px-3 py-3"><SizeBadge size={scan[3]} /></td><td className="px-3 py-3"><QualityBadge quality={scan[4]} /></td><td className="px-3 py-3">{scan[5]}</td></tr>)}</tbody>
      </table>
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  return (
    <div>
      <PageHeader title="Dashboard" description="Overview of egg inspections and system statistics" actions={<><button className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"><CalendarDays size={16} />July 25, 2026</button></>} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Eggs Inspected" value="1,248" detail={<span className="font-medium text-green-700">↑ 18.6%</span>} icon={Egg} tone="green" />
        <StatCard label="Good Eggs" value="1,087" detail="87.1% of total" icon={CheckCircle2} tone="green" />
        <StatCard label="Spoiled Eggs" value="161" detail="12.9% of total" icon={AlertTriangle} tone="red" />
        <StatCard label="Average Weight" value={<>56.4<span className="ml-1 text-base">g</span></>} detail={<span className="font-medium text-green-700">↑ 2.3%</span>} icon={Scale} tone="yellow" />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-12">
        <ChartCard title="Egg Size Distribution" className="xl:col-span-4">
          <div className="flex min-h-56 flex-col sm:flex-row sm:items-center"><ResponsiveContainer width="100%" height={190}><PieChart><Pie data={sizeDistribution} dataKey="value" nameKey="name" innerRadius={48} outerRadius={76} paddingAngle={2}>{sizeDistribution.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip formatter={(value) => [`${value} eggs`, 'Total']} /></PieChart></ResponsiveContainer><div className="grid shrink-0 grid-cols-2 gap-x-3 gap-y-1 text-[11px] sm:block">{sizeDistribution.map((item) => <div key={item.name} className="flex items-center gap-1.5 py-1 text-slate-600"><span className="h-2 w-2 rounded-full" style={{ background: item.color }} /><span>{item.name}</span><span className="ml-auto font-medium text-slate-800">{item.value}</span></div>)}</div></div>
        </ChartCard>
        <ChartCard title="Daily Egg Inspections" action={<select className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600"><option>Last 7 Days</option><option>Last 30 Days</option></select>} className="xl:col-span-4">
          <ResponsiveContainer width="100%" height={220}><BarChart data={dailyInspections} margin={{ top: 8, right: 0, left: -22, bottom: 0 }}><XAxis dataKey="day" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip cursor={{ fill: '#eff8f0' }} /><Bar dataKey="count" fill="#5bae60" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Quality Distribution" className="xl:col-span-4">
          <div className="relative flex min-h-56 items-center justify-center"><ResponsiveContainer width="100%" height={220}><PieChart><Pie data={qualityDistribution} dataKey="value" nameKey="name" innerRadius={62} outerRadius={88} paddingAngle={2}>{qualityDistribution.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer><div className="absolute text-center"><p className="text-xl font-bold text-slate-900">1,248</p><p className="text-[11px] text-slate-500">Total eggs</p></div><div className="absolute right-2 top-10 text-xs"><div className="mb-2 flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-green-500" />Good</div><div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-red-500" />Spoiled</div></div></div>
        </ChartCard>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-12">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm xl:col-span-8"><div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-bold text-slate-800">Recent Scans</h2><button onClick={() => navigate('/history')} className="inline-flex items-center gap-1 text-xs font-semibold text-forest-800 hover:underline">View all <ChevronRight size={15} /></button></div><ScanTable rows={scans.slice(0, 6)} /></section>
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm xl:col-span-4"><h2 className="text-sm font-bold text-slate-800">Device Status</h2><div className="mt-4 rounded-lg border border-amber-100 bg-amber-50 p-4"><div className="flex items-center gap-2 text-sm font-bold text-slate-800"><span className="h-2.5 w-2.5 rounded-full bg-amber-500" />Not Configured</div><p className="mt-2 text-xs leading-5 text-slate-600">The egg inspection device has not yet been configured.</p><p className="mt-3 text-xs text-slate-500">Data source: Sample data</p></div><dl className="mt-4 grid grid-cols-2 gap-y-2 text-xs"><dt className="text-slate-500">Device Name</dt><dd className="text-right font-medium">-</dd><dt className="text-slate-500">Connection</dt><dd className="text-right font-medium">-</dd><dt className="text-slate-500">Last Active</dt><dd className="text-right font-medium">-</dd><dt className="text-slate-500">Last Scan</dt><dd className="text-right font-medium">-</dd></dl><button className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-green-700 px-3 py-2 text-xs font-semibold text-forest-800 hover:bg-green-50"><Settings2 size={15} />Configure device</button></section>
      </div>
    </div>
  )
}
