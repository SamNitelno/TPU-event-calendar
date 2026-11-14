import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import Header from "@/components/calendar/Header";
import Footer from "@/components/calendar/Footer";
import Icon from "@/components/ui/icon";
import LinkifiedText from "@/components/calendar/LinkifiedText";
import { categoryBySlug } from "@/data/events";
import { ApiError, fetchEvent, formatEventDates, formatEventTime } from "@/lib/api";
import { cn } from "@/lib/utils";

const SITE_TITLE = "Календарь ТПУ";

export const Route = createFileRoute("/event/$id")({
  loader: async ({ params }) => {
    if (!/^\d{1,10}$/.test(params.id)) throw notFound();
    try {
      return await fetchEvent(params.id);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 404 || e.status === 422)) throw notFound();
      throw e;
    }
  },
  head: ({ loaderData }) => {
    if (!loaderData) return { meta: [{ title: `Мероприятие не найдено — ${SITE_TITLE}` }, { name: "robots", content: "noindex" }] };
    const title = `${loaderData.title} — ${SITE_TITLE}`;
    const when = formatEventDates(loaderData, true);
    const description = `${when}. ${loaderData.organizer}. ${(loaderData.description ?? "").replace(/\s+/g, " ").slice(0, 140)}`.trim();
    return {
      meta: [
        { title },
        { name: "description", content: description },
        { property: "og:title", content: loaderData.title },
        { property: "og:description", content: description },
        ...(loaderData.image_url ? [{ property: "og:image", content: loaderData.image_url }] : []),
      ],
    };
  },
  component: EventPage,
  notFoundComponent: EventNotFound,
  errorComponent: EventError,
});

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header showControls={false} />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 sm:px-6 lg:py-10">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-primary">
          <Icon name="ArrowLeft" size={16} /> К афише
        </Link>
        {children}
      </main>
      <Footer />
    </div>
  );
}

function Notice({ icon, title, text, children }: { icon: string; title: string; text: string; children?: React.ReactNode }) {
  return (
    <Shell>
      <div className="mt-6 flex flex-col items-center rounded-3xl border border-dashed border-border bg-card px-6 py-16 text-center sm:py-20">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-secondary text-primary">
          <Icon name={icon} size={26} />
        </span>
        <h1 className="mt-4 font-display text-2xl font-bold text-foreground">{title}</h1>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">{text}</p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row">{children}</div>
      </div>
    </Shell>
  );
}

const primaryBtn =
  "flex h-11 items-center justify-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90";

function EventNotFound() {
  return (
    <Notice icon="CalendarX" title="Мероприятие не найдено" text="Возможно, его удалили или ссылка указана с ошибкой.">
      <Link to="/" className={primaryBtn}>
        <Icon name="CalendarDays" size={16} /> Все мероприятия
      </Link>
    </Notice>
  );
}

function EventError({ reset }: { reset: () => void }) {
  return (
    <Notice icon="WifiOff" title="Не удалось загрузить мероприятие" text="Проверьте подключение к интернету и попробуйте ещё раз.">
      <button onClick={reset} className={primaryBtn}>
        <Icon name="RotateCw" size={16} /> Повторить
      </button>
    </Notice>
  );
}

function EventPage() {
  const event = Route.useLoaderData();
  const cat = categoryBySlug(event.category.slug);
  const time = formatEventTime(event);

  const facts = [
    ["CalendarDays", "Дата", formatEventDates(event, true)],
    ["Clock", "Время", time],
    ["MapPin", "Место", event.location],
    ["Users", "Организатор", event.organizer],
  ].filter(([, , v]) => v) as [string, string, string][];

  return (
    <Shell>
      <article className="mt-4 overflow-hidden rounded-3xl border border-border bg-card">
        {event.image_url && (
          <div className="bg-secondary">
            <img
              src={event.image_url}
              alt={event.title}
              className="mx-auto max-h-[460px] w-full object-cover"
              referrerPolicy="no-referrer"
              onError={(e) => ((e.currentTarget.parentElement as HTMLElement).style.display = "none")}
            />
          </div>
        )}

        <div className="relative overflow-hidden bg-secondary px-5 pb-6 pt-6 sm:px-8 sm:pt-8">
          <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-primary/10" />
          <span className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold", cat.chip)}>
            <Icon name={cat.icon} size={13} />
            {event.category.name}
          </span>
          <h1 className="mt-3 break-words font-display text-2xl font-bold leading-tight text-foreground sm:text-4xl">{event.title}</h1>
        </div>

        <div className="grid gap-8 px-5 pb-8 pt-6 sm:px-8 md:grid-cols-[1fr_260px]">
          <div className="order-2 min-w-0 md:order-1">
            {event.description ? (
              <p className="whitespace-pre-line break-words text-[15px] leading-relaxed text-foreground/85 sm:text-base">
                <LinkifiedText text={event.description} />
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">Организатор не добавил описание.</p>
            )}
          </div>

          <aside className="order-1 space-y-5 md:order-2">
            <ul className="grid gap-3">
              {facts.map(([icon, label, value]) => (
                <li key={label} className="flex items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
                    <Icon name={icon} size={17} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-xs text-muted-foreground">{label}</span>
                    <span className="block break-words font-semibold text-foreground">
                      <LinkifiedText text={value} />
                    </span>
                  </span>
                </li>
              ))}
            </ul>

            {event.original_post_link && (
              <a
                href={event.original_post_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary font-semibold text-primary-foreground transition hover:bg-primary/90"
              >
                Подробнее во ВКонтакте
                <Icon name="ExternalLink" size={16} />
              </a>
            )}
          </aside>
        </div>
      </article>
    </Shell>
  );
}
