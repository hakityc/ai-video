from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ai_video_control.models import CharacterBible, RenderResult, VideoJob


TORCH_DTYPES = {
    "float16": "float16",
    "bfloat16": "bfloat16",
    "float32": "float32",
}


def render_with_cogvideox(
    job_path: Path,
    job: VideoJob,
    character: CharacterBible,
) -> RenderResult:
    assert job.cogvideox is not None

    try:
        import torch
        from diffusers import CogVideoXImageToVideoPipeline
        from diffusers.utils import export_to_video, load_image
    except ImportError as exc:
        raise RuntimeError(
            "CogVideoX rendering requires the optional 'video' dependencies. "
            "Install with: uv sync --extra video"
        ) from exc

    prompt = job.prompt(character)
    negative_prompt = job.combined_negative_prompt(character)

    if job.input_image.source_type == "url":
        image = load_image(job.input_image.source)
    else:
        input_path = Path(job.input_image.source)
        if not input_path.is_absolute():
            input_path = (job_path.parent / input_path).resolve()
        image = load_image(str(input_path))

    dtype_name = job.cogvideox.torch_dtype
    torch_dtype = getattr(torch, TORCH_DTYPES[dtype_name])

    device = job.cogvideox.device
    if device == "auto":
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    pipe = CogVideoXImageToVideoPipeline.from_pretrained(
        job.cogvideox.model_id,
        torch_dtype=torch_dtype,
    )

    if job.cogvideox.enable_vae_slicing and hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()
    if job.cogvideox.enable_vae_tiling and hasattr(pipe, "enable_vae_tiling"):
        pipe.enable_vae_tiling()

    if job.cogvideox.enable_model_cpu_offload and device == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(device)

    generator = torch.Generator(device=device).manual_seed(job.seed)
    result = pipe(
        image=image,
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        guidance_scale=job.cogvideox.guidance_scale,
        num_inference_steps=job.cogvideox.num_inference_steps,
        num_frames=job.num_frames,
        use_dynamic_cfg=job.cogvideox.use_dynamic_cfg,
        generator=generator,
    )
    frames = result.frames[0]

    output_path = Path(job.cogvideox.output_path)
    if not output_path.is_absolute():
        output_path = (job_path.parent / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(output_path), fps=job.fps)

    metadata: Dict[str, Any] = {
        "model_id": job.cogvideox.model_id,
        "device": device,
        "num_frames": job.num_frames,
        "fps": job.fps,
    }
    return RenderResult(
        provider="cogvideox",
        prompt=prompt,
        negative_prompt=negative_prompt,
        output_paths=[str(output_path)],
        metadata=metadata,
    )

