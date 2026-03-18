"use client";

import { Play, RefreshCw, Sparkle, WandSparkles } from "lucide-react";
import { startTransition, useEffect, useState } from "react";

import { apiRequest, getEpisode } from "@/lib/api";
import type { Episode, Shot } from "@/lib/types";
import { EmptyState, FieldLabel, Panel } from "./common";
import { StudioShell } from "./studio-shell";

export function GenerationStudio({ projectId, episodeId }: { projectId: string; episodeId: string }) {
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [candidateCount, setCandidateCount] = useState(2);

  async function refreshEpisode() {
    try {
      const detail = await getEpisode(episodeId);
      startTransition(() => setEpisode(detail));
      setLoading(false);
    } catch {
      // ignore polling noise
    }
  }

  useEffect(() => {
    void refreshEpisode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void refreshEpisode();
    }, 4000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId]);

  async function runGeneration(shot: Shot, retry = false) {
    setError("");
    try {
      await apiRequest(`/shots/${shot.id}/${retry ? "retry" : "generate"}`, {
        method: "POST",
        body: JSON.stringify({
          candidate_count: candidateCount,
          high_quality: shot.duration >= 6,
          input_type: shot.generation_mode,
        }),
      });
      await refreshEpisode();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "镜头生成失败");
    }
  }

  async function selectVersion(shot: Shot, versionId: string) {
    setError("");
    try {
      await apiRequest(`/shots/${shot.id}/versions/${versionId}/select`, { method: "POST", body: JSON.stringify({}) });
      await refreshEpisode();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "采用候选失败");
    }
  }

  return (
    <StudioShell
      title={episode?.title ?? "镜头生成"}
      eyebrow="generation"
      projectId={projectId}
      episodeId={episodeId}
      activeHref={`/projects/${projectId}/episodes/${episodeId}/generation`}
    >
      <Panel
        title="Generation Controls"
        eyebrow="shot pipeline"
        aside={
          <div className="flex items-center gap-3">
            <FieldLabel>候选数量</FieldLabel>
            <input className="w-24" type="number" min={1} max={4} value={candidateCount} onChange={(event) => setCandidateCount(Number(event.target.value))} />
          </div>
        }
      >
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[26px] border border-white/10 bg-black/12 p-5">
            <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Shots</p>
            <p className="mt-3 font-display text-4xl text-stone-50">{episode?.shots?.length ?? 0}</p>
          </div>
          <div className="rounded-[26px] border border-white/10 bg-black/12 p-5">
            <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Selected</p>
            <p className="mt-3 font-display text-4xl text-stone-50">
              {episode?.shots?.filter((item) => item.current_version_id).length ?? 0}
            </p>
          </div>
          <div className="rounded-[26px] border border-white/10 bg-black/12 p-5">
            <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Episode Status</p>
            <p className="mt-3 font-display text-4xl text-stone-50">{episode?.status ?? "draft"}</p>
          </div>
        </div>
      </Panel>

      <Panel title="Candidate Versions" eyebrow="async tasks">
        {loading ? (
          <p className="text-sm text-stone-400">正在加载镜头...</p>
        ) : !episode?.shots?.length ? (
          <EmptyState title="还没有 Shot" body="先回到剧情与分镜页生成 Shot，再回来发起视频任务。" />
        ) : (
          <div className="space-y-4">
            {episode.shots.map((shot) => (
              <div key={shot.id} className="rounded-[28px] border border-white/10 bg-black/12 p-5">
                <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="font-display text-3xl text-stone-50">Shot {shot.order_no}</p>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-300">{shot.description}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.22em] text-stone-500">
                      <span>{shot.status}</span>
                      <span>{shot.generation_mode}</span>
                      <span>{shot.duration}s</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button className="primary-button inline-flex items-center gap-2" onClick={() => void runGeneration(shot, false)}>
                      <Play className="h-4 w-4" />
                      生成候选
                    </button>
                    <button className="secondary-button inline-flex items-center gap-2" onClick={() => void runGeneration(shot, true)}>
                      <RefreshCw className="h-4 w-4" />
                      重试
                    </button>
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {shot.versions?.length ? (
                    shot.versions.map((version) => (
                      <div key={version.id} className={`rounded-[24px] border p-4 ${version.is_selected ? "border-amber-200/30 bg-amber-200/10" : "border-white/8 bg-black/10"}`}>
                        <div className="mb-3 flex items-center justify-between">
                          <p className="text-sm uppercase tracking-[0.22em] text-stone-400">{version.provider}</p>
                          {version.is_selected ? <Sparkle className="h-4 w-4 text-amber-200" /> : null}
                        </div>
                        <div className="aspect-[9/16] overflow-hidden rounded-[20px] border border-white/8 bg-stone-950/50">
                          {version.asset_url ? (
                            <video className="h-full w-full object-cover" src={version.asset_url} controls />
                          ) : (
                            <div className="flex h-full items-center justify-center text-sm text-stone-500">无可用预览</div>
                          )}
                        </div>
                        <div className="mt-4 flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm text-stone-200">{version.model}</p>
                            <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{version.id.slice(0, 8)}</p>
                          </div>
                          <button className="secondary-button inline-flex items-center gap-2" onClick={() => void selectVersion(shot, version.id)}>
                            <WandSparkles className="h-4 w-4" />
                            设为采用
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-[24px] border border-dashed border-white/12 bg-black/10 p-8 text-sm text-stone-400 md:col-span-2 xl:col-span-3">
                      还没有候选版本。点击上方按钮发起异步视频任务。
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
      </Panel>
    </StudioShell>
  );
}
