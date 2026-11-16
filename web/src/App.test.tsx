import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import { addDays, todayInTomsk } from './dates'
import type { EventDetail } from './api'

const today = todayInTomsk()
const event: EventDetail = { id: 1, title: 'Научная встреча', organizer: 'ТПУ', category: { slug: 'science', name: 'Наука' }, source: 'vk', event_date: today, end_date: addDays(today, 2), start_time: null, end_time: null, location: 'Онлайн', original_post_link: null, description: '<script>alert(1)</script>', image_url: null }
const categories = [{ slug: 'science', name: 'Наука', events_count: 1 }, { slug: 'creativity', name: 'Культура', events_count: 0 }]
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } })
function mockApi(handler?: (url: URL, options?: RequestInit) => Response | Promise<Response> | undefined) {
  const fetch = vi.fn(async (path: string, options?: RequestInit) => {
    const url = new URL(path, 'http://localhost')
    const custom = handler?.(url, options)
    if (custom) return custom
    if (url.pathname === '/api/categories') return json(categories)
    if (url.pathname === '/api/events/1') return json(event)
    return json({ items: [event], page: 1, total: 1, per_page: 20 })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
const open = (path = '/') => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)

describe('сценарии календаря', () => {
  it('рисует данные API, не выдумывает время и открывает карточку', async () => {
    mockApi()
    open()
    await userEvent.click(await screen.findByText('Научная встреча'))
    expect(await screen.findByRole('heading', { name: 'Научная встреча' })).toBeInTheDocument()
    expect(screen.queryByText('00:00')).not.toBeInTheDocument()
    expect(screen.getByText('Онлайн')).toBeInTheDocument()
    expect(screen.queryByText('Открыть пост во ВКонтакте')).not.toBeInTheDocument()
    expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
  })

  it('поиск и категория одновременно отправляются в API', async () => {
    const fetch = mockApi()
    open('/?category=creativity')
    await screen.findByText('Научная встреча')
    await userEvent.type(screen.getByRole('textbox', { name: 'Поиск мероприятий' }), 'театр')
    await userEvent.click(screen.getByRole('button', { name: 'Найти' }))
    await waitFor(() => expect(fetch.mock.calls.some(([path]) => { const url = new URL(path, 'http://localhost'); return url.searchParams.get('q') === 'театр' && url.searchParams.get('category') === 'creativity' })).toBe(true))
  })

  it('показывает ошибку загрузки и повторяет запрос', async () => {
    let failed = true
    mockApi(url => url.pathname === '/api/events' && failed ? json({ detail: 'Сервис недоступен' }, 503) : undefined)
    open()
    expect(await screen.findByRole('alert')).toHaveTextContent('Сервис недоступен')
    failed = false
    await userEvent.click(screen.getByRole('button', { name: 'Повторить' }))
    expect(await screen.findByText('Научная встреча')).toBeInTheDocument()
  })

  it('добавляет следующую страницу к текущей ленте', async () => {
    const second = { ...event, id: 2, title: 'Вторая встреча' }
    mockApi(url => url.pathname === '/api/events' ? json({ items: [url.searchParams.get('page') === '2' ? second : event], page: Number(url.searchParams.get('page') || 1), per_page: 1, total: 2 }) : undefined)
    open()
    await userEvent.click(await screen.findByRole('button', { name: 'Показать ещё' }))
    expect(await screen.findByText('Вторая встреча')).toBeInTheDocument()
    expect(screen.getByText('Научная встреча')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Показать ещё' })).not.toBeInTheDocument()
  })

  it('не затирает новый поиск запоздалым ответом старого', async () => {
    let resolveOld!: (response: Response) => void
    mockApi(url => url.pathname === '/api/events' && !url.searchParams.get('q') ? new Promise<Response>(resolve => { resolveOld = resolve }) : undefined)
    open()
    await userEvent.type(screen.getByRole('textbox', { name: 'Поиск мероприятий' }), 'встреча')
    await userEvent.click(screen.getByRole('button', { name: 'Найти' }))
    await screen.findByText('Научная встреча')
    await act(async () => resolveOld(json({ items: [{ ...event, title: 'Старый ответ' }], total: 1 })))
    expect(screen.queryByText('Старый ответ')).not.toBeInTheDocument()
  })

  it('многодневное событие видно в календаре и на второй день', async () => {
    mockApi()
    const secondDay = addDays(today, 1)
    open(`/calendar?month=${secondDay.slice(0, 7)}`)
    const day = await screen.findByRole('button', { name: new RegExp(`^${Number(secondDay.slice(-2))} .*мероприятий 1`) })
    await userEvent.click(day)
    expect(await screen.findByRole('link', { name: /Научная встреча/ })).toBeInTheDocument()
  })

  it('не падает на неверной дате в ссылке календаря', async () => {
    mockApi()
    open('/calendar?month=2026-13&day=invalid')
    expect(await screen.findByRole('button', { name: 'Следующий месяц' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByLabelText('Календарь мероприятий')).toBeInTheDocument())
  })

  it('показывает 404 по прямой ссылке', async () => {
    mockApi(url => url.pathname === '/api/events/999' ? json({ detail: 'Мероприятие не найдено' }, 404) : undefined)
    open('/event/999')
    expect(await screen.findByRole('alert')).toHaveTextContent('Мероприятие не найдено')
  })

  it('отправляет заявку, сохраняет поля при 422 и показывает номер после успеха', async () => {
    let fail = true
    let body: unknown
    mockApi((url, options) => {
      if (url.pathname !== '/api/submissions') return undefined
      body = JSON.parse(options!.body as string)
      return fail ? json({ detail: [{ loc: ['body', 'contact'], msg: 'Уточните контакт', type: 'value_error' }] }, 422) : json({ id: 42, status: 'pending' }, 201)
    })
    open('/submit')
    await screen.findByRole('option', { name: 'Наука' })
    fireEvent.change(screen.getByLabelText('Название *'), { target: { value: 'Встреча студентов' } })
    fireEvent.change(screen.getByLabelText('Организация *'), { target: { value: 'ТПУ' } })
    fireEvent.change(screen.getByLabelText('Контакт для связи *'), { target: { value: 'club@example.com' } })
    fireEvent.change(screen.getByLabelText('Дата начала *'), { target: { value: today } })
    await userEvent.selectOptions(screen.getByLabelText('Категория *'), 'science')
    await userEvent.click(screen.getByRole('button', { name: 'Отправить на проверку' }))
    expect(await screen.findByText('Уточните контакт')).toBeInTheDocument()
    expect(screen.getByLabelText('Название *')).toHaveValue('Встреча студентов')
    fail = false
    await userEvent.click(screen.getByRole('button', { name: 'Отправить на проверку' }))
    expect(await screen.findByRole('heading', { name: 'Заявка отправлена' })).toBeInTheDocument()
    expect(body).toMatchObject({ title: 'Встреча студентов', category: 'science', event_date: today })
    expect(screen.getByText(/Номер заявки: 42/)).toBeInTheDocument()
  })
})
