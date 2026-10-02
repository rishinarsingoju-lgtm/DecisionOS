import type { ReactNode } from "react";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function SectionHeading({ eyebrow, title, note }: { eyebrow?: string; title: string; note?: string }) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
      </div>
      {note && <span className="section-note">{note}</span>}
    </div>
  );
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>;
}

export function StatusLabel({ status }: { status: string }) {
  const tone = status === "VERIFIED" || status === "Matched" || status === "Available" ? "verified" :
    status === "WITHHELD" || status === "Unavailable" ? "withheld" :
      status === "Stale" || status === "Limited evidence" ? "warning" : "neutral";
  return <Badge tone={tone}>{status}</Badge>;
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><strong>{title}</strong><span>{detail}</span></div>;
}