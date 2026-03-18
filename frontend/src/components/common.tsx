"use client";

import type { ReactNode } from "react";

export function Panel({
  title,
  eyebrow,
  aside,
  children,
}: {
  title: string;
  eyebrow?: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="glass-panel grid-sheen relative overflow-hidden p-6">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          {eyebrow ? <div className="section-chip mb-3">{eyebrow}</div> : null}
          <h2 className="font-display text-3xl text-stone-50">{title}</h2>
        </div>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function StatCard({
  label,
  value,
  tone = "amber",
}: {
  label: string;
  value: string | number;
  tone?: "amber" | "mint" | "stone";
}) {
  const toneClass =
    tone === "mint"
      ? "from-emerald-200/25 to-cyan-400/8 text-emerald-100"
      : tone === "stone"
        ? "from-stone-200/14 to-stone-500/6 text-stone-100"
        : "from-amber-200/25 to-orange-400/8 text-amber-100";
  return (
    <div className={`rounded-[26px] border border-white/10 bg-gradient-to-br ${toneClass} p-5`}>
      <p className="text-xs uppercase tracking-[0.32em] text-white/50">{label}</p>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}

export function FieldLabel({ children }: { children: ReactNode }) {
  return <label className="mb-2 block text-xs uppercase tracking-[0.28em] text-stone-400">{children}</label>;
}

export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-[28px] border border-dashed border-white/14 bg-black/10 px-6 py-12 text-center">
      <h3 className="font-display text-3xl text-stone-50">{title}</h3>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-stone-400">{body}</p>
    </div>
  );
}
