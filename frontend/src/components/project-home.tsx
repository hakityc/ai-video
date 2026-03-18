"use client";

import Link from "next/link";
import { ArrowRight, Clapperboard, FolderPlus, MapPinned, Radar, Users } from "lucide-react";
import { startTransition, useEffect, useState } from "react";

import { getProject, listProjects, apiRequest } from "@/lib/api";
import type { Project } from "@/lib/types";
import { EmptyState, FieldLabel, Panel, StatCard } from "./common";
import { StudioShell } from "./studio-shell";

const initialProjectForm = {
  name: "",
  genre: "悬疑",
  style: "cinematic noir",
  aspect_ratio: "9:16",
  target_duration: 30,
  created_by: "local-user",
};

const initialEpisodeForm = {
  title: "",
  logline: "",
  target_duration: 30,
};

export function ProjectHome() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projectForm, setProjectForm] = useState(initialProjectForm);
  const [episodeForm, setEpisodeForm] = useState(initialEpisodeForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>("");

  async function refresh(projectId?: string) {
    setLoading(true);
    setError("");
    try {
      const response = await listProjects();
      const fallbackId = response.items[0]?.id ?? "";
      startTransition(() => {
        setProjects(response.items);
        const nextId = projectId || selectedProjectId || fallbackId;
        setSelectedProjectId(nextId);
      });
      const nextId = projectId || selectedProjectId || fallbackId;
      if (nextId) {
        const detail = await getProject(nextId);
        setSelectedProject(detail);
      } else {
        setSelectedProject(null);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载项目失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedProjectId) return;
    void getProject(selectedProjectId).then(setSelectedProject).catch(() => undefined);
  }, [selectedProjectId]);

  async function createProject() {
    setSaving(true);
    setError("");
    try {
      const created = await apiRequest<Project>("/projects", {
        method: "POST",
        body: JSON.stringify(projectForm),
      });
      setProjectForm(initialProjectForm);
      await refresh(created.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建项目失败");
    } finally {
      setSaving(false);
    }
  }

  async function createEpisode() {
    if (!selectedProjectId) return;
    setSaving(true);
    setError("");
    try {
      await apiRequest(`/projects/${selectedProjectId}/episodes`, {
        method: "POST",
        body: JSON.stringify(episodeForm),
      });
      setEpisodeForm(initialEpisodeForm);
      await refresh(selectedProjectId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建剧集失败");
    } finally {
      setSaving(false);
    }
  }

  const latestEpisode = selectedProject?.episodes?.[0];

  return (
    <StudioShell title="剧情型 AI 视频平台" eyebrow="project home" activeHref="/">
      <Panel
        title="Production Radar"
        eyebrow="overview"
        aside={<div className="text-sm text-stone-400">从资产沉淀到粗剪导出的一整条流水线</div>}
      >
        <div className="grid gap-4 md:grid-cols-4">
          <StatCard label="Projects" value={projects.length} />
          <StatCard label="Episodes" value={selectedProject?.episodes?.length ?? 0} tone="mint" />
          <StatCard label="Characters" value={selectedProject?.characters?.length ?? 0} tone="stone" />
          <StatCard label="Locations" value={selectedProject?.locations?.length ?? 0} tone="amber" />
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Create Project" eyebrow="new series">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <FieldLabel>项目名称</FieldLabel>
              <input value={projectForm.name} onChange={(event) => setProjectForm({ ...projectForm, name: event.target.value })} placeholder="例如：雨夜便利店档案" />
            </div>
            <div>
              <FieldLabel>题材</FieldLabel>
              <input value={projectForm.genre} onChange={(event) => setProjectForm({ ...projectForm, genre: event.target.value })} />
            </div>
            <div>
              <FieldLabel>视觉风格</FieldLabel>
              <input value={projectForm.style} onChange={(event) => setProjectForm({ ...projectForm, style: event.target.value })} />
            </div>
            <div>
              <FieldLabel>画幅</FieldLabel>
              <input value={projectForm.aspect_ratio} onChange={(event) => setProjectForm({ ...projectForm, aspect_ratio: event.target.value })} />
            </div>
            <div>
              <FieldLabel>目标时长（秒）</FieldLabel>
              <input
                type="number"
                value={projectForm.target_duration}
                onChange={(event) => setProjectForm({ ...projectForm, target_duration: Number(event.target.value) })}
              />
            </div>
            <div className="flex items-end">
              <button className="primary-button inline-flex items-center gap-2" disabled={saving || !projectForm.name} onClick={createProject}>
                <FolderPlus className="h-4 w-4" />
                创建项目
              </button>
            </div>
          </div>
          {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
        </Panel>

        <Panel title="Project Library" eyebrow="catalog">
          {loading ? (
            <p className="text-sm text-stone-400">正在加载项目...</p>
          ) : projects.length === 0 ? (
            <EmptyState title="还没有项目" body="先在左侧创建一个剧情系列，随后就能进入角色资产、剧情拆解和镜头生成。" />
          ) : (
            <div className="space-y-3">
              {projects.map((project) => (
                <button
                  key={project.id}
                  className={`w-full rounded-[26px] border px-5 py-4 text-left transition ${
                    project.id === selectedProjectId
                      ? "border-amber-200/35 bg-amber-200/10"
                      : "border-white/8 bg-black/10 hover:border-white/16 hover:bg-white/6"
                  }`}
                  onClick={() => setSelectedProjectId(project.id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-display text-2xl text-stone-50">{project.name}</p>
                      <p className="mt-1 text-sm text-stone-400">
                        {project.genre} · {project.style} · {project.aspect_ratio}
                      </p>
                    </div>
                    <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.25em] text-stone-300">
                      {project.status}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Panel
          title={selectedProject ? selectedProject.name : "项目详情"}
          eyebrow="selected project"
          aside={
            selectedProject ? (
              <div className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.24em] text-stone-400">
                <span>{selectedProject.genre}</span>
                <span>{selectedProject.style}</span>
                <span>{selectedProject.aspect_ratio}</span>
              </div>
            ) : null
          }
        >
          {selectedProject ? (
            <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-[28px] border border-white/10 bg-black/15 p-5">
                <div className="mb-4 flex items-center gap-3">
                  <Radar className="h-5 w-5 text-amber-200" />
                  <p className="text-sm uppercase tracking-[0.28em] text-stone-400">Quick links</p>
                </div>
                <div className="grid gap-3">
                  <Link className="secondary-button inline-flex items-center justify-between" href={`/projects/${selectedProject.id}/characters`}>
                    进入角色与场景资产
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  {latestEpisode ? (
                    <>
                      <Link className="secondary-button inline-flex items-center justify-between" href={`/projects/${selectedProject.id}/episodes/${latestEpisode.id}/storyboard`}>
                        进入剧情与分镜
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                      <Link className="secondary-button inline-flex items-center justify-between" href={`/projects/${selectedProject.id}/episodes/${latestEpisode.id}/generation`}>
                        进入镜头生成
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                      <Link className="secondary-button inline-flex items-center justify-between" href={`/projects/${selectedProject.id}/episodes/${latestEpisode.id}/render`}>
                        进入粗剪导出
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </>
                  ) : null}
                </div>
              </div>

              <div className="rounded-[28px] border border-white/10 bg-black/15 p-5">
                <div className="mb-4 flex items-center gap-3">
                  <Users className="h-5 w-5 text-mint-200" />
                  <p className="text-sm uppercase tracking-[0.28em] text-stone-400">资产概览</p>
                </div>
                <div className="space-y-3 text-sm text-stone-300">
                  <p>角色资产：{selectedProject.characters?.length ?? 0}</p>
                  <p>场景资产：{selectedProject.locations?.length ?? 0}</p>
                  <p>剧集数量：{selectedProject.episodes?.length ?? 0}</p>
                  <p>目标总时长：{selectedProject.target_duration}s</p>
                </div>
              </div>
            </div>
          ) : (
            <EmptyState title="选择一个项目" body="右侧会显示该项目的剧集、资产和快捷入口。" />
          )}
        </Panel>

        <Panel title="Create Episode" eyebrow="episode manager">
          {!selectedProject ? (
            <EmptyState title="还没有选中项目" body="先从项目库选择一个项目，再为它创建第一集。" />
          ) : (
            <div className="space-y-5">
              <div className="grid gap-4">
                <div>
                  <FieldLabel>单集标题</FieldLabel>
                  <input value={episodeForm.title} onChange={(event) => setEpisodeForm({ ...episodeForm, title: event.target.value })} placeholder="例如：第 1 集 · 雨夜录音" />
                </div>
                <div>
                  <FieldLabel>一句话剧情</FieldLabel>
                  <textarea
                    rows={4}
                    value={episodeForm.logline}
                    onChange={(event) => setEpisodeForm({ ...episodeForm, logline: event.target.value })}
                    placeholder="写一句可以生成剧情卡的 logline"
                  />
                </div>
                <div>
                  <FieldLabel>目标时长（秒）</FieldLabel>
                  <input
                    type="number"
                    value={episodeForm.target_duration}
                    onChange={(event) => setEpisodeForm({ ...episodeForm, target_duration: Number(event.target.value) })}
                  />
                </div>
              </div>
              <button className="primary-button inline-flex items-center gap-2" disabled={saving || !episodeForm.title} onClick={createEpisode}>
                <Clapperboard className="h-4 w-4" />
                新建单集
              </button>

              <div className="rounded-[28px] border border-white/10 bg-black/15 p-5">
                <div className="mb-4 flex items-center gap-3">
                  <MapPinned className="h-5 w-5 text-amber-200" />
                  <p className="text-sm uppercase tracking-[0.28em] text-stone-400">剧集列表</p>
                </div>
                <div className="space-y-3">
                  {selectedProject.episodes?.length ? (
                    selectedProject.episodes.map((episode) => (
                      <div key={episode.id} className="rounded-[22px] border border-white/8 bg-black/10 p-4">
                        <p className="font-display text-2xl text-stone-50">{episode.title}</p>
                        <p className="mt-2 text-sm text-stone-400">{episode.logline}</p>
                        <div className="mt-3 flex flex-wrap gap-3 text-xs uppercase tracking-[0.22em] text-stone-500">
                          <span>{episode.status}</span>
                          <span>{episode.export_status}</span>
                          <span>{episode.target_duration}s</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-stone-400">还没有剧集。</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </StudioShell>
  );
}
