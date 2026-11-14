import funcUrls from "../../backend/func2url.json";
import { MONTHS_GEN, WEEKDAYS, parseDate } from "@/data/events";

const BASE = ((funcUrls as Record<string, string>)["events-api"] || "").replace(/\/+$/, "");

export interface ApiCategory {
  slug: string;
  name: string;
}

export interface ApiEvent {
  id: number;
  title: string;
  organizer: string;
  category: ApiCategory;
  event_date: string;
  end_date: string | null;
  start_time: string | null;
  end_time: string | null;
  location: string | null;
  original_post_link: string | null;
}

export interface ApiEventDetail extends ApiEvent {
  description: string | null;
  image_url: string | null;
}

export interface ApiEventsPage {
  items: ApiEvent[];
  page: number;
  per_page: number;
  total: number;
}

export interface ApiCategoryCount extends ApiCategory {
  events_count: number;
}

export interface EventsQuery {
  category?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
}

export interface FieldIssue {
  field: string;
  type: string;
  msg: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fields: FieldIssue[] = [],
  ) {
    super(message);
  }
}

function buildUrl(path: string, params?: URLSearchParams) {
  const qs = new URLSearchParams(params);
  qs.set("path", path);
  return `${BASE}/?${qs.toString()}`;
}

async function request<T>(path: string, init?: RequestInit & { params?: URLSearchParams }): Promise<T> {
  let res: Response;
  try {
    res = await fetch(buildUrl(path, init?.params), {
      ...init,
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) },
      signal: init?.signal ?? AbortSignal.timeout(15000),
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "Нет связи с сервером");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    const fields: FieldIssue[] = Array.isArray(detail)
      ? detail.map((d: { loc?: unknown[]; type?: string; msg?: string }) => ({
          field: String((d.loc ?? []).filter((x) => x !== "body").slice(-1)[0] ?? ""),
          type: d.type ?? "",
          msg: d.msg ?? "",
        }))
      : [];
    throw new ApiError(res.status, typeof detail === "string" ? detail : `Ошибка сервера (${res.status})`, fields);
  }
  return data as T;
}

export function fetchEvents(query: EventsQuery = {}, signal?: AbortSignal) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null && String(v).trim() !== "") params.set(k, String(v).trim());
  });
  return request<ApiEventsPage>("/api/events", { signal, params }).then((p) => {
    if (!p || !Array.isArray(p.items)) throw new ApiError(500, "Неожиданный ответ сервера");
    return p;
  });
}

export async function fetchAllEvents(query: Omit<EventsQuery, "page">, signal?: AbortSignal) {
  const first = await fetchEvents({ ...query, page: 1 }, signal);
  const pages = Math.min(Math.ceil(first.total / first.per_page), 10);
  const rest = await Promise.all(
    Array.from({ length: Math.max(pages - 1, 0) }, (_, i) => fetchEvents({ ...query, page: i + 2 }, signal)),
  );
  return [first, ...rest].flatMap((p) => p.items);
}

export function fetchEvent(id: number | string) {
  return request<ApiEventDetail>(`/api/events/${encodeURIComponent(String(id))}`).then((e) => {
    if (!e || typeof e.id !== "number" || !e.category) throw new ApiError(500, "Неожиданный ответ сервера");
    return e;
  });
}

export function fetchCategories(signal?: AbortSignal) {
  return request<ApiCategoryCount[]>("/api/categories", { signal }).then((c) => {
    if (!Array.isArray(c)) throw new ApiError(500, "Неожиданный ответ сервера");
    return c;
  });
}

export interface SubmissionPayload {
  title: string;
  organizer: string;
  category: string;
  event_date: string;
  end_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  location?: string | null;
  description?: string | null;
  contact: string;
}

export function createSubmission(payload: SubmissionPayload) {
  return request<{ id: number; status: string }>("/api/submissions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

const cleanTime = (t: string | null | undefined) => (t && t !== "00:00" && t !== "None" ? t.slice(0, 5) : null);

export function formatEventTime(e: Pick<ApiEvent, "start_time" | "end_time">): string | null {
  const start = cleanTime(e.start_time);
  const end = cleanTime(e.end_time);
  if (!start) return null;
  return end && end !== start ? `${start} – ${end}` : start;
}

const dayMonth = (iso: string) => {
  const d = parseDate(iso);
  return `${d.getDate()} ${MONTHS_GEN[d.getMonth()]}`;
};

export function isMultiDay(e: Pick<ApiEvent, "event_date" | "end_date">) {
  return !!e.end_date && e.end_date !== e.event_date;
}

export function formatEventDates(e: Pick<ApiEvent, "event_date" | "end_date">, withWeekday = false): string {
  if (!isMultiDay(e)) {
    const d = parseDate(e.event_date);
    return withWeekday ? `${dayMonth(e.event_date)}, ${WEEKDAYS[d.getDay()]}` : dayMonth(e.event_date);
  }
  const a = parseDate(e.event_date);
  const b = parseDate(e.end_date!);
  if (a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth()) {
    return `${a.getDate()}–${b.getDate()} ${MONTHS_GEN[b.getMonth()]}`;
  }
  return `${dayMonth(e.event_date)} – ${dayMonth(e.end_date!)}`;
}
