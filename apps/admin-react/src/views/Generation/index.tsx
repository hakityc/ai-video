import * as React from "react"
import { useDeferredValue, useEffect, useState } from "react"
import { motion } from "motion/react"
import {
  Shuffle,
  Wand2,
  Settings2,
  UserRound,
  SlidersHorizontal,
  Film,
  Search,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

import {
  WorkspaceCard,
  Field,
  SearchField,
  ModelField,
  EmptyState,
} from "../../components/ProjectUI"
import {
  blockedOptionsForAbility,
  filterModelGroupsByAbility,
  matchesQuery,
  formatTimestamp,
  statusTone,
} from "../../lib/utils"
import {
  scriptLengthOptions,
  scriptSeedPresets,
  characterSeedPresets,
} from "../../constants"
import type {
  AppStateResponse,
  EffectiveDefaults,
  ModelHealthEntry,
  PrimaryKey,
  ProviderModelGroup,
} from "../../types"

interface GenerationViewProps {
  data: AppStateResponse
  activeSecondary: string
  refreshState: (showLoading?: boolean) => Promise<void>
  runBackgroundAction: (url: string, payload: unknown, successText: string) => Promise<void>
  openText: (path: string) => Promise<void>
  switchPrimary: (primary: PrimaryKey, secondary?: string) => void
  switchSecondary: (primary: PrimaryKey, secondary: string) => void
  settings: Record<string, string>
  providerModelGroups: ProviderModelGroup[]
  modelHealthEntries: ModelHealthEntry[]
  effectiveDefaults: EffectiveDefaults
  selectedProviderGroupId: string | null
}

export function GenerationView({
  data,
  activeSecondary,
  runBackgroundAction,
  openText,
  switchPrimary,
  switchSecondary,
  settings,
  providerModelGroups,
  modelHealthEntries,
  effectiveDefaults,
  selectedProviderGroupId,
}: GenerationViewProps) {
  const safeEffectiveDefaults = effectiveDefaults ?? {
    script_generation: null,
    character_generation: null,
    shortform_generation: null,
  }
  const safeModelHealthEntries = modelHealthEntries ?? []

  const scriptDefaults = safeEffectiveDefaults.script_generation?.models ?? {}
  const characterDefaults = safeEffectiveDefaults.character_generation?.models ?? {}
  const shortformDefaults = safeEffectiveDefaults.shortform_generation?.models ?? {}

  // States moved from App.tsx
  const [scriptForm, setScriptForm] = useState({
    title: "",
    slug: "",
    concept: "",
    tone: "",
    text_model: scriptDefaults.text || settings.OPENAI_MODEL || "",
    length_profile: "short",
    seed_text: "",
  })
  const [characterForm, setCharacterForm] = useState({
    slug: "",
    concept: "",
    text_model: characterDefaults.text || settings.OPENAI_MODEL || "",
    image_model: characterDefaults.image || settings.OPENAI_IMAGE_MODEL || "",
    reference_preset: "turnaround",
    reference_image: "",
    relationship_hint: "",
    story_anchor: "",
    consistency_tags: ["面部特征锁定", "服装细节锁定"] as string[],
  })
  const [episodeConfig, setEpisodeConfig] = useState({
    image_model: shortformDefaults.image || settings.OPENAI_IMAGE_MODEL || "",
    video_model: shortformDefaults.video || settings.OPENAI_VIDEO_MODEL || "",
    ratio: settings.OPENAI_VIDEO_RATIO || "16:9",
    duration: Number(settings.OPENAI_VIDEO_DURATION || "5"),
    resolution: settings.OPENAI_VIDEO_RESOLUTION || "720p",
  })

  const [scriptQuery, setScriptQuery] = useState("")
  const [characterQuery, setCharacterQuery] = useState("")
  const [episodeQuery, setEpisodeQuery] = useState("")
  
  const [scriptAdvancedOpen, setScriptAdvancedOpen] = useState(false)
  const [characterAdvancedOpen, setCharacterAdvancedOpen] = useState(false)

  const deferredScriptQuery = useDeferredValue(scriptQuery)
  const deferredCharacterQuery = useDeferredValue(characterQuery)
  const deferredEpisodeQuery = useDeferredValue(episodeQuery)

  useEffect(() => {
    setScriptForm((current) =>
      current.text_model.trim()
        ? current
        : { ...current, text_model: scriptDefaults.text || settings.OPENAI_MODEL || "" },
    )
    setCharacterForm((current) => ({
      ...current,
      text_model: current.text_model || characterDefaults.text || settings.OPENAI_MODEL || "",
      image_model: current.image_model || characterDefaults.image || settings.OPENAI_IMAGE_MODEL || "",
    }))
    setEpisodeConfig((current) => ({
      ...current,
      image_model: current.image_model || shortformDefaults.image || settings.OPENAI_IMAGE_MODEL || "",
      video_model: current.video_model || shortformDefaults.video || settings.OPENAI_VIDEO_MODEL || "",
    }))
  }, [
    characterDefaults.image,
    characterDefaults.text,
    scriptDefaults.text,
    settings.OPENAI_IMAGE_MODEL,
    settings.OPENAI_MODEL,
    settings.OPENAI_VIDEO_MODEL,
    shortformDefaults.image,
    shortformDefaults.video,
  ])

  useEffect(() => {
    const handleReuse = (e: Event) => {
      const customEvent = e as CustomEvent
      const { kind, payload } = customEvent.detail
      if (!payload) return

      if (kind === "generate_script") {
        setScriptForm(prev => ({
          ...prev,
          title: payload.title || prev.title,
          slug: payload.slug || prev.slug,
          concept: payload.concept || prev.concept,
          tone: payload.tone || prev.tone,
          text_model: payload.text_model || prev.text_model,
          length_profile: payload.length_profile || prev.length_profile,
          seed_text: payload.seed_text || prev.seed_text,
        }))
        if (payload.text_model || payload.slug || payload.tone || payload.seed_text || payload.length_profile) {
          setScriptAdvancedOpen(true)
        }
        switchSecondary("generation", "scripts")
      } else if (kind === "generate_character") {
        setCharacterForm(prev => ({
          ...prev,
          slug: payload.slug || prev.slug,
          concept: payload.concept || prev.concept,
          text_model: payload.text_model || prev.text_model,
          image_model: payload.image_model || prev.image_model,
          reference_preset: payload.reference_preset || prev.reference_preset,
          reference_image: payload.reference_image || prev.reference_image,
        }))
        if (payload.text_model || payload.reference_preset !== "turnaround" || payload.reference_image) {
          setCharacterAdvancedOpen(true)
        }
        switchSecondary("generation", "characters")
      }
    }

    window.addEventListener("reuse-task-payload", handleReuse)
    return () => window.removeEventListener("reuse-task-payload", handleReuse)
  }, [switchSecondary])

  const scriptTextGroups = filterModelGroupsByAbility(providerModelGroups, safeModelHealthEntries, "text", "script_text")
  const characterTextGroups = filterModelGroupsByAbility(providerModelGroups, safeModelHealthEntries, "text", "character_text_json")
  const characterImageGroups = filterModelGroupsByAbility(providerModelGroups, safeModelHealthEntries, "image", "character_image_generation")
  const shortformImageGroups = filterModelGroupsByAbility(providerModelGroups, safeModelHealthEntries, "image", "shortform_image_generation")
  const shortformVideoGroups = filterModelGroupsByAbility(providerModelGroups, safeModelHealthEntries, "video", "shortform_video_generation")

  const scriptBlockedModels = blockedOptionsForAbility(safeModelHealthEntries, "text", "script_text")
  const characterBlockedTextModels = blockedOptionsForAbility(safeModelHealthEntries, "text", "character_text_json")
  const characterBlockedImageModels = blockedOptionsForAbility(safeModelHealthEntries, "image", "character_image_generation")
  const shortformBlockedImageModels = blockedOptionsForAbility(safeModelHealthEntries, "image", "shortform_image_generation")
  const shortformBlockedVideoModels = blockedOptionsForAbility(safeModelHealthEntries, "video", "shortform_video_generation")

  // Derived data
  const filteredScripts = data.app.generation.scripts.filter((item) =>
    matchesQuery(deferredScriptQuery, item.title, item.path, item.preview, item.kind),
  )
  const filteredCharacters = data.app.generation.characters.filter((item) =>
    matchesQuery(deferredCharacterQuery, item.name, item.slug, ...item.style_descriptors),
  )
  const filteredEpisodes = data.app.generation.episodes.filter((item) =>
    matchesQuery(deferredEpisodeQuery, item.episode, item.character, item.scene_pack, item.prop_pack, item.shot_template),
  )

  const allReferenceOptions = data.app.generation.characters.flatMap((character) =>
    character.references
      .filter((reference) => reference.exists)
      .map((reference) => ({
        ...reference,
        label: `${character.name} / ${reference.view}${reference.expression ? ` / ${reference.expression}` : ""}`,
        characterPath: character.path,
        characterName: character.name,
      })),
  )

  const blockedCharacterTextModelReason = characterAdvancedOpen
    ? characterBlockedTextModels[characterForm.text_model.trim().toLowerCase()] ?? ""
    : ""

  // Handlers
  const fillRandomScriptForm = () => {
    const preset = scriptSeedPresets[Math.floor(Math.random() * scriptSeedPresets.length)]
    setScriptForm((current) => ({
      ...current,
      title: preset.title,
      slug: preset.slug,
      concept: preset.concept,
      seed_text: preset.seed_text,
      tone: preset.tone,
      length_profile: preset.length_profile,
    }))
    setScriptAdvancedOpen(true)
  }

  const fillRandomCharacterForm = () => {
    const preset = characterSeedPresets[Math.floor(Math.random() * characterSeedPresets.length)]
    setCharacterForm((current) => ({
      ...current,
      slug: preset.slug,
      concept: preset.concept,
      relationship_hint: preset.relationship_hint,
      story_anchor: preset.story_anchor,
      consistency_tags: preset.consistency_tags,
      reference_preset: preset.reference_preset,
    }))
    setCharacterAdvancedOpen(true)
  }



  const buildCharacterConcept = () => {
    const lines = [characterForm.concept.trim()]
    lines.push(
      characterForm.relationship_hint.trim()
        ? `角色关系与对手戏重点：${characterForm.relationship_hint.trim()}`
        : "",
      characterForm.story_anchor.trim()
        ? `剧本锚点与固定场景线索：${characterForm.story_anchor.trim()}`
        : "",
      characterForm.consistency_tags.length
        ? `一致性优先级：${characterForm.consistency_tags.join("、")}`
        : "",
      characterForm.reference_preset === "turnaround"
        ? "需要稳定四视图参考，优先保证后续链式短视频生成的一致性。"
        : "先生成快速双视图参考，便于快速确认角色方向。",
    )
    return lines.filter(Boolean).join("\n")
  }

  if (activeSecondary === "scripts") {
    return (
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <WorkspaceCard
          eyebrow="视频生成"
          title="文案脚本"
          description="先填两个必填项就能生成。高级项只在需要时展开，避免一上来被一堆参数打断。"
          action={
            <Button variant="outline" onClick={fillRandomScriptForm}>
              <Shuffle className="size-4" />
              随机填充一版
            </Button>
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="标题">
              <Input
                value={scriptForm.title}
                onChange={(event) =>
                  setScriptForm((current) => ({ ...current, title: event.target.value }))
                }
                placeholder="例如：夜班地铁守灯人"
              />
            </Field>
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm leading-6 text-emerald-50">
              必填只保留标题和核心概念。模型、长度、种子段落和风格限制都放到高级项里。
            </div>
          </div>
          <Field label="核心概念">
            <Textarea
              rows={6}
              className="max-h-[320px] overflow-y-auto"
              value={scriptForm.concept}
              onChange={(event) =>
                setScriptForm((current) => ({ ...current, concept: event.target.value }))
              }
              placeholder="用中文写清楚人物、场景、冲突和你想要的内容方向。"
            />
          </Field>
          <Collapsible open={scriptAdvancedOpen} onOpenChange={setScriptAdvancedOpen} className="space-y-3">
            <CollapsibleTrigger asChild>
              <Button variant="outline" className="w-full justify-between border-white/10 bg-black/20">
                可选高级项
                <span className="text-xs text-white/45">{scriptAdvancedOpen ? "收起" : "展开"}</span>
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="英文 slug">
                  <Input
                    value={scriptForm.slug}
                    onChange={(event) =>
                      setScriptForm((current) => ({ ...current, slug: event.target.value }))
                    }
                    placeholder="night-shift-keeper"
                  />
                </Field>
                <Field label="文案模型">
                  <ModelField
                    value={scriptForm.text_model}
                    options={[]}
                    groups={scriptTextGroups}
                    kind="text"
                    preferredGroupId={selectedProviderGroupId}
                    disabledOptions={scriptBlockedModels}
                    placeholder="选择文案模型"
                    onChange={(value) =>
                      setScriptForm((current) => ({ ...current, text_model: value }))
                    }
                  />
                </Field>
              </div>
              <div className="grid gap-4 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                <Field label="文案长度">
                  <Select
                    value={scriptForm.length_profile}
                    onValueChange={(value) =>
                      setScriptForm((current) => ({ ...current, length_profile: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择文案长度" />
                    </SelectTrigger>
                    <SelectContent>
                      {scriptLengthOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label} · {option.estimate}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-white/40">估算成片时长</p>
                  <p className="mt-2 text-sm font-medium text-white">
                    {scriptLengthOptions.find((item) => item.value === scriptForm.length_profile)?.estimate}
                  </p>
                  <p className="mt-2 text-xs leading-5 text-white/52">
                    {scriptLengthOptions.find((item) => item.value === scriptForm.length_profile)?.guidance}
                  </p>
                </div>
              </div>
              <Field label="扩写种子段落" description="先写一小段原始想法，系统会基于它扩写。">
                <Textarea
                  rows={4}
                  value={scriptForm.seed_text}
                  onChange={(event) =>
                    setScriptForm((current) => ({ ...current, seed_text: event.target.value }))
                  }
                  placeholder="例如：深夜地铁停运后，女主发现站台广告牌会在无人时说话……"
                />
              </Field>
              <Field label="风格与限制">
                <Textarea
                  rows={4}
                  value={scriptForm.tone}
                  onChange={(event) =>
                    setScriptForm((current) => ({ ...current, tone: event.target.value }))
                  }
                  placeholder="例如：口语化、适合短视频、避免悬浮设定。"
                />
              </Field>
            </CollapsibleContent>
          </Collapsible>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() =>
                runBackgroundAction("/api/scripts/generate", scriptForm, "文案生成已提交")
              }
              className="min-w-36 bg-emerald-600 text-white hover:bg-emerald-700 shadow-lg shadow-emerald-900/20"
            >
              <Wand2 className="size-4" />
              生成文案
            </Button>
            <Button variant="outline" onClick={() => switchPrimary("settings")}>
              <Settings2 className="size-4" />
              去调整模型策略
            </Button>
          </div>
        </WorkspaceCard>

        <WorkspaceCard
          eyebrow="文案库"
          title="最近文案"
          description="列表默认收敛，只展示最相关内容，避免一屏塞太多。"
        >
          <SearchField value={scriptQuery} onChange={setScriptQuery} placeholder="搜索标题、路径或内容" />
          <ScrollArea className="h-[540px]">
            <div className="space-y-3 pr-4">
              {filteredScripts.slice(0, 6).map((item) => (
                <Card key={item.path} className="border-white/10 bg-white/5">
                  <CardContent className="space-y-3 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">{item.title}</p>
                        <p className="mt-1 text-xs text-white/45">{item.path}</p>
                      </div>
                      <Badge className={statusTone("pending")}>{item.kind === "story" ? "故事文案" : "剧集备注"}</Badge>
                    </div>
                    <p className="text-sm leading-6 text-white/72">{item.preview || "暂无预览内容"}</p>
                    <div className="flex items-center justify-between text-xs text-white/45">
                      <span>{formatTimestamp(item.updated_at)}</span>
                      <Button variant="outline" size="sm" onClick={() => openText(item.path)}>
                        查看原文
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {!filteredScripts.length ? <EmptyState title="没有匹配的文案" description="换个关键词或先生成一份新文案。" /> : null}
            </div>
          </ScrollArea>
          {filteredScripts.length > 6 ? (
            <p className="text-xs text-white/45">当前只展示前 6 条，继续搜索可以更快定位。</p>
          ) : null}
        </WorkspaceCard>
      </div>
    )
  }

  if (activeSecondary === "characters") {
    return (
      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <WorkspaceCard
          eyebrow="角色生产"
          title="角色生成"
          description="先填角色概念就能生成。关系、锚点、一致性按钮和图生图参考都放在可选项里。"
          action={
            <Button variant="outline" onClick={fillRandomCharacterForm}>
              <Shuffle className="size-4" />
              随机填充一版
            </Button>
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="角色 slug">
              <Input
                value={characterForm.slug}
                onChange={(event) =>
                  setCharacterForm((current) => ({ ...current, slug: event.target.value }))
                }
                placeholder="protagonist-nightguard"
              />
            </Field>
            <Field label="出图模型">
              <ModelField
                value={characterForm.image_model}
                options={[]}
                groups={characterImageGroups}
                kind="image"
                preferredGroupId={selectedProviderGroupId}
                disabledOptions={characterBlockedImageModels}
                placeholder="选择出图模型"
                onChange={(value) =>
                  setCharacterForm((current) => ({ ...current, image_model: value }))
                }
              />
            </Field>
          </div>
          <Field label="角色概念">
            <Textarea
              rows={8}
              className="max-h-[360px] overflow-y-auto"
              value={characterForm.concept}
              onChange={(event) =>
                setCharacterForm((current) => ({ ...current, concept: event.target.value }))
              }
              placeholder="尽量写清楚脸型、发型、年龄感、穿着、气质和世界观。"
            />
          </Field>
          <Field label="参考图 (图生图)" description="上传新图片、粘贴图片链接，或选择已有角色图，优先从中提取面部和服装特征。">
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <Input
                  type="file"
                  accept="image/*"
                  className="w-full max-w-[200px] cursor-pointer"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    const formData = new FormData()
                    formData.append("file", file)
                    try {
                      const res = await fetch("/api/upload", { method: "POST", body: formData })
                      if (!res.ok) throw new Error("Upload failed")
                      const { path } = await res.json()
                      setCharacterForm((current) => ({ ...current, reference_image: path }))
                    } catch (err) {
                      console.error("Upload failed", err)
                      alert("图片上传失败")
                    }
                  }}
                />
                <span className="text-xs text-white/45">或</span>
                <Input
                  type="text"
                  placeholder="粘贴图片URL (http/https)"
                  className="w-full max-w-[200px]"
                  value={characterForm.reference_image?.startsWith("http") ? characterForm.reference_image : ""}
                  onChange={(e) => {
                    const val = e.target.value.trim()
                    // Only update if it's a URL or if it's being cleared while currently a URL
                    if (val.startsWith("http") || val === "") {
                      setCharacterForm((current) => ({ ...current, reference_image: val }))
                    }
                  }}
                />
                <span className="text-xs text-white/45">或</span>
                <Select
                  value={
                    !characterForm.reference_image 
                      ? "__none__" 
                      : characterForm.reference_image.startsWith("http")
                      ? "__none__"
                      : characterForm.reference_image
                  }
                  onValueChange={(value) =>
                    setCharacterForm((current) => ({
                      ...current,
                      reference_image: value === "__none__" ? "" : value,
                    }))
                  }
                >
                  <SelectTrigger className="w-full max-w-[200px]">
                    <SelectValue placeholder="不使用参考图" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">不使用参考图</SelectItem>
                    {allReferenceOptions.map((item) => (
                      <SelectItem key={item.path} value={item.path}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {characterForm.reference_image && (
                <div className="text-xs text-emerald-400 break-all">
                  已选用: {characterForm.reference_image.startsWith("http") 
                    ? characterForm.reference_image 
                    : characterForm.reference_image.split('/').pop()}
                </div>
              )}
            </div>
          </Field>
          <Collapsible open={characterAdvancedOpen} onOpenChange={setCharacterAdvancedOpen} className="space-y-3">
            <CollapsibleTrigger asChild>
              <Button variant="outline" className="w-full justify-between border-white/10 bg-black/20">
                可选高级项
                <span className="text-xs text-white/45">{characterAdvancedOpen ? "收起" : "展开"}</span>
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-4">
              <div>
                <Field label="文本模型">
                  <ModelField
                    value={characterForm.text_model}
                    options={[]}
                    groups={characterTextGroups}
                    kind="text"
                    preferredGroupId={selectedProviderGroupId}
                    disabledOptions={characterBlockedTextModels}
                    placeholder="选择文本模型"
                    onChange={(value) =>
                      setCharacterForm((current) => ({ ...current, text_model: value }))
                    }
                  />
                </Field>
              </div>
              {blockedCharacterTextModelReason ? (
                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-50">
                  当前文本模型 <span className="font-semibold">{characterForm.text_model}</span> 已禁用。
                  {blockedCharacterTextModelReason}
                </div>
              ) : null}
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="角色关系 / 对手戏">
                  <Textarea
                    rows={4}
                    value={characterForm.relationship_hint}
                    onChange={(event) =>
                      setCharacterForm((current) => ({
                        ...current,
                        relationship_hint: event.target.value,
                      }))
                    }
                    placeholder="例如：她和站务长既互相提防又互相依赖。"
                  />
                </Field>
                <Field label="剧本锚点 / 固定线索">
                  <Textarea
                    rows={4}
                    value={characterForm.story_anchor}
                    onChange={(event) =>
                      setCharacterForm((current) => ({
                        ...current,
                        story_anchor: event.target.value,
                      }))
                    }
                    placeholder="例如：旧站台、广播噪音、红色工作牌不能变。"
                  />
                </Field>
              </div>
            </CollapsibleContent>
          </Collapsible>
          <div className="rounded-3xl border border-sky-500/20 bg-sky-500/10 p-4">
            <p className="text-sm font-semibold text-white">推荐编排方式</p>
            <p className="mt-2 text-sm leading-6 text-white/72">
              {"更稳的方式不是直接从角色图跳到视频，而是先把角色关系和剧本锚点写进角色圣经，再做稳定参考图；后续先生成通过 QA 的母场景，再让每个镜头只改允许变化项，并沿用上一镜头的 bridge frame 继续生成。这更符合当前链式短视频逻辑，也更贴合一致性 skill 里的 Character Bible First 和 Progressive Disclosure。"}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              disabled={Boolean(blockedCharacterTextModelReason)}
              className="min-w-36 bg-sky-600 text-white hover:bg-sky-700 shadow-lg shadow-sky-900/20"
              onClick={() =>
                runBackgroundAction(
                  "/api/characters/generate",
                  {
                    slug: characterForm.slug,
                    concept: buildCharacterConcept(),
                    image_model: characterForm.image_model,
                    ...(characterAdvancedOpen
                      ? {
                          text_model: characterForm.text_model,
                          reference_preset: characterForm.reference_preset,
                          reference_image: characterForm.reference_image || undefined,
                        }
                      : {}),
                  },
                  "角色生成已提交",
                )
              }
            >
              <UserRound className="size-4" />
              生成角色
            </Button>
            <Button variant="outline" onClick={() => switchSecondary("settings", "models")}>
              <SlidersHorizontal className="size-4" />
              管理模型库
            </Button>
          </div>
        </WorkspaceCard>

        <WorkspaceCard
          eyebrow="角色库"
          title="已生成角色"
          description="每张卡片只保留最关键的参考图和提示词信息，方便快速判断是否可复用。"
        >
          <SearchField
            value={characterQuery}
            onChange={setCharacterQuery}
            placeholder="搜索角色名、slug 或风格词"
          />
          <ScrollArea className="h-[620px]">
            <div className="grid gap-4 pr-4 md:grid-cols-2">
              {filteredCharacters.slice(0, 8).map((item) => (
                <Card key={item.path} className="border-white/10 bg-white/5">
                  <CardContent className="space-y-4 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">{item.name}</p>
                        <p className="mt-1 text-xs text-white/45">{item.slug}</p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => openText(item.path)}>
                        YAML
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {item.references
                        .filter((reference) => reference.url)
                        .slice(0, 4)
                        .map((reference) => (
                          <div
                            key={reference.path}
                            className="overflow-hidden rounded-xl border border-white/10 bg-black/20"
                          >
                            <img
                              src={reference.url ?? undefined}
                              alt={reference.view}
                              className="aspect-square w-full object-cover"
                            />
                            <div className="border-t border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70">
                              {reference.view} / {reference.expression ?? "默认"}
                            </div>
                          </div>
                        ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {item.style_descriptors.slice(0, 3).map((descriptor) => (
                        <Badge key={descriptor} variant="outline" className="border-white/10 bg-white/5 text-white/70">
                          {descriptor}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
              {!filteredCharacters.length ? <EmptyState title="没有匹配的角色" description="先生成角色，或缩小搜索关键词。" /> : null}
            </div>
          </ScrollArea>
        </WorkspaceCard>
      </div>
    )
  }

  if (activeSecondary === "assets") {
    const assetGroups = [
      { key: "scene", title: "场景包", items: data.app.generation.scenes, description: "固定世界元素与场景约束" },
      { key: "prop", title: "道具包", items: data.app.generation.props, description: "角色周边道具与出镜限制" },
      { key: "shot", title: "镜头模板", items: data.app.generation.shotTemplates, description: "镜头框架与允许变化范围" },
    ]

    return (
      <WorkspaceCard
        eyebrow="资产编排"
        title="场景 / 道具 / 镜头模板"
        description="资产部分不用堆成大表格，而是按制作阶段拆开，重点信息只露出一层。"
      >
        <Accordion type="multiple" className="space-y-3">
          {assetGroups.map((group) => (
            <AccordionItem key={group.key} value={group.key} className="rounded-2xl border border-white/10 bg-white/5 px-4">
              <AccordionTrigger className="py-4 text-left">
                <div>
                  <p className="text-sm font-semibold text-white">{group.title}</p>
                  <p className="text-xs text-white/45">{group.description}</p>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="grid gap-3 pb-3 md:grid-cols-2 xl:grid-cols-3">
                  {group.items.slice(0, 6).map((item) => (
                    <Card key={item.path} className="border-white/10 bg-black/20">
                      <CardContent className="space-y-3 p-4">
                        <div>
                          <p className="text-sm font-semibold text-white">{item.name}</p>
                          <p className="mt-1 text-xs text-white/45">{item.path}</p>
                        </div>
                        <div className="space-y-2 text-xs leading-6 text-white/65">
                          {(item.fixed_elements ?? item.fixed_props ?? item.framing ?? []).slice(0, 3).map((value) => (
                            <div key={value} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                              {value}
                            </div>
                          ))}
                          {(item.allowed_changes ?? item.forbidden_drift ?? []).slice(0, 2).map((value) => (
                            <div key={value} className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-amber-50">
                              {value}
                            </div>
                          ))}
                        </div>
                        <Button variant="outline" size="sm" onClick={() => openText(item.path)}>
                          查看配置
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </WorkspaceCard>
    )
  }

  if (activeSecondary === "episodes") {
    return (
      <div className="grid gap-4">
        <WorkspaceCard
          eyebrow="剧集策略"
          title="统一的剧集生成参数"
          description="这里配置一次，候选搜索和整集渲染会共用，避免每次重复填模型。"
        >
          <div className="rounded-3xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm leading-6 text-emerald-50">
            更稳的编排建议：先用文案里的“角色关系 + 世界锚点”建立角色圣经，再生成稳定四视图参考；随后只做一次母场景候选搜索，
            选出通过 QA 的主参考后，每个镜头只写允许变化项，视频阶段继续沿用上一镜头的 bridge frame 做链式续接。
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <Field label="关键帧模型">
              <ModelField
                value={episodeConfig.image_model}
                options={[]}
                groups={shortformImageGroups}
                kind="image"
                preferredGroupId={selectedProviderGroupId}
                disabledOptions={shortformBlockedImageModels}
                placeholder="选择关键帧模型"
                onChange={(value) => setEpisodeConfig((current) => ({ ...current, image_model: value }))}
              />
            </Field>
            <Field label="视频模型">
              <ModelField
                value={episodeConfig.video_model}
                options={[]}
                groups={shortformVideoGroups}
                kind="video"
                preferredGroupId={selectedProviderGroupId}
                disabledOptions={shortformBlockedVideoModels}
                placeholder="选择视频模型"
                onChange={(value) => setEpisodeConfig((current) => ({ ...current, video_model: value }))}
              />
            </Field>
            <Field label="画幅比例">
              <Select
                value={episodeConfig.ratio}
                onValueChange={(value) => setEpisodeConfig((current) => ({ ...current, ratio: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择比例" />
                </SelectTrigger>
                <SelectContent>
                  {data.app.catalog.video_ratios.map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="时长">
              <Select
                value={String(episodeConfig.duration)}
                onValueChange={(value) =>
                  setEpisodeConfig((current) => ({ ...current, duration: Number(value) }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择时长" />
                </SelectTrigger>
                <SelectContent>
                  {data.app.catalog.video_durations.map((value) => (
                    <SelectItem key={value} value={String(value)}>
                      {value} 秒
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="分辨率">
              <Select
                value={episodeConfig.resolution}
                onValueChange={(value) =>
                  setEpisodeConfig((current) => ({ ...current, resolution: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择分辨率" />
                </SelectTrigger>
                <SelectContent>
                  {data.app.catalog.video_resolutions.map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>
        </WorkspaceCard>

        <WorkspaceCard
          eyebrow="剧集库"
          title="剧集规格与生成操作"
          description="按剧集维度管理，卡片里只保留会影响产出的核心信息。"
        >
          <SearchField value={episodeQuery} onChange={setEpisodeQuery} placeholder="搜索剧集、角色或资产包" />
          <div className="grid gap-4 xl:grid-cols-2">
            {filteredEpisodes.slice(0, 6).map((episode) => (
              <motion.div
                key={episode.path}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.22 }}
              >
                <Card className="h-full border-white/10 bg-white/5">
                  <CardContent className="space-y-4 p-4">
                    <div className="flex items-start gap-4">
                      <img
                        src={episode.anchor_image_url}
                        alt={episode.episode}
                        className="size-20 rounded-2xl border border-white/10 object-cover"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-white">{episode.episode}</p>
                            <p className="mt-1 text-xs text-white/45">{episode.character}</p>
                          </div>
                          <Badge className={statusTone(episode.qa_summary?.search_status === "ok" ? "ok" : "pending")}>
                            {episode.qa_summary?.search_status === "ok" ? "已搜索" : "待搜索"}
                          </Badge>
                        </div>
                        <p className="mt-3 line-clamp-3 text-sm leading-6 text-white/70">
                          {episode.master_scene_prompt}
                        </p>
                      </div>
                    </div>

                    <div className="grid gap-2 md:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-white/40">场景</p>
                        <p className="mt-2 text-sm font-medium text-white">{episode.scene_pack}</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-white/40">道具</p>
                        <p className="mt-2 text-sm font-medium text-white">{episode.prop_pack}</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-white/40">镜头</p>
                        <p className="mt-2 text-sm font-medium text-white">{episode.shot_template}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        onClick={() =>
                          runBackgroundAction(
                            "/api/episodes/search-keyframes",
                            { spec_path: episode.path, ...episodeConfig },
                            "候选搜索已提交",
                          )
                        }
                      >
                        <Search className="size-4" />
                        搜索候选
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          runBackgroundAction(
                            "/api/episodes/render",
                            { spec_path: episode.path, ...episodeConfig },
                            "整集渲染已提交",
                          )
                        }
                      >
                        <Film className="size-4" />
                        整集渲染
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => openText(episode.path)}>
                        查看规格
                      </Button>
                    </div>

                    <Accordion type="single" collapsible>
                      <AccordionItem value="shots" className="border-white/10">
                        <AccordionTrigger className="py-2 text-sm text-white/72">
                          查看镜头提示词与污染检查
                        </AccordionTrigger>
                        <AccordionContent>
                          <ScrollArea className="h-60">
                            <div className="space-y-3 pr-4">
                              {episode.shots.map((shot) => (
                                <div key={shot.shot_id} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                                  <div className="flex items-center justify-between gap-3">
                                    <span className="text-sm font-medium text-white">{shot.shot_id}</span>
                                    <Badge className={statusTone(shot.pollution_issues.length ? "warning" : "ok")}>
                                      {shot.pollution_issues.length ? "需处理" : "通过"}
                                    </Badge>
                                  </div>
                                  <p className="mt-2 text-sm leading-6 text-white/65">{shot.prompt}</p>
                                  {shot.pollution_issues.length ? (
                                    <ul className="mt-3 space-y-2 text-xs leading-5 text-amber-50">
                                      {shot.pollution_issues.map((issue, idx) => (
                                        <li key={idx} className="rounded-lg bg-amber-500/10 px-3 py-2">
                                          {issue}
                                        </li>
                                      ))}
                                    </ul>
                                  ) : null}
                                </div>
                              ))}
                            </div>
                          </ScrollArea>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
            {!filteredEpisodes.length ? <EmptyState title="没有匹配的剧集" description="换个关键词或先创建新剧集。" /> : null}
          </div>
        </WorkspaceCard>
      </div>
    )
  }

  return null
}
