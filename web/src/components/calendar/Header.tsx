import { Link } from "@tanstack/react-router";
import Icon from "@/components/ui/icon";
import { cn } from "@/lib/utils";

export type ViewMode = "feed" | "calendar";

interface HeaderProps {
  query?: string;
  onQueryChange?: (v: string) => void;
  view?: ViewMode;
  onViewChange?: (v: ViewMode) => void;
  showControls?: boolean;
}

export function Logo() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-3">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground shadow-[0_6px_16px_-6px_hsl(var(--primary)/0.6)]">
        <Icon name="CalendarDays" size={20} />
      </span>
      <span className="leading-tight">
        <span className="block font-display text-[15px] font-bold tracking-tight text-foreground sm:text-[17px]">
          Календарь ТПУ
        </span>
        <span className="hidden text-[11px] text-muted-foreground sm:block">Все мероприятия университета</span>
      </span>
    </Link>
  );
}

export function ViewToggle({ view, onChange }: { view: ViewMode; onChange: (v: ViewMode) => void }) {
  return (
    <div className="flex shrink-0 rounded-xl bg-secondary p-1" role="tablist" aria-label="Режим просмотра">
      {(
        [
          ["feed", "Лента", "List"],
          ["calendar", "Календарь", "CalendarDays"],
        ] as const
      ).map(([id, label, icon]) => (
        <button
          key={id}
          role="tab"
          aria-selected={view === id}
          onClick={() => onChange(id)}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold transition-all sm:px-4",
            view === id
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          <Icon name={icon} size={15} className="sm:hidden" />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}

export default function Header({ query = "", onQueryChange, view = "feed", onViewChange, showControls = true }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:flex-nowrap lg:gap-6 lg:px-8 lg:py-4">
        <Logo />

        {showControls && (
          <label className="order-3 flex h-11 w-full items-center gap-2.5 rounded-full border border-border bg-background px-4 transition focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15 lg:order-none lg:flex-1">
            <Icon name="Search" size={17} className="shrink-0 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => onQueryChange?.(e.target.value)}
              placeholder="Поиск: хакатон, волейбол, лекция…"
              className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
            {query && (
              <button onClick={() => onQueryChange?.("")} aria-label="Очистить поиск" className="text-muted-foreground hover:text-foreground">
                <Icon name="X" size={16} />
              </button>
            )}
          </label>
        )}

        <div className="ml-auto flex items-center gap-2 lg:ml-0 lg:gap-3">
          {showControls && onViewChange && (
            <div className="hidden sm:block">
              <ViewToggle view={view} onChange={onViewChange} />
            </div>
          )}
          <Link
            to="/submit"
            className="flex h-10 items-center gap-2 rounded-full border border-border bg-card px-3 text-sm font-semibold text-foreground transition hover:border-primary hover:text-primary sm:h-11 sm:px-4"
          >
            <Icon name="Plus" size={16} />
            <span className="hidden md:inline">Подать мероприятие</span>
          </Link>
          <Link
            to="/admin"
            aria-label="Вход для администратора"
            className="grid h-10 w-10 place-items-center rounded-full text-muted-foreground transition hover:bg-secondary hover:text-foreground sm:h-11 sm:w-11"
          >
            <Icon name="ShieldCheck" size={18} />
          </Link>
        </div>
      </div>
    </header>
  );
}
