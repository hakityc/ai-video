import * as React from "react"
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  Search as SearchIcon,
} from "lucide-react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

import type {
  ModelKind,
  ProviderModelGroup,
  LucideIcon,
  QaEpisode,
  TaskStatus,
} from "../types"
import {
  cn,
  modelOptionsFromGroups,
  uniqueStrings,
  orderedModelGroups,
  statusTone,
  scoreText,
  taskStatusLabel,
  taskMeta,
} from "../lib/utils"

export function WorkspaceCard({
  eyebrow,
  title,
  description,
  children,
  action,
}: {
  eyebrow: string
  title: string
  description: string
  children: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <Card className="border-white/10 bg-white/5 shadow-[0_25px_80px_rgba(0,0,0,0.22)]">
      <CardHeader className="flex flex-col gap-3 p-4 md:gap-4 md:p-6 md:flex-row md:items-start md:justify-between">
        <div className="space-y-2">
          <CardDescription className="text-white/60">{eyebrow}</CardDescription>
          <CardTitle className="text-2xl text-white">{title}</CardTitle>
          <p className="max-w-3xl text-sm leading-6 text-white/70">{description}</p>
        </div>
        {action}
      </CardHeader>
      <CardContent className="space-y-3 px-4 pb-4 md:space-y-4 md:px-6 md:pb-6">{children}</CardContent>
    </Card>
  )
}

export function Field({
  label,
  description,
  children,
}: {
  label: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <label className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-white/88">{label}</span>
        {description ? <span className="text-xs text-white/60">{description}</span> : null}
      </div>
      {children}
    </label>
  )
}

export function SearchField({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
}) {
  return (
    <div className="relative">
      <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-white/50" />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="border-white/20 bg-black/20 pl-10 text-white placeholder:text-white/40 focus-visible:border-white/40 focus-visible:ring-1 focus-visible:ring-white/20 transition-all"
      />
    </div>
  )
}

export function ModelField({
  value,
  options = [],
  groups = [],
  kind,
  preferredGroupId,
  disabledOptions = {},
  onChange,
  placeholder,
}: {
  value: string
  options?: string[]
  groups?: ProviderModelGroup[]
  kind: ModelKind
  preferredGroupId?: string | null
  disabledOptions?: Record<string, string>
  onChange: (value: string) => void
  placeholder: string
}) {
  const groupOptions = modelOptionsFromGroups(groups, kind, preferredGroupId, value ? [value] : [])
  const selectOptions = uniqueStrings([...groupOptions, ...options, ...(value ? [value] : [])])
  const groupedOptions = orderedModelGroups(groups, kind, preferredGroupId)
  const hasValueOutsideGroups = Boolean(value && !groupedOptions.some((group) => group.models[kind].includes(value)))
  const disabledReasonFor = (option: string) => disabledOptions[option.trim().toLowerCase()] ?? ""

  return (
    <Select value={value} onValueChange={onChange} disabled={!selectOptions.length}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {hasValueOutsideGroups ? (
          <>
            <SelectGroup>
              <SelectLabel>当前值</SelectLabel>
              <SelectItem value={value} disabled={Boolean(disabledReasonFor(value))}>
                <div className="flex w-full items-center justify-between gap-3">
                  <span>{value}</span>
                  {disabledReasonFor(value) ? <span className="text-[11px] text-amber-200/80">已禁用</span> : null}
                </div>
              </SelectItem>
            </SelectGroup>
            {(groupedOptions.length || selectOptions.length > 1) ? <SelectSeparator /> : null}
          </>
        ) : null}
        {groupedOptions.length ? (
          groupedOptions.map((group, index) => (
            <div key={`${group.provider_id}-${kind}`}>
              <SelectGroup>
                <SelectLabel>{group.provider_label}</SelectLabel>
                {group.models[kind].map((option) => {
                  const disabledReason = disabledReasonFor(option)
                  return (
                    <SelectItem
                      key={`${group.provider_id}-${option}`}
                      value={option}
                      disabled={Boolean(disabledReason)}
                    >
                      <div className="flex w-full items-center justify-between gap-3">
                        <span>{option}</span>
                        {disabledReason ? <span className="text-[11px] text-amber-200/80">已禁用</span> : null}
                      </div>
                    </SelectItem>
                  )
                })}
              </SelectGroup>
              {index < groupedOptions.length - 1 ? <SelectSeparator /> : null}
            </div>
          ))
        ) : (
          selectOptions.map((option) => {
            const disabledReason = disabledReasonFor(option)
            return (
              <SelectItem key={option} value={option} disabled={Boolean(disabledReason)}>
                <div className="flex w-full items-center justify-between gap-3">
                  <span>{option}</span>
                  {disabledReason ? <span className="text-[11px] text-amber-200/80">已禁用</span> : null}
                </div>
              </SelectItem>
            )
          })
        )}
      </SelectContent>
    </Select>
  )
}

export function SelectedModelChips({
  items,
  onRemove,
}: {
  items: string[]
  onRemove: (value: string) => void
}) {
  if (!items.length) {
    return <p className="text-xs text-white/42">还没有加入候选模型。</p>
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onRemove(item)}
          className="rounded-full border border-white/12 bg-white/8 px-3 py-1.5 text-xs text-white/80 transition hover:border-white/20 hover:bg-white/12"
        >
          {item}
          <span className="ml-2 text-white/45">移除</span>
        </button>
      ))}
    </div>
  )
}

export function ProviderModelLibrary({
  groups,
  kind,
  onAdd,
  emptyLabel,
}: {
  groups: ProviderModelGroup[]
  kind: ModelKind
  onAdd: (value: string) => void
  emptyLabel: string
}) {
  const visibleGroups = groups.filter((group) => (group.models[kind] ?? []).length > 0)
  if (!visibleGroups.length) {
    return <p className="text-xs text-white/40">{emptyLabel}</p>
  }

  return (
    <div className="space-y-3">
      {visibleGroups.map((group) => (
        <div key={`${group.provider_id}-${kind}`} className="rounded-2xl border border-white/10 bg-black/20 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium text-white">{group.provider_label}</p>
              <p className="text-xs text-white/42">{group.source_label}</p>
            </div>
            <Badge className="border-white/10 bg-white/6 text-white/70">{group.models[kind].length} 个</Badge>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {group.models[kind].map((item) => (
              <button
                key={`${group.provider_id}-${item}`}
                type="button"
                onClick={() => onAdd(item)}
                className="rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs text-white/72 transition hover:border-white/18 hover:bg-white/10"
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export function ModelBucketCard({
  title,
  description,
  selected,
  groups,
  kind,
  onAdd,
  onRemove,
}: {
  title: string
  description: string
  selected: string[]
  groups: ProviderModelGroup[]
  kind: ModelKind
  onAdd: (value: string) => void
  onRemove: (value: string) => void
}) {
  return (
    <Card className="border-white/10 bg-black/20">
      <CardHeader className="space-y-2">
        <CardTitle className="text-lg text-white">{title}</CardTitle>
        <CardDescription className="text-white/52">{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.18em] text-white/40">已加入候选库</p>
          <SelectedModelChips items={selected} onRemove={onRemove} />
        </div>
        <ProviderModelLibrary
          groups={groups}
          kind={kind}
          onAdd={onAdd}
          emptyLabel="还没有抓到这个类型的可用模型。"
        />
      </CardContent>
    </Card>
  )
}

export function ModelChipGroup({
  title,
  items,
  onAdd,
}: {
  title: string
  items: string[]
  onAdd: (value: string) => void
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.18em] text-white/42">{title}</p>
      <div className="flex flex-wrap gap-2">
        {items.length ? (
          items.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => onAdd(item)}
              className="rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs text-white/72 transition hover:border-white/18 hover:bg-white/10"
            >
              {item}
            </button>
          ))
        ) : (
          <span className="text-xs text-white/40">还没有从供应商里发现可复用模型。</span>
        )}
      </div>
    </div>
  )
}

export function SummaryPill({
  title,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
}: {
  title: string
  value: string
  hint: string
  icon: LucideIcon
  tone?: "neutral" | "info" | "success" | "warning"
}) {
  const toneClass =
    tone === "info"
      ? "bg-sky-500/10 text-sky-100"
      : tone === "success"
        ? "bg-emerald-500/10 text-emerald-100"
        : tone === "warning"
          ? "bg-amber-500/10 text-amber-100"
          : "bg-white/6 text-white"

  return (
    <div className={cn("rounded-3xl border border-white/10 px-4 py-4", toneClass)}>
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.18em] text-white/45">{title}</p>
        <Icon className="size-4 text-white/45" />
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-xs text-white/52">{hint}</p>
    </div>
  )
}

export function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-3">
      <p className="text-[11px] uppercase tracking-[0.18em] text-white/40">{label}</p>
      <p className="mt-2 text-sm font-medium text-white">{value}</p>
    </div>
  )
}

export function InfoListBlock({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone: "info" | "warning"
}) {
  const toneClass =
    tone === "warning"
      ? "border-amber-500/20 bg-amber-500/10 text-amber-50"
      : "border-sky-500/20 bg-sky-500/10 text-sky-50"

  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.18em] text-white/42">{title}</p>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item} className={cn("rounded-2xl border px-3 py-3 text-sm leading-6", toneClass)}>
            {item}
          </div>
        ))}
      </div>
    </div>
  )
}

export function MiniSidebarCard({
  icon: Icon,
  title,
  value,
  description,
}: {
  icon: LucideIcon
  title: string
  value: string
  description: string
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-white/45">{title}</p>
        <Icon className="size-4 text-white/35" />
      </div>
      <p className="mt-3 text-lg font-semibold text-white">{value}</p>
      <p className="text-xs text-white/35">{description}</p>
    </div>
  )
}

export function StatusCard({
  title,
  description,
  ok,
}: {
  title: string
  description?: string
  ok: boolean
}) {
  return (
    <div className={cn("rounded-3xl border px-4 py-4", ok ? "border-emerald-500/25 bg-emerald-500/10" : "border-amber-500/25 bg-amber-500/10")}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-white">{title}</p>
        <CheckCircle2 className="size-4 text-emerald-300" />
      </div>
      <p className="mt-2 text-sm text-white/62">{description ?? (ok ? "已就绪" : "还未就绪")}</p>
    </div>
  )
}

export function EmptyState({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="rounded-3xl border border-dashed border-white/10 bg-black/15 px-5 py-8 text-center">
      <p className="text-sm font-medium text-white">{title}</p>
      <p className="mt-2 text-sm leading-6 text-white/52">{description}</p>
    </div>
  )
}

export function QaOverviewCard({
  entry,
  onOpenText,
}: {
  entry: QaEpisode
  onOpenText: (path: string) => void
}) {
  return (
    <Card className="border-white/10 bg-white/5">
      <CardContent className="space-y-4 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">{entry.episode}</p>
            <p className="mt-1 text-xs text-white/45">{entry.artifact_dir}</p>
          </div>
          <Badge className={statusTone(entry.keyframe_review?.pass_gate ? "ok" : "warning")}>
            {entry.keyframe_review?.pass_gate ? "稳定" : "待处理"}
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <MiniMetric label="关键帧" value={scoreText(entry.keyframe_review?.overall_score)} />
          <MiniMetric label="身份" value={scoreText(entry.episode_review?.overall_identity_score)} />
          <MiniMetric label="服装" value={scoreText(entry.episode_review?.overall_outfit_score)} />
          <MiniMetric label="氛围" value={scoreText(entry.episode_review?.overall_atmosphere_score)} />
        </div>
        {entry.keyframe_review?.issues.length ? (
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-50">
            {entry.keyframe_review.issues[0]}
          </div>
        ) : (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-50">
            当前关键帧复核通过。
          </div>
        )}
        <div className="flex gap-2">
          {entry.keyframe_review?.path ? (
            <Button variant="outline" size="sm" onClick={() => onOpenText(entry.keyframe_review!.path)}>
              查看关键帧 JSON
            </Button>
          ) : null}
          {entry.episode_review?.path ? (
            <Button variant="outline" size="sm" onClick={() => onOpenText(entry.episode_review!.path)}>
              查看整集 JSON
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

export function TaskProgress({ status }: { status: TaskStatus }) {
  const isQueued = status === "queued"
  const isRunning = status === "running"
  const isDone = status === "succeeded" || status === "failed"
  const isFailed = status === "failed"

  return (
    <div className="grid grid-cols-3 gap-2">
      <ProgressNode title="排队" active={isQueued || isRunning || isDone} failed={false} />
      <ProgressNode title="执行" active={isRunning || isDone} failed={false} />
      <ProgressNode title={isFailed ? "失败" : "完成"} active={isDone} failed={isFailed} />
    </div>
  )
}

export function ProgressNode({
  title,
  active,
  failed,
}: {
  title: string
  active: boolean
  failed: boolean
}) {
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-2 text-center text-xs",
        failed
          ? "border-amber-500/25 bg-amber-500/10 text-amber-50"
          : active
            ? "border-sky-500/20 bg-sky-500/10 text-sky-50"
            : "border-white/10 bg-white/5 text-white/38",
      )}
    >
      {title}
    </div>
  )
}
