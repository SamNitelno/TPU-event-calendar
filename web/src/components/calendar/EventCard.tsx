import { Link } from "@tanstack/react-router";
import Icon from "@/components/ui/icon";
import { categoryBySlug } from "@/data/events";
import { formatEventDates, formatEventTime, isMultiDay, type ApiEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  event: ApiEvent;
  compact?: boolean;
}

export default function EventCard({ event, compact }: Props) {
  const cat = categoryBySlug(event.category.slug);
  const time = formatEventTime(event);
  const meta = [isMultiDay(event) ? formatEventDates(event) : null, time, event.location].filter(Boolean) as string[];

  return (
    <Link
      to="/event/$id"
      params={{ id: String(event.id) }}
      className={cn(
        "group flex w-full items-center gap-4 rounded-2xl border border-border bg-card text-left transition-all duration-300 animate-in fade-in hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-[0_14px_30px_-18px_hsl(var(--foreground)/0.35)]",
        compact ? "p-3.5" : "p-4 sm:p-5",
      )}
    >
      <span className={cn("grid shrink-0 place-items-center rounded-xl", cat.chip, compact ? "h-10 w-10" : "h-11 w-11")}>
        <Icon name={cat.icon} size={compact ? 18 : 20} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="truncate">{event.organizer}</span>
          <span className={cn("hidden shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold sm:inline", cat.chip)}>
            {event.category.name}
          </span>
        </span>
        <span className="mt-0.5 block break-words font-bold leading-snug text-foreground sm:text-[17px]">{event.title}</span>
        {meta.length > 0 && (
          <span className="mt-1 flex flex-wrap items-center gap-x-1.5 text-sm text-muted-foreground">
            {meta.map((m, i) => (
              <span key={m} className="flex min-w-0 items-center gap-1.5">
                {i > 0 && <span aria-hidden>·</span>}
                <span className="truncate tabular-nums">{m}</span>
              </span>
            ))}
          </span>
        )}
      </span>
      <Icon
        name="ChevronRight"
        size={18}
        className="shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary"
      />
    </Link>
  );
}
