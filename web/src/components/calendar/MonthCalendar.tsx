import { useEffect, useMemo, useRef, useState } from "react";
import Icon from "@/components/ui/icon";
import { Skeleton } from "@/components/ui/skeleton";
import EventCard from "./EventCard";
import { FeedMessage } from "./EventFeed";
import {
  MONTHS_NOM,
  WEEKDAYS_SHORT,
  categoryBySlug,
  formatLongDate,
  parseDate,
  toIso,
} from "@/data/events";
import { fetchAllEvents, type ApiEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  today: string;
  category?: string;
  query?: string;
  day?: string;
  onDayChange?: (iso: string) => void;
}

export default function MonthCalendar({ today, category, query, day, onDayChange }: Props) {
  const initial = parseDate(day ?? today);
  const [cursor, setCursor] = useState({ y: initial.getFullYear(), m: initial.getMonth() });
  const [selected, setSelected] = useState(day ?? today);
  const listRef = useRef<HTMLDivElement>(null);

  const select = (iso: string, scroll = false) => {
    setSelected(iso);
    onDayChange?.(iso);
    const d = parseDate(iso);
    if (d.getFullYear() !== cursor.y || d.getMonth() !== cursor.m) setCursor({ y: d.getFullYear(), m: d.getMonth() });
    if (scroll && window.matchMedia("(max-width: 1279px)").matches) {
      setTimeout(() => listRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    }
  };

  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [reload, setReload] = useState(0);

  const cells = useMemo(() => {
    const first = new Date(cursor.y, cursor.m, 1);
    const offset = (first.getDay() + 6) % 7;
    const start = new Date(cursor.y, cursor.m, 1 - offset);
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      return { iso: toIso(d), day: d.getDate(), inMonth: d.getMonth() === cursor.m };
    });
  }, [cursor]);

  useEffect(() => {
    const ctrl = new AbortController();
    const from = cells[0].iso;
    const to = cells[cells.length - 1].iso;
    setStatus("loading");
    const timer = setTimeout(() => {
      fetchAllEvents({ date_from: from, date_to: to, category, q: query }, ctrl.signal)
        .then((items) => {
          setEvents(items);
          setStatus("ready");
        })
        .catch((e) => {
          if (!ctrl.signal.aborted) setStatus(e?.name === "AbortError" ? "loading" : "error");
        });
    }, query ? 350 : 0);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [cells, category, query, reload]);

  const byDate = useMemo(() => {
    const map = new Map<string, ApiEvent[]>();
    events.forEach((e) => {
      const start = parseDate(e.event_date);
      const end = parseDate(e.end_date && e.end_date > e.event_date ? e.end_date : e.event_date);
      for (let d = start, n = 0; d <= end && n < 62; d = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1), n++) {
        const iso = toIso(d);
        map.set(iso, [...(map.get(iso) ?? []), e]);
      }
    });
    return map;
  }, [events]);

  const shift = (n: number) => {
    const d = new Date(cursor.y, cursor.m + n, 1);
    const t = parseDate(today);
    const sameAsToday = d.getFullYear() === t.getFullYear() && d.getMonth() === t.getMonth();
    select(sameAsToday ? today : toIso(d));
  };

  const dayEvents = byDate.get(selected) ?? [];

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="rounded-3xl border border-border bg-card p-4 sm:p-6">
        <div className="mb-5 flex items-center justify-between gap-3">
          <h2 className="font-display text-xl font-bold text-foreground sm:text-2xl">
            {MONTHS_NOM[cursor.m]} <span className="text-muted-foreground">{cursor.y}</span>
          </h2>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => select(today)}
              className="mr-1 hidden rounded-full border border-border px-3 py-1.5 text-sm font-medium text-foreground transition hover:border-primary hover:text-primary sm:block"
            >
              Сегодня
            </button>
            <button onClick={() => shift(-1)} aria-label="Предыдущий месяц" className="grid h-9 w-9 place-items-center rounded-full border border-border text-foreground transition hover:border-primary hover:text-primary">
              <Icon name="ChevronLeft" size={18} />
            </button>
            <button onClick={() => shift(1)} aria-label="Следующий месяц" className="grid h-9 w-9 place-items-center rounded-full border border-border text-foreground transition hover:border-primary hover:text-primary">
              <Icon name="ChevronRight" size={18} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-7 gap-1 sm:gap-2">
          {WEEKDAYS_SHORT.map((w, i) => (
            <div key={w} className={cn("pb-2 text-center text-xs font-semibold uppercase tracking-wide", i > 4 ? "text-primary" : "text-muted-foreground")}>
              {w}
            </div>
          ))}
          {cells.map((c) => {
            const list = byDate.get(c.iso) ?? [];
            const isSel = c.iso === selected;
            const isToday = c.iso === today;
            return (
              <button
                key={c.iso}
                onClick={() => select(c.iso, true)}
                aria-label={`${formatLongDate(c.iso)}${list.length ? `, мероприятий: ${list.length}` : ""}`}
                aria-pressed={isSel}
                className={cn(
                  "relative flex aspect-square flex-col items-center justify-start rounded-xl border p-1 text-sm transition-all sm:aspect-[1.15] sm:items-start sm:p-2",
                  isSel
                    ? "border-primary bg-primary text-primary-foreground shadow-[0_10px_24px_-12px_hsl(var(--primary))]"
                    : list.length
                      ? "border-border bg-background hover:border-primary/60"
                      : "border-transparent hover:bg-secondary",
                  !c.inMonth && !isSel && "opacity-40",
                )}
              >
                <span
                  className={cn(
                    "grid h-7 w-7 place-items-center rounded-full font-semibold tabular-nums",
                    isToday && !isSel && "bg-highlight text-highlight-foreground",
                  )}
                >
                  {c.day}
                </span>
                {list.length > 0 && (
                  <>
                    <span className="mt-auto flex gap-0.5 sm:hidden">
                      {list.slice(0, 3).map((e) => (
                        <span key={e.id} className={cn("h-1.5 w-1.5 rounded-full", isSel ? "bg-primary-foreground" : "bg-primary")} />
                      ))}
                    </span>
                    <span className="mt-auto hidden w-full space-y-1 sm:block">
                      {list.slice(0, 2).map((e) => (
                        <span
                          key={e.id}
                          className={cn(
                            "block truncate rounded-md px-1.5 py-0.5 text-left text-[11px] font-medium",
                            isSel ? "bg-primary-foreground/20 text-primary-foreground" : categoryBySlug(e.category.slug).chip,
                          )}
                        >
                          {e.title}
                        </span>
                      ))}
                      {list.length > 2 && (
                        <span className={cn("block text-left text-[11px]", isSel ? "text-primary-foreground/85" : "text-muted-foreground")}>
                          ещё {list.length - 2}
                        </span>
                      )}
                    </span>
                  </>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="xl:sticky xl:top-24 xl:self-start">
        <div ref={listRef} key={selected} className="scroll-mt-24 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">Мероприятия дня</p>
          <h3 className="mt-1 font-display text-xl font-bold capitalize text-foreground">{formatLongDate(selected)}</h3>
          <div className="mt-4 space-y-3">
            {status === "loading" ? (
              [0, 1].map((i) => <Skeleton key={i} className="h-[76px] w-full rounded-2xl" />)
            ) : status === "error" ? (
              <FeedMessage
                icon="WifiOff"
                title="Не удалось загрузить"
                text="Проверьте подключение и попробуйте ещё раз."
                action={{ label: "Повторить", onClick: () => setReload((r) => r + 1) }}
              />
            ) : dayEvents.length ? (
              dayEvents.map((e) => <EventCard key={e.id} event={e} compact />)
            ) : (
              <div className="rounded-2xl border border-dashed border-border bg-card px-5 py-10 text-center">
                <Icon name="CalendarX" size={26} className="mx-auto text-muted-foreground" />
                <p className="mt-3 text-sm text-muted-foreground">В этот день мероприятий нет. Выберите дату с отметкой.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
