import { describe, expect, it } from 'vitest'
import { addDays, dateRange, dayLabel, monthBounds, shiftMonth, todayInTomsk } from './dates'

describe('даты в Томске', () => {
  it('переключает день в 17:00 UTC, независимо от пояса компьютера', () => {
    expect(todayInTomsk(new Date('2026-11-16T16:59:59Z'))).toBe('2026-11-16')
    expect(todayInTomsk(new Date('2026-11-16T17:00:00Z'))).toBe('2026-11-17')
  })
  it('считает сегодня и завтра на границе года', () => {
    expect(dayLabel('2027-01-01', '2026-12-31')).toBe('Завтра')
    expect(dayLabel('2026-12-31', '2026-12-31')).toBe('Сегодня')
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
  })
  it('сохраняет оба месяца и года у диапазона', () => {
    const range = dateRange('2026-12-30', '2027-01-02')
    expect(range).toContain('декабря 2026')
    expect(range).toContain('января 2027')
  })
  it('рассчитывает високосный февраль и переход через декабрь', () => {
    expect(monthBounds('2028-02')).toEqual({ date_from: '2028-02-01', date_to: '2028-02-29' })
    expect(shiftMonth('2026-12', 1)).toBe('2027-01')
  })
})
