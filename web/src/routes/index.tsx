import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import Header, { ViewToggle, type ViewMode } from "@/components/calendar/Header";
import CategorySidebar, { CategoryChips } from "@/components/calendar/CategorySidebar";
import EventFeed from "@/components/calendar/EventFeed";
import MonthCalendar from "@/components/calendar/MonthCalendar";
import Footer from "@/components/calendar/Footer";
import { CATEGORIES, categoryById, type CategoryId } from "@/data/events";
import { fetchCategories, fetchEvents, type ApiCategoryCount, type ApiEventsPage } from "@/lib/api";

const tomskToday = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);

interface IndexSearch {
  view?: "calendar";
  cat?: CategoryId;
  q?: string;
  day?: string;
}

export const Route = createFileRoute("/")({
  validateSearch: (raw: Record<string, unknown>): IndexSearch => {
    const out: IndexSearch = {};
    if (raw.view === "calendar") out.view = "calendar";
    if (typeof raw.cat === "string" && CATEGORIES.some((c) => c.id === raw.cat)) out.cat = raw.cat as CategoryId;
    if (typeof raw.q === "string" && raw.q.trim()) out.q = raw.q.slice(0, 100);
    if (typeof raw.day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(raw.day)) out.day = raw.day;
    return out;
  },
  loader: async () => {
    const [page, categories] = await Promise.all([
      fetchEvents({ page: 1 }).catch(() => null),
      fetchCategories().catch(() => null),
    ]);
    return { page, categories, today: tomskToday() };
  },
  staleTime: 60 * 1000,
  component: Index,
});

function Index() {
  const initial = Route.useLoaderData();
  const today = initial.today;
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/" });
  const [query, setQueryState] = useState(search.q ?? "");
  const [view, setViewState] = useState<ViewMode>(search.view ?? "feed");
  const [category, setCategoryState] = useState<CategoryId | "all">(search.cat ?? "all");

  const updateSearch = useCallback(
    (patch: Partial<IndexSearch>) =>
      navigate({ search: (prev: IndexSearch) => ({ ...prev, ...patch }), replace: true, resetScroll: false }),
    [navigate],
  );
  const setQuery = (v: string) => {
    setQueryState(v);
    updateSearch({ q: v.trim() ? v : undefined });
  };
  const setView = (v: ViewMode) => {
    setViewState(v);
    updateSearch({ view: v === "calendar" ? "calendar" : undefined, day: undefined });
  };
  const setCategory = (c: CategoryId | "all") => {
    setCategoryState(c);
    updateSearch({ cat: c === "all" ? undefined : c });
  };

  const [feed, setFeed] = useState<ApiEventsPage | null>(initial.page);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(initial.page ? "ready" : "error");
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState(false);
  const [categories, setCategories] = useState<ApiCategoryCount[] | null>(initial.categories);
  const [reload, setReload] = useState(0);
  const firstRun = useRef(!search.q && !search.cat);

  const slug = category === "all" ? undefined : categoryById(category).slug;
  const q = query.trim();

  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      if (initial.page) return;
    }
    firstRun.current = false;
    const ctrl = new AbortController();
    setStatus("loading");
    setMoreError(false);
    const timer = setTimeout(() => {
      fetchEvents({ page: 1, category: slug, q }, ctrl.signal)
        .then((p) => {
          setFeed(p);
          setStatus("ready");
        })
        .catch(() => {
          if (!ctrl.signal.aborted) setStatus("error");
        });
    }, q ? 350 : 0);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, q, reload]);

  useEffect(() => {
    if (categories) return;
    fetchCategories().then(setCategories).catch(() => undefined);
  }, [categories, reload]);

  const loadMore = useCallback(async () => {
    if (!feed || loadingMore) return;
    setLoadingMore(true);
    setMoreError(false);
    try {
      const next = await fetchEvents({ page: feed.page + 1, category: slug, q });
      setFeed((prev) => {
        if (!prev) return next;
        const seen = new Set(prev.items.map((e) => e.id));
        return { ...next, items: [...prev.items, ...next.items.filter((e) => !seen.has(e.id))] };
      });
    } catch {
      setMoreError(true);
    } finally {
      setLoadingMore(false);
    }
  }, [feed, loadingMore, slug, q]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    (categories ?? []).forEach((x) => {
      const cat = CATEGORIES.find((k) => k.slug === x.slug);
      if (cat) c[cat.id] = x.events_count;
    });
    return c;
  }, [categories]);
  const total = (categories ?? []).reduce((s, x) => s + x.events_count, 0);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header query={query} onQueryChange={setQuery} view={view} onViewChange={setView} />

      <div className="mx-auto grid w-full max-w-[1440px] flex-1 lg:grid-cols-[260px_minmax(0,1fr)]">
        <CategorySidebar active={category} onChange={setCategory} counts={counts} total={total} />

        <main className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
          <div className="mb-6 sm:mb-8">
            <h1 className="animate-in fade-in slide-in-from-bottom-3 font-display text-[34px] font-bold leading-[1.05] tracking-tight text-foreground duration-700 sm:text-5xl lg:text-[56px]">
              Все события ТПУ <span className="text-primary">в одном календаре</span>
            </h1>
          </div>

          <div className="mb-5 sm:hidden">
            <ViewToggle view={view} onChange={setView} />
          </div>

          <div className="mb-6">
            <CategoryChips active={category} onChange={setCategory} counts={counts} total={total} />
          </div>

          {view === "feed" ? (
            <EventFeed
              events={feed?.items ?? []}
              total={feed?.total ?? 0}
              today={today}
              status={status}
              loadingMore={loadingMore}
              moreError={moreError}
              filtered={!!slug || !!q}
              onMore={loadMore}
              onRetry={() => setReload((r) => r + 1)}
            />
          ) : (
            <MonthCalendar today={today} category={slug} query={q} day={search.day} onDayChange={(day) => updateSearch({ day })} />
          )}
        </main>
      </div>

      <Footer />
    </div>
  );
}
