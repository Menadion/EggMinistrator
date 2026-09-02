import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { connect } from 'node:net'

const envPath = resolve(fileURLToPath(new URL('..', import.meta.url)), '.env')
if (existsSync(envPath)) {
  readFileSync(envPath, 'utf8').split(/\r?\n/).forEach((line) => {
    const match = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/)
    if (match && !process.env[match[1]]) process.env[match[1]] = match[2].replace(/^['"]|['"]$/g, '')
  })
}

// True when something answers on the MySQL port. Integration tests skip, not
// fail, when XAMPP is down -- a red run must always mean a real defect.
export const databaseReachable = () => new Promise((done) => {
  const socket = connect({ host: process.env.DB_HOST || '127.0.0.1', port: Number(process.env.DB_PORT) || 3306 })
  socket.setTimeout(500)
  socket.once('connect', () => { socket.destroy(); done(true) })
  socket.once('error', () => done(false))
  socket.once('timeout', () => { socket.destroy(); done(false) })
})
