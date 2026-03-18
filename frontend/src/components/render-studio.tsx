"use client";

import { Clapperboard, Download, ScanSearch } from "lucide-react";
import { startTransition, useEffect, useState } from "react";

import { apiRequest, getEpisode } from "@/lib/api";
import type { Episode } from "@/lib/types";
import { EmptyState, FieldLabel, Panel } from "./common";
import { StudioShell } from "./studio-shell";

export function RenderStudio({ projectId, episodeId }: { projectId: string; episodeId: string }) {
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [subtitleText, setSubtitleText] = useState("");
  const [voiceAssetId, setVoiceAssetId] = useState("");
  const [bgmAssetId, setBgmAssetId] = useState("");
  const [error, setError] = useState("");

  async function refreshEpisode() {
    try {
      const detail = await getEpisode(episodeId);
      startTransition(() => setEpisode(detail));
    } catch {
      // ignore polling noise
    }
  }

  useEffect(() => {
    void refreshEpisode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId]);

  useEffect(() => {
    const timer = window.setInterval(() => void refreshEpisode(), 5000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId]);

  const selectedVersions =
    episode?.shots
      ?.map((shot) => shot.versions?.find((version) => version.is_selected))
      .filter(Boolean)
      .map((item) => item!.id) ?? [];

  async function renderEpisode() {
    setError("");
    try {
      await apiRequest(`/episodes/${episodeId}/render`, {
        method: "POST",
        body: JSON.stringify({
          selected_shot_version_ids: selectedVersions,
          subtitle_text: subtitleText,
          voice_asset_id: voiceAssetId,
          bgm_asset_id: bgmAssetId,
        }),
      });
      await refreshEpisode();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "导出失败");
    }
  }

  return (
    <StudioShell
      title={episode?.title ?? "粗剪导出"}
      eyebrow="render"
      projectId={projectId}
      episodeId={episodeId}
      activeHref={`/projects/${projectId}/episodes/${episodeId}/render`}
    >
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Render Setup" eyebrow="assembly">
          <div className="space-y-5">
            <div className="rounded-[28px] border border-white/10 bg-black/12 p-5">
              <div className="mb-4 flex items-center gap-3">
                <ScanSearch className="h-5 w-5 text-amber-200" />
                <p className="text-sm uppercase tracking-[0.28em] text-stone-400">选中的镜头版本</p>
              </div>
              {selectedVersions.length ? (
                <div className="space-y-2 text-sm text-stone-300">
                  {selectedVersions.map((id) => (
                    <div key={id} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
                      {id}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="还没有采用镜头" body="先去镜头生成页，至少为每个 Shot 选择一个候选版本。" />
              )}
            </div>

            <div>
              <FieldLabel>字幕内容</FieldLabel>
              <textarea rows={8} value={subtitleText} onChange={(event) => setSubtitleText(event.target.value)} placeholder="每行一句字幕，系统会自动转成 SRT 并叠加到导出视频。" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <FieldLabel>配音 Asset ID</FieldLabel>
                <input value={voiceAssetId} onChange={(event) => setVoiceAssetId(event.target.value)} placeholder="可选" />
              </div>
              <div>
                <FieldLabel>BGM Asset ID</FieldLabel>
                <input value={bgmAssetId} onChange={(event) => setBgmAssetId(event.target.value)} placeholder="可选" />
              </div>
            </div>
            <button className="primary-button inline-flex items-center gap-2" disabled={selectedVersions.length === 0} onClick={renderEpisode}>
              <Download className="h-4 w-4" />
              发起导出
            </button>
            {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          </div>
        </Panel>

        <Panel title="Render History" eyebrow="export jobs">
          {episode?.render_jobs?.length ? (
            <div className="space-y-4">
              {episode.render_jobs.map((job) => (
                <div key={job.id} className="rounded-[28px] border border-white/10 bg-black/12 p-5">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <p className="font-display text-3xl text-stone-50">{job.status}</p>
                      <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{job.created_at}</p>
                    </div>
                    <Clapperboard className="h-5 w-5 text-amber-200" />
                  </div>
                  <p className="text-sm leading-6 text-stone-300">
                    包含 {job.selected_shot_version_ids.length} 个镜头版本
                  </p>
                  {job.output_url ? (
                    <div className="mt-4 overflow-hidden rounded-[24px] border border-white/8 bg-stone-950/50">
                      <video className="w-full" src={job.output_url} controls />
                    </div>
                  ) : null}
                  {job.error_message ? <p className="mt-3 text-sm text-rose-300">{job.error_message}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="还没有导出历史" body="当你选择好候选镜头并发起导出后，这里会显示渲染状态和导出视频。" />
          )}
        </Panel>
      </div>
    </StudioShell>
  );
}
