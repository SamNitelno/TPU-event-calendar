import '@tanstack/react-start/server-only'
import { createHmac, timingSafeEqual } from 'node:crypto'
import { deleteCookie, getCookie, setCookie } from '@tanstack/react-start/server'

const COOKIE = '__Host-tpu-admin'
const TTL_SECONDS = 60 * 60 * 12

function secret() {
  return process.env.ADMIN_KEY || ''
}

function safeEqual(a: string, b: string) {
  const ab = Buffer.from(a)
  const bb = Buffer.from(b)
  return ab.length === bb.length && timingSafeEqual(ab, bb)
}

function sign(payload: string) {
  return createHmac('sha256', secret()).update(payload).digest('hex')
}

export function login(key: string) {
  const s = secret()
  if (!s) return { ok: false, error: 'Ключ администратора не настроен' }
  if (!safeEqual(key, s)) return { ok: false, error: 'Неверный ключ доступа' }
  const exp = String(Math.floor(Date.now() / 1000) + TTL_SECONDS)
  setCookie(COOKIE, `${exp}.${sign(exp)}`, {
    secure: true,
    httpOnly: true,
    path: '/',
    sameSite: 'lax',
    maxAge: TTL_SECONDS,
  })
  return { ok: true, error: '' }
}

export function isAuthed() {
  if (!secret()) return false
  const raw = getCookie(COOKIE)
  if (!raw) return false
  const [exp, sig] = raw.split('.')
  if (!exp || !sig || !safeEqual(sig, sign(exp))) return false
  return Number(exp) > Math.floor(Date.now() / 1000)
}

export function logout() {
  deleteCookie(COOKIE, { secure: true, httpOnly: true, path: '/', sameSite: 'lax' })
  return { ok: true }
}
