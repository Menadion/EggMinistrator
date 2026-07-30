const CURRENT_DAILY_TOTALS = [132, 190, 142, 188, 159, 190, 247]
const PREVIOUS_DAILY_TOTALS = [140, 150, 145, 155, 160, 165, 177]
const CURRENT_TOTAL = CURRENT_DAILY_TOTALS.reduce((sum, count) => sum + count, 0)
const PREVIOUS_TOTAL = PREVIOUS_DAILY_TOTALS.reduce((sum, count) => sum + count, 0)
const CURRENT_SPOILED_TOTAL = 161
const PREVIOUS_SPOILED_TOTAL = 144

const sizeDefinitions = [
  { name: 'Pewee', count: 102, color: '#5cae5e', minimumWeight: 0, maximumWeight: 45 },
  { name: 'Small', count: 191, color: '#4da6df', minimumWeight: 45, maximumWeight: 55 },
  { name: 'Medium', count: 276, color: '#f7b73b', minimumWeight: 55, maximumWeight: 60 },
  { name: 'Large', count: 304, color: '#f07855', minimumWeight: 60, maximumWeight: 65 },
  { name: 'Extra Large', count: 233, color: '#9c78d3', minimumWeight: 65, maximumWeight: 70 },
  { name: 'Jumbo', count: 142, color: '#ef7f95', minimumWeight: 70, maximumWeight: null, sampleMaximumWeight: 80 },
]

const getManilaToday = () => {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Manila', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date())
  const value = Object.fromEntries(parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]))
  return `${value.year}-${value.month}-${value.day}`
}

const dateFromIso = (isoDate) => new Date(`${isoDate}T00:00:00Z`)
const formatDate = (isoDate, options) => new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', ...options }).format(dateFromIso(isoDate))
const getDayDetails = (date, count) => {
  const isoDate = date.toISOString().slice(0, 10)
  return { isoDate, count, label: formatDate(isoDate, { month: 'short', day: 'numeric' }), displayDate: formatDate(isoDate, { month: '2-digit', day: '2-digit', year: 'numeric' }) }
}

const today = dateFromIso(getManilaToday())
const reportingDays = CURRENT_DAILY_TOTALS.map((count, index) => {
  const date = new Date(today)
  date.setUTCDate(today.getUTCDate() - (CURRENT_DAILY_TOTALS.length - 1 - index))
  return getDayDetails(date, count)
})
const previousDays = PREVIOUS_DAILY_TOTALS.map((count, index) => {
  const date = new Date(today)
  date.setUTCDate(today.getUTCDate() - (CURRENT_DAILY_TOTALS.length + PREVIOUS_DAILY_TOTALS.length - 1 - index))
  return getDayDetails(date, count)
})

const sizePool = sizeDefinitions.flatMap(({ name, count }) => Array.from({ length: count }, () => name))
const sizeByName = Object.fromEntries(sizeDefinitions.map((size) => [size.name, size]))

const createTime = (index) => {
  const totalSeconds = (8 * 60 * 60) + ((index * 47) % (4 * 60 * 60))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const suffix = hours >= 12 ? 'PM' : 'AM'
  return `${hours % 12 || 12}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')} ${suffix}`
}

const createInspections = (days, startingIndex, spoiledTarget, sizeOffset) => {
  const total = days.reduce((sum, day) => sum + day.count, 0)
  let inspectionIndex = startingIndex
  return days.flatMap((day) => Array.from({ length: day.count }, (_, dayIndex) => {
    const localIndex = inspectionIndex - startingIndex
    const size = sizePool[((localIndex * 317) + sizeOffset) % CURRENT_TOTAL]
    const sizeDefinition = sizeByName[size]
    const weightRatio = ((inspectionIndex * 17) % 100) / 100
    const sampleMaximumWeight = sizeDefinition.maximumWeight ?? sizeDefinition.sampleMaximumWeight
    const isSpoiled = Math.floor(((localIndex + 1) * spoiledTarget) / total) > Math.floor((localIndex * spoiledTarget) / total)
    const inspection = { date: day.isoDate, displayDate: day.displayDate, time: createTime(dayIndex), eggId: `EGG-${String(inspectionIndex + 1).padStart(6, '0')}`, weight: Number((sizeDefinition.minimumWeight + ((sampleMaximumWeight - sizeDefinition.minimumWeight) * weightRatio)).toFixed(1)), size, quality: isSpoiled ? 'Spoiled' : 'Good', device: 'Egg Scanner 01' }
    inspectionIndex += 1
    return inspection
  }))
}

const previousInspections = createInspections(previousDays, 0, PREVIOUS_SPOILED_TOTAL, 53)
const currentInspections = createInspections(reportingDays, PREVIOUS_TOTAL, CURRENT_SPOILED_TOTAL, 0)
export const mockInspections = [...previousInspections, ...currentInspections]
export const historyScans = [...mockInspections].reverse()
export const recentScans = historyScans.slice(0, 6)

const calculateStats = (inspections) => {
  const good = inspections.filter((inspection) => inspection.quality === 'Good').length
  const spoiled = inspections.length - good
  const totalWeight = inspections.reduce((sum, inspection) => sum + inspection.weight, 0)
  return { total: inspections.length, good, spoiled, averageWeight: inspections.length ? Number((totalWeight / inspections.length).toFixed(1)) : 0, goodPercentage: inspections.length ? Number(((good / inspections.length) * 100).toFixed(1)) : 0, spoilagePercentage: inspections.length ? Number(((spoiled / inspections.length) * 100).toFixed(1)) : 0 }
}

export const dashboardStats = calculateStats(currentInspections)
export const sizeDistribution = sizeDefinitions.map((size) => ({ name: size.name, value: currentInspections.filter((inspection) => inspection.size === size.name).length, color: size.color }))
export const qualityDistribution = [{ name: 'Good', value: dashboardStats.good, color: '#58ad5c' }, { name: 'Spoiled', value: dashboardStats.spoiled, color: '#ef5350' }]
export const dailyInspections = reportingDays.map((day) => ({ day: day.label, count: currentInspections.filter((inspection) => inspection.date === day.isoDate).length }))
export const spoilageTrend = reportingDays.map((day) => {
  const inspections = currentInspections.filter((inspection) => inspection.date === day.isoDate)
  const spoiled = inspections.filter((inspection) => inspection.quality === 'Spoiled').length
  return { day: day.label, rate: Number(((spoiled / inspections.length) * 100).toFixed(1)) }
})
export const weeklyTrend = [{ name: `${reportingDays[0].label}–${reportingDays.at(-1).label}`, count: dashboardStats.total }]
export const monthlyTrend = [{ name: formatDate(reportingDays.at(-1).isoDate, { month: 'short' }), count: dashboardStats.total }]
export const reportingPeriod = { start: reportingDays[0].isoDate, end: reportingDays.at(-1).isoDate, label: `${formatDate(reportingDays[0].isoDate, { month: 'short', day: 'numeric', year: 'numeric' })} – ${formatDate(reportingDays.at(-1).isoDate, { month: 'short', day: 'numeric', year: 'numeric' })}` }
