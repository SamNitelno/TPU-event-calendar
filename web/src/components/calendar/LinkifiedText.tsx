import { Fragment } from "react";

const TLD = "ru|com|рф|cc|me|org|net|io|su|online|pro|info|dev|app|site|space";
const LINK_RE = new RegExp(
  `((?:https?:\\/\\/|www\\.)[^\\s<>"«»]+|(?<![\\w@.\\/-])(?:[a-z0-9-]+\\.)+(?:${TLD})\\/[^\\s<>"«»]*)`,
  "gi",
);
const TRAILING = /[.,!?;:)\]'»…]+$/;

function toHref(raw: string) {
  return /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
}

export default function LinkifiedText({ text }: { text: string }) {
  const out: React.ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(LINK_RE)) {
    const start = m.index ?? 0;
    let link = m[0];
    const tail = link.match(TRAILING)?.[0] ?? "";
    if (tail && !(tail.startsWith(")") && link.includes("("))) link = link.slice(0, -tail.length);
    if (!link || link.endsWith("/") && link.length < 4) continue;
    if (start > last) out.push(<Fragment key={`t${start}`}>{text.slice(last, start)}</Fragment>);
    out.push(
      <a
        key={`l${start}`}
        href={toHref(link)}
        target="_blank"
        rel="noopener noreferrer"
        className="break-all font-medium text-primary underline underline-offset-2 hover:text-primary/80"
      >
        {link}
      </a>,
    );
    last = start + link.length;
  }
  if (last < text.length) out.push(<Fragment key="tail">{text.slice(last)}</Fragment>);
  return <>{out}</>;
}
