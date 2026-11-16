import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import AdminPage from './AdminPage'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
const session = { username: 'moderator', csrf_token: 'csrf-test' }
const event = { id: 7, title: 'Новая встреча', organizer: 'ТПУ', contact: 'private@example.com', category: null, event_date: null, end_date: null, start_time: null, end_time: null, location: null, original_post_link: null, description: null, image_url: null, status: 'pending', source: 'form' }
const categories = [{ slug: 'science', name: 'Наука', events_count: 0 }]

describe('администратор', () => {
  it('показывает вход и ошибку неверного пароля', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ detail: 'Неверный логин или пароль' }, 401)))
    render(<AdminPage categories={categories} />)
    fireEvent.change(await screen.findByLabelText('Логин'), { target: { value: 'moderator' } })
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'wrong' } })
    await userEvent.click(screen.getByRole('button', { name: 'Войти' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Неверный логин или пароль')
  })

  it('входит, редактирует неполную заявку, публикует и выходит', async () => {
    let logged = false
    let published = false
    const fetch = vi.fn(async (url: string, options?: RequestInit) => {
      if (url === '/api/admin/me') return logged ? json(session) : json({ detail: 'Войдите' }, 401)
      if (url === '/api/admin/login') { logged = true; return json(session) }
      if (url === '/api/admin/logout') return new Response(null, { status: 204 })
      if (url.startsWith('/api/admin/events?')) return json({ items: published ? [] : [event], total: published ? 0 : 1, page: 1 })
      if (url === '/api/admin/events/7') {
        expect(options?.method).toBe('PUT')
        expect(options?.headers).toMatchObject({ 'X-CSRF-Token': 'csrf-test' })
        expect(JSON.parse(options?.body as string)).toMatchObject({ status: 'published', category: 'science', event_date: '2026-12-01' })
        published = true
        return json({ ...event, status: 'published' })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetch)
    render(<AdminPage categories={categories} />)
    fireEvent.change(await screen.findByLabelText('Логин'), { target: { value: 'moderator' } })
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'test-password-123' } })
    await userEvent.click(screen.getByRole('button', { name: 'Войти' }))
    await userEvent.click(await screen.findByRole('button', { name: /Новая встреча/ }))
    expect(screen.getByText('Контакт автора: private@example.com')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Дата начала'), { target: { value: '2026-12-01' } })
    await userEvent.selectOptions(screen.getByLabelText('Категория'), 'science')
    await userEvent.selectOptions(screen.getByLabelText('Решение'), 'published')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить решение' }))
    expect(await screen.findByText('Решение сохранено.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Выйти' }))
    expect(await screen.findByRole('heading', { name: 'Вход администратора' })).toBeInTheDocument()
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => url === '/api/admin/logout')).toBe(true))
  })

  it('сохраняет правки при ошибке 422', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url === '/api/admin/me') return json(session)
      if (url.startsWith('/api/admin/events?')) return json({ items: [event], total: 1, page: 1 })
      return json({ detail: [{ loc: ['body', 'event_date'], msg: 'Укажите дату перед публикацией', type: 'value_error' }] }, 422)
    }))
    render(<AdminPage categories={categories} />)
    await userEvent.click(await screen.findByRole('button', { name: /Новая встреча/ }))
    fireEvent.change(screen.getByLabelText('Название'), { target: { value: 'Исправленное название' } })
    await userEvent.selectOptions(screen.getByLabelText('Решение'), 'published')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить решение' }))
    expect(await screen.findByText('Укажите дату перед публикацией')).toBeInTheDocument()
    expect(screen.getByLabelText('Название')).toHaveValue('Исправленное название')
  })
})
