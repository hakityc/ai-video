from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from ai_video_control.io import make_relative_path, read_yaml, write_json, write_yaml
from ai_video_control.models import CharacterBible, VideoJob
from ai_video_control.paths import ARTIFACTS_VIDEO_DIR, CHARACTERS_DIR, WORKFLOWS_DIR
from ai_video_control.providers.cogvideox import render_with_cogvideox
from ai_video_control.providers.comfyui import render_with_comfyui
from ai_video_control.providers.openai_compat import (
    OpenAICompatClient,
    build_character_brief_prompt,
    build_reference_image_prompts,
)
from ai_video_control.review import review_episode, review_keyframe_set
from ai_video_control.shortform import (
    build_continuity_ledger,
    build_master_scene_prompt,
    build_shot_card,
    build_shot_delta_prompt,
    load_shortform_bundle,
    render_shortform_episode,
    search_keyframe_candidates,
    validate_prompt_pollution,
)
from ai_video_control.review import review_master_scene_image, select_bridge_frame
from ai_video_control.settings import get_settings

app = typer.Typer(no_args_is_help=True)
console = Console()


def _load_character(path: Path) -> CharacterBible:
    return CharacterBible.model_validate(read_yaml(path))


def _load_job(path: Path) -> VideoJob:
    return VideoJob.model_validate(read_yaml(path))


def _check_reference_files(character_path: Path, character: CharacterBible) -> None:
    missing = []
    for ref in character.reference_images:
        ref_path = Path(ref.path)
        if not ref_path.is_absolute():
            ref_path = (character_path.parent / ref_path).resolve()
        if not ref_path.exists():
            missing.append(str(ref_path))
    if missing:
        raise typer.BadParameter(
            "Missing reference images:\n" + "\n".join(missing)
        )


@app.command("env")
def show_env() -> None:
    """Show the currently loaded environment configuration."""
    settings = get_settings()
    payload = settings.masked()
    payload["OPENAI_API_KEY_STATUS"] = "set" if settings.openai_api_key else "missing"
    payload["OPENAI_MODEL_STATUS"] = "set" if settings.openai_model else "missing"
    payload["OPENAI_IMAGE_MODEL_STATUS"] = (
        "set" if settings.openai_image_model else "missing"
    )
    payload["COMFYUI_URL_STATUS"] = "set" if settings.comfyui_url else "missing"
    console.print_json(json.dumps(payload))


@app.command("print-master-scene-prompt")
def print_master_scene_prompt(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Render the master-scene prompt for a shortform episode spec."""
    bundle = load_shortform_bundle(spec_path)
    console.print_json(json.dumps({"prompt": build_master_scene_prompt(bundle)}))


@app.command("print-shot-delta-prompt")
def print_shot_delta_prompt(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    shot_id: str = typer.Argument(...),
) -> None:
    """Render the shot-delta prompt for one shot in a shortform episode spec."""
    bundle = load_shortform_bundle(spec_path)
    console.print_json(
        json.dumps({"shot_id": shot_id, "prompt": build_shot_delta_prompt(bundle, shot_id)})
    )


@app.command("print-shot-card")
def print_shot_card_command(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    shot_id: str = typer.Argument(...),
) -> None:
    """Render the normalized shot-card view for one shot in a shortform episode spec."""
    bundle = load_shortform_bundle(spec_path)
    shot_card = build_shot_card(bundle, shot_id)
    console.print_json(
        json.dumps(
            {
                "shot_id": shot_id,
                "shot_card": shot_card.model_dump(mode="json"),
            }
        )
    )


@app.command("print-continuity-ledger")
def print_continuity_ledger_command(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Render the continuity-ledger scaffold for a shortform episode spec."""
    bundle = load_shortform_bundle(spec_path)
    ledger = build_continuity_ledger(bundle)
    console.print_json(json.dumps(ledger.model_dump(mode="json")))


@app.command("init-continuity-ledger")
def init_continuity_ledger_command(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Optional output path. Defaults to <spec>.continuity_ledger.json",
    ),
) -> None:
    """Write a continuity-ledger scaffold for a shortform episode spec."""
    bundle = load_shortform_bundle(spec_path)
    ledger = build_continuity_ledger(bundle)
    if output_path is None:
        output_path = spec_path.with_suffix(".continuity_ledger.json")
    write_json(output_path.resolve(), ledger.model_dump(mode="json"))
    console.print(
        Panel.fit(
            f"Saved continuity ledger scaffold.\npath={output_path.resolve()}",
            title="init-continuity-ledger",
        )
    )


@app.command("validate-prompt-pollution")
def validate_prompt_pollution_command(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    stage: str = typer.Option("shot_delta", "--stage"),
    shot_id: Optional[str] = typer.Option(None, "--shot-id"),
) -> None:
    """Check whether a prompt spec is over-describing locked details."""
    bundle = load_shortform_bundle(spec_path)
    issues = validate_prompt_pollution(bundle, stage=stage, shot_id=shot_id)
    payload = {"stage": stage, "shot_id": shot_id, "issues": issues, "pass": not issues}
    console.print_json(json.dumps(payload))
    if issues:
        raise typer.Exit(code=1)


@app.command("validate-character")
def validate_character(
    character_path: Path = typer.Argument(..., exists=True, readable=True),
    check_files: bool = typer.Option(False, help="Verify reference image paths exist."),
) -> None:
    """Validate a character bible YAML file."""
    try:
        character = _load_character(character_path)
        if check_files:
            _check_reference_files(character_path, character)
    except ValidationError as exc:
        console.print(exc)
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"Character bible is valid.\n"
            f"slug={character.slug}\n"
            f"references={len(character.reference_images)}",
            title="validate-character",
        )
    )


@app.command("validate-job")
def validate_job(
    job_path: Path = typer.Argument(..., exists=True, readable=True),
    check_files: bool = typer.Option(False, help="Verify referenced local files exist."),
) -> None:
    """Validate a video job YAML file and its linked character bible."""
    try:
        job = _load_job(job_path)
        character_path = job.resolve_character_bible_path(job_path)
        character = _load_character(character_path)
    except ValidationError as exc:
        console.print(exc)
        raise typer.Exit(code=1)

    if check_files:
        if job.input_image.source_type == "local_path":
            input_path = Path(job.input_image.source)
            if not input_path.is_absolute():
                input_path = (job_path.parent / input_path).resolve()
            if not input_path.exists():
                raise typer.BadParameter(f"Missing input image: {input_path}")
        _check_reference_files(character_path, character)

    console.print(
        Panel.fit(
            f"Video job is valid.\n"
            f"id={job.id}\n"
            f"provider={job.provider}\n"
            f"character={character.slug}",
            title="validate-job",
        )
    )


@app.command("print-prompt")
def print_prompt(
    job_path: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Render the final prompt and negative prompt for a job."""
    try:
        job = _load_job(job_path)
        character_path = job.resolve_character_bible_path(job_path)
        character = _load_character(character_path)
    except ValidationError as exc:
        console.print(exc)
        raise typer.Exit(code=1)

    payload = {
        "prompt": job.prompt(character),
        "negative_prompt": job.combined_negative_prompt(character),
    }
    console.print_json(json.dumps(payload))


@app.command("render")
def render(
    job_path: Path = typer.Argument(..., exists=True, readable=True),
    provider: Optional[str] = typer.Option(
        None,
        help="Override provider from job file.",
    ),
    comfyui_url: Optional[str] = typer.Option(
        None,
        envvar="COMFYUI_URL",
        help="ComfyUI base URL, for example http://127.0.0.1:8188",
    ),
) -> None:
    """Render a video with the provider configured in the job file."""
    settings = get_settings()
    try:
        job = _load_job(job_path)
        character_path = job.resolve_character_bible_path(job_path)
        character = _load_character(character_path)
    except ValidationError as exc:
        console.print(exc)
        raise typer.Exit(code=1)

    selected_provider = provider or job.provider
    if selected_provider == "comfyui":
        base_url = comfyui_url or settings.comfyui_url
        if not base_url:
            raise typer.BadParameter(
                "COMFYUI_URL is required for ComfyUI renders."
            )
        result = render_with_comfyui(
            job_path=job_path,
            job=job,
            character=character,
            base_url=base_url,
        )
    elif selected_provider == "cogvideox":
        result = render_with_cogvideox(
            job_path=job_path,
            job=job,
            character=character,
        )
    else:
        raise typer.BadParameter(f"Unsupported provider: {selected_provider}")

    console.print_json(result.model_dump_json(indent=2))


@app.command("create-job")
def create_job(
    job_id: str = typer.Argument(..., help="Unique shot or job id."),
    character_path: Path = typer.Option(
        ...,
        "--character",
        exists=True,
        readable=True,
        help="Path to a character bible YAML file.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output",
        help="Where to write the generated job YAML.",
    ),
    provider: str = typer.Option(
        "comfyui",
        "--provider",
        help="Provider to scaffold: comfyui or cogvideox.",
    ),
    scene_brief: str = typer.Option(
        ...,
        "--scene-brief",
        help="Human-readable shot brief.",
    ),
    input_image: Optional[Path] = typer.Option(
        None,
        "--input-image",
        help="Optional approved anchor image. Defaults to the first reference image.",
    ),
    seed: int = typer.Option(42, help="Initial seed."),
    fps: int = typer.Option(16, help="Frames per second."),
    num_frames: int = typer.Option(81, help="Frame count."),
) -> None:
    """Create a new job YAML scaffold from a character bible."""
    if provider not in {"comfyui", "cogvideox"}:
        raise typer.BadParameter("provider must be either 'comfyui' or 'cogvideox'")

    character = _load_character(character_path)
    output_path = output_path.resolve()
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_image is None:
        input_image = Path(character.reference_images[0].path)
        if not input_image.is_absolute():
            input_image = (character_path.parent / input_image).resolve()
    else:
        input_image = input_image.resolve()

    character_ref = make_relative_path(character_path.resolve(), output_dir)
    input_image_ref = make_relative_path(input_image.resolve(), output_dir)

    payload = {
        "version": "1",
        "id": job_id,
        "character_bible": character_ref,
        "provider": provider,
        "scene_prompt": scene_brief,
        "negative_prompt": "",
        "seed": seed,
        "fps": fps,
        "num_frames": num_frames,
        "output_prefix": job_id,
        "input_image": {
            "source": input_image_ref,
            "source_type": "local_path",
            "upload_to_comfyui": provider == "comfyui",
        },
    }

    character_slug = character.slug
    if provider == "comfyui":
        workflow_path = WORKFLOWS_DIR / "comfyui_i2v_template.json"
        output_dir_path = ARTIFACTS_VIDEO_DIR / "comfyui" / character_slug
        payload["comfyui"] = {
            "workflow_path": make_relative_path(workflow_path, output_dir),
            "output_dir": make_relative_path(output_dir_path, output_dir),
            "poll_interval_seconds": 5,
            "timeout_seconds": 1800,
            "download_outputs": True,
            "workflow_overrides": [
                {"node_id": "10", "input_name": "image", "value": "${input_image_name}"},
                {"node_id": "20", "input_name": "text", "value": "${prompt}"},
                {"node_id": "21", "input_name": "text", "value": "${negative_prompt}"},
                {"node_id": "30", "input_name": "seed", "value": "${seed}"},
                {"node_id": "30", "input_name": "steps", "value": 30},
                {"node_id": "30", "input_name": "cfg", "value": 6},
                {"node_id": "50", "input_name": "filename_prefix", "value": "${output_prefix}"},
            ],
        }
    else:
        payload["cogvideox"] = {
            "model_id": "THUDM/CogVideoX-5b-I2V",
            "output_path": make_relative_path(
                ARTIFACTS_VIDEO_DIR / "cogvideox" / character_slug / f"{job_id}.mp4",
                output_dir,
            ),
            "torch_dtype": "bfloat16",
            "device": "auto",
            "guidance_scale": 6,
            "num_inference_steps": 50,
            "use_dynamic_cfg": True,
            "enable_model_cpu_offload": False,
            "enable_vae_tiling": True,
            "enable_vae_slicing": True,
        }

    write_yaml(output_path, payload)
    console.print(
        Panel.fit(
            f"Created job scaffold.\nprovider={provider}\npath={output_path}",
            title="create-job",
        )
    )


@app.command("generate-character")
def generate_character(
    slug: str = typer.Argument(..., help="Character slug."),
    concept: str = typer.Option(
        "Grounded Chinese female detective protagonist for a contemporary cinematic crime mini-series.",
        "--concept",
        help="Creative concept used to synthesize the character brief.",
    ),
    character_yaml: Path = typer.Option(
        Path("examples/characters"),
        "--character-dir",
        help="Directory where the character bible YAML will be written.",
    ),
    reference_dir: Path = typer.Option(
        Path("assets/characters"),
        "--reference-dir",
        help="Base directory where generated character assets will be written.",
    ),
) -> None:
    """Generate a first-pass character bible plus reference stills."""
    settings = get_settings()
    if not settings.openai_model or not settings.openai_image_model:
        raise typer.BadParameter(
            "OPENAI_MODEL and OPENAI_IMAGE_MODEL must be set to use generate-character."
        )

    client = OpenAICompatClient(settings)
    brief = client.chat_json(build_character_brief_prompt(concept))
    prompts = build_reference_image_prompts(brief)
    negative_prompt = brief["negative_prompt"]
    if isinstance(negative_prompt, list):
        negative_prompt = ", ".join(negative_prompt)
    else:
        negative_prompt = str(negative_prompt)

    reference_dir = reference_dir.resolve() / slug / "reference"
    generated_paths = []
    for item in prompts:
        output_path = reference_dir / f"{slug}-{item['suffix']}.jpeg"
        client.generate_image(item["prompt"], output_path=output_path)
        generated_paths.append(output_path)

    character_dir = character_yaml.resolve()
    character_dir.mkdir(parents=True, exist_ok=True)
    character_path = character_dir / f"{slug}.yaml"

    bible_payload = {
        "version": "1",
        "slug": slug,
        "name": brief["name"],
        "identity_anchors": {
            "face": brief["face"],
            "hair": brief["hair"],
            "body": brief["body"],
            "outfit": brief["outfit"],
            "accessories": brief["accessories"],
        },
        "style_descriptors": brief["style_descriptors"],
        "color_palette": [],
        "prompt_template": "${name}, ${identity}, ${scene_prompt}, ${style}",
        "negative_prompt": negative_prompt,
        "reference_images": [
            {
                "path": make_relative_path(generated_paths[0], character_path.parent),
                "view": "front",
                "expression": "neutral",
            },
            {
                "path": make_relative_path(generated_paths[1], character_path.parent),
                "view": "three-quarter",
                "expression": "calm",
            },
        ],
    }
    write_yaml(character_path, bible_payload)

    metadata_path = reference_dir.parent / "generation.json"
    write_json(
        metadata_path,
        {
            "concept": concept,
            "brief": brief,
            "image_prompts": prompts,
            "outputs": [str(path) for path in generated_paths],
            "character_yaml": str(character_path),
        },
    )

    console.print(
        Panel.fit(
            f"Generated character assets.\nslug={slug}\ncharacter_yaml={character_path}\n"
            f"references={generated_paths[0].name}, {generated_paths[1].name}",
            title="generate-character",
        )
    )


@app.command("review-episode")
def review_episode_command(
    episode_dir: Path = typer.Argument(..., exists=True, readable=True),
    context: str = typer.Option(
        "",
        "--context",
        help="Optional extra continuity context passed to the reviewer.",
    ),
) -> None:
    """Extract sample frames and review continuity against the episode anchor image."""
    settings = get_settings()
    if not settings.openai_model:
        raise typer.BadParameter("OPENAI_MODEL must be set for episode review.")

    result = review_episode(episode_dir.resolve(), settings=settings, context=context)
    output_path = episode_dir.resolve() / "review.json"
    write_json(output_path, result)
    console.print_json(json.dumps(result))
    console.print(
        Panel.fit(
            f"Saved episode review.\npath={output_path}",
            title="review-episode",
        )
    )


@app.command("review-keyframes")
def review_keyframes_command(
    episode_dir: Path = typer.Argument(..., exists=True, readable=True),
    context: str = typer.Option(
        "",
        "--context",
        help="Optional extra continuity context passed to the reviewer.",
    ),
) -> None:
    """Review an episode's generated keyframe set before video generation."""
    settings = get_settings()
    if not settings.openai_model:
        raise typer.BadParameter("OPENAI_MODEL must be set for keyframe review.")

    result = review_keyframe_set(episode_dir.resolve(), settings=settings, context=context)
    output_path = episode_dir.resolve() / "keyframe_review.json"
    write_json(output_path, result)
    console.print_json(json.dumps(result))
    console.print(
        Panel.fit(
            f"Saved keyframe review.\npath={output_path}",
            title="review-keyframes",
        )
    )


@app.command("review-master-scene")
def review_master_scene_command(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    candidate_image: Path = typer.Argument(..., exists=True, readable=True),
    context: str = typer.Option("", "--context"),
) -> None:
    """Review one master-scene candidate image."""
    settings = get_settings()
    if not settings.openai_model:
        raise typer.BadParameter("OPENAI_MODEL must be set for master scene review.")
    bundle = load_shortform_bundle(spec_path)
    client = OpenAICompatClient(settings)
    result = review_master_scene_image(
        client=client,
        anchor_image=bundle.anchor_image,
        candidate_image=candidate_image.resolve(),
        context=context or bundle.spec.review_context,
    )
    output_path = candidate_image.resolve().with_suffix(".master_review.json")
    write_json(output_path, result)
    console.print_json(json.dumps(result))
    console.print(
        Panel.fit(
            f"Saved master-scene review.\npath={output_path}",
            title="review-master-scene",
        )
    )


@app.command("select-bridge-frame")
def select_bridge_frame_command(
    video_path: Path = typer.Argument(..., exists=True, readable=True),
    anchor_image: Path = typer.Option(..., "--anchor", exists=True, readable=True),
    output_dir: Path = typer.Option(Path("artifacts/bridge-frames"), "--output-dir"),
    context: str = typer.Option("", "--context"),
    tail_ratio: float = typer.Option(0.2, "--tail-ratio"),
    max_candidates: int = typer.Option(6, "--max-candidates"),
) -> None:
    """Extract and score bridge-frame candidates from the tail of a video."""
    settings = get_settings()
    if not settings.openai_model:
        raise typer.BadParameter("OPENAI_MODEL must be set for bridge-frame review.")
    result = select_bridge_frame(
        video_path=video_path.resolve(),
        anchor_image=anchor_image.resolve(),
        settings=settings,
        output_dir=output_dir.resolve(),
        context=context,
        tail_ratio=tail_ratio,
        max_candidates=max_candidates,
    )
    output_path = output_dir.resolve() / "bridge_selection.json"
    write_json(output_path, result)
    console.print_json(json.dumps(result))
    console.print(
        Panel.fit(
            f"Saved bridge-frame selection.\npath={output_path}",
            title="select-bridge-frame",
        )
    )


@app.command("search-keyframe-candidates")
def search_keyframe_candidates_command(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    output_root: Path = typer.Option(Path("artifacts/video/seedance"), "--output-root"),
    image_model: str = typer.Option("", "--image-model"),
    video_model: str = typer.Option(
        "doubao-seedance-1-5-pro-251215",
        "--video-model",
    ),
    ratio: str = typer.Option("16:9", "--ratio"),
    duration: int = typer.Option(5, "--duration"),
    resolution: str = typer.Option("720p", "--resolution"),
) -> None:
    """Search master-scene and shot-delta keyframe candidates for a shortform episode."""
    settings = get_settings()
    if not settings.openai_model or not settings.openai_image_model:
        raise typer.BadParameter("OPENAI_MODEL and OPENAI_IMAGE_MODEL must be set.")
    bundle = load_shortform_bundle(spec_path)
    result = search_keyframe_candidates(
        bundle=bundle,
        settings=settings,
        output_root=output_root,
        image_model=image_model or None,
        video_model=video_model,
        ratio=ratio,
        duration=duration,
        resolution=resolution,
    )
    console.print_json(json.dumps(result))


@app.command("render-shortform")
def render_shortform_command(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    output_root: Path = typer.Option(Path("artifacts/video/seedance"), "--output-root"),
    image_model: str = typer.Option("", "--image-model"),
    video_model: str = typer.Option(
        "doubao-seedance-1-5-pro-251215",
        "--video-model",
    ),
    ratio: str = typer.Option("16:9", "--ratio"),
    duration: int = typer.Option(5, "--duration"),
    resolution: str = typer.Option("720p", "--resolution"),
) -> None:
    """Render a chain-referenced shortform episode after staged keyframe gating."""
    settings = get_settings()
    if not settings.openai_model or not settings.openai_image_model:
        raise typer.BadParameter("OPENAI_MODEL and OPENAI_IMAGE_MODEL must be set.")
    bundle = load_shortform_bundle(spec_path)
    result = render_shortform_episode(
        bundle=bundle,
        settings=settings,
        output_root=output_root,
        image_model=image_model or None,
        video_model=video_model,
        ratio=ratio,
        duration=duration,
        resolution=resolution,
    )
    console.print_json(json.dumps(result))


if __name__ == "__main__":
    app()
