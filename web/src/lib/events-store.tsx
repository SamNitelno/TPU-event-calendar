import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  REFERENCE_TODAY,
  SEED_EVENTS,
  SEED_SUBMISSIONS,
  toIso,
  type Submission,
  type TpuEvent,
} from "@/data/events";

const EVENTS_KEY = "tpu-cal-events-v1";
const SUBS_KEY = "tpu-cal-submissions-v1";

interface EventsContextValue {
  events: TpuEvent[];
  submissions: Submission[];
  today: string;
  addSubmission: (s: Omit<Submission, "id" | "status" | "submittedAt">) => void;
  approveSubmission: (id: string) => void;
  rejectSubmission: (id: string, reason?: string) => void;
  updateEvent: (e: TpuEvent) => void;
  deleteEvent: (id: string) => void;
  resetDemo: () => void;
}

const EventsContext = createContext<EventsContextValue | null>(null);

const uid = (p: string) => `${p}${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`;

export function EventsProvider({ children }: { children: ReactNode }) {
  const [events, setEvents] = useState<TpuEvent[]>(SEED_EVENTS);
  const [submissions, setSubmissions] = useState<Submission[]>(SEED_SUBMISSIONS);
  const [today, setToday] = useState(REFERENCE_TODAY);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const e = localStorage.getItem(EVENTS_KEY);
      const s = localStorage.getItem(SUBS_KEY);
      if (e) setEvents(JSON.parse(e));
      if (s) setSubmissions(JSON.parse(s));
    } catch {
      /* ignore broken storage */
    }
    setToday(toIso(new Date()));
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!loaded) return;
    localStorage.setItem(EVENTS_KEY, JSON.stringify(events));
    localStorage.setItem(SUBS_KEY, JSON.stringify(submissions));
  }, [events, submissions, loaded]);

  const addSubmission = useCallback<EventsContextValue["addSubmission"]>((s) => {
    setSubmissions((prev) => [
      { ...s, id: uid("s"), status: "pending", submittedAt: toIso(new Date()) },
      ...prev,
    ]);
  }, []);

  const approveSubmission = useCallback((id: string) => {
    setSubmissions((prev) => {
      const sub = prev.find((x) => x.id === id);
      if (sub) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { status, contact, submittedAt, rejectReason, ...ev } = sub;
        setEvents((evs) => [...evs.filter((x) => x.id !== `ev-${id}`), { ...ev, id: `ev-${id}` }]);
      }
      return prev.map((x) => (x.id === id ? { ...x, status: "approved" } : x));
    });
  }, []);

  const rejectSubmission = useCallback((id: string, reason?: string) => {
    setSubmissions((prev) => prev.map((x) => (x.id === id ? { ...x, status: "rejected", rejectReason: reason } : x)));
  }, []);

  const updateEvent = useCallback((e: TpuEvent) => {
    setEvents((prev) => prev.map((x) => (x.id === e.id ? e : x)));
  }, []);

  const deleteEvent = useCallback((id: string) => {
    setEvents((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const resetDemo = useCallback(() => {
    setEvents(SEED_EVENTS);
    setSubmissions(SEED_SUBMISSIONS);
  }, []);

  const value = useMemo(
    () => ({
      events: [...events].sort((a, b) => (a.date + a.timeStart).localeCompare(b.date + b.timeStart)),
      submissions,
      today,
      addSubmission,
      approveSubmission,
      rejectSubmission,
      updateEvent,
      deleteEvent,
      resetDemo,
    }),
    [events, submissions, today, addSubmission, approveSubmission, rejectSubmission, updateEvent, deleteEvent, resetDemo],
  );

  return <EventsContext.Provider value={value}>{children}</EventsContext.Provider>;
}

export function useEvents() {
  const ctx = useContext(EventsContext);
  if (!ctx) throw new Error("useEvents must be used inside EventsProvider");
  return ctx;
}
