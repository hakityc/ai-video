CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  genre TEXT NOT NULL,
  style TEXT NOT NULL,
  aspect_ratio TEXT NOT NULL,
  target_duration INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_by TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS episodes (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  logline TEXT NOT NULL,
  target_duration INTEGER NOT NULL,
  status TEXT NOT NULL,
  export_status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS characters (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  age_tag TEXT NOT NULL DEFAULT '',
  appearance_desc TEXT NOT NULL,
  personality_desc TEXT NOT NULL,
  speaking_style TEXT NOT NULL DEFAULT '',
  costume_desc TEXT NOT NULL,
  locked_attributes JSONB NOT NULL DEFAULT '[]'::jsonb,
  reference_assets JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  reference_assets JSONB NOT NULL DEFAULT '[]'::jsonb,
  style_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS story_cards (
  id UUID PRIMARY KEY,
  episode_id UUID NOT NULL UNIQUE REFERENCES episodes(id) ON DELETE CASCADE,
  theme TEXT NOT NULL,
  conflict TEXT NOT NULL,
  twist TEXT NOT NULL,
  ending_hook TEXT NOT NULL,
  summary TEXT NOT NULL,
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS scenes (
  id UUID PRIMARY KEY,
  episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
  order_no INTEGER NOT NULL,
  summary TEXT NOT NULL,
  involved_character_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  involved_location_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS shots (
  id UUID PRIMARY KEY,
  episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
  scene_id UUID NULL REFERENCES scenes(id) ON DELETE SET NULL,
  order_no INTEGER NOT NULL,
  duration INTEGER NOT NULL CHECK (duration BETWEEN 3 AND 8),
  description TEXT NOT NULL,
  shot_type TEXT NOT NULL,
  camera_motion TEXT NOT NULL,
  subject_desc TEXT NOT NULL,
  action_desc TEXT NOT NULL,
  emotion_desc TEXT NOT NULL,
  dialogue_text TEXT NOT NULL DEFAULT '',
  generation_mode TEXT NOT NULL DEFAULT 'text',
  status TEXT NOT NULL,
  current_version_id UUID NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  id UUID PRIMARY KEY,
  project_id UUID NULL REFERENCES projects(id) ON DELETE SET NULL,
  kind TEXT NOT NULL,
  bucket TEXT NOT NULL,
  object_key TEXT NOT NULL,
  url TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_tasks (
  id UUID PRIMARY KEY,
  shot_id UUID NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  input_type TEXT NOT NULL,
  candidate_index INTEGER NOT NULL,
  prompt_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL,
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_asset_id UUID NULL REFERENCES assets(id) ON DELETE SET NULL,
  error_message TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  started_at TIMESTAMPTZ NULL,
  completed_at TIMESTAMPTZ NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS shot_versions (
  id UUID PRIMARY KEY,
  shot_id UUID NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES generation_tasks(id) ON DELETE CASCADE,
  asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  is_selected BOOLEAN NOT NULL DEFAULT false,
  prompt_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS render_jobs (
  id UUID PRIMARY KEY,
  episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
  selected_shot_version_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  subtitle_asset_id UUID NULL REFERENCES assets(id) ON DELETE SET NULL,
  voice_asset_id UUID NULL REFERENCES assets(id) ON DELETE SET NULL,
  bgm_asset_id UUID NULL REFERENCES assets(id) ON DELETE SET NULL,
  output_asset_id UUID NULL REFERENCES assets(id) ON DELETE SET NULL,
  status TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_message TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_episodes_project_id ON episodes(project_id);
CREATE INDEX IF NOT EXISTS idx_characters_project_id ON characters(project_id);
CREATE INDEX IF NOT EXISTS idx_locations_project_id ON locations(project_id);
CREATE INDEX IF NOT EXISTS idx_scenes_episode_id ON scenes(episode_id);
CREATE INDEX IF NOT EXISTS idx_shots_episode_id ON shots(episode_id);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_shot_id ON generation_tasks(shot_id);
CREATE INDEX IF NOT EXISTS idx_shot_versions_shot_id ON shot_versions(shot_id);
CREATE INDEX IF NOT EXISTS idx_render_jobs_episode_id ON render_jobs(episode_id);
