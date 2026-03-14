import { type LucideIcon } from "lucide-react"
export type { LucideIcon }

export type PrimaryKey = "generation" | "qa" | "tasks" | "settings"
export type TaskStatus = "queued" | "running" | "succeeded" | "failed"

export interface PreviewState {
  title: string
  subtitle: string
  content: string
}

export interface BackgroundTask {
  id: string
  kind: string
  label: string
  status: TaskStatus
  created_at: string
  started_at: string | null
  ended_at: string | null
  result: unknown
  error: { message: string; traceback?: string } | null
  payload?: Record<string, unknown>
}

export interface AppStateResponse {
  app: {
    settings: Record<string, string>
    providers: {
      selected_provider_id: string
      providers: ProviderConnection[]
    }
    provider_health_summary: ProviderHealthSummary[]
    model_health_entries: ModelHealthEntry[]
    effective_defaults: EffectiveDefaults
    catalog: {
      text_models: string[]
      image_models: string[]
      video_models: string[]
      provider_model_groups: ProviderModelGroup[]
      model_registry_updated_at: string
      task_constraints?: {
        character_generation?: {
          blocked_text_models?: Array<{
            model: string
            reason: string
          }>
        }
      }
      job_providers: Array<{ id: string; label: string }>
      video_resolutions: string[]
      video_durations: number[]
      video_ratios: string[]
    }
    capabilities: Record<string, boolean>
    generation: {
      counts: Record<string, number>
      scripts: ScriptDoc[]
      characters: CharacterItem[]
      scenes: AssetItem[]
      props: AssetItem[]
      shotTemplates: AssetItem[]
      episodes: EpisodeItem[]
      jobs: JobItem[]
      outputs: OutputItem[]
    }
    qa: {
      count: number
      episodes: QaEpisode[]
    }
  }
  tasks: BackgroundTask[]
}

export interface ProviderConnection {
  id: string
  name: string
  provider_type: "openai-compatible" | "comfyui" | "cogvideox" | "custom"
  manual_enabled: boolean
  enabled: boolean
  base_url: string
  api_key: string
  default_models: {
    text: string
    image: string
    video: string
    local: string
  }
  text_model: string
  image_model: string
  video_model: string
  local_model: string
  extra_config: string
  note: string
}

export interface ProviderHealthSummary {
  provider_id: string
  provider_name: string
  provider_type: ProviderConnection["provider_type"]
  manual_enabled: boolean
  status: "unknown" | "healthy" | "degraded" | "unhealthy" | "disabled_auto" | "disabled_manual"
  reason?: string | null
  last_checked_at?: string | null
  last_healthy_at?: string | null
  consecutive_failures: number
  default_models: ProviderConnection["default_models"]
  ability_summary: Array<{
    ability: string
    status: string
    model_id?: string
    kind?: ModelKind
    reason?: string | null
  }>
}

export interface ModelHealthEntry {
  provider_id: string
  provider_name: string
  provider_type: ProviderConnection["provider_type"]
  provider_manual_enabled: boolean
  model_id: string
  kind: ModelKind
  manual_enabled: boolean
  supported_abilities: string[]
  ability_states: Array<{
    ability: string
    status: string
    reason?: string | null
    error_class?: string | null
    error_code?: string | null
    last_checked_at?: string | null
    last_healthy_at?: string | null
    consecutive_failures: number
  }>
  overall_status: "unknown" | "healthy" | "degraded" | "unhealthy" | "disabled_auto" | "disabled_manual"
  reason?: string | null
}

export interface EffectiveDefaults {
  script_generation: {
    provider_id: string
    provider_name: string
    provider_type: ProviderConnection["provider_type"]
    models: Record<string, string>
  } | null
  character_generation: {
    provider_id: string
    provider_name: string
    provider_type: ProviderConnection["provider_type"]
    models: Record<string, string>
  } | null
  shortform_generation: {
    provider_id: string
    provider_name: string
    provider_type: ProviderConnection["provider_type"]
    models: Record<string, string>
  } | null
}

export type ModelKind = "text" | "image" | "video"

export interface ProviderModelGroup {
  provider_id: string
  provider_label: string
  provider_type: ProviderConnection["provider_type"]
  source_label: string
  source_url: string
  source_status: "curated" | "live"
  description: string
  total_models: number
  models: {
    text: string[]
    image: string[]
    video: string[]
  }
}

export interface ScriptDoc {
  kind: string
  title: string
  path: string
  updated_at: number
  preview: string
}

export interface CharacterItem {
  slug: string
  name: string
  path: string
  reference_count: number
  style_descriptors: string[]
  negative_prompt: string
  generation_metadata_path?: string | null
  references: Array<{
    view: string
    expression: string | null
    path: string
    url?: string | null
    exists?: boolean
  }>
}

export interface AssetItem {
  id: string
  name: string
  path: string
  scene_pack?: string
  fixed_elements?: string[]
  fixed_props?: string[]
  forbidden_drift?: string[]
  framing?: string[]
  allowed_changes?: string[]
}

export interface EpisodeShotPrompt {
  shot_id: string
  prompt: string
  pollution_issues: string[]
}

export interface EpisodeItem {
  episode: string
  path: string
  character: string
  anchor_image: string
  anchor_image_url: string
  scene_pack: string
  prop_pack: string
  shot_template: string
  master_scene_prompt: string
  master_scene_candidates: number
  shot_delta_candidates: number
  shot_count: number
  review_context: string
  shots: EpisodeShotPrompt[]
  qa_summary?: QaEpisode
}

export interface JobItem {
  id: string
  path: string
  provider: string
  character: string
  scene_prompt: string
  negative_prompt?: string | null
  input_image: string
  input_image_url?: string | null
  reference_images: string[]
  reference_image_count: number
  script_path?: string | null
  script_excerpt?: string | null
  storyboard_notes?: string | null
  camera_plan?: string | null
  fps: number
  num_frames: number
}

export interface StoryboardShot {
  label: string
  framing: string
  subject_motion: string
  camera_motion: string
  continuity_lock: string
  change_allowance: string
  bridge_goal: string
}

export interface StoryboardResponse {
  character_path: string
  script_path: string
  storyboard: string
  camera_plan: string
  negative_prompt_hints: string[]
  shots: StoryboardShot[]
  frames?: string[]
}

export interface JobPreflightAnalysis {
  character_path: string
  provider: string
  seed: number
  estimated_duration_seconds: number
  readiness: "ready" | "needs_attention" | "high_risk"
  score: number
  script_excerpt?: string | null
  continuity_locks: string[]
  missing_assets: string[]
  warnings: string[]
  recommended_assets: string[]
  negative_prompt_hints: string[]
  suggested_negative_prompt: string
  recommended_defaults: {
    provider: string
    fps: number
    num_frames: number
    guidance: string
  }
}

export interface OutputItem {
  path: string
  url: string
  updated_at: number
  size_bytes: number
}

export interface QaEpisode {
  episode: string
  artifact_dir: string
  updated_at: number
  search_status?: string
  master_scene?: {
    candidate_path?: string
    pass_gate?: boolean
    overall_score?: number
    issues?: string[]
  }
  shot_count?: number
  selected_shots?: Array<{ shot_id: string; selected?: { candidate_path?: string } }>
  manifest_path?: string
  rendered_shots?: Array<{
    shot_id: string
    video_path?: string
    bridge_frame_path?: string | null
    reference_mode?: string
  }>
  keyframe_review?: {
    pass_gate?: boolean
    overall_score?: number
    issues: string[]
    path: string
  }
  episode_review?: {
    overall_identity_score?: number
    overall_outfit_score?: number
    overall_atmosphere_score?: number
    path: string
  }
  final_reviews?: Array<{
    path: string
    pass_gate?: boolean
    overall_score?: number
    issues: string[]
  }>
}

export interface NavigationItem {
  key: PrimaryKey
  label: string
  description: string
  icon: LucideIcon
  sections: Array<{
    key: string
    label: string
    hint: string
  }>
}

export type AppData = AppStateResponse["app"]

export type SectionKey = "overview" | "assets" | "generation" | "review"
export type FilterKey = "all" | "running" | "review" | "repair"

export interface SectionConfig {
  key: SectionKey
  label: string
  kicker: string
  title: string
  description: string
  workspaceTitle: string
  scope: "all" | "assets" | "generation" | "review"
  defaultFilter: FilterKey
}

export interface StatItem {
  label: string
  value: string
  note: string
}

export interface DashboardMetrics {
  hero: StatItem[]
  strip: StatItem[]
}

export interface TaskItem {
  id: string
  title: string
  status: string
  statusLabel: string
  section: SectionKey
  summary: string
  owner: string
  stage: string
  assets: string[]
  issues: string[]
  nextStep: string
}
