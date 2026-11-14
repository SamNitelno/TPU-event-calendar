import { createServerFn } from '@tanstack/react-start'

export const adminLogin = createServerFn({ method: 'POST' })
  .validator((input: unknown) => {
    const key = (input as { key?: unknown })?.key
    if (typeof key !== 'string' || !key.trim() || key.length > 500) throw new Error('Некорректный ключ')
    return { key: key.trim() }
  })
  .handler(async ({ data }) => {
    const { login } = await import('./admin-auth.server')
    return login(data.key)
  })

export const adminCheck = createServerFn({ method: 'GET' }).handler(async () => {
  const { isAuthed } = await import('./admin-auth.server')
  return { authed: isAuthed() }
})

export const adminLogout = createServerFn({ method: 'POST' }).handler(async () => {
  const { logout } = await import('./admin-auth.server')
  return logout()
})
