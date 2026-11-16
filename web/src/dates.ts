export function todayInTomsk(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tomsk', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now)
  const part = (type: string) => parts.find(p => p.type === type)!.value
  return `${part('year')}-${part('month')}-${part('day')}`
}

// Даты API — календарные даты, не UTC-моменты.
export const dateValue = (day: string) => new Date(`${day}T12:00:00Z`)
export const dayKey = (date: Date) => date.toISOString().slice(0, 10)
export function isValidDay(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const date = dateValue(value)
  return !Number.isNaN(date.getTime()) && dayKey(date) === value
}
export function addDays(day: string, amount: number): string {
  const date = dateValue(day)
  date.setUTCDate(date.getUTCDate() + amount)
  return dayKey(date)
}
export function formatDate(day: string, options: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long' }): string {
  return new Intl.DateTimeFormat('ru-RU', { ...options, timeZone: 'UTC' }).format(dateValue(day))
}
export function dateRange(start: string, end: string | null) {
  const options: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long', year: 'numeric' }
  return !end || start === end ? formatDate(start, options) : `${formatDate(start, options)} — ${formatDate(end, options)}`
}
export function dayLabel(day: string, today = todayInTomsk()) {
  return day === today ? 'Сегодня' : day === addDays(today, 1) ? 'Завтра' : ''
}
export function monthBounds(month: string) {
  const first = `${month}-01`
  const last = dateValue(first)
  last.setUTCMonth(last.getUTCMonth() + 1, 0)
  return { date_from: first, date_to: dayKey(last) }
}
export function shiftMonth(month: string, amount: number) {
  const date = dateValue(`${month}-01`)
  date.setUTCMonth(date.getUTCMonth() + amount)
  return dayKey(date).slice(0, 7)
}
