"use client";

import { Save, Sparkles, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";

import { apiRequest, getEpisode, getProject } from "@/lib/api";
import type { Episode, Project, Shot } from "@/lib/types";
import { EmptyState, FieldLabel, Panel } from "./common";
import { StudioShell } from "./studio-shell";

export function StoryboardStudio({ projectId, episodeId }: { projectId: string; episodeId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [projectDetail, episodeDetail] = await Promise.all([getProject(projectId), getEpisode(episodeId)]);
      setProject(projectDetail);
      setEpisode(episodeDetail);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载分镜页失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, episodeId]);

  async function generateStoryCard() {
    await apiRequest(`/episodes/${episodeId}/story-card:generate`, {
      method: "POST",
      body: JSON.stringify({
        character_ids: project?.characters?.map((item) => item.id) ?? [],
        location_ids: project?.locations?.map((item) => item.id) ?? [],
      }),
    });
    await refresh();
  }

  async function generateStoryboard() {
    await apiRequest(`/episodes/${episodeId}/storyboard:generate`, {
      method: "POST",
      body: JSON.stringify({
        character_ids: project?.characters?.map((item) => item.id) ?? [],
        location_ids: project?.locations?.map((item) => item.id) ?? [],
        replace_existing: true,
      }),
    });
    await refresh();
  }

  async function saveShot(shot: Shot) {
    await apiRequest(`/shots/${shot.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        order_no: shot.order_no,
        duration: shot.duration,
        description: shot.description,
        shot_type: shot.shot_type,
        camera_motion: shot.camera_motion,
        subject_desc: shot.subject_desc,
        action_desc: shot.action_desc,
        emotion_desc: shot.emotion_desc,
        dialogue_text: shot.dialogue_text,
        generation_mode: shot.generation_mode,
        status: shot.status,
      }),
    });
    await refresh();
  }

  function updateShotLocal(next: Shot) {
    setEpisode((current) =>
      current
        ? {
            ...current,
            shots: current.shots?.map((item) => (item.id === next.id ? next : item)),
          }
        : current,
    );
  }

  return (
    <StudioShell
      title={episode?.title ?? "剧情与分镜"}
      eyebrow="storyboard"
      projectId={projectId}
      episodeId={episodeId}
      activeHref={`/projects/${projectId}/episodes/${episodeId}/storyboard`}
    >
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Logline & Story Card" eyebrow="narrative">
          {loading ? (
            <p className="text-sm text-stone-400">正在加载剧情...</p>
          ) : !episode ? (
            <EmptyState title="找不到剧集" body="请先回项目首页创建剧集。" />
          ) : (
            <div className="space-y-5">
              <div className="rounded-[28px] border border-white/10 bg-black/12 p-5">
                <FieldLabel>单集标题</FieldLabel>
                <p className="font-display text-3xl text-stone-50">{episode.title}</p>
                <FieldLabel>一句话剧情</FieldLabel>
                <p className="text-sm leading-7 text-stone-300">{episode.logline}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button className="primary-button inline-flex items-center gap-2" onClick={generateStoryCard}>
                  <Sparkles className="h-4 w-4" />
                  生成剧情卡
                </button>
                <button className="secondary-button inline-flex items-center gap-2" onClick={generateStoryboard}>
                  <Wand2 className="h-4 w-4" />
                  生成 Scene / Shot
                </button>
              </div>
              {episode.story_card ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-[24px] border border-white/10 bg-black/12 p-4">
                    <FieldLabel>主题</FieldLabel>
                    <p className="text-sm text-stone-200">{episode.story_card.theme}</p>
                  </div>
                  <div className="rounded-[24px] border border-white/10 bg-black/12 p-4">
                    <FieldLabel>冲突</FieldLabel>
                    <p className="text-sm text-stone-200">{episode.story_card.conflict}</p>
                  </div>
                  <div className="rounded-[24px] border border-white/10 bg-black/12 p-4">
                    <FieldLabel>反转</FieldLabel>
                    <p className="text-sm text-stone-200">{episode.story_card.twist}</p>
                  </div>
                  <div className="rounded-[24px] border border-white/10 bg-black/12 p-4">
                    <FieldLabel>结尾钩子</FieldLabel>
                    <p className="text-sm text-stone-200">{episode.story_card.ending_hook}</p>
                  </div>
                  <div className="rounded-[24px] border border-white/10 bg-black/12 p-4 md:col-span-2">
                    <FieldLabel>剧情概要</FieldLabel>
                    <p className="text-sm leading-7 text-stone-300">{episode.story_card.summary}</p>
                  </div>
                </div>
              ) : (
                <EmptyState title="还没有剧情卡" body="点击上方按钮，用当前项目的角色与场景资产生成结构化剧情卡。" />
              )}
            </div>
          )}
          {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
        </Panel>

        <Panel title="Shot Editor" eyebrow="editable storyboard">
          {!episode?.shots?.length ? (
            <EmptyState title="还没有分镜" body="先生成 Story Card，再让系统拆出 Scene 与 Shot。生成后你可以逐个编辑镜头参数。" />
          ) : (
            <div className="space-y-4">
              {episode.shots.map((shot) => (
                <div key={shot.id} className="rounded-[28px] border border-white/10 bg-black/12 p-5">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <p className="font-display text-3xl text-stone-50">Shot {shot.order_no}</p>
                      <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{shot.status}</p>
                    </div>
                    <button className="secondary-button inline-flex items-center gap-2" onClick={() => void saveShot(shot)}>
                      <Save className="h-4 w-4" />
                      保存
                    </button>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="md:col-span-2">
                      <FieldLabel>镜头描述</FieldLabel>
                      <textarea rows={3} value={shot.description} onChange={(event) => updateShotLocal({ ...shot, description: event.target.value })} />
                    </div>
                    <div>
                      <FieldLabel>时长</FieldLabel>
                      <input type="number" value={shot.duration} onChange={(event) => updateShotLocal({ ...shot, duration: Number(event.target.value) })} />
                    </div>
                    <div>
                      <FieldLabel>景别</FieldLabel>
                      <input value={shot.shot_type} onChange={(event) => updateShotLocal({ ...shot, shot_type: event.target.value })} />
                    </div>
                    <div>
                      <FieldLabel>运镜</FieldLabel>
                      <input value={shot.camera_motion} onChange={(event) => updateShotLocal({ ...shot, camera_motion: event.target.value })} />
                    </div>
                    <div>
                      <FieldLabel>生成模式</FieldLabel>
                      <input value={shot.generation_mode} onChange={(event) => updateShotLocal({ ...shot, generation_mode: event.target.value })} />
                    </div>
                    <div>
                      <FieldLabel>主体描述</FieldLabel>
                      <input value={shot.subject_desc} onChange={(event) => updateShotLocal({ ...shot, subject_desc: event.target.value })} />
                    </div>
                    <div>
                      <FieldLabel>动作描述</FieldLabel>
                      <input value={shot.action_desc} onChange={(event) => updateShotLocal({ ...shot, action_desc: event.target.value })} />
                    </div>
                    <div>
                      <FieldLabel>情绪描述</FieldLabel>
                      <input value={shot.emotion_desc} onChange={(event) => updateShotLocal({ ...shot, emotion_desc: event.target.value })} />
                    </div>
                    <div>
                      <FieldLabel>台词</FieldLabel>
                      <input value={shot.dialogue_text} onChange={(event) => updateShotLocal({ ...shot, dialogue_text: event.target.value })} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </StudioShell>
  );
}
