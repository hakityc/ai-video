import * as React from "react"
import { motion, AnimatePresence } from "motion/react"
import { 
  ListTodo, 
  X, 
  RefreshCw, 
  Clock,
  Loader2,
  ChevronLeft,
  Copy,
  AlertCircle,
  ChevronRight
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  cn, 
  taskMeta, 
  statusTone, 
  taskStatusLabel, 
  formatRelativeTime 
} from "@/lib/utils"
import type { BackgroundTask } from "@/types"

interface TaskFloatingBallProps {
  tasks: BackgroundTask[]
  onRefresh: () => Promise<void>
}

export function TaskFloatingBall({ tasks, onRefresh }: TaskFloatingBallProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [isRefreshing, setIsRefreshing] = React.useState(false)
  const [selectedTask, setSelectedTask] = React.useState<BackgroundTask | null>(null)

  const runningTasks = tasks.filter(t => t.status === "running")
  const queuedTasks = tasks.filter(t => t.status === "queued")
  // Show up to 100 recent tasks instead of 20
  const recentTasks = tasks.slice(0, 100)

  const activeCount = runningTasks.length + queuedTasks.length

  const handleRefresh = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsRefreshing(true)
    await onRefresh()
    setIsRefreshing(false)
  }

  const handleReuse = (task: BackgroundTask) => {
    if (task.payload) {
      // Dispatch a custom event to the rest of the application.
      const event = new CustomEvent("reuse-task-payload", {
        detail: { kind: task.kind, payload: task.payload }
      })
      window.dispatchEvent(event)
      setIsOpen(false)
    }
  }

  // Update selectedTask reference if it changes in upstream tasks array
  React.useEffect(() => {
    if (selectedTask) {
      const updated = tasks.find(t => t.id === selectedTask.id)
      if (updated) setSelectedTask(updated)
    }
  }, [tasks, selectedTask])

  return (
    <div className="fixed bottom-8 right-8 z-[9999] flex flex-col items-end">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20, transformOrigin: "bottom right" }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="mb-4 w-96 overflow-hidden rounded-3xl border border-white/20 bg-[#0d1520]/95 shadow-[0_25px_60px_rgba(0,0,0,0.6)] backdrop-blur-3xl"
          >
            {selectedTask ? (
              // DETAILS VIEW
              <motion.div 
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex h-[600px] flex-col"
              >
                <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-5 py-4 bg-white/5">
                  <div className="flex items-center gap-2">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="size-8 rounded-full hover:bg-white/10" 
                      onClick={() => setSelectedTask(null)}
                    >
                      <ChevronLeft className="size-4 text-white" />
                    </Button>
                    <h3 className="text-sm font-bold text-white tracking-wide">任务详情</h3>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="size-8 rounded-full hover:bg-white/10" 
                    onClick={() => setIsOpen(false)}
                  >
                    <X className="size-3.5 text-white/60" />
                  </Button>
                </div>
                
                <ScrollArea className="flex-1">
                  <div className="space-y-6 px-5 py-5">
                    <div>
                      <div className="flex items-center gap-3">
                        <Badge className={cn("text-xs font-bold uppercase tracking-wider border-none", statusTone(selectedTask.status))}>
                          {taskStatusLabel(selectedTask.status)}
                        </Badge>
                        <span className="text-xs text-white/50">{formatRelativeTime(selectedTask.created_at)}</span>
                      </div>
                      <h4 className="mt-3 text-sm font-semibold text-white">{taskMeta(selectedTask.kind).label}</h4>
                      <p className="mt-1 text-xs text-white/50">{selectedTask.label}</p>
                    </div>

                    {selectedTask.error && (
                      <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4">
                        <div className="flex items-center gap-2 text-red-400">
                          <AlertCircle className="size-4" />
                          <span className="text-xs font-bold uppercase">失败原因</span>
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-red-200">{selectedTask.error.message}</p>
                        {selectedTask.error.traceback && (
                          <details className="mt-3">
                            <summary className="cursor-pointer text-xs text-red-400/60 hover:text-red-400">查看完整堆栈</summary>
                            <div className="mt-2 overflow-x-auto rounded-xl bg-black/40 p-3">
                              <pre className="text-[10px] leading-relaxed text-red-200/70">{selectedTask.error.traceback}</pre>
                            </div>
                          </details>
                        )}
                      </div>
                    )}

                    {selectedTask.payload && Object.keys(selectedTask.payload).length > 0 && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white/60 uppercase tracking-wider">执行参数</span>
                          <Button 
                            variant="secondary" 
                            size="sm" 
                            className="h-7 rounded-full bg-white/10 px-3 text-[10px] hover:bg-white/20"
                            onClick={() => handleReuse(selectedTask)}
                          >
                            <Copy className="mr-1.5 size-3" />
                            复用此参数
                          </Button>
                        </div>
                        <div className="rounded-2xl border border-white/5 bg-black/20 p-4">
                          <pre className="whitespace-pre-wrap text-[11px] leading-relaxed text-emerald-100/80 font-mono">
                            {JSON.stringify(selectedTask.payload, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </motion.div>
            ) : (
              // LIST VIEW
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex flex-col"
              >
                <div className="flex items-center justify-between border-b border-white/10 px-5 py-4 bg-white/5">
                  <div className="flex items-center gap-2">
                    <div className="flex size-8 items-center justify-center rounded-xl bg-white/10">
                      <ListTodo className="size-4 text-white" />
                    </div>
                    <h3 className="text-sm font-bold text-white tracking-wide">任务历史</h3>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="size-8 rounded-full hover:bg-white/10" 
                      onClick={handleRefresh}
                      disabled={isRefreshing}
                    >
                      <RefreshCw className={cn("size-3.5 text-white/60", isRefreshing && "animate-spin")} />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="size-8 rounded-full hover:bg-white/10" 
                      onClick={() => setIsOpen(false)}
                    >
                      <X className="size-3.5 text-white/60" />
                    </Button>
                  </div>
                </div>

                <ScrollArea className="h-[500px] px-2 py-3">
                  <div className="space-y-2.5 px-3">
                    {tasks.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="mb-3 rounded-2xl bg-white/5 p-4">
                          <ListTodo className="size-8 text-white/10" />
                        </div>
                        <p className="text-xs text-white/30">暂无任何任务记录</p>
                      </div>
                    ) : (
                      recentTasks.map((task) => (
                        <div 
                          key={task.id} 
                          onClick={() => setSelectedTask(task)}
                          className="group relative cursor-pointer rounded-2xl border border-white/5 bg-white/5 p-3.5 transition hover:bg-white/10 hover:border-white/10"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <p className="truncate text-xs font-bold text-white">
                                    {taskMeta(task.kind).label}
                                  </p>
                                  <Badge className={cn("h-4 shrink-0 px-1 text-[9px] font-bold uppercase tracking-wider border-none", statusTone(task.status))}>
                                    {taskStatusLabel(task.status)}
                                  </Badge>
                                </div>
                                <ChevronRight className="size-3.5 text-white/20 transition group-hover:text-white/60 group-hover:translate-x-0.5" />
                              </div>
                              
                              <p className="mt-1.5 truncate text-[11px] leading-relaxed text-white/50">
                                {task.label}
                              </p>
                              
                              <div className="mt-3 flex items-center justify-between text-[10px] text-white/30">
                                <span className="flex items-center gap-1.5 font-medium">
                                  <Clock className="size-3" />
                                  {formatRelativeTime(task.created_at)}
                                </span>
                                {task.status === "running" && (
                                  <span className="flex items-center gap-1.5 font-semibold text-sky-400">
                                    <Loader2 className="size-3 animate-spin" />
                                    处理中
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
                
                <div className="border-t border-white/5 px-5 py-3 text-center">
                    <p className="text-[10px] text-white/20">仅显示最近 100 条记录</p>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* The Ball */}
      <motion.button
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.92 }}
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative flex size-16 items-center justify-center rounded-2xl border-2 shadow-[0_15px_40px_rgba(0,0,0,0.5)] transition-all duration-500",
          isOpen 
            ? "bg-white border-white text-black" 
            : activeCount > 0 
              ? "bg-[linear-gradient(135deg,#ff9a4d,#ff742d)] border-orange-400 text-white" 
              : "bg-white/15 border-white/20 text-white backdrop-blur-2xl"
        )}
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ opacity: 0, rotate: -90 }}
              animate={{ opacity: 1, rotate: 0 }}
              exit={{ opacity: 0, rotate: 90 }}
            >
              <X className="size-6" />
            </motion.div>
          ) : (
            <motion.div
              key="icon"
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              className="relative"
            >
              <ListTodo className="size-6" />
              {activeCount > 0 && (
                <span className="absolute -right-2 -top-2 flex size-5 items-center justify-center rounded-full bg-black text-[10px] font-bold text-white shadow-lg">
                  {activeCount}
                </span>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Pulsing ring for active tasks */}
        {!isOpen && activeCount > 0 && (
          <div className="absolute inset-0 -z-10 animate-ping rounded-2xl bg-orange-500/30 ring-4 ring-orange-500/20" />
        )}
      </motion.button>
    </div>
  )
}
