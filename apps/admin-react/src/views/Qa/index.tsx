import React, { useDeferredValue } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

import type { AppData } from "@/types"
import { formatTimestamp, matchesQuery, scoreText, statusTone } from "@/lib/utils"
import { WorkspaceCard, SearchField, EmptyState } from "@/components/ProjectUI"


interface QaViewProps {
  data: AppData
  activeSecondary: string
  refreshState: () => void
  runBackgroundAction: (url: string, body: any, successTitle: string) => void
  openText: (path: string) => void
  qaQuery: string
  setQaQuery: (val: string) => void
}

export function QaView({
  data,
  runBackgroundAction,
  openText,
  qaQuery,
  setQaQuery,
}: QaViewProps) {
  const deferredQaQuery = useDeferredValue(qaQuery)
  const episodes = data.qa.episodes.filter((entry) =>
    matchesQuery(
      deferredQaQuery,
      entry.episode,
      entry.search_status,
      ...(entry.keyframe_review?.issues ?? []),
      ...(entry.final_reviews?.flatMap((item) => item.issues) ?? []),
    ),
  )

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
      <WorkspaceCard eyebrow="QA 概览" title="质量概况" description="复核结果直接来自当前项目的 QA 产物。">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-white/40">剧集数</p>
            <p className="mt-2 text-2xl font-semibold text-white">{data.qa.count}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-white/40">关键帧通过</p>
            <p className="mt-2 text-2xl font-semibold text-white">
              {data.qa.episodes.filter((entry) => entry.keyframe_review?.pass_gate).length}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-white/40">终审记录</p>
            <p className="mt-2 text-2xl font-semibold text-white">
              {data.qa.episodes.reduce((count, entry) => count + (entry.final_reviews?.length ?? 0), 0)}
            </p>
          </div>
        </div>
      </WorkspaceCard>

      <WorkspaceCard eyebrow="打分管理" title="最近 QA 结果" description="按剧集查看关键帧、整集和桥接帧的复核结果。">
        <SearchField value={qaQuery} onChange={setQaQuery} placeholder="搜索剧集 ID、问题关键词" />
        <ScrollArea className="h-[680px]">
          <div className="space-y-4 pr-4">
            {episodes.map((entry) => (
              <Card key={entry.episode} className="border-white/10 bg-white/5">
                <CardContent className="space-y-4 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{entry.episode}</p>
                      <p className="mt-1 text-xs text-white/45">更新于 {formatTimestamp(entry.updated_at)}</p>
                    </div>
                    <Badge className={statusTone(entry.keyframe_review?.pass_gate ? "ok" : "warning")}>
                      关键帧 {scoreText(entry.keyframe_review?.overall_score)}
                    </Badge>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/20 p-3 text-sm text-white/72">
                    <p>搜索状态：{entry.search_status || "未记录"}</p>
                    <p>主场景：{entry.master_scene?.candidate_path || "未记录"}</p>
                    <p>渲染镜头：{entry.rendered_shots?.length ?? 0}</p>
                  </div>

                  {(entry.keyframe_review?.issues?.length ?? 0) > 0 ? (
                    <div className="space-y-2 rounded-2xl border border-amber-500/20 bg-amber-500/10 p-3">
                      <p className="text-xs uppercase tracking-[0.16em] text-amber-100/80">关键帧问题</p>
                      {(entry.keyframe_review?.issues ?? []).map((issue) => (
                        <p key={issue} className="text-sm text-amber-50/85">
                          {issue}
                        </p>
                      ))}
                    </div>
                  ) : null}

                  <div className="flex flex-wrap gap-2">
                    {entry.keyframe_review?.path ? (
                      <Button variant="outline" size="sm" onClick={() => openText(entry.keyframe_review?.path || "")}>
                        查看关键帧报告
                      </Button>
                    ) : null}
                    {entry.episode_review?.path ? (
                      <Button variant="outline" size="sm" onClick={() => openText(entry.episode_review?.path || "")}>
                        查看整集报告
                      </Button>
                    ) : null}
                    {entry.artifact_dir ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          runBackgroundAction(
                            "/api/qa/review-episode",
                            { episode_dir: entry.artifact_dir, context: "" },
                            "已提交整集复核",
                          )
                        }
                      >
                        重新跑整集 QA
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            ))}
            {!episodes.length ? <EmptyState title="未找到相关 QA 结果" description="换个关键词试试。" /> : null}
          </div>
        </ScrollArea>
      </WorkspaceCard>
    </div>
  )
}
