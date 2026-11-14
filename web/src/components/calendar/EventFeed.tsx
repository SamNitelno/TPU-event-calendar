import { useMemo } from "react";
import Icon from "@/components/ui/icon";
import { Skeleton } from "@/components/ui/skeleton";
import EventCard from "./EventCard";
import { MONTHS_GEN, WEEKDAYS, parseDate, toIso } from "@/data/events";
import type { ApiEvent } from "@/lib/api";

interface Props {
  events: ApiEvent[];
  today: string;
  total: number;
  status: "loading" | "ready" | "error";
  loadingMore: boolean;
  moreError: boolean;
  filtered: boolean;
  onMore: () => void;
  onRetry: () => void;
}

const addDays = (iso: string, n: number) => {
  const d = parseDate(iso);
  d.setDate(d.getDate() + n);
  return toIso(d);
};

export function FeedSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Загрузка мероприятий">
      {[0, 1].map((g) => (
        <div key={g} className="grid gap-3 sm:grid-cols-[150px_1fr] sm:gap-6">
          <div className="flex items-baseline gap-3 sm:block">
            <Skeleton className="h-10 w-12 sm:h-12" />
            <Skeleton className="h-4 w-28 sm:mt-3" />
          </div>
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4 sm:p-5">
                <Skeleton className="h-11 w-11 shrink-0 rounded-xl" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3 w-1/3" />
                  <Skeleton className="h-4 w-4/5" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function FeedMessage({
  icon,
  title,
  text,
  action,
}: {
  icon: string;
  title: string;
  text?: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="flex flex-col items-center rounded-3xl border border-dashed border-border bg-card px-6 py-16 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-2xl bg-secondary text-primary">
        <Icon name={icon} size={26} />
      </span>
      <p className="mt-4 font-display text-lg font-semibold text-foreground">{title}</p>
      {text && <p className="mt-1 max-w-xs text-sm text-muted-foreground">{text}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 flex h-11 items-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
        >
          <Icon name="RotateCw" size={16} />
          {action.label}
        </button>
      )}
    </div>
  );
}

export default function EventFeed({ events, today, total, status, loadingMore, moreError, filtered, onMore, onRetry }: Props) {
  const groups = useMemo(() => {
    const map = new Map<string, ApiEvent[]>();
    events.forEach((e) => {
      const key = e.event_date < today ? today : e.event_date;
      map.set(key, [...(map.get(key) ?? []), e]);
    });
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [events, today]);

  if (status === "loading") return <FeedSkeleton />;

  if (status === "error") {
    return (
      <FeedMessage
        icon="WifiOff"
        title="Не удалось загрузить мероприятия"
        text="Проверьте подключение к интернету и попробуйте ещё раз."
        action={{ label: "Повторить", onClick: onRetry }}
      />
    );
  }

  if (groups.length === 0) {
    return filtered ? (
      <FeedMessage icon="SearchX" title="Ничего не нашлось" text="Попробуйте другое слово или выберите другую категорию." />
    ) : (
      <FeedMessage icon="CalendarX" title="Пока нет мероприятий" text="Загляните позже — новые события появляются каждый день." />
    );
  }

  const tomorrow = addDays(today, 1);
  const hasMore = events.length < total;

  return (
    <div className="space-y-8 sm:space-y-10">
      {groups.map(([date, list]) => {
        const d = parseDate(date);
        const badge = date === today ? "Сегодня" : date === tomorrow ? "Завтра" : null;
        return (
          <section key={date} className="grid gap-3 sm:grid-cols-[150px_1fr] sm:gap-6">
            <div className="flex items-baseline gap-3 sm:block">
              <div className="font-display text-4xl font-bold leading-none text-primary sm:text-5xl">{d.getDate()}</div>
              <div className="sm:mt-2">
                <div className="text-sm capitalize text-foreground">
                  {MONTHS_GEN[d.getMonth()]}, {WEEKDAYS[d.getDay()]}
                </div>
                {badge && (
                  <span className="mt-1.5 inline-block rounded-md bg-highlight px-2 py-0.5 text-xs font-bold text-highlight-foreground">
                    {badge}
                  </span>
                )}
              </div>
            </div>
            <div className="min-w-0 space-y-3">
              {list.map((e) => (
                <EventCard key={e.id} event={e} />
              ))}
            </div>
          </section>
        );
      })}

      {hasMore && (
        <div className="flex flex-col items-center gap-2 pt-2">
          <button
            onClick={onMore}
            disabled={loadingMore}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border bg-card px-6 font-semibold text-foreground transition hover:border-primary hover:text-primary disabled:opacity-60 sm:w-auto"
          >
            <Icon name={loadingMore ? "Loader2" : "ChevronDown"} size={18} className={loadingMore ? "animate-spin" : undefined} />
            {loadingMore ? "Загружаю…" : "Показать ещё"}
          </button>
          {moreError && <p className="text-sm font-medium text-destructive">Не удалось загрузить, попробуйте ещё раз</p>}
          <p className="text-xs text-muted-foreground">
            Показано {events.length} из {total}
          </p>
        </div>
      )}
    </div>
  );
}
