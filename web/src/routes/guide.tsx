import { createFileRoute, Link } from "@tanstack/react-router";
import { marked } from "marked";
import Header from "@/components/calendar/Header";
import Footer from "@/components/calendar/Footer";
import Icon from "@/components/ui/icon";
import guideMd from "../../docs/user_guide.md?raw";

const TITLE = "Как пользоваться календарём — Календарь ТПУ";
const DESCRIPTION =
  "Пошаговая инструкция: как найти мероприятие ТПУ, пользоваться фильтром, поиском и календарём, подать событие и проверить заявку.";

const html = (marked.parse(guideMd.replace(/\]\(\.\.\/public\//g, "](/"), { async: false }) as string)
  .replace(/<img /g, '<img loading="lazy" ')
  .replace(/<a href="(https?:)/g, '<a target="_blank" rel="noopener noreferrer" href="$1');

export const Route = createFileRoute("/guide")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
    ],
  }),
  component: GuidePage,
});

function GuidePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header showControls={false} />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6 lg:py-10">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-primary">
          <Icon name="ArrowLeft" size={16} /> К афише
        </Link>
        <article className="guide mt-4 rounded-3xl border border-border bg-card p-5 sm:p-8" dangerouslySetInnerHTML={{ __html: html }} />
      </main>
      <Footer />
    </div>
  );
}
