# AI Video Consistency Engine

This repository is the starting point for an AI video consistency pipeline focused on long-form episodic content.

## Goal

Build a practical "generate -> validate -> repair" loop that reduces:

- character identity drift across shots
- continuity breaks across episodes and segments

## Current recommendation

Do not start with full-series automation.

Start with a small, controllable MVP:

1. one core character
2. one approved reference pack
3. one 3-5 second shot
4. one image-to-video generation path
5. one identity QA pass

Once that loop is stable, add repair, story-state carry-over, and episode anchor frames.

## New Working Direction

Do not treat short-form story generation as "three prompts in a row".

The working direction is now asset-driven:

1. character pack
2. scene pack
3. prop pack
4. shot template
5. keyframe gate
6. short video generation
7. QA and repair

This mirrors how stronger AI short-video creators keep characters and scenes stable enough for editing.

The current v1 implementation uses a stricter variant for Ark/Seedance:

1. build a master scene prompt
2. search master scene candidates
3. gate the master scene
4. build subtractive shot-delta prompts
5. search gated shot-delta keyframes
6. generate short videos
7. select bridge frames from the tail of the previous clip
8. use the selected bridge frame to generate the next clip

## Recommended MVP path

Because the current machine is Apple Silicon (`Apple M4 Pro`), the practical split is:

- local Mac: orchestration, prompt/state management, QA, ffmpeg post-processing
- remote NVIDIA box: heavy video generation and inpainting

The first pipeline to run through should be:

1. Create a character bible and golden reference images.
2. Generate a hero keyframe with IP-Adapter / InstantID / LoRA constraints.
3. Run image-to-video generation from that approved frame.
4. Sample frames from the generated clip.
5. Run face similarity scoring against the reference pack.
6. If below threshold, mark for repair in the next milestone.

## What seems best for this project

- Workflow surface: ComfyUI
- Model/control library: Diffusers
- Identity QA: InsightFace
- Region masking: SAM 2
- Orchestration: LangGraph or Prefect
- Video post-processing: FFmpeg

## Docs

- [MVP Stack](./docs/mvp-stack.md)
- [MVP Roadmap](./docs/mvp-roadmap.md)
- [Project Structure](./docs/project-structure.md)
- [Tooling Survey](./docs/tooling-survey.md)
- [Continuity Workflow V2](./docs/workflows/continuity-v2.md)
- [Asset-Driven Shortform Workflow](./docs/workflows/asset-driven-shortform.md)

## Quick Start

Install the base control-plane dependencies:

```bash
uv sync
```

Inspect the currently loaded environment:

```bash
uv run aivideo env
```

Validate the sample character bible and job:

```bash
uv run aivideo validate-character examples/characters/protagonist.yaml
uv run aivideo validate-job examples/jobs/shot-001-comfyui.yaml
```

Render the final prompt that will be sent to a model:

```bash
uv run aivideo print-prompt examples/jobs/shot-001-comfyui.yaml
```

Render shortform prompts from the new five-dimension spec:

```bash
uv run aivideo print-master-scene-prompt examples/episodes/tomb-raider-female-ep007.yaml
uv run aivideo print-shot-delta-prompt examples/episodes/tomb-raider-female-ep007.yaml shot-001
uv run aivideo print-shot-card examples/episodes/tomb-raider-female-ep007.yaml shot-001
uv run aivideo print-continuity-ledger examples/episodes/tomb-raider-female-ep007.yaml
uv run aivideo init-continuity-ledger examples/episodes/tomb-raider-female-ep007.yaml
```

Validate that a shot-delta prompt is not over-describing locked details:

```bash
uv run aivideo validate-prompt-pollution \
  examples/episodes/tomb-raider-female-ep007.yaml \
  --stage shot_delta \
  --shot-id shot-001
```

Search gated master-scene and shot-delta candidates:

```bash
uv run aivideo search-keyframe-candidates \
  examples/episodes/tomb-raider-female-ep007.yaml \
  --video-model doubao-seedance-1-5-pro-251215
```

This staged search now works in two different ways:

- `master scene`: text-to-image candidate search
- `shot delta`: reference-conditioned Seedance draft clips, then frame extraction and gating against the approved master scene

Every search/render run also writes `continuity_ledger.json` inside the episode artifact directory.

Render the full chain-referenced shortform sequence:

```bash
uv run aivideo render-shortform examples/episodes/tomb-raider-female-ep007.yaml
```

For `shot n > 1`, the renderer now submits the previous shot's approved bridge frame as `first_frame`
and the current shot's approved keyframe as `last_frame`.

Scaffold a new job from a character bible:

```bash
uv run aivideo create-job shot-002 \
  --character examples/characters/protagonist.yaml \
  --output examples/jobs/shot-002-comfyui.yaml \
  --provider comfyui \
  --scene-brief "wide shot, walking under wet street lights, slow cinematic dolly"
```

Run a ComfyUI-backed render:

```bash
uv run aivideo render examples/jobs/shot-001-comfyui.yaml
```

Run a direct Diffusers `CogVideoX` render:

```bash
uv sync --extra video
uv run aivideo render examples/jobs/shot-001-cogvideox.yaml
```

## Current status

The repository now includes:

- a Python control-plane scaffold
- `.env` and `.env.example` for shared runtime configuration
- YAML schemas for character bibles and generation jobs
- a ComfyUI API workflow submitter
- a `Diffusers` `CogVideoXImageToVideoPipeline` entry point
- an `env` diagnostics command
- a `create-job` scaffold command
- sample configs under `examples/`
- reusable scene / prop / shot-template packs under `examples/`

Generated media and reference images are now organized by character slug.
Do not put new reference stills into a flat shared folder.

Before generating new short-scene videos, first define:

- a character bible
- a scene pack
- a prop pack
- a shot template

The included ComfyUI workflow JSON is only a placeholder to demonstrate patching.
For a real render, export an API workflow from ComfyUI and update the node ids in the sample job file.
