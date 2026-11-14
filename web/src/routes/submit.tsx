import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import Header from "@/components/calendar/Header";
import Footer from "@/components/calendar/Footer";
import Icon from "@/components/ui/icon";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { CATEGORIES, categoryById, type CategoryId } from "@/data/events";
import { cn } from "@/lib/utils";
import { ApiError, createSubmission } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/submit")({
  head: () => ({
    meta: [
      { title: "Подать мероприятие — Календарь ТПУ" },
      { name: "description", content: "Форма заявки для студенческих организаций ТПУ: мероприятие появится в календаре после проверки администратором." },
    ],
  }),
  component: SubmitPage,
});

const empty = {
  title: "",
  organizer: "",
  category: "" as CategoryId | "",
  date: "",
  timeStart: "",
  timeEnd: "",
  dateEnd: "",
  place: "",
  description: "",
  contact: "",
};

type Form = typeof empty;
type Errors = Partial<Record<keyof Form, string>>;

const tomskToday = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);

function validate(f: Form): Errors {
  const e: Errors = {};
  if (f.title.trim().length < 3) e.title = "Название — не короче 3 символов";
  else if (f.title.trim().length > 300) e.title = "Название — не длиннее 300 символов";
  if (f.organizer.trim().length < 2) e.organizer = "Укажите организацию";
  else if (f.organizer.trim().length > 200) e.organizer = "Не длиннее 200 символов";
  if (!f.category) e.category = "Выберите категорию";
  if (!f.date) e.date = "Укажите дату";
  else if (f.date < tomskToday()) e.date = "Дата уже прошла";
  if (f.dateEnd && f.date && f.dateEnd < f.date) e.dateEnd = "Не раньше даты начала";
  const sameDay = !f.dateEnd || f.dateEnd === f.date;
  if (f.timeEnd && !f.timeStart) e.timeStart = "Укажите и время начала";
  if (sameDay && f.timeEnd && f.timeStart && f.timeEnd <= f.timeStart) e.timeEnd = "Позже начала";
  if (f.place.trim().length > 300) e.place = "Не длиннее 300 символов";
  if (f.description.trim().length > 5000) e.description = "Не длиннее 5000 символов";
  if (f.contact.trim().length < 3) e.contact = "Оставьте почту или телефон для связи";
  else if (f.contact.trim().length > 200) e.contact = "Не длиннее 200 символов";
  return e;
}

const API_FIELDS: Record<string, keyof Form> = {
  title: "title",
  organizer: "organizer",
  category: "category",
  event_date: "date",
  end_date: "dateEnd",
  start_time: "timeStart",
  end_time: "timeEnd",
  location: "place",
  description: "description",
  contact: "contact",
};

function serverErrors(e: ApiError): Errors {
  const out: Errors = {};
  if (e.message.includes("прошла")) out.date = "Дата уже прошла";
  if (e.message.includes("категория")) out.category = "Выберите категорию из списка";
  e.fields.forEach((f) => {
    const key = API_FIELDS[f.field];
    if (key) out[key] = f.type.includes("too_short") ? "Слишком коротко" : f.type.includes("too_long") ? "Слишком длинно" : "Проверьте значение";
    else if (f.msg.includes("end_date")) out.dateEnd = "Не раньше даты начала";
  });
  return out;
}

function Field({ label, error, children, className }: { label: string; error?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label className="text-sm font-semibold text-foreground">{label}</Label>
      {children}
      {error && <p className="text-xs font-medium text-destructive">{error}</p>}
    </div>
  );
}

function SubmitPage() {
  const [form, setForm] = useState<Form>(empty);
  const [errors, setErrors] = useState<Errors>({});
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);

  const set = <K extends keyof Form>(k: K, v: Form[K]) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (errors[k]) setErrors((er) => ({ ...er, [k]: undefined }));
  };

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    const er = validate(form);
    setErrors(er);
    if (Object.keys(er).length || sending) return;
    setSending(true);
    try {
      await createSubmission({
        title: form.title.trim(),
        organizer: form.organizer.trim(),
        category: categoryById(form.category as CategoryId).slug,
        event_date: form.date,
        end_date: form.dateEnd && form.dateEnd !== form.date ? form.dateEnd : null,
        start_time: form.timeStart || null,
        end_time: form.timeEnd || null,
        location: form.place.trim() || null,
        description: form.description.trim() || null,
        contact: form.contact.trim(),
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        const fe = serverErrors(e);
        setErrors(fe);
        toast.error("Заявка не отправлена", { description: "Исправьте поля, отмеченные красным" });
      } else {
        toast.error("Заявка не отправлена", {
          description: e instanceof ApiError && e.status === 0 ? "Нет связи с сервером, попробуйте ещё раз" : "Сервер не ответил, попробуйте ещё раз",
        });
      }
      return;
    } finally {
      setSending(false);
    }
    setSent(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
    setForm(empty);
  };

  const inputCls = (k: keyof Form) => cn("h-11 rounded-xl bg-background", errors[k] && "border-destructive");

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header showControls={false} />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-primary">
          <Icon name="ArrowLeft" size={16} /> К афише
        </Link>

        <div className="mt-4 grid gap-8 lg:grid-cols-[1fr_300px]">
          <div>
            <h1 className="font-display text-3xl font-bold leading-tight text-foreground sm:text-4xl">Подать мероприятие</h1>
            <p className="mt-3 max-w-xl text-muted-foreground">
              Заявка от студенческой организации. Мероприятие появится в общем календаре только после проверки администратором.
            </p>

            {sent ? (
              <div className="mt-8 animate-in fade-in zoom-in-95 rounded-3xl border border-primary/30 bg-accent p-8 text-center duration-500">
                <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary text-primary-foreground">
                  <Icon name="Check" size={28} />
                </span>
                <h2 className="mt-4 font-display text-xl font-bold text-foreground">Заявка отправлена на проверку</h2>
                <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
                  Администратор проверит данные и опубликует мероприятие. Если что-то нужно уточнить, с вами свяжутся по указанному контакту.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-3">
                  <button onClick={() => setSent(false)} className="h-11 rounded-xl border border-border bg-card px-5 text-sm font-semibold text-foreground hover:border-primary">
                    Подать ещё одно
                  </button>
                  <Link to="/" className="flex h-11 items-center rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
                    Вернуться к афише
                  </Link>
                </div>
              </div>
            ) : (
              <form onSubmit={submit} noValidate className="mt-8 grid gap-5 rounded-3xl border border-border bg-card p-5 sm:grid-cols-2 sm:p-8">
                <Field label="Название мероприятия *" error={errors.title} className="sm:col-span-2">
                  <Input value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="Например, Хакатон «Энергия кода»" className={inputCls("title")} />
                </Field>
                <Field label="Организация *" error={errors.organizer}>
                  <Input value={form.organizer} onChange={(e) => set("organizer", e.target.value)} placeholder="Клуб, совет, кафедра" className={inputCls("organizer")} />
                </Field>
                <Field label="Контакт для связи *" error={errors.contact}>
                  <Input value={form.contact} onChange={(e) => set("contact", e.target.value)} placeholder="почта или телефон" className={inputCls("contact")} />
                </Field>

                <Field label="Категория *" error={errors.category} className="sm:col-span-2">
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map((c) => (
                      <button
                        type="button"
                        key={c.id}
                        onClick={() => set("category", c.id)}
                        className={cn(
                          "flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-sm font-medium transition",
                          form.category === c.id
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border bg-background text-foreground hover:border-primary/50",
                        )}
                      >
                        <Icon name={c.icon} size={14} />
                        {c.label}
                      </button>
                    ))}
                  </div>
                </Field>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Дата *" error={errors.date}>
                    <Input type="date" min={tomskToday()} value={form.date} onChange={(e) => set("date", e.target.value)} className={inputCls("date")} />
                  </Field>
                  <Field label="Дата окончания" error={errors.dateEnd}>
                    <Input type="date" min={form.date || tomskToday()} value={form.dateEnd} onChange={(e) => set("dateEnd", e.target.value)} className={inputCls("dateEnd")} />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Начало" error={errors.timeStart}>
                    <Input type="time" value={form.timeStart} onChange={(e) => set("timeStart", e.target.value)} className={inputCls("timeStart")} />
                  </Field>
                  <Field label="Окончание" error={errors.timeEnd}>
                    <Input type="time" value={form.timeEnd} onChange={(e) => set("timeEnd", e.target.value)} className={inputCls("timeEnd")} />
                  </Field>
                </div>

                <Field label="Место проведения" error={errors.place} className="sm:col-span-2">
                  <Input value={form.place} onChange={(e) => set("place", e.target.value)} placeholder="Корпус, аудитория" className={inputCls("place")} />
                </Field>
                <Field label="Описание" error={errors.description} className="sm:col-span-2">
                  <Textarea
                    value={form.description}
                    onChange={(e) => set("description", e.target.value)}
                    rows={4}
                    placeholder="Коротко: о чём мероприятие и для кого"
                    className={cn("rounded-xl bg-background", errors.description && "border-destructive")}
                  />
                </Field>

                <button type="submit" disabled={sending} className="flex h-12 items-center justify-center gap-2 rounded-xl bg-primary font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:opacity-60 sm:col-span-2">
                  <Icon name="Send" size={17} />
                  {sending ? "Отправляю…" : "Отправить на проверку"}
                </button>
              </form>
            )}
          </div>

          <aside className="space-y-4 lg:pt-24">
            {[
              ["FileText", "Заявка", "Заполните форму. Поля со звёздочкой обязательны, остальные помогут найти мероприятие."],
              ["ShieldCheck", "Проверка", "Администратор проверяет данные и одобряет или отклоняет заявку."],
              ["CalendarCheck", "Публикация", "После одобрения событие появляется в ленте и календаре."],
            ].map(([icon, t, d], i) => (
              <div key={t} className="flex gap-3 rounded-2xl border border-border bg-card p-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
                  <Icon name={icon} size={17} />
                </span>
                <div>
                  <p className="text-sm font-bold text-foreground">
                    {i + 1}. {t}
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{d}</p>
                </div>
              </div>
            ))}
          </aside>
        </div>
      </main>
      <Footer />
    </div>
  );
}
