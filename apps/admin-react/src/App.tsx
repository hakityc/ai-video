import { startTransition, useEffect, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import {
  RefreshCw,
  Sparkles,
  ShieldCheck,
  Film,
  ChevronRight,
} from "lucide-react"
import useWebSocket from "react-use-websocket"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { Toaster } from "@/components/ui/sonner"
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider
} from "@/components/ui/tooltip"

import type {
  PrimaryKey,
  PreviewState,
  BackgroundTask,
  AppStateResponse,
  ProviderConnection,
} from "./types"
import {
  navigation,
  defaultSecondaryState,
} from "./constants"
import { fetchJson } from "./lib/api"
import {
  cn,
  resolveRouteFromHash,
  taskMeta,
  statusTone,
  taskStatusLabel,
  getSectionCount,
  preferredGroupIdForProvider,
} from "./lib/utils"
import {
  MiniSidebarCard,
} from "./components/ProjectUI"
import { GenerationView } from "./views/Generation"
import { QaView } from "./views/Qa"
import { SettingsView } from "./views/Settings"
import { TaskFloatingBall } from "./components/TaskFloatingBall"

const emptyEffectiveDefaults = {
  script_generation: null,
  character_generation: null,
  shortform_generation: null,
} as const

function normalizeAppState(response: AppStateResponse): AppStateResponse {
  return {
    ...response,
    app: {
      ...response.app,
      provider_health_summary: response.app.provider_health_summary ?? [],
      model_health_entries: response.app.model_health_entries ?? [],
      effective_defaults: response.app.effective_defaults ?? emptyEffectiveDefaults,
    },
  }
}

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(() => typeof window !== "undefined" ? window.innerWidth >= 1280 : true)
  const initialRoute = resolveRouteFromHash(window.location.hash)
  const [activePrimary, setActivePrimary] = useState<PrimaryKey>(initialRoute.primary)
  const [secondaryState, setSecondaryState] = useState<Record<PrimaryKey, string>>({
    ...defaultSecondaryState,
    [initialRoute.primary]: initialRoute.secondary,
  })

  const [data, setData] = useState<AppStateResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<PreviewState | null>(null)


  // Shared states for QaView
  const [qaQuery, setQaQuery] = useState("")

  // Shared states for SettingsView
  const [settingsForm, setSettingsForm] = useState<Record<string, string>>({})
  const [providerSettings, setProviderSettings] = useState<{
    selected_provider_id: string
    providers: ProviderConnection[]
  }>({
    selected_provider_id: "",
    providers: [],
  })
  const [providerQuery, setProviderQuery] = useState("")

  const activeSecondary = secondaryState[activePrimary]
  const activeNavigation = navigation.find((item) => item.key === activePrimary) ?? navigation[0]
  const activeSection = activeNavigation.sections.find((item) => item.key === activeSecondary) ?? activeNavigation.sections[0]
  const activeSectionCount = getSectionCount(data, activePrimary, activeSecondary)
  
  const pendingQaCount =
    data?.app.qa.episodes.filter(
      (entry) => !entry.keyframe_review?.pass_gate || Boolean(entry.keyframe_review?.issues?.length),
    ).length ?? 0
  const runningTaskCount = data?.tasks.filter((task) => task.status === "running").length ?? 0

  async function refreshState(showLoading = false) {
    if (showLoading) {
      setLoading(true)
    }

    try {
      const next = normalizeAppState(await fetchJson<AppStateResponse>("/api/state"))
      startTransition(() => {
        setData(next)
        setSettingsForm((current) => (Object.keys(current).length === 0 ? next.app.settings : current))
        setProviderSettings((current) =>
          current.providers.length === 0 ? next.app.providers : current,
        )
        setLoading(false)
      })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载失败")
      setLoading(false)
    }
  }

  useEffect(() => {
    const handleHashChange = () => {
      const route = resolveRouteFromHash(window.location.hash)
      startTransition(() => {
        setActivePrimary(route.primary)
        setSecondaryState((current) => ({
          ...current,
          [route.primary]: route.secondary,
        }))
      })
    }

    window.addEventListener("hashchange", handleHashChange)
    return () => window.removeEventListener("hashchange", handleHashChange)
  }, [])

  useEffect(() => {
    const hash = `#${activePrimary}/${activeSecondary}`
    if (window.location.hash !== hash) {
      window.history.replaceState(null, "", hash)
    }
  }, [activePrimary, activeSecondary])

  useEffect(() => {
    const kickoff = window.setTimeout(() => {
      void refreshState(true)
    }, 0)
    return () => {
      window.clearTimeout(kickoff)
    }
  }, [])

  const wsUrl = typeof window !== "undefined" 
    ? `ws://${window.location.host}/api/ws` 
    : ""
    
  // @ts-expect-error type import issue
  useWebSocket(wsUrl, {
    shouldReconnect: () => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
    onMessage: (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === "state_updated") {
          void refreshState(false)
        }
      } catch {
        // ignore invalid json payload
      }
    }
  })

  function switchPrimary(primary: PrimaryKey) {
    const nextSecondary = secondaryState[primary] || navigation.find((item) => item.key === primary)?.sections[0]?.key || "overview"
    startTransition(() => {
      setActivePrimary(primary)
      setSecondaryState((current) => ({
        ...current,
        [primary]: nextSecondary,
      }))
    })
  }

  function switchSecondary(primary: PrimaryKey, secondary: string) {
    startTransition(() => {
      setActivePrimary(primary)
      setSecondaryState((current) => ({
        ...current,
        [primary]: secondary,
      }))
    })
  }

  async function runBackgroundAction(url: string, payload: unknown, successText: string) {
    try {
      const response = await fetchJson<{ task: BackgroundTask }>(url, {
        method: "POST",
        body: JSON.stringify(payload),
      })
      toast.success(`${successText}，已进入队列`, {
        description: response.task.label,
      })
      await refreshState(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "执行失败")
    }
  }

  async function runAction<T = unknown>(url: string, payload: unknown, successText: string): Promise<T | null> {
    try {
      const response = await fetchJson<T>(url, {
        method: "POST",
        body: JSON.stringify(payload),
      })
      toast.success(successText)
      await refreshState(false)
      return response
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "执行失败")
      return null
    }
  }

  async function openText(path: string) {
    try {
      const response = await fetchJson<{ path: string; content: string }>(
        `/api/text?path=${encodeURIComponent(path)}`,
      )
      setPreview({
        title: response.path.split("/").slice(-1)[0],
        subtitle: response.path,
        content: response.content,
      })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "打开文件失败")
    }
  }

  function renderGenerationContent() {
    const allProviderModelGroups = data?.app.catalog.provider_model_groups ?? []
    const selectedProvider =
        providerSettings.providers.find((item) => item.id === providerSettings.selected_provider_id) ??
        providerSettings.providers[0] ??
        null
    const selectedProviderGroupId = preferredGroupIdForProvider(selectedProvider)
    const providerModelGroups = selectedProviderGroupId
      ? allProviderModelGroups.filter((group) => group.provider_id === selectedProviderGroupId)
      : allProviderModelGroups

    return (
      <GenerationView
        data={data!}
        activeSecondary={activeSecondary}
        refreshState={refreshState}
        runBackgroundAction={runBackgroundAction}
        openText={openText}
        switchPrimary={switchPrimary}
        switchSecondary={switchSecondary}
        settings={settingsForm}
        providerModelGroups={providerModelGroups}
        modelHealthEntries={data!.app.model_health_entries ?? []}
        effectiveDefaults={data!.app.effective_defaults ?? emptyEffectiveDefaults}
        selectedProviderGroupId={selectedProviderGroupId}
      />
    )
  }

  function renderQaContent() {
    return (
      <QaView
        data={data!.app}
        activeSecondary={activeSecondary}
        refreshState={refreshState}
        runBackgroundAction={runBackgroundAction}
        openText={openText}
        qaQuery={qaQuery}
        setQaQuery={setQaQuery}
      />
    )
  }


  function renderSettingsContent() {
    return (
      <SettingsView
        data={data!.app}
        activeSecondary={activeSecondary}
        refreshState={refreshState}
        runBackgroundAction={runBackgroundAction}
        runAction={runAction}
        settingsForm={settingsForm}
        setSettingsForm={setSettingsForm}
        providerSettings={providerSettings}
        setProviderSettings={setProviderSettings}
        providerQuery={providerQuery}
        setProviderQuery={setProviderQuery}
        switchSecondary={switchSecondary}
      />
    )
  }

  return (
    <TooltipProvider>
      <SidebarProvider
        open={sidebarOpen}
        onOpenChange={setSidebarOpen}
        className="dark min-h-dvh w-full overflow-x-hidden bg-[radial-gradient(circle_at_top_left,rgba(255,180,94,0.18),transparent_24%),radial-gradient(circle_at_top_right,rgba(84,191,197,0.16),transparent_22%),linear-gradient(180deg,#070b11_0%,#0b1320_55%,#06090d_100%)] text-white"
      >
        <Sidebar variant="sidebar" collapsible="icon" className="border-r border-white/10">
            <SidebarHeader className="border-b border-white/10 px-3 py-4">
              <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                <div className="flex size-11 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,rgba(255,176,87,0.9),rgba(255,116,45,0.45))] text-sm font-semibold text-black">
                  AV
                </div>
                <div className="min-w-0 group-data-[collapsible=icon]:hidden">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-white/45">控制中台</p>
                  <p className="truncate text-sm font-semibold text-white">AI 视频控制台</p>
                </div>
              </div>
            </SidebarHeader>

            <SidebarContent className="px-2 py-3">
              <SidebarGroup>
                <SidebarGroupLabel>一级导航</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {navigation.map((item) => {
                      const Icon = item.icon
                      return (
                        <SidebarMenuItem key={item.key}>
                          <SidebarMenuButton
                            tooltip={item.label}
                            isActive={activePrimary === item.key}
                            onClick={() => switchPrimary(item.key)}
                          >
                            <Icon />
                            <span>{item.label}</span>
                          </SidebarMenuButton>
                          {getSectionCount(data, item.key, item.sections[0]?.key ?? "overview") ? (
                            <SidebarMenuBadge>{getSectionCount(data, item.key, item.sections[0]?.key ?? "overview")}</SidebarMenuBadge>
                          ) : null}
                        </SidebarMenuItem>
                      )
                    })}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>

              <SidebarSeparator />

              <SidebarGroup>
                <SidebarGroupLabel>当前状态</SidebarGroupLabel>
                <SidebarGroupContent>
                  <div className="space-y-3 px-2 group-data-[collapsible=icon]:hidden">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="cursor-help">
                          <MiniSidebarCard
                            icon={Sparkles}
                            title="运行中任务"
                            value={`${runningTaskCount}`}
                            description="后台异步队列"
                          />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="border-white/10 bg-[#0d1520] text-white/80">
                        正在后台通过调度器排队或执行的任务数量。
                      </TooltipContent>
                    </Tooltip>
                    
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="cursor-help">
                          <MiniSidebarCard
                            icon={ShieldCheck}
                            title="待处理 QA"
                            value={`${pendingQaCount}`}
                            description="需要人工判断"
                          />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="border-white/10 bg-[#0d1520] text-white/80">
                        生成完毕但关键帧存在问题需要人工介入的任务。
                      </TooltipContent>
                    </Tooltip>
                    
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="cursor-help">
                          <MiniSidebarCard
                            icon={Film}
                            title="视频产出"
                            value={`${data?.app.generation.outputs.length ?? 0}`}
                            description="已收录成果库"
                          />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="border-white/10 bg-[#0d1520] text-white/80">
                        所有成功渲染并落地的最终成片。
                      </TooltipContent>
                    </Tooltip>
                  </div>
                </SidebarGroupContent>
              </SidebarGroup>
            </SidebarContent>

            <SidebarFooter className="border-t border-white/10 px-2 py-3">
              <div className="space-y-2 group-data-[collapsible=icon]:hidden">
                {(data?.tasks.slice(0, 3) ?? []).map((task) => (
                  <div key={task.id} className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-xs font-medium text-white">{taskMeta(task.kind).label}</p>
                        <p className="mt-1 truncate text-[11px] text-white/45">{task.label}</p>
                      </div>
                      <Badge className={cn("shrink-0 text-[11px]", statusTone(task.status))}>
                        {taskStatusLabel(task.status)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </SidebarFooter>
            <SidebarRail />
        </Sidebar>

        <SidebarInset className="min-h-dvh bg-[radial-gradient(circle_at_top_left,rgba(255,154,77,0.08),transparent_20%),radial-gradient(circle_at_top_right,rgba(74,163,255,0.08),transparent_18%),linear-gradient(180deg,rgba(7,11,17,0.98)_0%,rgba(10,18,30,0.98)_58%,rgba(6,9,13,0.98)_100%)]">
          <div className="flex min-h-dvh min-w-0 w-full flex-col overflow-x-clip">
            <header className="sticky top-0 z-20 px-3 py-2 md:px-4 xl:px-5">
              <div className="relative overflow-hidden rounded-[24px] border border-white/10 bg-[linear-gradient(135deg,rgba(8,12,18,0.96),rgba(11,20,34,0.94)_58%,rgba(9,15,26,0.94))] shadow-[0_18px_48px_rgba(0,0,0,0.28)] backdrop-blur-xl">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,160,77,0.14),transparent_20%),radial-gradient(circle_at_top_right,rgba(87,168,255,0.14),transparent_20%)]" />
                <div className="relative space-y-2 px-4 py-3 md:px-5 md:py-3.5">
                  <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                    <div className="flex min-w-0 items-start gap-3">
                      <SidebarTrigger
                        variant="outline"
                        size="icon-sm"
                        className="mt-0.5 border-white/10 bg-white/6 text-white hover:bg-white/10"
                      />
                      <div className="min-w-0 space-y-2">
                        <Breadcrumb>
                          <BreadcrumbList>
                            <BreadcrumbItem>控制台</BreadcrumbItem>
                            <BreadcrumbSeparator>
                              <ChevronRight className="size-3.5" />
                            </BreadcrumbSeparator>
                            <BreadcrumbItem>{activeNavigation.label}</BreadcrumbItem>
                            <BreadcrumbSeparator>
                              <ChevronRight className="size-3.5" />
                            </BreadcrumbSeparator>
                            <BreadcrumbItem>
                              <BreadcrumbPage>{activeSection?.label}</BreadcrumbPage>
                            </BreadcrumbItem>
                          </BreadcrumbList>
                        </Breadcrumb>
                        <div className="flex flex-wrap items-center gap-2">
                          <h1 className="text-lg font-semibold tracking-tight text-white md:text-xl">
                            {activeSection?.label}
                          </h1>
                          <span className="rounded-full border border-white/10 bg-white/6 px-2.5 py-1 text-xs text-white/58">
                            {activeNavigation.label}
                          </span>
                          <span className="rounded-full border border-white/10 bg-white/6 px-2.5 py-1 text-xs text-white/58">
                            {activeSectionCount} 项
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="border-sky-500/20 bg-sky-500/10 text-sky-100">运行中 {runningTaskCount}</Badge>
                      <Badge className="border-amber-500/20 bg-amber-500/10 text-amber-100">待处理 QA {pendingQaCount}</Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-white/10 bg-white/6 text-white hover:bg-white/10"
                        onClick={() => void refreshState(false)}
                      >
                        <RefreshCw className="size-4" />
                        刷新状态
                      </Button>
                    </div>
                  </div>

                  <div className="flex min-w-0 gap-2 overflow-x-auto pb-2 scrollbar-thin">
                      {activeNavigation.sections.map((section) => (
                        <button
                          key={section.key}
                          type="button"
                          onClick={() => switchSecondary(activeNavigation.key, section.key)}
                          className={cn(
                            "group flex shrink-0 items-center gap-2 rounded-xl border px-3 py-1.5 text-left transition",
                            activeSecondary === section.key
                              ? "border-white/18 bg-white/90 text-black shadow-[0_10px_24px_rgba(255,255,255,0.08)]"
                              : "border-white/10 bg-white/6 text-white hover:border-white/18 hover:bg-white/10",
                          )}
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-semibold">{section.label}</p>
                          </div>
                          <span
                            className={cn(
                              "rounded-full px-2 py-1 text-xs font-medium",
                              activeSecondary === section.key ? "bg-black/10 text-black/72" : "bg-black/20 text-white/60",
                            )}
                          >
                            {getSectionCount(data, activeNavigation.key, section.key)}
                          </span>
                        </button>
                      ))}
                  </div>
                </div>
              </div>
            </header>

            <main className="min-w-0 flex-1 px-3 py-3 md:px-4 md:py-4 xl:px-5">
                {loading || !data ? (
                  <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_360px]">
                    <Card className="border-white/10 bg-white/5">
                      <CardContent className="space-y-4 p-6">
                        <Skeleton className="h-8 w-48 rounded-xl bg-white/10" />
                        <Skeleton className="h-20 w-full rounded-2xl bg-white/10" />
                        <Skeleton className="h-56 w-full rounded-2xl bg-white/10" />
                      </CardContent>
                    </Card>
                    <Card className="border-white/10 bg-white/5">
                      <CardContent className="space-y-4 p-6">
                        <Skeleton className="h-7 w-36 rounded-xl bg-white/10" />
                        <Skeleton className="h-28 w-full rounded-2xl bg-white/10" />
                        <Skeleton className="h-28 w-full rounded-2xl bg-white/10" />
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={`${activePrimary}-${activeSecondary}`}
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.18 }}
                      className="min-w-0 space-y-4"
                    >
                      {activePrimary === "generation" ? renderGenerationContent() : null}
                      {activePrimary === "qa" ? renderQaContent() : null}
                      {activePrimary === "settings" ? renderSettingsContent() : null}
                    </motion.div>
                  </AnimatePresence>
                )}
            </main>
          </div>
        </SidebarInset>

        <Dialog open={Boolean(preview)} onOpenChange={(open) => (!open ? setPreview(null) : null)}>
          <DialogContent className="max-w-4xl border-white/10 bg-[#09111b] text-white">
            <DialogHeader>
              <DialogTitle>{preview?.title}</DialogTitle>
              <DialogDescription className="text-white/45">{preview?.subtitle}</DialogDescription>
            </DialogHeader>
            <ScrollArea className="h-[70vh] rounded-2xl border border-white/10 bg-black/30 p-4">
              <pre className="whitespace-pre-wrap break-words font-mono text-sm leading-6 text-white/78">
                {preview?.content}
              </pre>
            </ScrollArea>
          </DialogContent>
        </Dialog>

        <Toaster
          position="top-right"
          richColors
          closeButton
          toastOptions={{
            classNames: {
              toast: "border border-white/10 bg-[#0b1320] text-white",
            },
          }}
        />
        <TaskFloatingBall 
          tasks={data?.tasks ?? []} 
          onRefresh={() => refreshState(false)} 
        />
      </SidebarProvider>
    </TooltipProvider>
  )
}

export default App
