import React from "react"
import {
  Save,
  Plus,
  ShieldCheck,
  Power,
  RefreshCw,
  RotateCcw,
  Globe,
  Cpu,
  Trash2,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"

import type {
  AppData,
  ModelHealthEntry,
  PrimaryKey,
  ProviderConnection,
  ProviderHealthSummary,
} from "@/types"
import { cn, formatTimestamp, matchesQuery, providerTypeLabel } from "@/lib/utils"
import { WorkspaceCard, Field, SearchField } from "@/components/ProjectUI"


interface SettingsViewProps {
  data: AppData
  activeSecondary: string
  refreshState: (showLoading?: boolean) => void
  runBackgroundAction: (url: string, body: any, successTitle: string) => void
  runAction: <T = unknown>(url: string, payload: unknown, successText: string) => Promise<T | null>
  settingsForm: Record<string, string>
  setSettingsForm: React.Dispatch<React.SetStateAction<Record<string, string>>>
  providerSettings: {
    selected_provider_id: string
    providers: ProviderConnection[]
  }
  setProviderSettings: React.Dispatch<
    React.SetStateAction<{
      selected_provider_id: string
      providers: ProviderConnection[]
    }>
  >
  providerQuery: string
  setProviderQuery: (val: string) => void
  switchSecondary: (primary: PrimaryKey, secondary: string) => void
}

function providerStatusTone(status: ProviderHealthSummary["status"]) {
  if (status === "healthy") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
  if (status === "degraded") return "border-amber-500/30 bg-amber-500/10 text-amber-100"
  if (status === "unhealthy" || status === "disabled_auto") return "border-red-500/30 bg-red-500/10 text-red-100"
  if (status === "disabled_manual") return "border-white/10 bg-white/5 text-white/60"
  return "border-sky-500/30 bg-sky-500/10 text-sky-100"
}

function providerStatusLabel(status: ProviderHealthSummary["status"]) {
  if (status === "healthy") return "健康"
  if (status === "degraded") return "部分降级"
  if (status === "unhealthy") return "不可用"
  if (status === "disabled_auto") return "自动熔断"
  if (status === "disabled_manual") return "手动禁用"
  return "待体检"
}

function abilityLabel(value: string) {
  if (value === "script_text") return "脚本文本"
  if (value === "character_text_json") return "角色 JSON"
  if (value === "character_image_generation") return "角色出图"
  if (value === "shortform_image_generation") return "关键帧出图"
  if (value === "shortform_video_generation") return "视频生成"
  return value
}

export function SettingsView({
  data,
  activeSecondary,
  refreshState,
  runBackgroundAction,
  runAction,
  settingsForm,
  setSettingsForm,
  providerSettings,
  setProviderSettings,
  providerQuery,
  setProviderQuery,
}: SettingsViewProps) {
  const providerHealthSummary = data.provider_health_summary ?? []
  const modelHealthEntries = data.model_health_entries ?? []
  const effectiveDefaults = data.effective_defaults ?? {
    script_generation: null,
    character_generation: null,
    shortform_generation: null,
  }

  const providerHealthById = new Map<string, ProviderHealthSummary>(
    providerHealthSummary.map((item) => [item.provider_id, item]),
  )
  const modelEntriesByProvider = new Map<string, ModelHealthEntry[]>()
  for (const entry of modelHealthEntries) {
    if (!modelEntriesByProvider.has(entry.provider_id)) {
      modelEntriesByProvider.set(entry.provider_id, [])
    }
    modelEntriesByProvider.get(entry.provider_id)?.push(entry)
  }

  const filteredProviders = providerSettings.providers.filter((provider) =>
    matchesQuery(
      providerQuery,
      provider.name,
      provider.id,
      provider.base_url,
      provider.default_models.text,
      provider.default_models.image,
      provider.default_models.video,
      provider.note,
    ),
  )

  const saveProviders = async () => {
    const response = await runAction<{
      selected_provider_id: string
      providers: ProviderConnection[]
    }>("/api/providers", providerSettings, "Provider 配置已保存并完成体检")
    if (response) {
      setProviderSettings({
        selected_provider_id: response.selected_provider_id,
        providers: response.providers,
      })
    }
  }

  const runHealthCheck = async () => {
    await runAction("/api/providers/health/run", {}, "健康检查已完成")
    refreshState(false)
  }

  const keepHealthyOnly = async () => {
    const response = await runAction<{
      provider_settings: {
        selected_provider_id: string
        providers: ProviderConnection[]
      }
    }>("/api/providers/health/apply", { action: "keep_healthy_only" }, "已禁用异常 provider / model")
    if (response?.provider_settings) {
      setProviderSettings(response.provider_settings)
    }
  }

  const restoreRecovered = async () => {
    const response = await runAction<{
      provider_settings: {
        selected_provider_id: string
        providers: ProviderConnection[]
      }
    }>("/api/providers/health/apply", { action: "recheck_and_restore" }, "已恢复通过体检的项")
    if (response?.provider_settings) {
      setProviderSettings(response.provider_settings)
    }
  }

  const updateProvider = (providerId: string, updater: (provider: ProviderConnection) => ProviderConnection) => {
    setProviderSettings((current) => ({
      ...current,
      providers: current.providers.map((provider) => (provider.id === providerId ? updater(provider) : provider)),
    }))
  }

  const removeProvider = (providerId: string) => {
    setProviderSettings((current) => ({
      selected_provider_id:
        current.selected_provider_id === providerId
          ? current.providers.find((item) => item.id !== providerId)?.id ?? ""
          : current.selected_provider_id,
      providers: current.providers.filter((provider) => provider.id !== providerId),
    }))
  }

  const addProvider = () => {
    const nextIndex = providerSettings.providers.length + 1
    const draft: ProviderConnection = {
      id: `provider-${nextIndex}`,
      name: `新 Provider ${nextIndex}`,
      provider_type: "openai-compatible",
      manual_enabled: true,
      enabled: true,
      base_url: "",
      api_key: "",
      default_models: { text: "", image: "", video: "", local: "" },
      text_model: "",
      image_model: "",
      video_model: "",
      local_model: "",
      extra_config: "",
      note: "",
    }
    setProviderSettings((current) => ({
      selected_provider_id: current.selected_provider_id || draft.id,
      providers: [...current.providers, draft],
    }))
  }

  const saveSystemSettings = async () => {
    await runAction("/api/settings", settingsForm, "系统设置已保存")
  }

  if (activeSecondary === "providers") {
    return (
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <WorkspaceCard
          eyebrow="健康治理"
          title="Provider / Model 控制面"
          description="这里同时管理 provider 配置、默认模型、健康状态和自动熔断结果。执行页默认只展示通过体检的模型。"
          action={
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={addProvider}>
                <Plus className="size-4" />
                添加 Provider
              </Button>
              <Button variant="outline" onClick={runHealthCheck}>
                <RefreshCw className="size-4" />
                立即体检
              </Button>
              <Button variant="outline" onClick={keepHealthyOnly}>
                <ShieldCheck className="size-4" />
                一键禁用异常项
              </Button>
              <Button variant="outline" onClick={restoreRecovered}>
                <RotateCcw className="size-4" />
                恢复已通过体检项
              </Button>
              <Button onClick={saveProviders}>
                <Save className="size-4" />
                保存配置
              </Button>
            </div>
          }
        >
          <SearchField value={providerQuery} onChange={setProviderQuery} placeholder="搜索 provider、模型或备注" />
          <div className="space-y-4">
            {filteredProviders.map((provider) => {
              const summary = providerHealthById.get(provider.id)
              const models = modelEntriesByProvider.get(provider.id) ?? []
              const isSelected = providerSettings.selected_provider_id === provider.id
              return (
                <Card key={provider.id} className="border-white/10 bg-white/5">
                  <CardContent className="space-y-5 p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <div className="flex size-10 items-center justify-center rounded-xl bg-white/5 text-white/70">
                          {provider.provider_type === "openai-compatible" || provider.provider_type === "custom" ? (
                            <Globe className="size-5" />
                          ) : (
                            <Cpu className="size-5" />
                          )}
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold text-white">{provider.name}</p>
                            <Badge variant="outline" className={providerStatusTone(summary?.status ?? "unknown")}>
                              {providerStatusLabel(summary?.status ?? "unknown")}
                            </Badge>
                            {isSelected ? <Badge className="bg-sky-500/10 text-sky-200">当前优先</Badge> : null}
                          </div>
                          <p className="mt-1 text-xs text-white/45">
                            {provider.id} · {providerTypeLabel(provider.provider_type)}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Button
                          size="sm"
                          variant={isSelected ? "default" : "outline"}
                          onClick={() =>
                            setProviderSettings((current) => ({ ...current, selected_provider_id: provider.id }))
                          }
                        >
                          <Power className="size-4" />
                          设为优先
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-300"
                          onClick={() => removeProvider(provider.id)}
                        >
                          <Trash2 className="size-4" />
                          移除
                        </Button>
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <Field label="名称">
                        <Input
                          value={provider.name}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({ ...current, name: event.target.value }))
                          }
                        />
                      </Field>
                      <Field label="ID">
                        <Input
                          value={provider.id}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({ ...current, id: event.target.value }))
                          }
                        />
                      </Field>
                      <Field label="Base URL">
                        <Input
                          value={provider.base_url}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({ ...current, base_url: event.target.value }))
                          }
                          placeholder="https://api.example.com/v1"
                        />
                      </Field>
                      <Field label="API Key">
                        <Input
                          type="password"
                          value={provider.api_key}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({ ...current, api_key: event.target.value }))
                          }
                          placeholder="sk-..."
                        />
                      </Field>
                      <Field label="默认文本模型">
                        <Input
                          value={provider.default_models.text}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({
                              ...current,
                              default_models: { ...current.default_models, text: event.target.value },
                              text_model: event.target.value,
                            }))
                          }
                        />
                      </Field>
                      <Field label="默认图像模型">
                        <Input
                          value={provider.default_models.image}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({
                              ...current,
                              default_models: { ...current.default_models, image: event.target.value },
                              image_model: event.target.value,
                            }))
                          }
                        />
                      </Field>
                      <Field label="默认视频模型">
                        <Input
                          value={provider.default_models.video}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({
                              ...current,
                              default_models: { ...current.default_models, video: event.target.value },
                              video_model: event.target.value,
                            }))
                          }
                        />
                      </Field>
                      <Field label="本地模型">
                        <Input
                          value={provider.default_models.local}
                          onChange={(event) =>
                            updateProvider(provider.id, (current) => ({
                              ...current,
                              default_models: { ...current.default_models, local: event.target.value },
                              local_model: event.target.value,
                            }))
                          }
                        />
                      </Field>
                    </div>

                    <Field label="备注">
                      <Textarea
                        rows={2}
                        value={provider.note}
                        onChange={(event) =>
                          updateProvider(provider.id, (current) => ({ ...current, note: event.target.value }))
                        }
                        placeholder="记录用途、限流、计费或兼容性说明。"
                      />
                    </Field>

                    <div className="flex flex-wrap items-center gap-2 text-xs text-white/55">
                      <Button
                        size="sm"
                        variant={provider.manual_enabled ? "default" : "outline"}
                        onClick={() =>
                          updateProvider(provider.id, (current) => ({
                            ...current,
                            manual_enabled: !current.manual_enabled,
                            enabled: !current.manual_enabled,
                          }))
                        }
                      >
                        {provider.manual_enabled ? "手动已启用" : "手动已禁用"}
                      </Button>
                      <span>最近体检：{formatTimestamp(summary?.last_checked_at)}</span>
                      <span>最近健康：{formatTimestamp(summary?.last_healthy_at)}</span>
                      {summary?.reason ? <span className="text-amber-200/80">原因：{summary.reason}</span> : null}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {(summary?.ability_summary ?? []).map((item) => (
                        <Badge
                          key={`${provider.id}-${item.ability}`}
                          variant="outline"
                          className={cn(
                            "border-white/10 bg-black/20 text-white/70",
                            item.status === "healthy" && "border-emerald-500/30 text-emerald-100",
                            item.status === "degraded" && "border-amber-500/30 text-amber-100",
                            (item.status === "unhealthy" || item.status === "disabled_auto") &&
                              "border-red-500/30 text-red-100",
                          )}
                        >
                          {abilityLabel(item.ability)} · {item.model_id || "-"}
                        </Badge>
                      ))}
                    </div>

                    {models.length ? (
                      <div className="space-y-2 rounded-2xl border border-white/10 bg-black/20 p-3">
                        <p className="text-xs uppercase tracking-[0.16em] text-white/40">模型能力状态</p>
                        <div className="space-y-2">
                          {models.map((entry) => (
                            <div
                              key={`${entry.provider_id}-${entry.kind}-${entry.model_id}`}
                              className="rounded-xl border border-white/8 bg-white/5 px-3 py-2"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div>
                                  <p className="text-sm font-medium text-white">
                                    {entry.model_id}
                                    <span className="ml-2 text-xs text-white/45">{entry.kind}</span>
                                  </p>
                                  <p className="text-xs text-white/45">
                                    {entry.manual_enabled ? "模型启用" : "模型已禁用"} · 总状态 {entry.overall_status}
                                  </p>
                                </div>
                                <Badge variant="outline" className={providerStatusTone(entry.overall_status as ProviderHealthSummary["status"])}>
                                  {entry.overall_status}
                                </Badge>
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {entry.ability_states.map((abilityState) => (
                                  <Badge key={`${entry.model_id}-${abilityState.ability}`} variant="outline" className="border-white/10 bg-white/5 text-white/70">
                                    {abilityLabel(abilityState.ability)} · {abilityState.status}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </WorkspaceCard>

        <div className="space-y-4">
          <WorkspaceCard
            eyebrow="默认路由"
            title="当前生效默认项"
            description="Resolver 会从健康 provider/model 中自动选择默认链路；指定项失效时会回退。"
          >
            <div className="space-y-4 text-sm text-white/75">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-white/40">脚本生成</p>
                <p className="mt-2">{effectiveDefaults.script_generation?.provider_name || "暂无健康默认项"}</p>
                <p className="text-xs text-white/45">{effectiveDefaults.script_generation?.models.text || "-"}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-white/40">角色生成</p>
                <p className="mt-2">{effectiveDefaults.character_generation?.provider_name || "暂无健康默认项"}</p>
                <p className="text-xs text-white/45">
                  文本 {effectiveDefaults.character_generation?.models.text || "-"} / 图像{" "}
                  {effectiveDefaults.character_generation?.models.image || "-"}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-white/40">短视频链路</p>
                <p className="mt-2">{effectiveDefaults.shortform_generation?.provider_name || "暂无健康默认项"}</p>
                <p className="text-xs text-white/45">
                  图像 {effectiveDefaults.shortform_generation?.models.image || "-"} / 视频{" "}
                  {effectiveDefaults.shortform_generation?.models.video || "-"}
                </p>
              </div>
            </div>
          </WorkspaceCard>
        </div>
      </div>
    )
  }

  if (activeSecondary === "system") {
    return (
      <WorkspaceCard eyebrow="兼容层" title="遗留系统设置" description="这些字段暂时仍保留给旧链路和本地渲染使用。">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[
            "OPENAI_VIDEO_RATIO",
            "OPENAI_VIDEO_DURATION",
            "OPENAI_VIDEO_RESOLUTION",
            "COMFYUI_URL",
            "COGVIDEOX_MODEL_ID",
          ].map((key) => (
            <Field key={key} label={key}>
              <Input
                value={settingsForm[key] || ""}
                onChange={(event) => setSettingsForm((current) => ({ ...current, [key]: event.target.value }))}
              />
            </Field>
          ))}
        </div>
        <div className="mt-6 flex gap-3">
          <Button onClick={saveSystemSettings}>
            <Save className="size-4" />
            保存系统设置
          </Button>
          <Button variant="outline" onClick={() => runHealthCheck()}>
            <RefreshCw className="size-4" />
            重新体检
          </Button>
        </div>
      </WorkspaceCard>
    )
  }

  return null
}
