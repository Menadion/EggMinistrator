export const sizeDistribution = [
  { name: 'Peewee', value: 102, color: '#5cae5e' },
  { name: 'Small', value: 191, color: '#4da6df' },
  { name: 'Medium', value: 276, color: '#f7b73b' },
  { name: 'Large', value: 304, color: '#f07855' },
  { name: 'Extra Large', value: 233, color: '#9c78d3' },
  { name: 'Jumbo', value: 142, color: '#ef7f95' },
]

export const dailyInspections = [
  { day: 'Jul 19', count: 206 },
  { day: 'Jul 20', count: 300 },
  { day: 'Jul 21', count: 221 },
  { day: 'Jul 22', count: 298 },
  { day: 'Jul 23', count: 255 },
  { day: 'Jul 24', count: 302 },
  { day: 'Jul 25', count: 366 },
]

export const qualityDistribution = [
  { name: 'Good', value: 1087, color: '#58ad5c' },
  { name: 'Spoiled', value: 161, color: '#ef5350' },
]

export const scans = [
  ['10:35:21 AM', 'EGG-001248', 58.2, 'Large', 'Good', 'Egg Scanner 01'],
  ['10:32:10 AM', 'EGG-001247', 42.7, 'Small', 'Spoiled', 'Egg Scanner 01'],
  ['10:28:54 AM', 'EGG-001246', 61.3, 'Extra Large', 'Good', 'Egg Scanner 01'],
  ['10:25:33 AM', 'EGG-001245', 36.9, 'Peewee', 'Good', 'Egg Scanner 01'],
  ['10:22:18 AM', 'EGG-001244', 70.2, 'Jumbo', 'Good', 'Egg Scanner 01'],
  ['10:18:05 AM', 'EGG-001243', 55.3, 'Medium', 'Good', 'Egg Scanner 01'],
  ['10:15:42 AM', 'EGG-001242', 47.8, 'Small', 'Spoiled', 'Egg Scanner 01'],
  ['10:11:45 AM', 'EGG-001241', 60.4, 'Large', 'Good', 'Egg Scanner 01'],
  ['10:08:12 AM', 'EGG-001240', 63.1, 'Extra Large', 'Good', 'Egg Scanner 01'],
  ['10:03:46 AM', 'EGG-001239', 52.6, 'Medium', 'Good', 'Egg Scanner 01'],
  ['09:58:38 AM', 'EGG-001238', 43.9, 'Small', 'Spoiled', 'Egg Scanner 01'],
  ['09:54:01 AM', 'EGG-001237', 69.5, 'Jumbo', 'Good', 'Egg Scanner 01'],
]

export const historyScans = scans.map((scan, index) => ({
  date: index > 7 ? '07/24/2026' : '07/25/2026',
  time: scan[0],
  eggId: scan[1],
  weight: scan[2],
  size: scan[3],
  quality: scan[4],
  device: scan[5],
}))

export const weeklyTrend = [
  { name: 'Wk 1', count: 1320 },
  { name: 'Wk 2', count: 1700 },
  { name: 'Wk 3', count: 1510 },
  { name: 'Wk 4', count: 1810 },
]

export const monthlyTrend = [
  { name: 'Jan', count: 2800 },
  { name: 'Feb', count: 3900 },
  { name: 'Mar', count: 4700 },
  { name: 'Apr', count: 4100 },
  { name: 'May', count: 5800 },
  { name: 'Jun', count: 6200 },
  { name: 'Jul', count: 8400 },
]

export const spoilageTrend = [
  { day: 'Jun 26', rate: 11 },
  { day: 'Jul 1', rate: 8 },
  { day: 'Jul 5', rate: 13 },
  { day: 'Jul 10', rate: 12 },
  { day: 'Jul 15', rate: 15 },
  { day: 'Jul 20', rate: 11 },
  { day: 'Jul 25', rate: 15 },
]
