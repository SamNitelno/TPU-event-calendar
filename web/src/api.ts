export interface Category {
  slug: string
  name: string
  events_count: number
}

export interface Event {
  id: number
  title: string
  organizer: string
  category: Pick<Category, 'slug' | 'name'>
  source: 'vk' | 'form'
  event_date: string
  end_date: string | null
  start_time: string | null
  end_time: string | null
  location: string | null
  original_post_link: string | null
}

export interface EventDetail extends Event {
  description: string | null
  image_url: string | null
}

export interface EventsPage {
  items: Event[]
  page: number
  per_page: number
  total: number
}

export interface EventFilters {
  category?: string
  q?: string
  date_from?: string
  date_to?: string
  page?: number
  per_page?: number
}

export interface Submission {
  title: string
  organizer: string
  contact: string
  category: string
  event_date: string
  end_date: string
  start_time: string
  end_time: string
  location: string
  original_post_link: string
  description: string
}

interface ValidationIssue {
  loc: (string | number)[]
  msg: string
  type: string
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public fields: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (options.signal?.aborted) abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  const timeout = setTimeout(abort, 15000)
  let response: Response
  let body: unknown = null
  let isJson = false
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { Accept: 'application/json', ...options.headers },
      signal: controller.signal,
    })
    isJson = !!response.headers.get('content-type')?.includes('application/json')
    if (isJson) {
      try { body = await response.json() }
      catch { throw new ApiError('Сервер вернул неверный ответ. Попробуйте ещё раз.', response.status) }
    }
  } catch (error) {
    if (options.signal?.aborted) throw error
    if (error instanceof ApiError) throw error
    throw new ApiError('Не удалось связаться с сервером. Проверьте подключение и повторите попытку.', 0)
  } finally {
    clearTimeout(timeout)
    options.signal?.removeEventListener('abort', abort)
  }
  if (!response.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    const fields: Record<string, string> = {}
    if (Array.isArray(detail)) {
      for (const issue of detail as ValidationIssue[]) {
        if (Array.isArray(issue.loc) && typeof issue.msg === 'string') {
          fields[String(issue.loc.at(-1))] = issue.msg
        }
      }
    }
    throw new ApiError(
      typeof detail === 'string' ? detail : response.status === 422
        ? 'Проверьте отмеченные поля.' : 'Сервис временно недоступен. Попробуйте ещё раз.',
      response.status, fields,
    )
  }
  if (!isJson) throw new ApiError('Сервер вернул неверный ответ. Попробуйте ещё раз.', response.status)
  return body as T
}

export function fetchEvents(filters: EventFilters = {}, signal?: AbortSignal) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  return request<EventsPage>(`/events?${query}`, { signal })
}

// Календарю нужны все страницы месяца, включая многодневные события и прошлые дни.
export async function fetchMonthEvents(filters: EventFilters, signal?: AbortSignal): Promise<Event[]> {
  const events: Event[] = []
  for (let page = 1; ; page++) {
    const result = await fetchEvents({ ...filters, page, per_page: 100 }, signal)
    events.push(...result.items)
    if (events.length >= result.total || result.items.length === 0) return events
  }
}

export const fetchCategories = (signal?: AbortSignal) => request<Category[]>('/categories', { signal })
export const fetchEvent = (id: string, signal?: AbortSignal) => request<EventDetail>(`/events/${encodeURIComponent(id)}`, { signal })
export const submitEvent = (submission: Submission) => request<{ id: number; status: 'pending' }>('/submissions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(submission),
})
