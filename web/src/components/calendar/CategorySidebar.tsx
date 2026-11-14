import Icon from "@/components/ui/icon";
import { CATEGORIES, type CategoryId } from "@/data/events";
import { cn } from "@/lib/utils";

interface Props {
  active: CategoryId | "all";
  onChange: (c: CategoryId | "all") => void;
  counts: Record<string, number>;
  total: number;
}

const items = [{ id: "all" as const, label: "Все", icon: "LayoutGrid" }, ...CATEGORIES];

export function CategoryChips({ active, onChange, counts, total }: Props) {
  return (
    <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:hidden">
      {items.map((c) => {
        const n = c.id === "all" ? total : counts[c.id] ?? 0;
        const isActive = active === c.id;
        return (
          <button
            key={c.id}
            onClick={() => onChange(c.id)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-medium transition",
              isActive
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-foreground hover:border-primary/50",
            )}
          >
            {c.label}
            <span className={cn("text-xs", isActive ? "text-primary-foreground/80" : "text-muted-foreground")}>{n}</span>
          </button>
        );
      })}
    </div>
  );
}

export default function CategorySidebar({ active, onChange, counts, total }: Props) {
  return (
    <aside className="hidden border-r border-border lg:block">
      <div className="sticky top-[73px] px-6 py-8">
        <p className="mb-3 px-1 text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">Категории</p>
        <nav className="flex flex-col gap-1">
          {items.map((c, i) => {
            const n = c.id === "all" ? total : counts[c.id] ?? 0;
            const isActive = active === c.id;
            return (
              <button
                key={c.id}
                onClick={() => onChange(c.id)}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3.5 py-3 text-left text-[15px] font-medium transition-all",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-[0_8px_20px_-10px_hsl(var(--primary)/0.8)]"
                    : "text-foreground hover:bg-secondary",
                )}
              >
                <Icon
                  name={c.icon}
                  size={17}
                  className={cn(isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-primary")}
                />
                <span className="flex-1">{c.label}</span>
                <span className={cn("text-xs tabular-nums", isActive ? "text-primary-foreground/85" : "text-muted-foreground")}>
                  {n}
                </span>
              </button>
            );
          })}
        </nav>

        <div className="mt-8 rounded-2xl border border-border bg-card p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
            <Icon name="RefreshCw" size={15} className="text-primary" />
            Сбор из ВКонтакте
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Анонсы автоматически собираются из сообществ ТПУ по расписанию и публикуются только после проверки администратором.
          </p>
        </div>
      </div>
    </aside>
  );
}
