export interface AssetReference {
  asset_id?: string;
  url: string;
  label?: string;
}

export interface Character {
  id: string;
  project_id: string;
  name: string;
  age_tag: string;
  appearance_desc: string;
  personality_desc: string;
  speaking_style: string;
  costume_desc: string;
  locked_attributes: string[];
  reference_assets: AssetReference[];
}

export interface Location {
  id: string;
  project_id: string;
  name: string;
  description: string;
  style_tags: string[];
  reference_assets: AssetReference[];
}

export interface StoryCard {
  id: string;
  episode_id: string;
  theme: string;
  conflict: string;
  twist: string;
  ending_hook: string;
  summary: string;
}

export interface ShotVersion {
  id: string;
  shot_id: string;
  task_id: string;
  asset_id: string;
  provider: string;
  model: string;
  is_selected: boolean;
  asset_url: string;
}

export interface Shot {
  id: string;
  episode_id: string;
  scene_id?: string | null;
  order_no: number;
  duration: number;
  description: string;
  shot_type: string;
  camera_motion: string;
  subject_desc: string;
  action_desc: string;
  emotion_desc: string;
  dialogue_text: string;
  generation_mode: string;
  status: string;
  current_version_id?: string | null;
  versions?: ShotVersion[];
}

export interface Scene {
  id: string;
  episode_id: string;
  order_no: number;
  summary: string;
  involved_character_ids: string[];
  involved_location_ids: string[];
}

export interface RenderJob {
  id: string;
  episode_id: string;
  selected_shot_version_ids: string[];
  status: string;
  output_url?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface Episode {
  id: string;
  project_id: string;
  title: string;
  logline: string;
  target_duration: number;
  status: string;
  export_status: string;
  story_card?: StoryCard | null;
  scenes?: Scene[];
  shots?: Shot[];
  render_jobs?: RenderJob[];
}

export interface Project {
  id: string;
  name: string;
  genre: string;
  style: string;
  aspect_ratio: string;
  target_duration: number;
  status: string;
  created_by?: string | null;
  episodes?: Episode[];
  characters?: Character[];
  locations?: Location[];
}

export interface Task {
  id: string;
  shot_id: string;
  provider: string;
  model: string;
  input_type: string;
  candidate_index: number;
  status: string;
  error_message?: string | null;
}
