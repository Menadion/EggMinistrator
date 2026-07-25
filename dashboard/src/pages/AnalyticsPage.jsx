import { RefreshCw } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { dailyInspections, monthlyTrend, qualityDistribution, sizeDistribution, spoilageTrend, weeklyTrend } from '../data/mockData'
import { ChartCard, DemoBadge, PageHeader } from '../components/Ui'

function TrendChart({ data, type = 'line', color = '#227849' }) {
  const Chart = type === 'bar' ? BarChart : type === 'area' ? AreaChart : LineChart
  return <ResponsiveContainer width="100%" height={240}><Chart data={data} margin={{ top: 12, left: -22, right: 4 }}><XAxis dataKey={data[0].day ? 'day' : 'name'} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip />{type === 'bar' ? <Bar dataKey={data[0].rate === undefined ? 'count' : 'rate'} fill={color} radius={[4, 4, 0, 0]} /> : type === 'area' ? <Area dataKey="rate" type="monotone" stroke={color} fill={color} fillOpacity={0.13} strokeWidth={2} /> : <Line dataKey="count" type="monotone" stroke={color} strokeWidth={2.5} dot={{ r: 3, fill: color }} />}</Chart></ResponsiveContainer>
}

export default function AnalyticsPage() {
  return (
    <div>
      <PageHeader title="Analytics" description="Detailed inspection insights and trends" actions={<><select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"><option>Last 30 Days</option><option>Last 7 Days</option><option>Last 12 Months</option></select><button className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><RefreshCw size={16} />Refresh</button><DemoBadge /></>} />
      <div className="grid gap-4 xl:grid-cols-3"><ChartCard title="Daily Inspections Trend"><TrendChart data={dailyInspections} /></ChartCard><ChartCard title="Weekly Inspections Trend"><TrendChart data={weeklyTrend} type="bar" color="#5cae5e" /></ChartCard><ChartCard title="Monthly Inspections Trend"><TrendChart data={monthlyTrend} color="#176f3c" /></ChartCard></div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3"><ChartCard title="Spoilage Percentage Over Time"><TrendChart data={spoilageTrend} type="area" color="#ef5350" /></ChartCard><ChartCard title="Size Distribution"><ResponsiveContainer width="100%" height={240}><PieChart><Pie data={sizeDistribution} dataKey="value" nameKey="name" outerRadius={90} innerRadius={45}>{sizeDistribution.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></ChartCard><ChartCard title="Good vs Spoiled"><div className="relative"><ResponsiveContainer width="100%" height={240}><PieChart><Pie data={qualityDistribution} dataKey="value" nameKey="name" outerRadius={90} innerRadius={58}>{qualityDistribution.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer><div className="absolute inset-0 grid place-items-center text-center"><div><p className="text-xl font-bold">87.1%</p><p className="text-xs text-slate-500">Good eggs</p></div></div></div></ChartCard></div>
      <section className="mt-4 rounded-xl border border-green-100 bg-green-50 p-4 text-sm text-green-800"><p className="font-semibold">Demo analytics</p><p className="mt-1 text-green-700">Charts are currently calculated from sample data. They will update automatically after the ESP32-S3 and MariaDB integrations are connected.</p></section>
    </div>
  )
}
