# MVP Stack Recommendation

## Short answer

For the first version, the best stack is:

- `ComfyUI` for inference workflow assembly and fast iteration
- `Diffusers` for programmable adapters and model-level control
- `InsightFace` for face identity scoring
- `SAM 2` for face/clothes region masking before repair
- `FFmpeg` for frame extraction, assembly, and color/post steps
- `LangGraph` or `Prefect` for orchestration and retries

## Why this stack

### 1. Generation surface: ComfyUI

Use ComfyUI as the first workflow execution layer.

Why:

- fastest way to get an image-to-video graph running
- supports `Wan 2.1`, `Wan 2.2`, `Hunyuan Video`, LoRA, inpainting, ControlNet, and API/back-end usage
- good for visually debugging drift and repair steps

Use it for:

- reference-conditioned keyframe generation
- image-to-video generation
- inpainting repair graphs
- batch workflow execution from JSON/API

Recommendation:

- use ComfyUI as the "GPU worker" surface
- keep business logic outside ComfyUI in Python services

### 2. Programmable control layer: Diffusers

Use Diffusers when you need code-level control instead of node graphs.

Why:

- official support for `IP-Adapter`
- supports loading `LoRA`
- supports `ControlNet`
- supports multiple video pipelines including `CogVideoX` and `AnimateDiff`
- supports Apple Silicon `mps` for lightweight local experiments

Use it for:

- reproducible pipeline experiments
- offline evaluation scripts
- service-side inference wrappers
- adapter loading and prompt templating

Important:

- Diffusers on Apple Silicon is real, but only suitable for light experiments
- heavy video generation should still run on remote CUDA machines

### 3. Identity locking: IP-Adapter + InstantID + LoRA

Use these in layers, not as mutually exclusive choices.

Suggested order:

1. `IP-Adapter` for quick reference image injection
2. `InstantID` for stronger face identity preservation in zero-shot cases
3. character `LoRA` for recurring main characters after reference pack stabilizes

Practical rule:

- prototype phase: IP-Adapter or InstantID
- scale phase: LoRA for core cast

### 4. Face QA: InsightFace

Use InsightFace as the first hard gate in the pipeline.

Why:

- includes face recognition, detection, and alignment
- good fit for the ArcFace-style similarity requirement in the PRD

Use it for:

- reference embedding generation
- frame-level identity scoring
- clip-level aggregate pass/fail

Suggested MVP thresholds:

- `>= 0.85`: pass
- `0.75 - 0.85`: warning
- `< 0.75`: fail

Start slightly looser than the PRD if your first generation model is unstable, then tighten later.

### 5. Repair masks: SAM 2

Use SAM 2 to isolate only the region you want to repair.

Why:

- strong segmentation foundation for images and video
- useful for face-only or clothing-only repair

Use it for:

- face crop mask generation
- clothes/accessory mask generation
- repair-area extraction before inpainting

### 6. Orchestration: LangGraph or Prefect

There are two realistic choices.

`LangGraph` if you want agentic QA and stateful decision logic:

- validate
- decide repair strategy
- retry with different constraints
- keep story state in graph state

`Prefect` if you want simpler pipeline orchestration first:

- retries
- scheduling
- observability
- task dependencies

My recommendation:

- first month: `Prefect` or plain Python jobs
- once QA and repair branches get complex: add `LangGraph`

### 7. Post-processing: FFmpeg

Use FFmpeg from day one.

Why:

- frame extraction
- clip stitching
- audio mux
- color and filter operations
- transition and delivery packaging

Even if final editing later moves into Remotion or another layer, FFmpeg should remain the low-level workhorse.

## Best model path for the first video flow

Do not optimize for "best benchmark model" first. Optimize for controllability.

### Recommended first path

`approved anchor image -> image-to-video`

Why:

- easier to lock character identity
- easier to validate against a still reference
- easier to debug than pure text-to-video

### Suggested model order

1. `CogVideoX-5b-I2V` via Diffusers for a programmable proof of concept
2. `Wan` or `Hunyuan Video` inside ComfyUI on a remote GPU for better production quality

Why not start directly with `HunyuanVideo`:

- official repo requires NVIDIA CUDA and large VRAM
- this machine is Apple Silicon, so it is not the right local first target

## What to use locally on this Mac

Local Apple Silicon is good for:

- prompt/state services
- frame QA
- embedding generation
- FFmpeg processing
- small Diffusers tests on `mps`

Local Apple Silicon is not the right primary target for:

- large open video foundation models
- production-quality batch inpainting on long clips
- heavy LoRA training for video pipelines

## Skills that help right now

### Installed and relevant

- `art-consistency`
  - strongest match to your PRD
  - useful for character bible, golden reference, QA rules, drift failure modes

- `comfyui-video-pipeline`
  - useful for choosing between Wan / FramePack / AnimateDiff style workflows
  - packaged summary is useful, but its referenced workflow files were not included, so treat it as guidance, not as a drop-in template

- `context7`
  - useful whenever we need current docs for `diffusers`, `langgraph`, `prefect`, or other moving libraries

- `find-skills`
  - useful for discovering more specialized skills later

### Secondary, not first-wave

- `remotion-best-practices`
  - useful later for packaging, subtitles, intro/outro, trailer assembly, and final episode composition
  - not the first tool for solving identity drift

## Recommended project split

### Control plane

Runs on the Mac:

- project configs
- character bible
- story state manager
- orchestration
- QA reports

### GPU worker plane

Runs on Linux + NVIDIA:

- ComfyUI server
- model weights
- generation workflows
- inpainting workflows

This split is the safest way to keep iteration speed high without blocking on local hardware.

## Source links

- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [Diffusers IP-Adapter docs](https://huggingface.co/docs/diffusers/en/using-diffusers/ip_adapter)
- [Diffusers ControlNet docs](https://huggingface.co/docs/diffusers/api/pipelines/controlnet)
- [Diffusers CogVideoX docs](https://huggingface.co/docs/diffusers/main/en/using-diffusers/cogvideox)
- [Diffusers AnimateDiff docs](https://huggingface.co/docs/diffusers/api/pipelines/animatediff)
- [Diffusers MPS docs](https://huggingface.co/docs/diffusers/main/en/optimization/mps)
- [InsightFace](https://github.com/deepinsight/insightface)
- [SAM 2](https://github.com/facebookresearch/sam2)
- [InstantID](https://github.com/instantX-research/InstantID)
- [LoRA training in Diffusers](https://huggingface.co/docs/diffusers/en/training/lora)
- [kohya_ss sd-scripts](https://github.com/kohya-ss/sd-scripts)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Prefect](https://github.com/PrefectHQ/prefect)
- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)
- [HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo)

