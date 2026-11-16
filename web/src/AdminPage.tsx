import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, fetchAdminEvents, getAdminSession, loginAdmin, logoutAdmin, saveAdminEvent, type AdminEvent, type AdminSession, type EventStatus, type Moderation, type Category } from './api'

const statusNames: Record<EventStatus, string> = { pending: 'На проверке', published: 'Опубликовано', rejected: 'Отклонено' }
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Не удалось выполнить действие'

function LoginForm({ onLogin }: { onLogin: (session: AdminSession) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    try { onLogin(await loginAdmin(username, password)); setPassword('') }
    catch (error) { setError(errorMessage(error)) }
    finally { setPending(false) }
  }
  return <section className="form-page"><h1>Вход администратора</h1><form className="submission-form" onSubmit={submit}>
    <fieldset disabled={pending}><div className="form-grid">
      <div className="field wide"><label htmlFor="username">Логин</label><input id="username" autoComplete="username" minLength={3} maxLength={64} required value={username} onChange={e => setUsername(e.target.value)} /></div>
      <div className="field wide"><label htmlFor="password">Пароль</label><input id="password" type="password" autoComplete="current-password" maxLength={1024} required value={password} onChange={e => setPassword(e.target.value)} /></div>
    </div></fieldset>{error && <p role="alert" className="field-error">{error}</p>}<button className="button primary" disabled={pending}>{pending ? 'Входим…' : 'Войти'}</button>
  </form></section>
}

const editFields = [
  ['title', 'Название', 'text', 300], ['organizer', 'Организатор', 'text', 200],
  ['event_date', 'Дата начала', 'date'], ['end_date', 'Дата окончания', 'date'],
  ['start_time', 'Начало', 'time'], ['end_time', 'Окончание', 'time'],
  ['location', 'Место проведения', 'text', 300], ['original_post_link', 'Ссылка на пост ВКонтакте', 'url', 300],
] as const

function Editor({ event, categories, csrf, onSaved, onExpired }: { event: AdminEvent; categories: Category[]; csrf: string; onSaved: () => void; onExpired: () => void }) {
  const [values, setValues] = useState<Moderation>({ title: event.title, organizer: event.organizer, category: event.category?.slug || '', event_date: event.event_date || '', end_date: event.end_date || '', start_time: event.start_time || '', end_time: event.end_time || '', location: event.location || '', original_post_link: event.original_post_link || '', description: event.description || '', status: event.status })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  async function submit(e: FormEvent) {
    e.preventDefault()
    setPending(true)
    setErrors({})
    setError('')
    try { await saveAdminEvent(event.id, values, csrf); onSaved() }
    catch (error) {
      if (error instanceof ApiError && error.status === 401) { onExpired(); return }
      setError(errorMessage(error))
      if (error instanceof ApiError) setErrors(error.fields)
    } finally { setPending(false) }
  }
  return <section className="admin-editor"><h2>Мероприятие №{event.id}</h2>
    <p>Источник: {event.source === 'vk' ? 'ВКонтакте' : 'Форма сайта'}</p>{event.contact && <p className="admin-contact">Контакт автора: {event.contact}</p>}
    <form onSubmit={submit}><fieldset disabled={pending}><div className="form-grid">
      {editFields.map(([key, label, type, max]) => <div className="field" key={key}><label htmlFor={`edit-${key}`}>{label}</label><input id={`edit-${key}`} type={type} maxLength={max} required={key === 'title' || key === 'organizer'} minLength={key === 'title' ? 3 : key === 'organizer' ? 2 : undefined} value={values[key]} onChange={e => setValues({ ...values, [key]: e.target.value })} aria-invalid={!!errors[key]} aria-describedby={errors[key] ? `edit-${key}-error` : undefined} />{errors[key] && <small id={`edit-${key}-error`} className="field-error">{errors[key]}</small>}</div>)}
      <div className="field"><label htmlFor="edit-category">Категория</label><select id="edit-category" value={values.category} onChange={e => setValues({ ...values, category: e.target.value })} aria-invalid={!!errors.category}><option value="">Не определена</option>{categories.map(cat => <option value={cat.slug} key={cat.slug}>{cat.name}</option>)}</select>{errors.category && <small className="field-error">{errors.category}</small>}</div>
      <div className="field"><label htmlFor="edit-status">Решение</label><select id="edit-status" value={values.status} onChange={e => setValues({ ...values, status: e.target.value as EventStatus })}>{Object.entries(statusNames).map(([value, title]) => <option key={value} value={value}>{title}</option>)}</select></div>
      <div className="field wide"><label htmlFor="edit-description">Описание</label><textarea id="edit-description" rows={8} maxLength={5000} value={values.description} onChange={e => setValues({ ...values, description: e.target.value })} /></div>
    </div></fieldset>{error && <p role="alert" className="field-error">{error}</p>}<button className="button primary" disabled={pending}>{pending ? 'Сохраняем…' : 'Сохранить решение'}</button></form>
  </section>
}

function ModerationQueue({ session, categories, onExpired, onModerated }: { session: AdminSession; categories: Category[]; onExpired: () => void; onModerated?: () => void }) {
  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(1)
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{ items: AdminEvent[]; total: number }>()
  const [selected, setSelected] = useState<AdminEvent>()
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    fetchAdminEvents(status, page, controller.signal).then(value => {
      if (!controller.signal.aborted) setResult(value)
    }).catch(error => {
      if (controller.signal.aborted) return
      if (error instanceof ApiError && error.status === 401) onExpired()
      else setError(errorMessage(error))
    })
    return () => controller.abort()
  }, [status, page, attempt, onExpired])
  async function logout() {
    setBusy(true)
    try { await logoutAdmin(session.csrf_token); onExpired() }
    catch (error) { setError(errorMessage(error)) }
    finally { setBusy(false) }
  }
  function refresh() { setResult(undefined); setError(''); setSelected(undefined); setAttempt(value => value + 1) }
  return <section><div className="admin-heading"><h1>Модерация</h1><span>{session.username}</span><button className="button secondary" disabled={busy} onClick={logout}>Выйти</button></div>
    <div className="admin-toolbar"><label htmlFor="status-filter">Показать</label><select id="status-filter" value={status} onChange={e => { setStatus(e.target.value); setPage(1); refresh(); setSaved(false) }}>{Object.entries(statusNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}<option value="all">Все статусы</option></select><button className="button secondary" onClick={refresh}>Обновить</button></div>
    {saved && <p role="status">Решение сохранено.</p>}{error && <p role="alert" className="field-error">{error}</p>}
    {!result && !error && <p role="status">Загружаем очередь…</p>}
    {result && <><p>Мероприятий: {result.total}</p><div className="admin-items">{result.items.map(event => <button className={`admin-item ${selected?.id === event.id ? 'selected' : ''}`} key={event.id} onClick={() => { setSelected(event); setSaved(false) }}><strong>{event.title}</strong><small>{statusNames[event.status]} · {event.event_date || 'Дата не определена'}</small></button>)}</div>{!result.items.length && <p>В этой очереди мероприятий нет.</p>}
      <div className="admin-toolbar"><button className="button secondary" disabled={page === 1} onClick={() => { setPage(value => value - 1); refresh() }}>Назад</button><span>Страница {page}</span><button className="button secondary" disabled={page * 20 >= result.total} onClick={() => { setPage(value => value + 1); refresh() }}>Далее</button></div></>}
    {selected && <Editor key={selected.id} event={selected} categories={categories} csrf={session.csrf_token} onExpired={onExpired} onSaved={() => { refresh(); setSaved(true); onModerated?.() }} />}
  </section>
}

export default function AdminPage({ categories, onModerated }: { categories: Category[]; onModerated?: () => void }) {
  const [session, setSession] = useState<AdminSession | null>()
  const [error, setError] = useState('')
  const [attempt, retry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    getAdminSession(controller.signal).then(value => { if (!controller.signal.aborted) setSession(value) }).catch(error => {
      if (controller.signal.aborted) return
      if (error instanceof ApiError && error.status === 401) setSession(null)
      else setError(errorMessage(error))
    })
    return () => controller.abort()
  }, [attempt])
  const [expire] = useState(() => () => setSession(null))
  if (error) return <div role="alert"><p>{error}</p><button className="button secondary" onClick={() => { setError(''); retry(value => value + 1) }}>Повторить</button></div>
  if (session === undefined) return <p role="status">Проверяем вход…</p>
  return session ? <ModerationQueue session={session} categories={categories} onExpired={expire} onModerated={onModerated} /> : <LoginForm onLogin={setSession} />
}
