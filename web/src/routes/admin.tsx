import { useEffect, useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Logo } from "@/components/calendar/Header";
import EditEventDialog from "@/components/admin/EditEventDialog";
import Icon from "@/components/ui/icon";
import { Input } from "@/components/ui/input";
import { categoryById, formatLongDate, formatTime, type Submission, type TpuEvent } from "@/data/events";
import { useEvents } from "@/lib/events-store";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { adminCheck, adminLogin, adminLogout } from "@/lib/admin-auth";

export const Route = createFileRoute("/admin")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Панель администратора — Календарь ТПУ" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AdminPage,
});

function AdminPage() {
  const [authed, setAuthed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    adminCheck()
      .then((r) => setAuthed(r.authed))
      .catch(() => setAuthed(false))
      .finally(() => setReady(true));
  }, []);

  if (!ready) return null;
  return authed ? (
    <Dashboard
      onLogout={() => {
        adminLogout().finally(() => setAuthed(false));
      }}
    />
  ) : (
    <Login
      onSuccess={() => setAuthed(true)}
    />
  );
}

function Login({ onSuccess }: { onSuccess: () => void }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <div className="w-full max-w-sm animate-in fade-in slide-in-from-bottom-3 duration-500">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!key.trim() || loading) return;
            setLoading(true);
            try {
              const r = await adminLogin({ data: { key } });
              if (r.ok) onSuccess();
              else setError(r.error);
            } catch {
              setError("Не удалось выполнить вход, попробуйте ещё раз");
            } finally {
              setLoading(false);
            }
          }}
          className="rounded-3xl border border-border bg-card p-6 shadow-[0_20px_50px_-30px_hsl(var(--foreground)/0.4)] sm:p-8"
        >
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-accent text-accent-foreground">
            <Icon name="LockKeyhole" size={22} />
          </span>
          <h1 className="mt-4 font-display text-2xl font-bold text-foreground">Вход для администратора</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">Проверка заявок и управление мероприятиями.</p>
          <div className="relative mt-6">
            <Input
              type={show ? "text" : "password"}
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setError("");
              }}
              placeholder="Ключ доступа"
              className={cn("h-12 rounded-xl pr-11", error && "border-destructive")}
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              aria-label="Показать ключ"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <Icon name={show ? "EyeOff" : "Eye"} size={18} />
            </button>
          </div>
          {error && <p className="mt-2 text-xs font-medium text-destructive">{error}</p>}
          <button type="submit" disabled={loading} className="mt-5 h-12 w-full rounded-xl bg-primary font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60">
            {loading ? "Проверяю…" : "Войти"}
          </button>
        </form>
        <Link to="/" className="mt-6 flex items-center justify-center gap-1.5 text-sm text-muted-foreground hover:text-primary">
          <Icon name="ArrowLeft" size={15} /> Вернуться к афише
        </Link>
      </div>
    </div>
  );
}

type Tab = "pending" | "events" | "history";

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const { submissions, events, today, approveSubmission, rejectSubmission, updateEvent, deleteEvent, resetDemo } = useEvents();
  const [tab, setTab] = useState<Tab>("pending");
  const [editing, setEditing] = useState<TpuEvent | null>(null);
  const [search, setSearch] = useState("");

  const pending = submissions.filter((s) => s.status === "pending");
  const history = submissions.filter((s) => s.status !== "pending");
  const filteredEvents = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? events.filter((e) => `${e.title} ${e.organizer}`.toLowerCase().includes(q)) : events;
  }, [events, search]);

  const stats = [
    ["Inbox", "На проверке", pending.length],
    ["CalendarCheck", "Опубликовано", events.length],
    ["CalendarClock", "Предстоит", events.filter((e) => e.date >= today).length],
  ] as const;

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-card/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Logo />
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-full bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground sm:flex">
              <Icon name="ShieldCheck" size={14} /> Администратор
            </span>
            <button onClick={onLogout} className="flex h-10 items-center gap-1.5 rounded-full border border-border px-4 text-sm font-semibold hover:border-primary hover:text-primary">
              <Icon name="LogOut" size={15} /> Выйти
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <h1 className="font-display text-3xl font-bold text-foreground sm:text-4xl">Панель администратора</h1>

        <div className="mt-6 grid grid-cols-3 gap-3">
          {stats.map(([icon, label, n]) => (
            <div key={label} className="rounded-2xl border border-border bg-card p-4">
              <Icon name={icon} size={18} className="text-primary" />
              <div className="mt-2 font-display text-2xl font-bold text-foreground sm:text-3xl">{n}</div>
              <div className="text-xs text-muted-foreground sm:text-sm">{label}</div>
            </div>
          ))}
        </div>

        <div className="no-scrollbar mt-8 flex gap-1 overflow-x-auto rounded-xl bg-secondary p-1 sm:inline-flex">
          {(
            [
              ["pending", `Заявки (${pending.length})`],
              ["events", "Все мероприятия"],
              ["history", "История"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                "shrink-0 rounded-lg px-4 py-2 text-sm font-semibold transition",
                tab === id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="mt-6">
          {tab === "pending" &&
            (pending.length ? (
              <div className="grid gap-4">
                {pending.map((s) => (
                  <SubmissionCard
                    key={s.id}
                    s={s}
                    onApprove={() => {
                      approveSubmission(s.id);
                      toast.success("Мероприятие опубликовано", { description: s.title });
                    }}
                    onReject={(reason) => {
                      rejectSubmission(s.id, reason);
                      toast("Заявка отклонена", { description: s.title });
                    }}
                  />
                ))}
              </div>
            ) : (
              <Empty icon="Inbox" text="Новых заявок нет. Всё проверено." />
            ))}

          {tab === "events" && (
            <div>
              <div className="mb-4 flex h-11 max-w-md items-center gap-2 rounded-full border border-border bg-card px-4">
                <Icon name="Search" size={16} className="text-muted-foreground" />
                <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Найти мероприятие" className="flex-1 bg-transparent text-sm outline-none" />
              </div>
              <div className="overflow-hidden rounded-2xl border border-border bg-card">
                {filteredEvents.map((e) => {
                  const cat = categoryById(e.category);
                  return (
                    <div key={e.id} className="flex items-center gap-3 border-b border-border p-3 last:border-b-0 sm:p-4">
                      <span className={cn("hidden h-10 w-10 shrink-0 place-items-center rounded-xl sm:grid", cat.chip)}>
                        <Icon name={cat.icon} size={18} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold text-foreground">{e.title}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {formatLongDate(e.date)} · {formatTime(e)} · {e.organizer}
                        </p>
                      </div>
                      <button onClick={() => setEditing(e)} aria-label="Редактировать" className="grid h-9 w-9 place-items-center rounded-lg text-muted-foreground hover:bg-secondary hover:text-primary">
                        <Icon name="Pencil" size={16} />
                      </button>
                      <button
                        onClick={() => {
                          if (window.confirm(`Удалить «${e.title}»?`)) {
                            deleteEvent(e.id);
                            toast("Мероприятие удалено");
                          }
                        }}
                        aria-label="Удалить"
                        className="grid h-9 w-9 place-items-center rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Icon name="Trash2" size={16} />
                      </button>
                    </div>
                  );
                })}
                {!filteredEvents.length && <p className="p-6 text-center text-sm text-muted-foreground">Ничего не найдено</p>}
              </div>
            </div>
          )}

          {tab === "history" &&
            (history.length ? (
              <div className="overflow-hidden rounded-2xl border border-border bg-card">
                {history.map((s) => (
                  <div key={s.id} className="flex items-center gap-3 border-b border-border p-4 last:border-b-0">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-1 text-xs font-semibold",
                        s.status === "approved" ? "bg-accent text-accent-foreground" : "bg-destructive/10 text-destructive",
                      )}
                    >
                      {s.status === "approved" ? "Одобрено" : "Отклонено"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-foreground">{s.title}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {s.organizer}
                        {s.rejectReason ? ` · Причина: ${s.rejectReason}` : ""}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Empty icon="History" text="Здесь появятся одобренные и отклонённые заявки." />
            ))}
        </div>

        <button onClick={() => { resetDemo(); toast("Демо-данные восстановлены"); }} className="mt-10 text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
          Сбросить демо-данные
        </button>
      </main>

      <EditEventDialog
        event={editing}
        onClose={() => setEditing(null)}
        onSave={(e) => {
          updateEvent(e);
          setEditing(null);
          toast.success("Изменения сохранены");
        }}
      />
    </div>
  );
}

function Empty({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-border bg-card px-6 py-14 text-center">
      <Icon name={icon} size={28} className="mx-auto text-muted-foreground" />
      <p className="mt-3 text-sm text-muted-foreground">{text}</p>
    </div>
  );
}

function SubmissionCard({ s, onApprove, onReject }: { s: Submission; onApprove: () => void; onReject: (reason?: string) => void }) {
  const cat = categoryById(s.category);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 rounded-2xl border border-border bg-card p-5 duration-300">
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold", cat.chip)}>
          <Icon name={cat.icon} size={12} /> {cat.label}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-muted-foreground">
          <Icon name={s.source === "vk" ? "RefreshCw" : "FileText"} size={12} />
          {s.source === "vk" ? "Собрано из ВКонтакте" : "Заявка через форму"}
        </span>
        <span className="ml-auto text-xs text-muted-foreground">получено {formatLongDate(s.submittedAt).split(",")[0]}</span>
      </div>
      <h3 className="mt-3 text-lg font-bold text-foreground">{s.title}</h3>
      <p className="text-sm text-muted-foreground">{s.organizer} · {s.contact}</p>
      <div className="mt-3 grid gap-1 text-sm text-foreground sm:grid-cols-3">
        <span className="flex items-center gap-1.5"><Icon name="CalendarDays" size={14} className="text-primary" />{formatLongDate(s.date)}</span>
        <span className="flex items-center gap-1.5"><Icon name="Clock" size={14} className="text-primary" />{formatTime(s)}</span>
        <span className="flex items-center gap-1.5"><Icon name="MapPin" size={14} className="text-primary" />{s.place}</span>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-foreground/80">{s.description}</p>
      <a href={s.vkUrl} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
        Пост ВКонтакте <Icon name="ExternalLink" size={13} />
      </a>

      {rejecting ? (
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Причина отклонения (необязательно)" className="h-11 rounded-xl" autoFocus />
          <div className="flex gap-2">
            <button onClick={() => setRejecting(false)} className="h-11 rounded-xl border border-border px-4 text-sm font-semibold">Отмена</button>
            <button onClick={() => onReject(reason.trim() || undefined)} className="h-11 rounded-xl bg-destructive px-4 text-sm font-semibold text-destructive-foreground">Отклонить</button>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex gap-2">
          <button onClick={onApprove} className="flex h-11 flex-1 items-center justify-center gap-1.5 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 sm:flex-none">
            <Icon name="Check" size={16} /> Одобрить
          </button>
          <button onClick={() => setRejecting(true)} className="flex h-11 flex-1 items-center justify-center gap-1.5 rounded-xl border border-border px-5 text-sm font-semibold text-foreground hover:border-destructive hover:text-destructive sm:flex-none">
            <Icon name="X" size={16} /> Отклонить
          </button>
        </div>
      )}
    </div>
  );
}
