# 剧情型 AI 视频平台 V1 工程规范

## 1. 文档角色

- 本文档是仓库唯一工程规范。
- `docs/prd.md` 是业务真相来源；当旧 spec 草稿与 PRD 冲突时，以 PRD 为准补齐并修正本文档。
- 所有实现必须满足以下硬约束：
  - Shot 是唯一视频生成单元。
  - 不允许直接生成整条视频。
  - 所有视频生成必须走异步任务系统。
  - 所有模型调用必须经过 provider router。
  - 所有状态必须可追踪并保留原始 provider payload。

## 2. 一期交付范围

### 2.1 必做

- 项目与剧集管理
- 角色资产管理
- 场景资产管理
- 剧情卡生成
- Scene / Shot 分镜生成
- Shot 级候选视频生成、重试、替换、采用
- 粗剪导出与导出历史
- 五页工作台前端

### 2.2 不做

- 正式鉴权与多人协作
- 自动分发平台
- 高级非线性时间线
- 复杂口型同步
- AI TTS 作为强依赖能力

## 3. 技术栈

```yaml
frontend:
  framework: Next.js App Router
  language: TypeScript
  styling: Tailwind CSS v4

backend:
  language: Go
  framework: Gin
  database_driver: pgx

ai_service:
  language: Python
  framework: FastAPI
  http_client: httpx

database:
  main: PostgreSQL
  queue: Redis Streams
  storage: S3-compatible MinIO
```

## 4. 仓库结构

```text
.
├── frontend/
├── backend/
│   ├── cmd/server
│   ├── internal/
│   │   ├── project
│   │   ├── episode
│   │   ├── character
│   │   ├── location
│   │   ├── shot
│   │   ├── task
│   │   ├── render
│   │   ├── auth
│   │   └── platform
│   ├── migrations
│   └── api
├── ai-service/
│   └── app/
└── docs/
```

## 5. 页面与路由

- `/` 项目首页
- `/projects/[projectId]/characters` 角色资产页
- `/projects/[projectId]/episodes/[episodeId]/storyboard` 剧情与分镜页
- `/projects/[projectId]/episodes/[episodeId]/generation` 镜头生成页
- `/projects/[projectId]/episodes/[episodeId]/render` 粗剪导出页

## 6. 数据模型

### 6.1 Projects

```sql
id UUID PRIMARY KEY
name TEXT NOT NULL
genre TEXT NOT NULL
style TEXT NOT NULL
aspect_ratio TEXT NOT NULL
target_duration INTEGER NOT NULL
status TEXT NOT NULL
created_by TEXT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.2 Episodes

```sql
id UUID PRIMARY KEY
project_id UUID NOT NULL REFERENCES projects(id)
title TEXT NOT NULL
logline TEXT NOT NULL
target_duration INTEGER NOT NULL
status TEXT NOT NULL
export_status TEXT NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.3 Characters

```sql
id UUID PRIMARY KEY
project_id UUID NOT NULL REFERENCES projects(id)
name TEXT NOT NULL
age_tag TEXT
appearance_desc TEXT NOT NULL
personality_desc TEXT NOT NULL
speaking_style TEXT
costume_desc TEXT NOT NULL
locked_attributes JSONB NOT NULL
reference_assets JSONB NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.4 Locations

```sql
id UUID PRIMARY KEY
project_id UUID NOT NULL REFERENCES projects(id)
name TEXT NOT NULL
description TEXT NOT NULL
reference_assets JSONB NOT NULL
style_tags JSONB NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.5 Story Cards

```sql
id UUID PRIMARY KEY
episode_id UUID NOT NULL UNIQUE REFERENCES episodes(id)
theme TEXT NOT NULL
conflict TEXT NOT NULL
twist TEXT NOT NULL
ending_hook TEXT NOT NULL
summary TEXT NOT NULL
raw_payload JSONB NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.6 Scenes

```sql
id UUID PRIMARY KEY
episode_id UUID NOT NULL REFERENCES episodes(id)
order_no INTEGER NOT NULL
summary TEXT NOT NULL
involved_character_ids JSONB NOT NULL
involved_location_ids JSONB NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.7 Shots

```sql
id UUID PRIMARY KEY
episode_id UUID NOT NULL REFERENCES episodes(id)
scene_id UUID NULL REFERENCES scenes(id)
order_no INTEGER NOT NULL
duration INTEGER NOT NULL
description TEXT NOT NULL
shot_type TEXT NOT NULL
camera_motion TEXT NOT NULL
subject_desc TEXT NOT NULL
action_desc TEXT NOT NULL
emotion_desc TEXT NOT NULL
dialogue_text TEXT NOT NULL
generation_mode TEXT NOT NULL
status TEXT NOT NULL
current_version_id UUID NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.8 Assets

```sql
id UUID PRIMARY KEY
project_id UUID NULL REFERENCES projects(id)
kind TEXT NOT NULL
bucket TEXT NOT NULL
object_key TEXT NOT NULL
url TEXT NOT NULL
metadata JSONB NOT NULL
created_at TIMESTAMPTZ NOT NULL
```

### 6.9 Generation Tasks

```sql
id UUID PRIMARY KEY
shot_id UUID NOT NULL REFERENCES shots(id)
provider TEXT NOT NULL
model TEXT NOT NULL
input_type TEXT NOT NULL
candidate_index INTEGER NOT NULL
prompt_payload JSONB NOT NULL
status TEXT NOT NULL
raw_payload JSONB NOT NULL
output_asset_id UUID NULL REFERENCES assets(id)
error_message TEXT NULL
created_at TIMESTAMPTZ NOT NULL
started_at TIMESTAMPTZ NULL
completed_at TIMESTAMPTZ NULL
updated_at TIMESTAMPTZ NOT NULL
```

### 6.10 Shot Versions

```sql
id UUID PRIMARY KEY
shot_id UUID NOT NULL REFERENCES shots(id)
task_id UUID NOT NULL REFERENCES generation_tasks(id)
asset_id UUID NOT NULL REFERENCES assets(id)
provider TEXT NOT NULL
model TEXT NOT NULL
is_selected BOOLEAN NOT NULL DEFAULT false
prompt_payload JSONB NOT NULL
metadata JSONB NOT NULL
created_at TIMESTAMPTZ NOT NULL
```

### 6.11 Render Jobs

```sql
id UUID PRIMARY KEY
episode_id UUID NOT NULL REFERENCES episodes(id)
selected_shot_version_ids JSONB NOT NULL
subtitle_asset_id UUID NULL REFERENCES assets(id)
voice_asset_id UUID NULL REFERENCES assets(id)
bgm_asset_id UUID NULL REFERENCES assets(id)
output_asset_id UUID NULL REFERENCES assets(id)
status TEXT NOT NULL
metadata JSONB NOT NULL
error_message TEXT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

## 7. 状态机

```yaml
project_status:
  - draft
  - active
  - archived

episode_status:
  - draft
  - story_ready
  - storyboard_ready
  - generating
  - assembled
  - failed

episode_export_status:
  - draft
  - pending
  - processing
  - success
  - failed

shot_status:
  - draft
  - generating
  - success
  - failed

generation_task_status:
  - pending
  - processing
  - success
  - failed

render_job_status:
  - pending
  - processing
  - success
  - failed
```

## 8. 核心 API

### 8.1 CRUD

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{id}`
- `POST /api/v1/projects/{id}/episodes`
- `POST /api/v1/projects/{id}/characters`
- `POST /api/v1/projects/{id}/locations`
- `POST /api/v1/projects/{id}/assets:upload`
- `PATCH /api/v1/episodes/{id}`
- `PATCH /api/v1/characters/{id}`
- `PATCH /api/v1/locations/{id}`
- `PATCH /api/v1/scenes/{id}`
- `PATCH /api/v1/shots/{id}`

### 8.2 智能生成

- `POST /api/v1/episodes/{id}/story-card:generate`
- `POST /api/v1/episodes/{id}/storyboard:generate`
- `POST /api/v1/shots/{id}/generate`
- `POST /api/v1/shots/{id}/retry`
- `POST /api/v1/shots/{id}/versions/{versionId}/select`

### 8.3 导出与任务

- `POST /api/v1/episodes/{id}/render`
- `GET /api/v1/tasks/{id}`
- `GET /api/v1/render-jobs/{id}`

## 9. 任务与队列

- 视频生成与导出使用 Redis Streams。
- `POST /shots/{id}/generate` 一次最多创建 4 个候选任务。
- 外部视频任务系统最大并发为 3。
- AI worker 负责视频任务消费。
- Render worker 负责导出任务消费。

## 10. Prompt 与文本生成

- 文本模型必须走可配置 `TextModelProvider`。
- 首个实现采用 OpenAI-compatible chat 接口。
- 必须返回结构化 JSON：
  - Story card: `theme/conflict/twist/ending_hook/summary`
  - Storyboard: `scenes[]` 与 `shots[]`
- Shot Prompt 标准字段：

```json
{
  "scene": "rainy convenience store",
  "character": "young man, black hair",
  "action": "finds recorder",
  "emotion": "tense",
  "style": "cinematic",
  "camera": "slow push in",
  "duration": 4
}
```

## 11. 视频 provider 路由

```yaml
routing:
  - condition: has_reference_image
    provider: minimax
  - condition: human_character_consistency
    provider: minimax
  - condition: high_quality == true
    provider: runway
  - condition: duration >= 7 and no_human_reference
    provider: sora
  - default: minimax
```

- `MiniMax` 负责参考图、主体一致性优先场景。
- `Runway` 负责高质量文本或图片到视频场景。
- `Sora` 只在不依赖人脸/真人 likeness 参考的长时长镜头中启用。

## 12. 约束

```yaml
shot_duration:
  min: 3
  max: 8

candidate_count:
  min: 1
  max: 4

max_parallel_tasks: 3
```

## 13. 验收标准

- 可创建项目、角色、场景、剧集
- 可生成剧情卡与 Scene/Shot 分镜
- 可对单个 Shot 发起 1..4 个候选视频任务
- 可查看任务状态、重试失败任务、选择采用版本
- 可按采用版本完成粗剪导出 MP4
- 页面刷新后任务状态不丢失
- provider 凭证缺失时，禁用对应 provider 且系统仍可继续工作
