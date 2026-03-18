"use client";

import Link from "next/link";
import { Film, FolderKanban, Layers3, PersonStanding, ScissorsLineDashed, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

const nav = [
  { label: "项目首页", href: "/", icon: FolderKanban },
  { label: "角色资产", href: "__characters__", icon: PersonStanding },
  { label: "剧情分镜", href: "__storyboard__", icon: Layers3 },
  { label: "镜头生成", href: "__generation__", icon: Film },
  { label: "粗剪导出", href: "__render__", icon: ScissorsLineDashed },
];

interface StudioShellProps {
  title: string;
  eyebrow: string;
  projectId?: string;
  episodeId?: string;
  activeHref: string;
  children: ReactNode;
}

function resolveHref(template: string, projectId?: string, episodeId?: string) {
  if (template === "/") return "/";
  if (!projectId) return "/";
  if (template === "__characters__") return `/projects/${projectId}/characters`;
  if (template === "__storyboard__") return episodeId ? `/projects/${projectId}/episodes/${episodeId}/storyboard` : "/";
  if (template === "__generation__") return episodeId ? `/projects/${projectId}/episodes/${episodeId}/generation` : "/";
  if (template === "__render__") return episodeId ? `/projects/${projectId}/episodes/${episodeId}/render` : "/";
  return "/";
}

export function StudioShell({ title, eyebrow, projectId, episodeId, activeHref, children }: StudioShellProps) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(255,163,67,0.18),_transparent_22%),radial-gradient(circle_at_top_right,_rgba(74,203,163,0.16),_transparent_20%),linear-gradient(180deg,_#f4ecdd_0%,_#efe6d7_42%,_#1e1d1b_42%,_#181715_100%)] text-stone-100">
      <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 gap-6 px-4 py-4 lg:grid-cols-[280px_1fr] lg:px-6">
        <aside className="glass-panel flex flex-col gap-6 overflow-hidden p-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-stone-950/40 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-amber-200/90">
              <Sparkles className="h-3 w-3" />
              cinematic pipeline
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.4em] text-stone-400">{eyebrow}</p>
              <h1 className="font-display text-4xl leading-none text-stone-50">{title}</h1>
            </div>
            <p className="max-w-sm text-sm leading-6 text-stone-300">
              为剧情短视频提供角色资产、结构化分镜、镜头生成和粗剪导出的一体化工作台。
            </p>
          </div>

          <nav className="space-y-2">
            {nav.map((item) => {
              const href = resolveHref(item.href, projectId, episodeId);
              const Icon = item.icon;
              const active = href === activeHref;
              return (
                <Link
                  key={item.label}
                  href={href}
                  className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition ${
                    active
                      ? "bg-[linear-gradient(135deg,rgba(247,146,86,0.28),rgba(255,237,201,0.12))] text-white shadow-[0_24px_80px_rgba(0,0,0,0.35)]"
                      : "bg-stone-900/30 text-stone-300 hover:bg-stone-900/50 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="rounded-[28px] border border-white/10 bg-stone-950/50 p-5">
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-amber-300/15 text-amber-200">
                <Film className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-stone-500">V1 Focus</p>
                <p className="text-sm text-stone-200">连续剧情生产，而非单镜头炫技</p>
              </div>
            </div>
            <ul className="space-y-2 text-sm text-stone-400">
              <li>Shot 是唯一生成单元</li>
              <li>候选镜头最多 4 个</li>
              <li>导出链路保留历史</li>
            </ul>
          </div>
        </aside>

        <main className="space-y-6 pb-8">{children}</main>
      </div>
    </div>
  );
}
