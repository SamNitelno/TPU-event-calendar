import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fetchCategories, fetchEvent, fetchEvents, fetchMonthEvents, submitEvent, type Submission } from './api'

afterEach(() => vi.unstubAllGlobals())
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })

describe('контракт FastAPI', () => {
  it('сохраняет пагинацию и кодирует параметры поиска', async () => {
    const fetch = vi.fn().mockResolvedValue(json({ items: [], total: 0, page: 2, per_page: 20 }))
    vi.stubGlobal('fetch', fetch)
    const page = await fetchEvents({ q: 'наука & спорт', category: 'creativity', page: 2 })
    const url = new URL(fetch.mock.calls[0][0], 'http://localhost')
    expect(url.pathname).toBe('/api/events')
    expect(url.searchParams.get('q')).toBe('наука & спорт')
    expect(url.searchParams.get('category')).toBe('creativity')
    expect(page.page).toBe(2)
  })

  it('показывает отказ API, не подменяет его моками', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'База недоступна' }, 503)))
    await expect(fetchEvents()).rejects.toMatchObject({ status: 503, message: 'База недоступна' })
  })

  it('раскладывает 422 по полям формы', async () => {
    const fetch = vi.fn().mockResolvedValue(json({ detail: [{ loc: ['body', 'event_date'], msg: 'Дата мероприятия уже прошла', type: 'value_error' }] }, 422))
    vi.stubGlobal('fetch', fetch)
    await expect(submitEvent({ title: 'Турнир' } as Submission)).rejects.toMatchObject({ fields: { event_date: 'Дата мероприятия уже прошла' } })
    expect(fetch.mock.calls[0][0]).toBe('/api/submissions')
    expect(fetch.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ title: 'Турнир' })
  })

  it('не принимает HTML вместо JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>app</html>', { headers: { 'content-type': 'text/html' } })))
    await expect(fetchCategories()).rejects.toBeInstanceOf(ApiError)
  })

  it('объясняет повреждённый JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{broken', { headers: { 'content-type': 'application/json' } })))
    await expect(fetchEvents()).rejects.toMatchObject({ message: 'Сервер вернул неверный ответ. Попробуйте ещё раз.' })
  })

  it('прерывает запрос при смене экрана', async () => {
    const controller = new AbortController()
    const fetch = vi.fn((_url: string, options: RequestInit) => new Promise((_resolve, reject) => {
      options.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    }))
    vi.stubGlobal('fetch', fetch)
    const request = fetchEvents({}, controller.signal)
    controller.abort()
    await expect(request).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetch.mock.calls[0][1].signal!.aborted).toBe(true)
  })

  it('ограничивает время чтения 15 секундами даже с сигналом экрана', async () => {
    vi.useFakeTimers()
    try {
      vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => new Promise((_resolve, reject) => {
        options.signal!.addEventListener('abort', () => reject(new DOMException('Timeout', 'AbortError')))
      })))
      const result = expect(fetchEvents({}, new AbortController().signal)).rejects.toMatchObject({ status: 0 })
      await vi.advanceTimersByTimeAsync(15000)
      await result
    } finally { vi.useRealTimers() }
  })

  it('объясняет ошибку сети', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(fetchEvents()).rejects.toMatchObject({ status: 0 })
  })

  it('отличает 404 карточки от недоступности сервера', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'Мероприятие не найдено' }, 404)))
    await expect(fetchEvent('999')).rejects.toMatchObject({ status: 404 })
  })

  it('загружает все страницы календаря, даже если событий больше 100', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(json({ items: Array.from({ length: 100 }, (_, id) => ({ id })), total: 101 }))
      .mockResolvedValueOnce(json({ items: [{ id: 100 }], total: 101 }))
    vi.stubGlobal('fetch', fetch)
    const events = await fetchMonthEvents({ date_from: '2026-11-01', date_to: '2026-11-30' })
    expect(events).toHaveLength(101)
    expect(fetch.mock.calls[1][0]).toContain('page=2')
    expect(fetch.mock.calls[1][0]).toContain('per_page=100')
  })
})
