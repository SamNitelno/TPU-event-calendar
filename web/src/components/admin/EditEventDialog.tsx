import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { CATEGORIES, type TpuEvent } from "@/data/events";
import { cn } from "@/lib/utils";

interface Props {
  event: TpuEvent | null;
  onClose: () => void;
  onSave: (e: TpuEvent) => void;
}

export default function EditEventDialog({ event, onClose, onSave }: Props) {
  const [draft, setDraft] = useState<TpuEvent | null>(event);
  useEffect(() => setDraft(event), [event]);

  const set = <K extends keyof TpuEvent>(k: K, v: TpuEvent[K]) => setDraft((d) => (d ? { ...d, [k]: v } : d));
  const valid = !!draft && draft.title.trim() && draft.date && draft.timeStart && draft.place.trim();

  return (
    <Dialog open={!!event} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[92vh] w-[calc(100%-2rem)] max-w-xl overflow-y-auto rounded-3xl">
        <DialogTitle className="font-display text-xl font-bold">Редактирование мероприятия</DialogTitle>
        <DialogDescription>Изменения сразу видны в ленте и календаре.</DialogDescription>
        {draft && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Название</Label>
              <Input value={draft.title} onChange={(e) => set("title", e.target.value)} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Организатор</Label>
              <Input value={draft.organizer} onChange={(e) => set("organizer", e.target.value)} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Категория</Label>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map((c) => (
                  <button
                    type="button"
                    key={c.id}
                    onClick={() => set("category", c.id)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition",
                      draft.category === c.id ? "border-primary bg-primary text-primary-foreground" : "border-border hover:border-primary/50",
                    )}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Дата</Label>
              <Input type="date" value={draft.date} onChange={(e) => set("date", e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label>Начало</Label>
                <Input type="time" value={draft.timeStart} onChange={(e) => set("timeStart", e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>Конец</Label>
                <Input type="time" value={draft.timeEnd ?? ""} onChange={(e) => set("timeEnd", e.target.value || undefined)} />
              </div>
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Место</Label>
              <Input value={draft.place} onChange={(e) => set("place", e.target.value)} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Ссылка на пост ВКонтакте</Label>
              <Input value={draft.vkUrl} onChange={(e) => set("vkUrl", e.target.value)} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Описание</Label>
              <Textarea rows={4} value={draft.description} onChange={(e) => set("description", e.target.value)} />
            </div>
            <div className="flex justify-end gap-2 sm:col-span-2">
              <button onClick={onClose} className="h-11 rounded-xl border border-border px-5 text-sm font-semibold hover:border-primary">
                Отмена
              </button>
              <button
                disabled={!valid}
                onClick={() => draft && onSave(draft)}
                className="h-11 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                Сохранить
              </button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
