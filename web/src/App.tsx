import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, BriefcaseBusiness, CalendarDays, ChevronLeft, ChevronRight, Clock3, FlaskConical, GraduationCap, Grid2X2, HandHeart, List, MapPin, Music2, Plus, RefreshCw, Search, Trophy, type LucideIcon } from 'lucide-react'
import { ApiError, fetchCategories, fetchEvent, fetchEvents, fetchMonthEvents, submitEvent, type Category, type Event, type Submission } from './api'
import { addDays, dateRange, dateValue, dayLabel, formatDate, isValidDay, monthBounds, shiftMonth, todayInTomsk } from './dates'

const categoryIcons: Record<string, LucideIcon> = {
  science: FlaskConical, sport: Trophy, creativity: Music2, career: BriefcaseBusiness,
  volunteering: HandHeart, student_life: GraduationCap,
}
const message = (error: unknown) => error instanceof Error ? error.message : 'Не удалось загрузить данные.'

function useResource<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ data?: T; error?: string; status?: number }>({})
  const [attempt, retry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setState({})
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ data })
    }).catch(error => {
      if (!controller.signal.aborted) setState({ error: message(error), status: error instanceof ApiError ? error.status : 0 })
    })
    return () => controller.abort()
    // Ключ описывает параметры загрузки; новая функция сама по себе не перезапускает запрос.
  }, [key, attempt])
  return { ...state, retry: () => retry(value => value + 1) }
}

function Notice({ children, retry, error = false }: { children: ReactNode; retry?: () => void; error?: boolean }) {
  return <div className={`notice ${error ? 'notice-error' : ''}`} role={error ? 'alert' : 'status'}>
    <p>{children}</p>{retry && <button className="button secondary" onClick={retry}><RefreshCw size={16} /> Повторить</button>}
  </div>
}

function CategoryIcon({ slug, size = 20 }: { slug: string; size?: number }) {
  const Icon = categoryIcons[slug] || Grid2X2
  return <Icon size={size} aria-hidden="true" />
}

function Categories({ categories, mobile = false }: { categories: Category[]; mobile?: boolean }) {
  const [params] = useSearchParams()
  const location = useLocation()
  const selected = params.get('category') || ''
  const base = location.pathname === '/calendar' ? '/calendar' : '/'
  function href(slug: string) {
    const query = new URLSearchParams(params)
    query.delete('day')
    if (slug) query.set('category', slug)
    else query.delete('category')
    return `${base}?${query}`
  }
  const all = [{ slug: '', name: 'Все', events_count: categories.reduce((sum, cat) => sum + cat.events_count, 0) }, ...categories]
  return <nav aria-label={mobile ? 'Категории на мобильном экране' : 'Категории'} className={mobile ? 'mobile-categories' : 'categories'}>
    {all.map(cat => <Link key={cat.slug} to={href(cat.slug)} className={`category-link ${selected === cat.slug ? 'active' : ''}`} aria-current={selected === cat.slug ? 'true' : undefined}>
      {!mobile && <CategoryIcon slug={cat.slug} size={18} />}<span>{cat.name}</span><small>{cat.events_count}</small>
    </Link>)}
  </nav>
}

function Header() {
  const [params] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') || '')
  const navigate = useNavigate()
  const location = useLocation()
  useEffect(() => setQuery(params.get('q') || ''), [params])
  function search(e: FormEvent) {
    e.preventDefault()
    const next = new URLSearchParams(params)
    if (query.trim()) next.set('q', query.trim())
    else next.delete('q')
    navigate(`${location.pathname === '/calendar' ? '/calendar' : '/'}?${next}`)
  }
  return <header className="site-header"><div className="header-inner">
    <Link to="/" className="brand"><span className="brand-icon"><CalendarDays size={22} /></span><span><strong>Календарь ТПУ</strong><small>Все мероприятия университета</small></span></Link>
    <form className="search" role="search" onSubmit={search}><Search size={18} aria-hidden="true" /><input aria-label="Поиск мероприятий" placeholder="Найти мероприятие…" value={query} maxLength={100} onChange={e => setQuery(e.target.value)} /><button type="submit" aria-label="Найти"><ArrowRight size={18} /></button></form>
    <nav className="header-nav" aria-label="Основная навигация"><NavLink to="/" end>Афиша</NavLink><NavLink to="/guide">Как пользоваться</NavLink></nav>
    <Link className="button primary submit-link" to="/submit"><Plus size={17} /> Подать мероприятие</Link>
  </div></header>
}

function EventCard({ event, compact = false }: { event: Event; compact?: boolean }) {
  return <Link to={`/event/${event.id}`} className={`event-card ${compact ? 'compact' : ''}`}>
    <span className={`category-icon cat-${event.category.slug}`}><CategoryIcon slug={event.category.slug} /></span>
    <span className="event-content"><span className="event-topline"><span className="organizer">{event.organizer}</span><span className={`badge cat-${event.category.slug}`}>{event.category.name}</span></span>
      <strong>{event.title}</strong><span className="event-meta">
        <span>{dateRange(event.event_date, event.end_date)}</span>
        {event.start_time && <span><Clock3 size={14} />{event.start_time}{event.end_time && ` — ${event.end_time}`}</span>}
        {event.location && <span><MapPin size={14} />{event.location}</span>}
      </span></span><ArrowRight className="card-arrow" size={19} aria-hidden="true" />
  </Link>
}

function Feed({ category, q, day, today }: { category: string; q: string; day: string; today: string }) {
  const [page, setPage] = useState(1)
  const [attempt, retry] = useState(0)
  const [items, setItems] = useState<Event[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    fetchEvents({ category, q, page, ...(day ? { date_from: day, date_to: day } : {}) }, controller.signal).then(result => {
      if (controller.signal.aborted) return
      setItems(previous => page === 1 ? result.items : [...previous, ...result.items.filter(item => !previous.some(old => old.id === item.id))])
      setTotal(result.total)
    }).catch(error => {
      if (!controller.signal.aborted) setError(message(error))
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [category, q, day, page, attempt])
  const groups = new Map<string, Event[]>()
  for (const event of items) {
    const firstVisibleDay = day || today
    const dayKey = event.event_date < firstVisibleDay ? firstVisibleDay : event.event_date
    groups.set(dayKey, [...(groups.get(dayKey) || []), event])
  }
  return <div aria-busy={loading}>
    {Array.from(groups, ([date, events]) => <section className="day-group" key={date} aria-label={formatDate(date)}>
      <div className="day-heading"><strong>{dateValue(date).getUTCDate()}</strong><div>{formatDate(date, { month: 'long' })},<br className="desktop-break" /> {formatDate(date, { weekday: 'long' })}</div>{dayLabel(date, today) && <span className="today-label">{dayLabel(date, today)}</span>}</div>
      <div className="day-events">{events!.map(event => <EventCard key={event.id} event={event} />)}</div>
    </section>)}
    {loading && <Notice>Загружаем мероприятия…</Notice>}
    {error && <Notice error retry={() => retry(value => value + 1)}>{error}</Notice>}
    {!loading && !error && !items.length && <Notice>Пока нет мероприятий{q || category || day ? ' по выбранным условиям. Измените поиск или фильтры.' : '. Загляните позже или подайте своё.'}</Notice>}
    {!loading && !error && items.length < total && <div className="load-more"><button className="button secondary" onClick={() => setPage(value => value + 1)}>Показать ещё <ArrowRight size={17} /></button><small>Показано {items.length} из {total}</small></div>}
  </div>
}

function MonthCalendar({ category, q, today }: { category: string; q: string; today: string }) {
  const [params, setParams] = useSearchParams()
  const requested = params.get('month') || ''
  const month = /^\d{4}-(0[1-9]|1[0-2])$/.test(requested) && requested >= '1900-01' && requested <= '2100-12' ? requested : today.slice(0, 7)
  const dayParam = params.get('day') || ''
  const selected = isValidDay(dayParam) && dayParam.startsWith(month) ? dayParam : ''
  const bounds = monthBounds(month)
  const resource = useResource(`${month}|${category}|${q}`, signal => fetchMonthEvents({ ...bounds, category, q }, signal))
  function changeMonth(value: string) {
    const next = new URLSearchParams(params)
    next.set('month', value)
    next.delete('day')
    setParams(next)
  }
  const weekday = (dateValue(bounds.date_from).getUTCDay() + 6) % 7
  const days = Array.from({ length: dateValue(bounds.date_to).getUTCDate() }, (_, index) => addDays(bounds.date_from, index))
  const selectedEvents = (resource.data || []).filter(event => event.event_date <= selected && (event.end_date || event.event_date) >= selected)
  return <>
    <div className="month-toolbar"><h2>{formatDate(bounds.date_from, { month: 'long', year: 'numeric' })}</h2><div className="month-actions">
      <button className="button secondary" onClick={() => changeMonth(today.slice(0, 7))}>Этот месяц</button>
      <button className="icon-button" aria-label="Предыдущий месяц" onClick={() => changeMonth(shiftMonth(month, -1))}><ChevronLeft /></button>
      <button className="icon-button" aria-label="Следующий месяц" onClick={() => changeMonth(shiftMonth(month, 1))}><ChevronRight /></button>
    </div></div>
    {!resource.data && !resource.error && <Notice>Загружаем календарь…</Notice>}
    {resource.error && <Notice error retry={resource.retry}>{resource.error}</Notice>}
    {resource.data && <>
      <div className="calendar" aria-label="Календарь мероприятий">
        {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map(day => <div className="weekday" key={day}>{day}</div>)}
        {Array.from({ length: weekday }, (_, index) => <div className="calendar-blank" key={`blank-${index}`} />)}
        {days.map(day => {
          const events = resource.data!.filter(event => event.event_date <= day && (event.end_date || event.event_date) >= day)
          return <button key={day} className={`calendar-day ${day === today ? 'is-today' : ''} ${day === selected ? 'selected' : ''}`} aria-label={`${formatDate(day)}: мероприятий ${events.length}`} aria-pressed={day === selected} onClick={() => { const next = new URLSearchParams(params); next.set('day', day); setParams(next) }}>
            <span className="day-number">{Number(day.slice(-2))}</span><span className="calendar-event-titles">{events.slice(0, 2).map(event => <span className={`calendar-event cat-${event.category.slug}`} key={event.id}>{event.title}</span>)}</span>
            {!!events.length && <small className="calendar-count">{events.length} соб.</small>}
          </button>
        })}
      </div>
      {selected && <section className="selected-day"><h2>{formatDate(selected)}</h2>{selectedEvents.length ? selectedEvents.map(event => <EventCard key={event.id} event={event} compact />) : <Notice>В этот день мероприятий нет.</Notice>}</section>}
    </>}
  </>
}

function Listing({ categories, calendar = false, today }: { categories: Category[]; calendar?: boolean; today: string }) {
  const [params] = useSearchParams()
  const category = params.get('category') || ''
  const q = params.get('q') || ''
  const dayParam = params.get('day') || ''
  const day = isValidDay(dayParam) ? dayParam : ''
  const categoryName = categories.find(item => item.slug === category)?.name
  return <>
    <div className="page-heading"><h1>{category ? categoryName || 'Мероприятия по категории' : <>Все события ТПУ <span>в одном календаре</span></>}</h1></div>
    <div className="listing-toolbar"><div className="view-switch" aria-label="Вид мероприятий"><Link className={!calendar ? 'active' : ''} to={`/?${params}`}><List size={16} />Лента</Link><Link className={calendar ? 'active' : ''} to={`/calendar?${params}`}><CalendarDays size={16} />Календарь</Link></div>
      {(q || category || day) && <Link className="text-link" to={calendar ? '/calendar' : '/'}>Сбросить фильтры</Link>}
    </div>
    {q && <p className="search-summary">Результаты поиска: «{q}»</p>}
    {calendar ? <MonthCalendar category={category} q={q} today={today} /> : <Feed key={`${category}|${q}|${day}|${today}`} category={category} q={q} day={day} today={today} />}
  </>
}

function safeUrl(value: string | null) {
  if (!value) return undefined
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined } catch { return undefined }
}

function EventPage() {
  const { id = '' } = useParams()
  const resource = useResource(id, signal => fetchEvent(id, signal))
  const event = resource.data
  return <article className="detail-page"><Link className="back-link" to="/"><ArrowLeft size={17} />К афише</Link>
    {resource.error ? <Notice error retry={resource.status === 404 ? undefined : resource.retry}>{resource.status === 404 ? 'Мероприятие не найдено' : resource.error}</Notice> : !event ? <Notice>Загружаем мероприятие…</Notice> : <>
      <span className={`badge cat-${event.category.slug}`}>{event.category.name}</span><h1>{event.title}</h1>
      <div className="detail-meta"><p><CalendarDays size={19} />{dateRange(event.event_date, event.end_date)}</p>
        {event.start_time && <p><Clock3 size={19} />{event.start_time}{event.end_time && ` — ${event.end_time}`} <small>по Томску</small></p>}
        {event.location && <p><MapPin size={19} />{event.location}</p>}<p><GraduationCap size={19} />{event.organizer}</p></div>
      {safeUrl(event.image_url) && <img className="event-image" src={safeUrl(event.image_url)} alt="" />}
      <p className="description">{event.description || 'Описание не указано.'}</p>
      {safeUrl(event.original_post_link) && <div className="info-card"><h2>Подробности и регистрация</h2><p>Актуальная информация — в сообществе организатора.</p><a className="button primary" href={safeUrl(event.original_post_link)} target="_blank" rel="noopener noreferrer">Открыть пост во ВКонтакте <ArrowRight size={17} /></a></div>}
    </>}
  </article>
}

const emptySubmission: Submission = { title: '', organizer: '', contact: '', category: '', event_date: '', end_date: '', start_time: '', end_time: '', location: '', original_post_link: '', description: '' }
const fieldConfig: { name: keyof Submission; label: string; type?: string; required?: boolean; minLength?: number; maxLength?: number; wide?: boolean }[] = [
  { name: 'title', label: 'Название', required: true, minLength: 3, maxLength: 300, wide: true },
  { name: 'organizer', label: 'Организация', required: true, minLength: 2, maxLength: 200 },
  { name: 'contact', label: 'Контакт для связи', required: true, minLength: 3, maxLength: 200 },
  { name: 'event_date', label: 'Дата начала', type: 'date', required: true },
  { name: 'end_date', label: 'Дата окончания', type: 'date' },
  { name: 'start_time', label: 'Начало', type: 'time' },
  { name: 'end_time', label: 'Окончание', type: 'time' },
  { name: 'location', label: 'Место проведения', maxLength: 300, wide: true },
  { name: 'original_post_link', label: 'Ссылка на пост ВКонтакте', type: 'url', maxLength: 300, wide: true },
]

function SubmitPage({ categories, today }: { categories: Category[]; today: string }) {
  const [values, setValues] = useState<Submission>(emptySubmission)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [created, setCreated] = useState<number>()
  const locked = useRef(false)
  async function send(e: FormEvent) {
    e.preventDefault()
    if (locked.current) return
    const nextErrors: Record<string, string> = {}
    if (values.event_date < today) nextErrors.event_date = 'Дата мероприятия уже прошла'
    if (values.end_date && values.end_date < values.event_date) nextErrors.end_date = 'Дата окончания раньше даты начала'
    if ((!values.end_date || values.end_date === values.event_date) && values.start_time && values.end_time && values.end_time <= values.start_time) nextErrors.end_time = 'Время окончания должно быть позже начала'
    setErrors(nextErrors)
    setError('')
    if (Object.keys(nextErrors).length) return
    locked.current = true
    setPending(true)
    try { const result = await submitEvent(values); setCreated(result.id) }
    catch (error) { setError(message(error)); if (error instanceof ApiError) setErrors(error.fields) }
    finally { locked.current = false; setPending(false) }
  }
  if (created !== undefined) return <section className="success-panel" role="status"><HandHeart size={40} /><h1>Заявка отправлена</h1><p>Номер заявки: {created}. Мероприятие появится в календаре после проверки администратором.</p><Link className="button primary" to="/">К афише</Link></section>
  return <section className="form-page"><Link className="back-link" to="/"><ArrowLeft size={17} />К афише</Link><h1>Подать мероприятие</h1><p className="intro">Расскажите о событии для студентов ТПУ. После проверки оно появится в календаре. Время указывайте по Томску.</p>
    <form className="submission-form" onSubmit={send}>
      <fieldset disabled={pending}><legend className="sr-only">Данные мероприятия</legend><div className="form-grid">
        {fieldConfig.map(field => <div className={`field ${field.wide ? 'wide' : ''}`} key={field.name}><label htmlFor={field.name}>{field.label}{field.required ? ' *' : ''}</label>
          <input id={field.name} name={field.name} type={field.type || 'text'} required={field.required} minLength={field.minLength} maxLength={field.maxLength} min={field.type === 'date' ? field.name === 'end_date' ? values.event_date || today : today : undefined} value={values[field.name]} aria-invalid={!!errors[field.name]} aria-describedby={errors[field.name] ? `${field.name}-error` : field.name === 'contact' ? 'contact-hint' : undefined} onChange={e => setValues({ ...values, [field.name]: e.target.value })} />
          {field.name === 'contact' && <small id="contact-hint">Почта, телефон или ссылка на профиль. Контакт не публикуется.</small>}
          {errors[field.name] && <small className="field-error" id={`${field.name}-error`}>{errors[field.name]}</small>}
        </div>)}
        <div className="field wide"><label htmlFor="category">Категория *</label><select required id="category" value={values.category} aria-invalid={!!errors.category} aria-describedby={errors.category ? 'category-error' : undefined} onChange={e => setValues({ ...values, category: e.target.value })}><option value="">Выберите категорию</option>{categories.map(cat => <option key={cat.slug} value={cat.slug}>{cat.name}</option>)}</select>{errors.category && <small id="category-error" className="field-error">{errors.category}</small>}</div>
        <div className="field wide"><label htmlFor="description">Описание</label><textarea id="description" rows={6} maxLength={5000} value={values.description} aria-invalid={!!errors.description} aria-describedby={errors.description ? 'description-error' : undefined} onChange={e => setValues({ ...values, description: e.target.value })} />{errors.description && <small className="field-error" id="description-error">{errors.description}</small>}</div>
      </div></fieldset>
      {error && <Notice error>{error}</Notice>}
      <p className="form-note">* Обязательные поля. Отправка заявки не означает публикацию.</p><button className="button primary" type="submit" disabled={pending || !categories.length}>{pending ? 'Отправляем…' : 'Отправить на проверку'}<ArrowRight size={17} /></button>
    </form>
  </section>
}

function Guide() {
  return <section className="guide"><h1>Как пользоваться</h1><div className="info-card"><h2>Найдите своё событие</h2><p>Выберите категорию или введите слово в поиске. Лента показывает предстоящие и продолжающиеся мероприятия. В календаре можно открыть любой месяц и выбрать день.</p></div><div className="info-card"><h2>Уточните подробности</h2><p>Нажмите на карточку, чтобы увидеть описание, место и время по Томску. Если есть ссылка на пост ВКонтакте, подробности регистрации доступны у организатора.</p></div><div className="info-card"><h2>Предложите мероприятие</h2><p>Заполните форму. Заявку проверит администратор; до проверки она не показывается в афише. Контакт для связи не публикуется.</p><Link className="button primary" to="/submit">Подать мероприятие</Link></div></section>
}

export default function App() {
  const categories = useResource('categories', fetchCategories)
  const [today, setToday] = useState(todayInTomsk)
  const location = useLocation()
  useEffect(() => {
    const timer = window.setInterval(() => setToday(todayInTomsk()), 30000)
    return () => window.clearInterval(timer)
  }, [])
  useEffect(() => {
    document.title = 'Календарь ТПУ — все мероприятия университета'
    window.scrollTo?.(0, 0)
  }, [location.pathname])
  const list = categories.data || []
  return <><a href="#main" className="skip-link">К содержимому</a><Header /><div className="site-layout"><aside className="sidebar"><div className="sidebar-inner"><p className="eyebrow">Категории</p><Categories categories={list} /><div className="collection-note"><strong><RefreshCw size={16} />Сбор из ВКонтакте</strong><p>Анонсы собираются из сообществ ТПУ. События с неполными данными проверяет администратор.</p></div></div></aside>
    <main id="main"><Categories categories={list} mobile />{categories.error && <Notice error retry={categories.retry}>Не удалось загрузить категории. {categories.error}</Notice>}
      <Routes><Route path="/" element={<Listing categories={list} today={today} />} /><Route path="/calendar" element={<Listing categories={list} calendar today={today} />} /><Route path="/event/:id" element={<EventPage />} /><Route path="/submit" element={<SubmitPage categories={list} today={today} />} /><Route path="/guide" element={<Guide />} /><Route path="/admin" element={<Notice>Панель администратора пока недоступна. <Link to="/">Вернуться к афише</Link></Notice>} /><Route path="*" element={<Notice>Страница не найдена. <Link to="/">Вернуться к афише</Link></Notice>} /></Routes>
    </main></div><footer className="site-footer"><div><p>Календарь мероприятий Томского политехнического университета</p><nav aria-label="Навигация в подвале"><Link to="/">Афиша</Link><Link to="/guide">Как пользоваться</Link><Link to="/submit">Подать мероприятие</Link></nav></div></footer></>
}
