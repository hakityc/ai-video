import React, { useDeferredValue } from "react"
import { motion } from "framer-motion"
import {
  Rocket,
  Wand2,
  Search,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
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

import type { AppStateResponse, JobPreflightAnalysis, StoryboardResponse, PrimaryKey } from "@/types"
import { formatTimestamp, statusTone } from "@/lib/utils"
import {
  WorkspaceCard,
  Field,
  SearchField,
  MiniMetric,
  TaskProgress,
  EmptyState,
} from "@/components/ProjectUI"

interface TaskViewProps {
  data: AppStateResponse
  activeSecondary: string
  refreshState: (showLoading?: boolean) => Promise<void>
  runBackgroundAction: (url: string, payload: unknown, successText: string) => Promise<void>
  openText: (path: string) => Promise<void>
  switchPrimary: (id: PrimaryKey, sub?: string) => void
  jobForm: any
  setJobForm: React.Dispatch<React.SetStateAction<any>>
  jobAdvancedOpen: boolean
  setJobAdvancedOpen: (val: boolean) => void
  taskQuery: string
  setTaskQuery: (val: string) => void
  jobPreflight: JobPreflightAnalysis | null
  setJobPreflight: (val: JobPreflightAnalysis | null) => void
  storyboardResult: StoryboardResponse | null
  setStoryboardResult: (val: StoryboardResponse | null) => void
}

export function TaskView({
  data,
  activeSecondary,
  runBackgroundAction,
  jobForm,
  setJobForm,
  jobAdvancedOpen,
  setJobAdvancedOpen,
  taskQuery,
  setTaskQuery,
  jobPreflight,
  setJobPreflight,
  storyboardResult,
  setStoryboardResult,
}: TaskViewProps) {
  const deferredTaskQuery = useDeferredValue(taskQuery)

  const filteredTasks = data.tasks.filter(
    (item) =>
      item.label.toLowerCase().includes(deferredTaskQuery.toLowerCase()) ||
      item.status.toLowerCase().includes(deferredTaskQuery.toLowerCase()),
  )

  const preflightJob = async () => {
    if (!jobForm.script_path || !jobForm.character_path) {
      alert("请先选择脚本和角色")
      return
    }
    const res = await fetch("/api/jobs/preflight", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(jobForm),
    })
    const response = await res.json()
    setJobPreflight(response.analysis)
  }

  const generateStoryboard = async () => {
    if (!jobForm.script_path || !jobForm.character_path) {
        alert("请先选择脚本和角色")
        return
      }
    const res = await fetch("/api/storyboards/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...jobForm,
        text_model: data.app.settings.OPENAI_MODEL || "",
        shot_count: 4,
      }),
    })
    const result = await res.json()
    setStoryboardResult(result.storyboard)
  }

  if (activeSecondary === "queue") {
    return (
      <WorkspaceCard eyebrow="任务队列" title="执行中的动作" description="所有正在生成的视频和预检任务轨迹。">
        <SearchField value={taskQuery} onChange={setTaskQuery} placeholder="搜索任务 ID、状态" />
        <div className="grid gap-4 xl:grid-cols-2">
          {filteredTasks.slice(0, 8).map((task) => (
            <Card key={task.id} className="border-white/10 bg-white/5">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-semibold text-white">{task.label}</p>
                    <p className="mt-1 text-xs text-white/45">开始于 {formatTimestamp(task.created_at)}</p>
                  </div>
                  <Badge className={statusTone(task.status)}>{task.status}</Badge>
                </div>
                <div className="mt-6">
                  <TaskProgress status={task.status} />
                </div>
              </CardContent>
            </Card>
          ))}
          {!filteredTasks.length ? <EmptyState title="队列空空如也" description="发起一个新任务来看看。" /> : null}
        </div>
      </WorkspaceCard>
    )
  }

  if (activeSecondary === "create") {
    return (
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <WorkspaceCard
          eyebrow="生产编排"
          title="发起生成任务"
          description="从这里开始发起真实的视频任务。建议先进行预检。"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="关联剧本">
              <Select
                value={jobForm.script_path || "__none__"}
                onValueChange={(value) =>
                  setJobForm((current: any) => ({ ...current, script_path: value === "__none__" ? "" : value }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择脚本" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">不选脚本</SelectItem>
                  {data.app.generation.scripts.map((item) => (
                    <SelectItem key={item.path} value={item.path}>
                      {item.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="关联角色">
              <Select
                value={jobForm.character_path || "__none__"}
                onValueChange={(value) =>
                  setJobForm((current: any) => ({
                    ...current,
                    character_path: value === "__none__" ? "" : value,
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择角色" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">不选角色</SelectItem>
                  {data.app.generation.characters.map((item) => (
                    <SelectItem key={item.path} value={item.path}>
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>
          <Field label="场景简述">
            <Textarea
              rows={4}
              value={jobForm.scene_brief}
              onChange={(e) => setJobForm((current: any) => ({ ...current, scene_brief: e.target.value }))}
              placeholder="描述当前镜头的画面表现细节。"
            />
          </Field>
          <Collapsible open={jobAdvancedOpen} onOpenChange={setJobAdvancedOpen} className="space-y-3">
            <CollapsibleTrigger asChild>
              <Button variant="outline" className="w-full justify-between border-white/10 bg-black/20">
                环境与渲染高级参数
                <span className="text-xs text-white/45">{jobAdvancedOpen ? "收起" : "展开"}</span>
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="种子 (Seed)">
                  <Input
                    type="number"
                    value={jobForm.seed}
                    onChange={(e) => setJobForm((current: any) => ({ ...current, seed: Number(e.target.value) }))}
                  />
                </Field>
                <Field label="帧率 (FPS)">
                  <Input
                    type="number"
                    value={jobForm.fps}
                    onChange={(e) => setJobForm((current: any) => ({ ...current, fps: Number(e.target.value) }))}
                  />
                </Field>
              </div>
              <Field label="总帧数">
                <Input
                  type="number"
                  value={jobForm.num_frames}
                  onChange={(e) => setJobForm((current: any) => ({ ...current, num_frames: Number(e.target.value) }))}
                />
              </Field>
              <Field label="分镜备注">
                <Textarea
                  rows={3}
                  value={jobForm.storyboard_notes}
                  onChange={(e) => setJobForm((current: any) => ({ ...current, storyboard_notes: e.target.value }))}
                  placeholder="补充对分镜的具体要求。"
                />
              </Field>
              <Field label="运镜规划">
                <Textarea
                  rows={3}
                  value={jobForm.camera_plan}
                  onChange={(e) => setJobForm((current: any) => ({ ...current, camera_plan: e.target.value }))}
                  placeholder="例如：缓慢推近、360度环绕。"
                />
              </Field>
            </CollapsibleContent>
          </Collapsible>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={preflightJob}>
              <Wand2 className="size-4" />
              执行预检
            </Button>
            <Button variant="outline" onClick={generateStoryboard}>
              <Search className="size-4" />
              生成分镜
            </Button>
            <Button
              onClick={() => runBackgroundAction("/api/jobs/create", jobForm, "生成任务已提交")}
              className="bg-emerald-600 hover:bg-emerald-500"
            >
              <Rocket className="size-4" />
              正式提交任务
            </Button>
          </div>
        </WorkspaceCard>

        <div className="space-y-4">
          {jobPreflight ? (
            <WorkspaceCard eyebrow="预检结果" title="分析报告" description="基于当前参数的冲突检测与建议。">
              <div className="space-y-4">
                <div className="grid gap-2 md:grid-cols-2">
                  <MiniMetric label="准备就绪" value={jobPreflight.readiness === "ready" ? "高" : "需注意"} />
                  <MiniMetric label="预期风险" value={jobPreflight.readiness === "high_risk" ? "高" : "低"} />
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-white/40">推荐参数</p>
                  <div className="grid grid-cols-2 gap-2">
                    <MiniMetric label="FPS" value={String(jobPreflight.recommended_defaults.fps)} />
                    <MiniMetric label="帧数" value={String(jobPreflight.recommended_defaults.num_frames)} />
                  </div>
                </div>
              </div>
            </WorkspaceCard>
          ) : null}

          {storyboardResult ? (
            <WorkspaceCard eyebrow="分镜预览" title="Storyboard" description="AI 生成的视觉参考方案。">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  {(storyboardResult.frames ?? []).map((frame: string, idx: number) => (
                    <div key={idx} className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
                      <img src={frame} alt={`Frame ${idx}`} className="aspect-video w-full object-cover" />
                    </div>
                  ))}
                </div>
                <div className="rounded-2xl border border-sky-500/20 bg-sky-500/10 p-4">
                  <p className="text-sm font-semibold text-white">分镜说明</p>
                  <p className="mt-2 text-sm leading-6 text-white/72">{storyboardResult.storyboard}</p>
                </div>
              </div>
            </WorkspaceCard>
          ) : (
            <div className="flex h-40 items-center justify-center rounded-3xl border border-dashed border-white/10 text-sm text-white/20">
              等待发起预检或分镜建议生成...
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="space-y-4"
    >
        <EmptyState title="选择子板块" description="点击上方导航按钮切换 任务队列 或 生产编排。" />
    </motion.div>
  )
}
