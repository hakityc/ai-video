"use client";

import { Film, ImageUp, MapPinned, Plus, Upload } from "lucide-react";
import { useEffect, useState } from "react";

import { apiRequest, getProject, uploadAsset } from "@/lib/api";
import type { AssetReference, Character, Location, Project } from "@/lib/types";
import { EmptyState, FieldLabel, Panel } from "./common";
import { StudioShell } from "./studio-shell";

function toTags(text: string) {
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function CharacterStudio({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [characterFile, setCharacterFile] = useState<File | null>(null);
  const [locationFile, setLocationFile] = useState<File | null>(null);
  const [characterAssets, setCharacterAssets] = useState<AssetReference[]>([]);
  const [locationAssets, setLocationAssets] = useState<AssetReference[]>([]);
  const [characterForm, setCharacterForm] = useState({
    name: "",
    age_tag: "",
    appearance_desc: "",
    personality_desc: "",
    speaking_style: "",
    costume_desc: "",
    locked_attributes_text: "",
  });
  const [locationForm, setLocationForm] = useState({
    name: "",
    description: "",
    style_tags_text: "",
  });

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const detail = await getProject(projectId);
      setProject(detail);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载项目失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function pushAsset(file: File, kind: string, setter: (next: AssetReference[]) => void, current: AssetReference[]) {
    const uploaded = await uploadAsset(projectId, file, kind);
    setter([...current, { asset_id: uploaded.id, url: uploaded.url, label: file.name }]);
  }

  async function createCharacter() {
    try {
      await apiRequest<Character>(`/projects/${projectId}/characters`, {
        method: "POST",
        body: JSON.stringify({
          ...characterForm,
          locked_attributes: toTags(characterForm.locked_attributes_text),
          reference_assets: characterAssets,
        }),
      });
      setCharacterForm({
        name: "",
        age_tag: "",
        appearance_desc: "",
        personality_desc: "",
        speaking_style: "",
        costume_desc: "",
        locked_attributes_text: "",
      });
      setCharacterAssets([]);
      setCharacterFile(null);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建角色失败");
    }
  }

  async function createLocation() {
    try {
      await apiRequest<Location>(`/projects/${projectId}/locations`, {
        method: "POST",
        body: JSON.stringify({
          name: locationForm.name,
          description: locationForm.description,
          style_tags: toTags(locationForm.style_tags_text),
          reference_assets: locationAssets,
        }),
      });
      setLocationForm({ name: "", description: "", style_tags_text: "" });
      setLocationAssets([]);
      setLocationFile(null);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建场景失败");
    }
  }

  return (
    <StudioShell title={project?.name ?? "角色资产"} eyebrow="character studio" projectId={projectId} activeHref={`/projects/${projectId}/characters`}>
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Create Character Card" eyebrow="character asset">
          <div className="grid gap-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <FieldLabel>角色名称</FieldLabel>
                <input value={characterForm.name} onChange={(event) => setCharacterForm({ ...characterForm, name: event.target.value })} />
              </div>
              <div>
                <FieldLabel>年龄标签</FieldLabel>
                <input value={characterForm.age_tag} onChange={(event) => setCharacterForm({ ...characterForm, age_tag: event.target.value })} placeholder="青年 / 中年 / 少年" />
              </div>
            </div>
            <div>
              <FieldLabel>外貌描述</FieldLabel>
              <textarea rows={3} value={characterForm.appearance_desc} onChange={(event) => setCharacterForm({ ...characterForm, appearance_desc: event.target.value })} />
            </div>
            <div>
              <FieldLabel>性格描述</FieldLabel>
              <textarea rows={3} value={characterForm.personality_desc} onChange={(event) => setCharacterForm({ ...characterForm, personality_desc: event.target.value })} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <FieldLabel>说话风格</FieldLabel>
                <input value={characterForm.speaking_style} onChange={(event) => setCharacterForm({ ...characterForm, speaking_style: event.target.value })} />
              </div>
              <div>
                <FieldLabel>服装描述</FieldLabel>
                <input value={characterForm.costume_desc} onChange={(event) => setCharacterForm({ ...characterForm, costume_desc: event.target.value })} />
              </div>
            </div>
            <div>
              <FieldLabel>禁止变化项（逗号分隔）</FieldLabel>
              <input value={characterForm.locked_attributes_text} onChange={(event) => setCharacterForm({ ...characterForm, locked_attributes_text: event.target.value })} placeholder="黑色短发, 录音笔挂绳, 风衣剪裁" />
            </div>

            <div className="rounded-[26px] border border-white/10 bg-black/15 p-5">
              <div className="mb-4 flex items-center gap-3">
                <ImageUp className="h-5 w-5 text-amber-200" />
                <p className="text-sm uppercase tracking-[0.28em] text-stone-400">角色参考图</p>
              </div>
              <div className="grid gap-4 md:grid-cols-[1fr_auto]">
                <input type="file" onChange={(event) => setCharacterFile(event.target.files?.[0] ?? null)} />
                <button
                  className="secondary-button inline-flex items-center gap-2"
                  disabled={!characterFile}
                  onClick={() => characterFile && pushAsset(characterFile, "character_reference", setCharacterAssets, characterAssets)}
                >
                  <Upload className="h-4 w-4" />
                  上传
                </button>
              </div>
              <div className="mt-4 space-y-2 text-sm text-stone-300">
                {characterAssets.map((asset) => (
                  <div key={asset.url} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
                    <p className="truncate">{asset.label ?? asset.url}</p>
                  </div>
                ))}
              </div>
            </div>

            <button className="primary-button inline-flex items-center gap-2" onClick={createCharacter}>
              <Plus className="h-4 w-4" />
              保存角色卡
            </button>
          </div>
          {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
        </Panel>

        <Panel title="Characters Library" eyebrow="cast">
          {loading ? (
            <p className="text-sm text-stone-400">正在加载角色...</p>
          ) : project?.characters?.length ? (
            <div className="space-y-4">
              {project.characters.map((character) => (
                <div key={character.id} className="rounded-[26px] border border-white/10 bg-black/14 p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <p className="font-display text-3xl text-stone-50">{character.name}</p>
                    <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-stone-400">
                      {character.age_tag || "未标记"}
                    </span>
                  </div>
                  <p className="text-sm leading-6 text-stone-300">{character.appearance_desc}</p>
                  <p className="mt-3 text-sm leading-6 text-stone-400">{character.personality_desc}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {character.locked_attributes.map((item) => (
                      <span key={item} className="rounded-full bg-white/6 px-3 py-1 text-xs text-stone-300">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="还没有角色卡" body="在左侧填写角色设定并上传参考图，后续剧情卡与镜头生成会直接复用这些资产。" />
          )}
        </Panel>
      </div>

      <Panel title="Create Location Card" eyebrow="scene asset">
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="grid gap-4">
            <div>
              <FieldLabel>场景名称</FieldLabel>
              <input value={locationForm.name} onChange={(event) => setLocationForm({ ...locationForm, name: event.target.value })} placeholder="雨夜便利店" />
            </div>
            <div>
              <FieldLabel>场景描述</FieldLabel>
              <textarea rows={4} value={locationForm.description} onChange={(event) => setLocationForm({ ...locationForm, description: event.target.value })} />
            </div>
            <div>
              <FieldLabel>风格标签（逗号分隔）</FieldLabel>
              <input value={locationForm.style_tags_text} onChange={(event) => setLocationForm({ ...locationForm, style_tags_text: event.target.value })} placeholder="霓虹, 潮湿, 24h, 监控感" />
            </div>
            <div className="rounded-[26px] border border-white/10 bg-black/15 p-5">
              <div className="mb-4 flex items-center gap-3">
                <Film className="h-5 w-5 text-mint-200" />
                <p className="text-sm uppercase tracking-[0.28em] text-stone-400">场景参考图</p>
              </div>
              <div className="grid gap-4 md:grid-cols-[1fr_auto]">
                <input type="file" onChange={(event) => setLocationFile(event.target.files?.[0] ?? null)} />
                <button
                  className="secondary-button inline-flex items-center gap-2"
                  disabled={!locationFile}
                  onClick={() => locationFile && pushAsset(locationFile, "location_reference", setLocationAssets, locationAssets)}
                >
                  <Upload className="h-4 w-4" />
                  上传
                </button>
              </div>
              <div className="mt-4 space-y-2 text-sm text-stone-300">
                {locationAssets.map((asset) => (
                  <div key={asset.url} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
                    <p className="truncate">{asset.label ?? asset.url}</p>
                  </div>
                ))}
              </div>
            </div>
            <button className="primary-button inline-flex items-center gap-2" onClick={createLocation}>
              <MapPinned className="h-4 w-4" />
              保存场景卡
            </button>
          </div>

          <div className="space-y-4">
            {project?.locations?.length ? (
              project.locations.map((location) => (
                <div key={location.id} className="rounded-[26px] border border-white/10 bg-black/14 p-5">
                  <div className="mb-3 flex items-center gap-3">
                    <MapPinned className="h-4 w-4 text-amber-200" />
                    <p className="font-display text-3xl text-stone-50">{location.name}</p>
                  </div>
                  <p className="text-sm leading-6 text-stone-300">{location.description}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {location.style_tags.map((item) => (
                      <span key={item} className="rounded-full bg-white/6 px-3 py-1 text-xs text-stone-300">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="还没有场景卡" body="补充世界观场景后，剧情卡和分镜生成会更稳，镜头路由也能利用参考图。" />
            )}
          </div>
        </div>
      </Panel>
    </StudioShell>
  );
}
