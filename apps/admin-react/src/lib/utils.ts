import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { navigation, taskKindLabels, providerPresetOptions } from "../constants"
import type {
  PrimaryKey,
  ProviderConnection,
  ModelKind,
  ProviderModelGroup,
  TaskStatus,
  AppStateResponse,
  ModelHealthEntry,
} from "../types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function resolveRouteFromHash(hash: string) {
  const normalized = hash.replace(/^#/, "").split("/").filter(Boolean)
  const primary = (navigation.find((item) => item.key === normalized[0])?.key as PrimaryKey) ?? "generation"
  const sections = navigation.find((item) => item.key === primary)?.sections ?? []
  const secondary = sections.find((item) => item.key === normalized[1])?.key ?? sections[0]?.key ?? "scripts"
  return { primary, secondary }
}

export function matchesQuery(query: string, ...values: Array<string | number | null | undefined>) {
  if (!query.trim()) {
    return true
  }
  const normalized = query.trim().toLowerCase()
  return values.some((value) => String(value ?? "").toLowerCase().includes(normalized))
}

export function formatTimestamp(value: string | number | null | undefined) {
  if (!value) {
    return "未记录"
  }
  const date = new Date(typeof value === "number" ? value * 1000 : value)
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

export function formatRelativeTime(value: string | null | undefined) {
  if (!value) {
    return "未开始"
  }
  const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000)
  if (seconds < 60) {
    return `${seconds} 秒前`
  }
  if (seconds < 3600) {
    return `${Math.round(seconds / 60)} 分钟前`
  }
  if (seconds < 86400) {
    return `${Math.round(seconds / 3600)} 小时前`
  }
  return `${Math.round(seconds / 86400)} 天前`
}

export function formatDuration(startedAt: string | null, endedAt: string | null) {
  if (!startedAt) {
    return "排队中"
  }
  const end = endedAt ? new Date(endedAt).getTime() : Date.now()
  const start = new Date(startedAt).getTime()
  const seconds = Math.max(1, Math.round((end - start) / 1000))
  if (seconds < 60) {
    return `${seconds} 秒`
  }
  return `${Math.round(seconds / 60)} 分钟`
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function outputCategoryFromPath(path: string) {
  if (path.includes("/seedance/")) {
    return "兼容视频模型"
  }
  if (path.includes("/comfyui/")) {
    return "ComfyUI"
  }
  if (path.includes("/cogvideox/")) {
    return "CogVideoX"
  }
  return "其他"
}

export function taskMeta(kind: string) {
  return taskKindLabels[kind] ?? { category: "generation" as const, label: kind }
}

export function providerTypeLabel(providerType: ProviderConnection["provider_type"]) {
  if (providerType === "openai-compatible") return "OpenAI 兼容"
  if (providerType === "comfyui") return "ComfyUI"
  if (providerType === "cogvideox") return "CogVideoX"
  return "自定义"
}

export function providerPresetFor(provider: ProviderConnection | null) {
  if (!provider) {
    return null
  }
  return (
    providerPresetOptions.find(
      (item) => provider.id === item.key || provider.id.startsWith(`${item.key}-`) || provider.name === item.label,
    ) ?? null
  )
}

export function parseModelOptionList(value: string | null | undefined) {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

export function uniqueStrings(values: string[]) {
  const seen = new Set<string>()
  return values.filter((value) => {
    const normalized = value.trim().toLowerCase()
    if (!normalized || seen.has(normalized)) {
      return false
    }
    seen.add(normalized)
    return true
  })
}

export function preferredGroupIdForProvider(provider: ProviderConnection | null) {
  if (!provider) {
    return null
  }
  const preset = providerPresetFor(provider)
  if (preset) {
    return preset.key
  }
  if (provider.provider_type === "cogvideox") {
    return "cogvideox-local"
  }
  return null
}

export function findProviderForModel(
  providers: ProviderConnection[],
  kind: ModelKind,
  value: string | null | undefined,
) {
  const target = String(value ?? "").trim()
  if (!target) {
    return null
  }
  const fieldName =
    kind === "text" ? "text_model" : kind === "image" ? "image_model" : "video_model"
  return (
    providers.find((provider) => (provider as any)[fieldName] === target) ??
    (kind === "video" ? providers.find((provider) => provider.local_model === target) : null)
  )
}

export function orderedModelGroups(
  groups: ProviderModelGroup[],
  kind: ModelKind,
  preferredGroupId?: string | null,
) {
  return groups
    .filter((group) => (group.models[kind] ?? []).length > 0)
    .sort((left, right) => {
      if (preferredGroupId && left.provider_id === preferredGroupId) return -1
      if (preferredGroupId && right.provider_id === preferredGroupId) return 1
      return left.provider_label.localeCompare(right.provider_label, "zh-CN")
    })
}

export function modelOptionsFromGroups(
  groups: ProviderModelGroup[],
  kind: ModelKind,
  preferredGroupId?: string | null,
  extraValues: string[] = [],
) {
  const values = orderedModelGroups(groups, kind, preferredGroupId).flatMap((group) => group.models[kind] ?? [])
  return uniqueStrings([...extraValues, ...values])
}

export function filterModelGroupsByAbility(
  groups: ProviderModelGroup[],
  entries: ModelHealthEntry[],
  kind: ModelKind,
  ability: string,
) {
  const healthyByProvider = new Map<string, Set<string>>()
  for (const entry of entries) {
    if (entry.kind !== kind || entry.overall_status !== "healthy") {
      continue
    }
    if (!entry.provider_manual_enabled || !entry.manual_enabled) {
      continue
    }
    if (!entry.ability_states.some((item) => item.ability === ability && item.status === "healthy")) {
      continue
    }
    if (!healthyByProvider.has(entry.provider_id)) {
      healthyByProvider.set(entry.provider_id, new Set<string>())
    }
    healthyByProvider.get(entry.provider_id)?.add(entry.model_id)
  }

  return groups
    .map((group) => {
      const allowed = healthyByProvider.get(group.provider_id) ?? new Set<string>()
      return {
        ...group,
        models: {
          ...group.models,
          [kind]: group.models[kind].filter((model) => allowed.has(model)),
        },
      }
    })
    .filter((group) => group.models[kind].length > 0)
}

export function blockedOptionsForAbility(
  entries: ModelHealthEntry[],
  kind: ModelKind,
  ability: string,
) {
  const reasons = new Map<string, string>()
  for (const entry of entries) {
    if (entry.kind !== kind) {
      continue
    }
    const abilityState = entry.ability_states.find((item) => item.ability === ability)
    if (!abilityState) {
      continue
    }
    if (
      entry.overall_status === "healthy" &&
      entry.provider_manual_enabled &&
      entry.manual_enabled &&
      abilityState.status === "healthy"
    ) {
      continue
    }
    reasons.set(entry.model_id.trim().toLowerCase(), abilityState.reason || entry.reason || "当前模型不可用")
  }
  return Object.fromEntries(reasons)
}

export function statusTone(status: TaskStatus | "warning" | "ok" | "pending") {
  if (status === "failed" || status === "warning") {
    return "border-amber-500/30 bg-amber-500/10 text-amber-100"
  }
  if (status === "succeeded" || status === "ok") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
  }
  if (status === "running") {
    return "border-sky-500/30 bg-sky-500/10 text-sky-100"
  }
  return "border-white/10 bg-white/5 text-white/70"
}

export function getSectionCount(data: AppStateResponse | null, primary: PrimaryKey, secondary: string) {
  if (!data) {
    return 0
  }

  if (primary === "generation") {
    if (secondary === "scripts") return data.app.generation.counts.scripts ?? 0
    if (secondary === "characters") return data.app.generation.counts.characters ?? 0
    if (secondary === "assets") {
      return (
        (data.app.generation.counts.scenes ?? 0) +
        (data.app.generation.counts.props ?? 0) +
        (data.app.generation.counts.shot_templates ?? 0)
      )
    }
    if (secondary === "episodes") return data.app.generation.counts.episodes ?? 0
    if (secondary === "jobs") return data.app.generation.counts.jobs ?? 0
    if (secondary === "outputs") return data.app.generation.counts.outputs ?? 0
  }

  if (primary === "qa") {
    if (secondary === "bridge") {
      return data.app.qa.episodes.reduce((count, entry) => count + (entry.rendered_shots?.length ?? 0), 0)
    }
    return data.app.qa.count
  }

  if (primary === "tasks") {
    if (secondary === "all") return data.tasks.length
    return data.tasks.filter((task) => taskMeta(task.kind).category === secondary).length
  }

  return 0
}

export function scoreText(value?: number) {
  return typeof value === "number" ? value.toFixed(3) : "-"
}

export function taskStatusLabel(status: TaskStatus) {
  if (status === "queued") return "排队中"
  if (status === "running") return "执行中"
  if (status === "succeeded") return "已完成"
  return "失败"
}
