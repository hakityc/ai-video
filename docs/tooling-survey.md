# Tooling Survey

Last reviewed: 2026-03-12

This document narrows the current options for the first milestone: run one reliable short `image-to-video` pipeline and keep room for identity QA later.

## Recommended now

### 1. ComfyUI

Use as the main GPU-side workflow runner.

Why it stays:

- strong ecosystem for open video generation workflows
- practical for `image-to-video`, inpainting, LoRA, and post nodes
- best fit for remote NVIDIA worker deployment

Why it is better than starting with custom Python only:

- faster debugging of generation parameters
- easier to swap models and workflow branches
- lower cost to iterate on repair graphs later

Source:

- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)

### 2. Diffusers

Use as the programmable control layer and for first reproducible experiments.

Why it stays:

- official support for `IP-Adapter`
- official video pipelines such as `CogVideoXImageToVideoPipeline` and `AnimateDiffPipeline`
- supports LoRA loading and composition
- useful for service code, evaluation jobs, and local experiments

Best use in this project:

- prototype `I2V` jobs in code
- write repeatable QA and benchmark scripts
- wrap model calls behind stable interfaces

Sources:

- [Diffusers IP-Adapter](https://huggingface.co/docs/diffusers/en/using-diffusers/ip_adapter)
- [Diffusers CogVideoX](https://huggingface.co/docs/diffusers/main/en/using-diffusers/cogvideox)
- [Diffusers AnimateDiff](https://huggingface.co/docs/diffusers/main/api/pipelines/animatediff)
- [Diffusers ControlNet](https://huggingface.co/docs/diffusers/api/pipelines/controlnet)
- [Diffusers LoRA training](https://huggingface.co/docs/diffusers/en/training/lora)
- [Diffusers on Apple Silicon MPS](https://huggingface.co/docs/diffusers/main/en/optimization/mps)

### 3. CogVideoX-5B-I2V

Use as the first code-driven `image-to-video` candidate.

Why it stays:

- official `Diffusers` support is already documented
- direct `I2V` path matches the project's first milestone
- easier to wire into Python than many ComfyUI-only community workflows

Why this is the best first programmable path:

- it gets us from approved anchor image to short clip with minimal extra plumbing
- it is easier to benchmark and compare than a large graph-first setup

Sources:

- [THUDM CogVideo repo](https://github.com/THUDM/CogVideo)
- [Diffusers CogVideoX API](https://huggingface.co/docs/diffusers/en/api/pipelines/cogvideox)

### 4. HunyuanVideo

Use as a production-quality remote GPU candidate, not as the first local target.

Why it stays:

- actively maintained official repo
- supports current open video generation workflows
- has image-to-video and customization directions in the Tencent ecosystem

Why it is not first:

- heavier infrastructure requirements
- better suited for the remote NVIDIA worker stage

Sources:

- [HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo)
- [HunyuanCustom](https://github.com/Tencent-Hunyuan/HunyuanCustom)

### 5. InsightFace

Use as the first QA gate for identity consistency.

Why it stays:

- established open-source face analysis stack
- fits the PRD requirement for ArcFace-style similarity scoring
- useful even before automatic repair is built

Source:

- [InsightFace](https://github.com/deepinsight/insightface)

### 6. SAM 2

Use for precise repair masks later, especially face-only and outfit-only fixes.

Why it stays:

- current official segmentation foundation from Meta
- useful for targeted inpainting instead of whole-frame regeneration

Source:

- [SAM 2](https://github.com/facebookresearch/sam2)

### 7. FFmpeg

Use from day one.

Why it stays:

- frame extraction
- clip assembly
- delivery encoding
- transition and color utility steps

Source:

- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)

### 8. Prefect

Use as the first orchestration layer if we want retries and visibility without overbuilding.

Why it stays:

- current v3 docs still position it as a Python-native workflow engine
- task and flow retry behavior maps well to generation and QA retries

Why it beats LangGraph for milestone 0:

- less ceremony
- lower operational complexity
- better fit for deterministic pipeline steps

Source:

- [Prefect docs](https://docs.prefect.io/)
- [Prefect GitHub](https://github.com/PrefectHQ/prefect)

## Useful, but not first-wave

### LangGraph

Worth using when the pipeline becomes branch-heavy:

- QA decides repair method
- repair decides retry strategy
- story-state updates become graph state

Not first-wave because milestone 0 is mostly deterministic.

Sources:

- [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)

### InstantID

Strong option when face identity is the main anchor and a single reference image must carry more weight.

Why not first:

- useful, but adds another control stack on top of the base image workflow
- better introduced after we have one baseline path running

Source:

- [InstantID](https://github.com/instantX-research/InstantID)

### LoRA training

Important for recurring main cast, but not for day-zero delivery.

Why not first:

- depends on a stable reference pack first
- training and evaluation overhead slows the first milestone

Secondary source:

- [kohya_ss sd-scripts](https://github.com/kohya-ss/sd-scripts)

## Skills review

### Keep using

#### `find-skills`

Useful for scanning the current skill ecosystem quickly.

Why it stays:

- good for finding wrappers around ComfyUI, inference platforms, and content pipelines
- low effort way to discover options before committing engineering time

#### `context7`

Useful whenever a library API is likely to have moved.

Why it stays:

- strong fit for `diffusers`, `prefect`, `langgraph`, and similar fast-moving libraries
- better than relying on stale examples

### Helpful but secondary

#### `comfyui-video-pipeline`

Installed locally and directionally useful.

Why it helps:

- gives a practical decision tree for `Wan`, `FramePack`, and `AnimateDiff`
- good shorthand for choosing the right generation path

Why it is not authoritative:

- referenced workflow files were missing from the installed package
- keep it as guidance, not as source of truth

#### `ai-video-generation`

Installed locally and broad in model coverage.

Why it helps:

- fast way to try hosted video models through `inference.sh`
- useful for benchmark comparisons or quick external validation

Why it is not core:

- not an open-source local inference path
- depends on external hosted services and the `infsh` CLI
- useful as an optional accelerator, not as the foundation of this repo

## Recommended first stack

If the goal is only to run the first short video generation path, use:

- `ComfyUI` on remote GPU for generation
- `Diffusers` locally for reproducible experiments and wrappers
- `CogVideoX-5B-I2V` as the first code-driven `I2V` candidate
- `FFmpeg` for clip and frame processing
- `Prefect` only if we want immediate retries and job state

If the goal is the first end-to-end project stack, use:

- `ComfyUI`
- `Diffusers`
- `InsightFace`
- `SAM 2`
- `FFmpeg`
- `Prefect`

## Recommendation summary

Use fewer tools, but pick the right layers:

- inference surface: `ComfyUI`
- programmable layer: `Diffusers`
- first `I2V` model: `CogVideoX-5B-I2V`
- future production GPU candidate: `HunyuanVideo`
- QA: `InsightFace`
- repair masking: `SAM 2`
- orchestration: `Prefect` first, `LangGraph` later

