# 剧情型 AI 视频平台

一个按 `docs/spec.md` 与 `docs/prd.md` 落地的剧情型 AI 视频生产工作台。仓库包含：

- `frontend/`: Next.js 五页工作台
- `backend/`: Go + Gin 业务 API、持久化、任务编排、导出 worker
- `ai-service/`: FastAPI 文本生成、Prompt Builder、视频 provider 适配与异步 worker
- `infra/`: 本地开发基础设施与脚本

## 快速开始

1. 复制环境变量：

```bash
cp .env.example .env
```

2. 启动基础设施与服务：

```bash
docker compose up --build
```

3. 打开：

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8080/healthz`
- AI service health: `http://localhost:8000/healthz`

## 目录

```text
.
├── ai-service
├── backend
├── docs
├── frontend
└── infra
```

## 当前实现原则

- Shot 是唯一视频生成单元
- 视频生成与导出一律异步
- 模型调用必须经过 router
- provider 可以按配置启停
- 文本模型供应商不可写死
