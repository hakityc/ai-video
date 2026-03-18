对，你这个思路是对的 👍 —— **给 Codex 一份“统一工程说明文档”是最优解** ，比你反复 prompt 它稳定得多。

我帮你收敛成一份  **“Codex 实现说明文档（单文件版）”** ，你可以直接丢给 Codex 或作为 repo 的 `/docs/ENGINEERING_SPEC.md`。

---

# 📄 AI 视频平台工程实现说明（给 Codex）

## 1. 项目目标

构建一个  **剧情型 AI 视频生产系统（后端 + AI 服务）** ，支持：

* 项目 / 剧集 / 角色 / 分镜管理
* Shot（镜头）级视频生成
* 多模型路由（Minimax / Runway / Sora 等）
* 异步任务系统
* 视频拼接与导出

---

## 2. 技术架构约束（必须遵守）

```yaml
frontend:
  framework: Next.js (后续实现)

backend:
  language: Go
  framework: Gin

ai_service:
  language: Python
  framework: FastAPI

database:
  main: PostgreSQL
  cache: Redis

queue:
  system: Redis Queue（或简单队列）

storage:
  type: S3-compatible（本地可用 MinIO）
```

---

## 3. 项目目录结构

```bash
ai-video-platform/
├── backend/
├── ai-service/
├── frontend/
├── docs/
├── infra/
```

### backend

```bash
/backend
├── cmd/server/main.go
├── internal/
│   ├── project/
│   ├── episode/
│   ├── character/
│   ├── location/
│   ├── shot/
│   ├── task/
│   ├── render/
│   └── auth/
├── pkg/
│   ├── db/
│   ├── queue/
│   └── storage/
├── api/
```

---

### ai-service

```bash
/ai-service
├── main.py
├── story/
├── storyboard/
├── prompt_builder/
├── video_router/
├── providers/
│   ├── minimax.py
│   ├── runway.py
│   ├── sora.py
```

---

## 4. 数据库 Schema（必须按此实现）

```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY,
  name TEXT,
  genre TEXT,
  style TEXT,
  aspect_ratio TEXT,
  created_at TIMESTAMP
);

CREATE TABLE episodes (
  id UUID PRIMARY KEY,
  project_id UUID,
  title TEXT,
  logline TEXT,
  status TEXT,
  created_at TIMESTAMP
);

CREATE TABLE characters (
  id UUID PRIMARY KEY,
  project_id UUID,
  name TEXT,
  appearance TEXT,
  personality TEXT,
  costume TEXT,
  reference_images JSONB,
  created_at TIMESTAMP
);

CREATE TABLE shots (
  id UUID PRIMARY KEY,
  episode_id UUID,
  order_no INT,
  duration INT,
  description TEXT,
  status TEXT,
  created_at TIMESTAMP
);

CREATE TABLE generation_tasks (
  id UUID PRIMARY KEY,
  shot_id UUID,
  provider TEXT,
  model TEXT,
  status TEXT,
  output_url TEXT,
  error TEXT,
  created_at TIMESTAMP
);

CREATE TABLE assets (
  id UUID PRIMARY KEY,
  type TEXT,
  url TEXT,
  metadata JSONB,
  created_at TIMESTAMP
);
```

---

## 5. 核心状态机（统一使用）

```yaml
shot_status:
  - draft
  - generating
  - success
  - failed

task_status:
  - pending
  - processing
  - success
  - failed
```

---

## 6. AI 工作流定义（核心逻辑）

### Shot 生成流程

```yaml
workflow: generate_shot

input:
  shot_id

steps:
  - load_shot
  - load_character_assets
  - build_prompt
  - route_model
  - call_provider
  - save_video_asset
  - update_shot_status

output:
  video_url
```

---

## 7. Prompt 标准结构

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

---

## 8. 模型路由策略

```yaml
routing:

  - condition: has_reference_image
    provider: minimax

  - condition: high_quality == true
    provider: runway

  - condition: long_duration
    provider: sora

  - default: minimax
```

---

## 9. 任务执行机制（必须异步）

### API 行为

```text
POST /shots/{id}/generate
```

流程：

```text
1. 创建 generation_task（status = pending）
2. 推送任务到队列
3. AI service 消费任务
4. 更新状态 → processing → success/failed
```

---

## 10. 示例数据（必须使用）

### 示例 Shot

```json
{
  "id": "shot_1",
  "description": "男主在雨夜便利店发现录音笔",
  "duration": 4
}
```

---

### 示例任务

```json
{
  "provider": "minimax",
  "prompt": "cinematic rainy night, young man finds recorder",
  "duration": 4
}
```

---

## 11. 系统约束（必须遵守）

```yaml
constraints:
  shot_duration:
    min: 3
    max: 8

  candidate_count:
    min: 1
    max: 4

  max_parallel_tasks: 3
```

---

## 12. 开发顺序（严格按顺序）

### Step 1

实现 backend skeleton（不写业务）

### Step 2

实现基础 CRUD：

* project
* episode
* character
* shot

### Step 3

实现任务系统：

* generation_task
* queue worker

### Step 4

实现 AI service（先 mock）

### Step 5

接入真实模型 provider

---

## 13. 重要约束（必须遵守）

* 所有视频生成必须基于 **Shot（镜头）**
* 不允许直接生成整条视频
* 所有生成必须通过任务系统
* 所有模型调用必须走 router
* 所有状态必须可追踪

---

## 14. 第一阶段交付目标

完成后应具备：

* 创建项目
* 创建角色
* 创建分镜（shot）
* 发起视频生成
* 返回视频结果 URL
