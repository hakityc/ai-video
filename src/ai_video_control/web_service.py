from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ai_video_control.healthcheck import run_health_checks
from ai_video_control.io import make_relative_path, read_json, read_yaml, write_json, write_yaml
from ai_video_control.model_registry import get_model_registry
from ai_video_control.models import (
    CharacterBible,
    PropPack,
    ScenePack,
    ShotTemplate,
    VideoJob,
)
from ai_video_control.paths import (
    ARTIFACTS_OUTPUT_DIR,
    ARTIFACTS_VIDEO_DIR,
    ASSETS_CHARACTERS_DIR,
    CHARACTERS_DIR,
    EPISODES_DIR,
    EPISODE_NOTES_DIR,
    JOBS_DIR,
    PROPS_DIR,
    REPO_ROOT,
    SCENES_DIR,
    SHOT_TEMPLATES_DIR,
    STORIES_DIR,
    WORKFLOWS_DIR,
)
from ai_video_control.providers.cogvideox import render_with_cogvideox
from ai_video_control.providers.comfyui import render_with_comfyui
from ai_video_control.providers.openai_compat import (
    OpenAICompatClient,
    build_character_brief_prompt,
    build_reference_image_prompts,
    image_path_to_data_url,
)
from ai_video_control.review import (
    review_episode,
    review_keyframe_set,
    review_master_scene_image,
    select_bridge_frame,
)
from ai_video_control.provider_runtime import get_provider_runtime_snapshot, resolve_openai_runtime
from ai_video_control.settings import (
    LOCKED_PROVIDER_DEFAULT_MODELS,
    LOCKED_PROVIDER_ID,
    get_settings,
    read_raw_settings,
    update_settings,
    update_provider_settings,
)
from ai_video_control.shortform import (
    build_master_scene_prompt,
    build_shot_delta_prompt,
    load_shortform_bundle,
    render_shortform_episode,
    search_keyframe_candidates,
    validate_prompt_pollution,
)


def get_app_state() -> dict[str, Any]:
    settings = read_raw_settings()
    runtime = get_provider_runtime_snapshot()
    scripts = list_script_library()
    characters = list_characters()
    scenes = list_scenes()
    props = list_props()
    shot_templates = list_shot_templates()
    jobs = list_jobs()
    episodes = list_episode_specs()
    outputs = list_outputs()
    qa = list_qa_entries()
    return {
        "settings": settings,
        "providers": {
            "selected_provider_id": runtime["selected_provider_id"],
            "providers": runtime["providers"],
        },
        "catalog": build_model_catalog(settings, runtime=runtime),
        "provider_health_summary": runtime["provider_health_summary"],
        "model_health_entries": runtime["model_health_entries"],
        "effective_defaults": runtime["effective_defaults"],
        "capabilities": build_capabilities(),
        "generation": {
            "counts": {
                "scripts": len(scripts),
                "characters": len(characters),
                "scenes": len(scenes),
                "props": len(props),
                "shot_templates": len(shot_templates),
                "episodes": len(episodes),
                "jobs": len(jobs),
                "outputs": len(outputs),
            },
            "scripts": scripts,
            "characters": characters,
            "scenes": scenes,
            "props": props,
            "shotTemplates": shot_templates,
            "episodes": episodes,
            "jobs": jobs,
            "outputs": outputs,
        },
        "qa": qa,
    }


def save_provider_connections(selected_provider_id: str, providers: list[dict[str, Any]]) -> dict[str, Any]:
    saved = update_provider_settings(selected_provider_id, providers)
    health_report = run_health_checks()
    return {
        **saved,
        "health_report": health_report,
    }


def refresh_model_catalog() -> dict[str, Any]:
    get_model_registry(force_refresh=True)
    return run_health_checks()


def build_model_catalog(settings: dict[str, str], runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = runtime or get_provider_runtime_snapshot()
    providers = [
        provider
        for provider in snapshot["providers"]
        if provider.get("manual_enabled", provider.get("enabled", True))
    ]
    active_provider_ids = {provider["id"] for provider in providers}
    provider_defaults = {provider["id"]: provider.get("default_models", {}) for provider in providers}
    provider_model_groups = []
    for group in snapshot["provider_model_groups"]:
        if group["provider_id"] not in active_provider_ids:
            continue
        if group["provider_id"] == LOCKED_PROVIDER_ID:
            defaults = provider_defaults.get(group["provider_id"], LOCKED_PROVIDER_DEFAULT_MODELS)
            provider_model_groups.append(
                {
                    **group,
                    "models": {
                        "text": [defaults["text"]],
                        "image": [defaults["image"]],
                        "video": [defaults["video"]],
                    },
                    "total_models": 3,
                }
            )
            continue
        provider_model_groups.append(group)
    return {
        "text_models": _catalog_values(
            settings,
            "TEXT_MODEL_OPTIONS",
            settings.get("OPENAI_MODEL", ""),
            *_registry_model_values(provider_model_groups, "text"),
            *_provider_model_values(providers, "text_model"),
        ),
        "image_models": _catalog_values(
            settings,
            "IMAGE_MODEL_OPTIONS",
            settings.get("OPENAI_IMAGE_MODEL", ""),
            *_registry_model_values(provider_model_groups, "image"),
            *_provider_model_values(providers, "image_model"),
        ),
        "video_models": _catalog_values(
            settings,
            "VIDEO_MODEL_OPTIONS",
            settings.get("OPENAI_VIDEO_MODEL", ""),
            settings.get("COGVIDEOX_MODEL_ID", ""),
            *_registry_model_values(provider_model_groups, "video"),
            *_provider_model_values(providers, "video_model"),
            *_provider_model_values(providers, "local_model"),
        ),
        "provider_model_groups": provider_model_groups,
        "model_registry_updated_at": get_model_registry().get("updated_at", ""),
        "task_constraints": {
            "character_generation": {
                "blocked_text_models": _blocked_character_text_models(
                    model_entries=snapshot["model_health_entries"],
                ),
            },
            "healthy_model_entries": snapshot["model_health_entries"],
        },
        "job_providers": [
            {"id": "comfyui", "label": "ComfyUI"},
            {"id": "cogvideox", "label": "CogVideoX"},
        ],
        "video_resolutions": ["480p", "720p", "1080p"],
        "video_durations": [3, 5, 8],
        "video_ratios": ["16:9", "9:16", "1:1"],
    }


def _provider_model_values(providers: list[dict[str, Any]], field_name: str) -> list[str]:
    values = []
    for provider in providers:
        value = str(provider.get(field_name, "")).strip()
        if value:
            values.append(value)
    return values


def _registry_model_values(provider_model_groups: list[dict[str, Any]], kind: str) -> list[str]:
    values: list[str] = []
    for group in provider_model_groups:
        models = group.get("models", {})
        values.extend(str(item).strip() for item in models.get(kind, []) if str(item).strip())
    return values


def _blocked_character_text_models(
    *,
    model_entries: list[dict[str, Any]],
) -> list[dict[str, str]]:
    blocked = []
    for entry in model_entries:
        if entry["kind"] != "text":
            continue
        for ability_state in entry.get("ability_states", []):
            if ability_state["ability"] != "character_text_json":
                continue
            if ability_state["status"] in {"unhealthy", "disabled_auto", "disabled_manual"}:
                blocked.append(
                    {
                        "model": entry["model_id"],
                        "reason": ability_state.get("reason") or "当前模型未通过角色结构化 JSON 健康检查。",
                    }
                )
    return blocked


def ensure_character_generation_text_model_supported(text_model: str | None = None) -> None:
    resolve_openai_runtime("character_generation", text_model=text_model)


def build_capabilities() -> dict[str, bool]:
    snapshot = get_provider_runtime_snapshot()
    effective_defaults = snapshot["effective_defaults"]
    settings = get_settings()
    return {
        "can_generate_scripts": bool(effective_defaults.get("script_generation")),
        "can_generate_characters": bool(effective_defaults.get("character_generation")),
        "can_search_shortform": bool(effective_defaults.get("shortform_generation")),
        "can_review": bool(settings.openai_base_url and settings.openai_api_key and settings.openai_model),
        "can_render_comfyui": bool(settings.comfyui_url),
        "can_render_cogvideox": True,
    }


def list_script_library() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    mapping = [
        ("story", STORIES_DIR, "*.md"),
        ("episode_note", EPISODE_NOTES_DIR, "*.md"),
    ]
    for kind, root, pattern in mapping:
        for path in sorted(root.glob(pattern)):
            content = path.read_text(encoding="utf-8")
            items.append(
                {
                    "kind": kind,
                    "title": _extract_title(content, path.stem),
                    "path": repo_relative(path),
                    "updated_at": path.stat().st_mtime,
                    "preview": _markdown_preview(content),
                }
            )
    return sorted(items, key=lambda item: item["updated_at"], reverse=True)


def list_characters() -> list[dict[str, Any]]:
    root = CHARACTERS_DIR
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        data = CharacterBible.model_validate(read_yaml(path))
        metadata_path = ASSETS_CHARACTERS_DIR / data.slug / "generation.json"
        items.append(
            {
                "slug": data.slug,
                "name": data.name,
                "path": repo_relative(path),
                "reference_count": len(data.reference_images),
                "style_descriptors": data.style_descriptors,
                "negative_prompt": data.negative_prompt,
                "references": [
                    _serialize_reference(path.parent, ref.path, ref.view, ref.expression)
                    for ref in data.reference_images
                ],
                "generation_metadata_path": repo_relative(metadata_path) if metadata_path.exists() else None,
            }
        )
    return items


def list_scenes() -> list[dict[str, Any]]:
    root = SCENES_DIR
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        payload = read_yaml(path)
        items.append(
            {
                "id": payload.get("id", path.stem),
                "name": payload.get("name", path.stem),
                "path": repo_relative(path),
                "fixed_elements": payload.get("fixed_elements", []),
                "forbidden_drift": payload.get("forbidden_drift", []),
            }
        )
    return items


def list_props() -> list[dict[str, Any]]:
    root = PROPS_DIR
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        payload = read_yaml(path)
        items.append(
            {
                "id": payload.get("id", path.stem),
                "name": payload.get("name", path.stem),
                "path": repo_relative(path),
                "scene_pack": payload.get("scene_pack", ""),
                "fixed_props": payload.get("fixed_props", []),
            }
        )
    return items


def list_shot_templates() -> list[dict[str, Any]]:
    root = SHOT_TEMPLATES_DIR
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        payload = read_yaml(path)
        items.append(
            {
                "id": payload.get("id", path.stem),
                "name": payload.get("name", path.stem),
                "path": repo_relative(path),
                "scene_pack": payload.get("scene_pack", ""),
                "framing": payload.get("framing", []),
                "allowed_changes": payload.get("allowed_changes", []),
            }
        )
    return items


def list_episode_specs() -> list[dict[str, Any]]:
    root = EPISODES_DIR
    qa_lookup = _qa_lookup()
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        try:
            bundle = load_shortform_bundle(path)
        except Exception:  # noqa: BLE001
            continue
        prompts = []
        for shot in bundle.spec.shots:
            prompts.append(
                {
                    "shot_id": shot.shot_id,
                    "prompt": build_shot_delta_prompt(bundle, shot.shot_id),
                    "pollution_issues": validate_prompt_pollution(
                        bundle,
                        stage="shot_delta",
                        shot_id=shot.shot_id,
                    ),
                }
            )
        qa_entry = qa_lookup.get(bundle.spec.episode)
        items.append(
            {
                "episode": bundle.spec.episode,
                "path": repo_relative(path),
                "character": bundle.character.slug,
                "anchor_image": repo_relative(bundle.anchor_image),
                "anchor_image_url": file_url(bundle.anchor_image),
                "scene_pack": bundle.scene_pack.name,
                "prop_pack": bundle.prop_pack.name,
                "shot_template": bundle.shot_template.name,
                "master_scene_prompt": build_master_scene_prompt(bundle),
                "master_scene_candidates": bundle.spec.master_scene_candidates,
                "shot_delta_candidates": bundle.spec.shot_delta_candidates,
                "shot_count": len(bundle.spec.shots),
                "review_context": bundle.spec.review_context,
                "shots": prompts,
                "qa_summary": qa_entry,
            }
        )
    return items


def list_jobs() -> list[dict[str, Any]]:
    root = JOBS_DIR
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        job = VideoJob.model_validate(read_yaml(path))
        character_path = job.resolve_character_bible_path(path)
        character = CharacterBible.model_validate(read_yaml(character_path))
        input_image_path = None
        input_image_url = None
        if job.input_image.source_type == "local_path":
            resolved = resolve_relative_path(path.parent, job.input_image.source)
            input_image_path = repo_relative(resolved)
            input_image_url = file_url(resolved)
        items.append(
            {
                "id": job.id,
                "path": repo_relative(path),
                "provider": job.provider,
                "character": character.slug,
                "scene_prompt": job.scene_prompt,
                "negative_prompt": job.negative_prompt,
                "input_image": input_image_path or job.input_image.source,
                "input_image_url": input_image_url,
                "reference_images": [item.source for item in job.reference_images],
                "reference_image_count": len(job.reference_images),
                "script_path": job.script_path,
                "script_excerpt": job.script_excerpt,
                "storyboard_notes": job.storyboard_notes,
                "camera_plan": job.camera_plan,
                "fps": job.fps,
                "num_frames": job.num_frames,
            }
        )
    return items


def list_outputs() -> list[dict[str, Any]]:
    roots = [ARTIFACTS_VIDEO_DIR, ARTIFACTS_OUTPUT_DIR]
    items: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.mp4")):
            items.append(
                {
                    "path": repo_relative(path),
                    "url": file_url(path),
                    "updated_at": path.stat().st_mtime,
                    "size_bytes": path.stat().st_size,
                }
            )
    return sorted(items, key=lambda item: item["updated_at"], reverse=True)


def list_qa_entries() -> dict[str, Any]:
    entries = list(_qa_lookup().values())
    entries.sort(key=lambda item: item.get("updated_at", 0), reverse=True)
    return {
        "count": len(entries),
        "episodes": entries,
    }


def save_settings(payload: dict[str, str]) -> dict[str, str]:
    return update_settings(payload)


def _resolved_client(
    task_name: str,
    *,
    provider_id: str | None = None,
    text_model: str | None = None,
    image_model: str | None = None,
    video_model: str | None = None,
) -> tuple[OpenAICompatClient, dict[str, Any]]:
    resolved = resolve_openai_runtime(
        task_name,
        provider_id=provider_id,
        text_model=text_model,
        image_model=image_model,
        video_model=video_model,
    )
    ability_map = {
        "script_generation": ("script_text", None, None),
        "storyboard_generation": ("script_text", None, None),
        "character_generation": ("character_text_json", "character_image_generation", None),
        "shortform_generation": ("script_text", "shortform_image_generation", "shortform_video_generation"),
        "review_text": ("script_text", None, None),
    }
    text_ability, image_ability, video_ability = ability_map[task_name]
    client = OpenAICompatClient(
        resolved["settings"],
        provider_id=resolved["provider_id"],
        text_ability=text_ability,
        image_ability=image_ability,
        video_ability=video_ability,
        health_source="runtime",
    )
    return client, resolved


def generate_story_script(
    slug: str,
    title: str,
    concept: str,
    tone: str = "",
    text_model: str | None = None,
    length_profile: str | None = None,
    seed_text: str = "",
) -> dict[str, Any]:
    client, resolved = _resolved_client("script_generation", text_model=text_model)
    slug_value = slugify(slug or title)
    output_path = STORIES_DIR / f"{slug_value}.md"
    length_guide = _script_length_guide(length_profile)
    prompt = (
        "请用简体中文输出一个面向 AI 短视频生产的 markdown 文案。"
        "必须使用这些一级标题：标题、内容定位、角色关系、世界与场景锚点、剧情钩子、镜头节奏建议、首集切入方式。"
        "内容要便于后续做角色设定、场景锚定、镜头拆分和链式视频生成。"
        f"项目标题：{title}。"
        f"核心概念：{concept}。"
        f"风格与额外限制：{tone or '无'}。"
        f"长度目标：{length_guide}。"
        f"用户给出的扩写种子段落：{seed_text or '无'}。"
        "如果有种子段落，请在保留核心信息的前提下做扩写和结构化，不要逐句照抄。"
    )
    content = client.chat_text(prompt, model=text_model or None)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content.strip() + "\n", encoding="utf-8")
    return {
        "path": repo_relative(output_path),
        "title": title,
        "provider_id": resolved["provider_id"],
        "text_model": resolved["models"].get("text"),
    }


def generate_character_assets(
    slug: str,
    concept: str,
    text_model: str | None = None,
    image_model: str | None = None,
    reference_preset: str = "standard",
    reference_image: str | None = None,
) -> dict[str, Any]:
    client, resolved = _resolved_client(
        "character_generation",
        text_model=text_model,
        image_model=image_model,
    )
    if reference_image:
        reference_path = resolve_repo_path(reference_image)
        brief = client.chat_json_with_content(
            [
                {
                    "type": "text",
                    "text": (
                        "Use the attached image as the primary visual source of truth. "
                        "Extract stable identity anchors from the person in the image, then merge them with the concept. "
                        "Return JSON only with keys: name, age_range, face, hair, body, outfit, accessories, "
                        "style_descriptors, color_palette, negative_prompt. "
                        "Keep descriptors reusable for consistent character image generation. "
                        f"Concept extension: {concept}"
                    ),
                },
                {"type": "image_url", "image_url": {"url": image_path_to_data_url(reference_path)}},
            ],
            model=text_model or None,
            max_tokens=1400,
        )
    else:
        brief = client.chat_json(build_character_brief_prompt(concept), model=text_model or None)
    prompts = build_reference_image_prompts(brief, reference_preset=reference_preset)
    negative_prompt = brief["negative_prompt"]
    if isinstance(negative_prompt, list):
        negative_prompt = ", ".join(str(item) for item in negative_prompt)
    else:
        negative_prompt = str(negative_prompt)

    slug_value = slugify(slug)
    reference_dir = ASSETS_CHARACTERS_DIR / slug_value / "reference"
    generated_paths = []
    for item in prompts:
        output_path = reference_dir / f"{slug_value}-{item['suffix']}.jpeg"
        client.generate_image(item["prompt"], output_path=output_path, model=image_model or None)
        generated_paths.append(output_path)

    character_path = CHARACTERS_DIR / f"{slug_value}.yaml"
    bible_payload = {
        "version": "1",
        "slug": slug_value,
        "name": brief["name"],
        "identity_anchors": {
            "face": brief["face"],
            "hair": brief["hair"],
            "body": brief["body"],
            "outfit": brief["outfit"],
            "accessories": brief["accessories"],
        },
        "style_descriptors": brief["style_descriptors"],
        "color_palette": brief.get("color_palette", []),
        "prompt_template": "${name}, ${identity}, ${scene_prompt}, ${style}",
        "negative_prompt": negative_prompt,
        "reference_images": [],
    }
    bible_payload["reference_images"] = [
        {
            "path": relative_from(character_path.parent, path),
            "view": item["view"],
            "expression": item["expression"],
        }
        for item, path in zip(prompts, generated_paths, strict=False)
    ]
    write_yaml(character_path, bible_payload)

    metadata_path = reference_dir.parent / "generation.json"
    write_json(
        metadata_path,
        {
            "concept": concept,
            "brief": brief,
            "reference_preset": reference_preset,
            "reference_image": repo_relative(resolve_repo_path(reference_image)) if reference_image else None,
            "image_prompts": prompts,
            "outputs": [repo_relative(path) for path in generated_paths],
            "character_yaml": repo_relative(character_path),
        },
    )
    return {
        "slug": slug_value,
        "character_path": repo_relative(character_path),
        "reference_paths": [repo_relative(path) for path in generated_paths],
        "provider_id": resolved["provider_id"],
        "text_model": resolved["models"].get("text"),
        "image_model": resolved["models"].get("image"),
    }


def create_video_job(
    job_id: str,
    character_path: str,
    provider: str,
    scene_brief: str,
    input_image: str | None = None,
    reference_images: list[str] | None = None,
    script_path: str | None = None,
    storyboard_notes: str | None = None,
    camera_plan: str | None = None,
    seed: int = 42,
    fps: int = 16,
    num_frames: int = 81,
) -> dict[str, Any]:
    if provider not in {"comfyui", "cogvideox"}:
        raise ValueError("provider must be comfyui or cogvideox")

    character_file = resolve_repo_path(character_path)
    character = CharacterBible.model_validate(read_yaml(character_file))
    output_path = JOBS_DIR / f"{job_id}-{provider}.yaml"

    selected_reference_paths: list[Path] = []
    for item in reference_images or []:
        if str(item).strip():
            selected_reference_paths.append(resolve_repo_path(item))

    if input_image:
        input_image_path = resolve_repo_path(input_image)
    elif selected_reference_paths:
        input_image_path = selected_reference_paths[0]
    else:
        input_image_path = resolve_relative_path(character_file.parent, character.reference_images[0].path)

    if not selected_reference_paths:
        selected_reference_paths = [input_image_path]

    script_excerpt = ""
    script_path_value = None
    if script_path:
        script_file = resolve_repo_path(script_path)
        script_path_value = relative_from(output_path.parent, script_file)
        script_excerpt = _markdown_preview(script_file.read_text(encoding="utf-8"))

    composed_scene_prompt = scene_brief.strip()
    context_parts = []
    if script_excerpt:
        context_parts.append(f"参考文案：{script_excerpt}")
    if storyboard_notes:
        context_parts.append(f"分镜锚点：{storyboard_notes.strip()}")
    if camera_plan:
        context_parts.append(f"镜头运动与节奏：{camera_plan.strip()}")
    if len(selected_reference_paths) > 1:
        context_parts.append(
            "额外参考图：" + "、".join(path.stem for path in selected_reference_paths[1:])
        )
    if context_parts:
        composed_scene_prompt = composed_scene_prompt + "\n\n" + "\n".join(context_parts)

    negative_prompt = _build_job_negative_prompt(
        character=character,
        scene_brief=scene_brief,
        script_excerpt=script_excerpt,
        storyboard_notes=storyboard_notes or "",
        camera_plan=camera_plan or "",
        reference_count=len(selected_reference_paths),
    )

    payload: dict[str, Any] = {
        "version": "1",
        "id": job_id,
        "character_bible": relative_from(output_path.parent, character_file),
        "provider": provider,
        "scene_prompt": composed_scene_prompt,
        "script_path": script_path_value,
        "script_excerpt": script_excerpt or None,
        "storyboard_notes": storyboard_notes or None,
        "camera_plan": camera_plan or None,
        "negative_prompt": negative_prompt,
        "seed": seed,
        "fps": fps,
        "num_frames": num_frames,
        "output_prefix": job_id,
        "input_image": {
            "source": relative_from(output_path.parent, input_image_path),
            "source_type": "local_path",
            "upload_to_comfyui": provider == "comfyui",
        },
        "reference_images": [
            {
                "source": relative_from(output_path.parent, path),
                "source_type": "local_path",
                "upload_to_comfyui": False,
            }
            for path in selected_reference_paths
        ],
    }

    if provider == "comfyui":
        workflow_path = WORKFLOWS_DIR / "comfyui_i2v_template.json"
        output_dir = ARTIFACTS_VIDEO_DIR / "comfyui" / character.slug
        payload["comfyui"] = {
            "workflow_path": relative_from(output_path.parent, workflow_path),
            "output_dir": relative_from(output_path.parent, output_dir),
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
        settings = get_settings()
        payload["cogvideox"] = {
            "model_id": settings.cogvideox_model_id or "THUDM/CogVideoX-5b-I2V",
            "output_path": relative_from(
                output_path.parent,
                ARTIFACTS_VIDEO_DIR / "cogvideox" / character.slug / f"{job_id}.mp4",
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
    return {"path": repo_relative(output_path), "id": job_id}


def analyze_video_job_plan(
    job_id: str,
    character_path: str,
    provider: str,
    scene_brief: str,
    input_image: str | None = None,
    reference_images: list[str] | None = None,
    script_path: str | None = None,
    storyboard_notes: str | None = None,
    camera_plan: str | None = None,
    seed: int = 42,
    fps: int = 16,
    num_frames: int = 81,
) -> dict[str, Any]:
    character_file = resolve_repo_path(character_path)
    character = CharacterBible.model_validate(read_yaml(character_file))
    selected_reference_paths = [resolve_repo_path(item) for item in (reference_images or []) if str(item).strip()]
    script_excerpt = ""
    if script_path:
        script_file = resolve_repo_path(script_path)
        script_excerpt = _markdown_preview(script_file.read_text(encoding="utf-8"))

    duration_seconds = round(num_frames / max(fps, 1), 2)
    motion_terms = _match_terms(
        scene_brief + "\n" + (storyboard_notes or ""),
        [
            "跑",
            "冲",
            "追",
            "打",
            "坠",
            "爆炸",
            "翻滚",
            "跳",
            "飞",
            "快速推进",
            "快速跟拍",
            "run",
            "chase",
            "fight",
            "explosion",
            "jump",
        ],
    )
    location_terms = _match_terms(
        scene_brief + "\n" + script_excerpt,
        [
            "便利店",
            "街道",
            "巷子",
            "楼顶",
            "房间",
            "办公室",
            "车内",
            "地铁",
            "店外",
            "street",
            "alley",
            "rooftop",
            "room",
            "office",
            "car interior",
        ],
    )

    warnings: list[str] = []
    missing_assets: list[str] = []
    recommended_assets: list[str] = []
    negative_prompt_hints = [
        "不要换脸，不要换发型，不要改服装主色",
        "不要新增道具，不要改变场景布局",
        "不要突然切镜头焦段，不要出现肢体畸变或多余手指",
    ]

    if not script_path:
        missing_assets.append("未绑定文案，镜头容易缺少剧情约束")
        recommended_assets.append("先选一份文案，再生成分镜锚点")
    if not storyboard_notes:
        missing_assets.append("未生成分镜锚点，模型缺少镜头级约束")
        recommended_assets.append("调用分镜建议服务，固定景别、动作和过渡")
    if not camera_plan:
        missing_assets.append("未填写镜头运动与节奏，视频运动容易发散")
        recommended_assets.append("补一段镜头运动计划，例如缓推、轻微手持、结尾停稳")
    if len(selected_reference_paths) < 2:
        recommended_assets.append("补至少 2 张参考图，建议正脸 + 3/4 或全身")
    if input_image is None and not selected_reference_paths:
        warnings.append("当前没有显式主参考图，将退回角色默认参考图")
    if duration_seconds > 6:
        warnings.append("单条任务时长偏长，链式短视频更建议拆成两个镜头或先做桥接镜头")
    if len(motion_terms) >= 2:
        warnings.append("场景说明里动作变化偏多，建议每条任务只保留一个主动作轴")
    if len(location_terms) >= 2:
        warnings.append("场景文本混入多个地点，容易造成空间漂移")
    if "多人" in scene_brief or "对手戏" in scene_brief or "两人" in scene_brief:
        warnings.append("多人镜头建议补主次关系和站位，否则身份一致性容易抖动")
        negative_prompt_hints.append("不要让配角抢主角脸部权重，不要让站位突变")

    recommended_defaults = _recommend_job_defaults(
        provider=provider,
        scene_brief=scene_brief,
        duration_seconds=duration_seconds,
        motion_terms=motion_terms,
    )
    suggested_negative_prompt = _build_job_negative_prompt(
        character=character,
        scene_brief=scene_brief,
        script_excerpt=script_excerpt,
        storyboard_notes=storyboard_notes or "",
        camera_plan=camera_plan or "",
        reference_count=len(selected_reference_paths),
    )
    continuity_locks = _build_continuity_locks(
        character=character,
        reference_paths=selected_reference_paths,
        script_excerpt=script_excerpt,
        storyboard_notes=storyboard_notes or "",
    )

    score = 100
    score -= len(missing_assets) * 12
    score -= len(warnings) * 8
    if len(selected_reference_paths) < 2:
        score -= 8
    score = max(score, 20)
    if score >= 82:
        readiness = "ready"
    elif score >= 58:
        readiness = "needs_attention"
    else:
        readiness = "high_risk"

    return {
        "character_path": repo_relative(character_file),
        "provider": provider,
        "seed": seed,
        "estimated_duration_seconds": duration_seconds,
        "readiness": readiness,
        "score": score,
        "script_excerpt": script_excerpt or None,
        "continuity_locks": continuity_locks,
        "missing_assets": _unique_texts(missing_assets),
        "warnings": _unique_texts(warnings),
        "recommended_assets": _unique_texts(recommended_assets),
        "negative_prompt_hints": _unique_texts(negative_prompt_hints),
        "suggested_negative_prompt": suggested_negative_prompt,
        "recommended_defaults": recommended_defaults,
    }


def generate_storyboard_outline(
    character_path: str,
    script_path: str,
    brief: str = "",
    text_model: str | None = None,
    shot_count: int = 4,
) -> dict[str, Any]:
    character_file = resolve_repo_path(character_path)
    script_file = resolve_repo_path(script_path)
    character = CharacterBible.model_validate(read_yaml(character_file))
    script_content = script_file.read_text(encoding="utf-8")
    script_excerpt = _markdown_preview(script_content)

    client, resolved = _resolved_client("storyboard_generation", text_model=text_model)
    try:
        structured = client.chat_json(
            (
                "You are planning a chain-referenced shortform video. "
                "Return JSON only with keys: summary, camera_plan, negative_prompt_hints, shots. "
                f"Create {max(3, min(shot_count, 8))} shots for image-to-video production. "
                "shots must be an array. Each shot must include: label, framing, subject_motion, camera_motion, continuity_lock, change_allowance, bridge_goal. "
                "All fields must be concise Simplified Chinese strings. "
                "Prioritize identity stability, outfit stability, scene anchors, and bridge-frame-friendly transitions. "
                f"Character anchors: {character.identity_text()}. "
                f"Character style: {character.style_text()}. "
                f"Script excerpt: {script_excerpt}. "
                f"Extra brief: {brief or '无'}."
            ),
            model=text_model or None,
        )
    except Exception:  # noqa: BLE001
        fallback = _fallback_storyboard_plan(
            character=character,
            script_excerpt=script_excerpt,
            brief=brief,
            shot_count=max(3, min(shot_count, 8)),
        )
        return {
            "character_path": repo_relative(character_file),
            "script_path": repo_relative(script_file),
            "storyboard": _render_storyboard_text(
                summary=fallback["summary"],
                shots=fallback["shots"],
            ),
            "camera_plan": fallback["camera_plan"],
            "negative_prompt_hints": fallback["negative_prompt_hints"],
            "shots": fallback["shots"],
        }
    shots = [
        {
            "label": str(item.get("label", "")).strip(),
            "framing": str(item.get("framing", "")).strip(),
            "subject_motion": str(item.get("subject_motion", "")).strip(),
            "camera_motion": str(item.get("camera_motion", "")).strip(),
            "continuity_lock": str(item.get("continuity_lock", "")).strip(),
            "change_allowance": str(item.get("change_allowance", "")).strip(),
            "bridge_goal": str(item.get("bridge_goal", "")).strip(),
        }
        for item in structured.get("shots", [])
        if isinstance(item, dict)
    ]
    content = _render_storyboard_text(
        summary=str(structured.get("summary", "")).strip(),
        shots=shots,
    )
    return {
        "character_path": repo_relative(character_file),
        "script_path": repo_relative(script_file),
        "storyboard": content.strip(),
        "camera_plan": str(structured.get("camera_plan", "")).strip(),
        "negative_prompt_hints": [
            str(item).strip() for item in structured.get("negative_prompt_hints", []) if str(item).strip()
        ],
        "shots": shots,
        "provider_id": resolved["provider_id"],
        "text_model": resolved["models"].get("text"),
    }


def render_video_job(job_path: str, provider_override: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    job_file = resolve_repo_path(job_path)
    job = VideoJob.model_validate(read_yaml(job_file))
    character = CharacterBible.model_validate(read_yaml(job.resolve_character_bible_path(job_file)))
    provider = provider_override or job.provider
    if provider == "comfyui":
        if not settings.comfyui_url:
            raise ValueError("COMFYUI_URL is required before running ComfyUI jobs.")
        result = render_with_comfyui(job_file, job, character, base_url=settings.comfyui_url)
    elif provider == "cogvideox":
        result = render_with_cogvideox(job_file, job, character)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    return result.model_dump()


def _recommend_job_defaults(
    provider: str,
    scene_brief: str,
    duration_seconds: float,
    motion_terms: list[str],
) -> dict[str, Any]:
    text = scene_brief.lower()
    static_terms = ["特写", "凝视", "停顿", "对话", "close-up", "still", "stare"]
    walk_terms = ["走", "走过", "穿过", "跟拍", "walk", "tracking", "follow"]
    complex_terms = ["跑", "追", "fight", "explosion", "爆炸", "翻滚", "跳"]
    if any(term in text for term in complex_terms):
        return {
            "provider": provider,
            "fps": 16,
            "num_frames": 65,
            "guidance": "动作复杂，建议拆成更短镜头，先保住主体一致性和剪辑接点。",
        }
    if any(term in text for term in walk_terms) or motion_terms:
        return {
            "provider": provider,
            "fps": 16,
            "num_frames": 81 if duration_seconds <= 5.2 else 97,
            "guidance": "中等运动镜头建议保留轻动作和稳定镜头轨迹。",
        }
    if any(term in text for term in static_terms):
        return {
            "provider": provider,
            "fps": 16,
            "num_frames": 65,
            "guidance": "静态或情绪镜头可缩短总帧数，换取更稳的人脸和服装一致性。",
        }
    return {
        "provider": provider,
        "fps": 16,
        "num_frames": 81,
        "guidance": "默认建议适合桥接、行走和普通叙事镜头。",
    }


def _build_job_negative_prompt(
    character: CharacterBible,
    scene_brief: str,
    script_excerpt: str,
    storyboard_notes: str,
    camera_plan: str,
    reference_count: int,
) -> str:
    items = [
        character.negative_prompt,
        "不要换脸，不要改变眼型、脸型和发型轮廓",
        "不要改服装主色，不要丢失关键配饰和工牌",
        "不要新增无关道具，不要改变场景布局和灯位逻辑",
        "不要出现多余手指、肢体畸变、糊脸、双重五官",
        "不要突然切换镜头焦段，不要发生空间跳变",
    ]
    lowered = "\n".join([scene_brief, script_excerpt, storyboard_notes, camera_plan]).lower()
    if any(term in lowered for term in ["多人", "两人", "对手戏", "多角色", "dual", "two people"]):
        items.append("不要让配角抢主角脸部权重，不要让人物站位突然互换")
    if any(term in lowered for term in ["跑", "追", "fight", "爆炸", "翻滚", "jump"]):
        items.append("不要做大幅度动作形变，不要让背景运动超过主体运动")
    if reference_count < 2:
        items.append("不要偏离已有角色参考图的服装和发型")
    return ", ".join(_unique_texts(items))


def _build_continuity_locks(
    character: CharacterBible,
    reference_paths: list[Path],
    script_excerpt: str,
    storyboard_notes: str,
) -> list[str]:
    locks = []
    locks.extend(character.identity_anchors.face[:2])
    locks.extend(character.identity_anchors.hair[:2])
    locks.extend(character.identity_anchors.outfit[:2])
    if reference_paths:
        locks.append("主参考图锚定：" + "、".join(path.stem for path in reference_paths[:3]))
    if script_excerpt:
        locks.append("剧情锚点：" + script_excerpt[:80])
    if storyboard_notes:
        locks.append("分镜锚点已提供，优先遵循景别和动作边界")
    return _unique_texts(locks)


def _match_terms(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def _unique_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        text = value.strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(text)
    return results


def _render_storyboard_text(summary: str, shots: list[dict[str, str]]) -> str:
    lines: list[str] = []
    if summary:
        lines.append(summary)
    for index, shot in enumerate(shots, start=1):
        label = shot.get("label") or f"镜头 {index}"
        lines.append(
            (
                f"{index}. {label}｜景别：{shot.get('framing') or '未写'}；"
                f"主体动作：{shot.get('subject_motion') or '未写'}；"
                f"镜头运动：{shot.get('camera_motion') or '未写'}；"
                f"连续性锁：{shot.get('continuity_lock') or '未写'}；"
                f"允许变化：{shot.get('change_allowance') or '未写'}；"
                f"桥接目标：{shot.get('bridge_goal') or '未写'}"
            )
        )
    return "\n".join(lines).strip()


def _fallback_storyboard_plan(
    character: CharacterBible,
    script_excerpt: str,
    brief: str,
    shot_count: int,
) -> dict[str, Any]:
    identity_lock = "锁定 " + "、".join(_unique_texts(character.identity_anchors.face[:1] + character.identity_anchors.hair[:1] + character.identity_anchors.outfit[:1]))
    base_motion = "轻微动作，不做大幅度形变"
    base_camera = "缓慢前推或稳定跟随，结尾停稳方便桥接"
    summary = "先稳住角色身份和场景，再逐步释放动作变化，确保每个镜头只承担一个主要变化。"
    shots = []
    templates = [
        {
            "label": "镜头 1 建立",
            "framing": "中景",
            "subject_motion": "角色先站定并确认周围状态",
            "camera_motion": "稳定开场，轻微前推",
            "continuity_lock": identity_lock,
            "change_allowance": "只允许视线和肩部小幅变化",
            "bridge_goal": "结尾保持可接下一镜的清晰站姿",
        },
        {
            "label": "镜头 2 反应",
            "framing": "中近景",
            "subject_motion": "角色做一次明确但克制的反应动作",
            "camera_motion": "轻微跟随，不改变轴线",
            "continuity_lock": "保持脸、发型、服装主轮廓稳定",
            "change_allowance": "只放开表情和上半身动作",
            "bridge_goal": "停在表情最清楚的一帧",
        },
        {
            "label": "镜头 3 推进",
            "framing": "中景到中近景",
            "subject_motion": base_motion,
            "camera_motion": base_camera,
            "continuity_lock": "场景锚点和道具位置不变",
            "change_allowance": "允许一步移动或一次回头",
            "bridge_goal": "收在动作将止未止的姿态",
        },
        {
            "label": "镜头 4 收尾",
            "framing": "中近景或特写",
            "subject_motion": "把当前情绪落稳，不再新增复杂动作",
            "camera_motion": "停止运动，留 6 到 8 帧静止余量",
            "continuity_lock": "锁定脸部细节、服装配饰和主光位",
            "change_allowance": "只允许眼神或手部小动作",
            "bridge_goal": "直接可作为下一镜桥接起点",
        },
    ]
    for item in templates[:shot_count]:
        shots.append(item)
    if brief:
        shots[0]["subject_motion"] = brief[:48]
    if script_excerpt:
        shots[0]["bridge_goal"] = f"承接文案重点：{script_excerpt[:42]}"
    return {
        "summary": summary,
        "camera_plan": "整体保持单一运动逻辑，先稳后动，结尾必须停稳，避免突然切轴或节奏断裂。",
        "negative_prompt_hints": [
            "不要换脸，不要改发型主轮廓",
            "不要改服装主色和关键配饰",
            "不要新增无关道具，不要突然改变空间布局",
        ],
        "shots": shots,
    }


def search_shortform_candidates(
    spec_path: str,
    image_model: str | None = None,
    video_model: str | None = None,
    ratio: str | None = None,
    duration: int | None = None,
    resolution: str | None = None,
) -> dict[str, Any]:
    resolved = resolve_openai_runtime(
        "shortform_generation",
        image_model=image_model,
        video_model=video_model,
    )
    spec_file = resolve_repo_path(spec_path)
    bundle = load_shortform_bundle(spec_file)
    result = search_keyframe_candidates(
        bundle=bundle,
        settings=resolved["settings"],
        output_root=REPO_ROOT / "artifacts" / "video" / "seedance",
        image_model=resolved["models"].get("image"),
        video_model=resolved["models"].get("video") or "doubao-seedance-1-5-pro-251215",
        ratio=ratio or resolved["settings"].openai_video_ratio or "16:9",
        duration=duration or int(resolved["settings"].openai_video_duration or "5"),
        resolution=resolution or resolved["settings"].openai_video_resolution or "720p",
    )
    result["provider_id"] = resolved["provider_id"]
    result["text_model"] = resolved["models"].get("text")
    result["image_model"] = resolved["models"].get("image")
    result["video_model"] = resolved["models"].get("video")
    return result


def render_shortform(
    spec_path: str,
    image_model: str | None = None,
    video_model: str | None = None,
    ratio: str | None = None,
    duration: int | None = None,
    resolution: str | None = None,
) -> dict[str, Any]:
    resolved = resolve_openai_runtime(
        "shortform_generation",
        image_model=image_model,
        video_model=video_model,
    )
    spec_file = resolve_repo_path(spec_path)
    bundle = load_shortform_bundle(spec_file)
    result = render_shortform_episode(
        bundle=bundle,
        settings=resolved["settings"],
        output_root=REPO_ROOT / "artifacts" / "video" / "seedance",
        image_model=resolved["models"].get("image"),
        video_model=resolved["models"].get("video") or "doubao-seedance-1-5-pro-251215",
        ratio=ratio or resolved["settings"].openai_video_ratio or "16:9",
        duration=duration or int(resolved["settings"].openai_video_duration or "5"),
        resolution=resolution or resolved["settings"].openai_video_resolution or "720p",
    )
    result["provider_id"] = resolved["provider_id"]
    result["text_model"] = resolved["models"].get("text")
    result["image_model"] = resolved["models"].get("image")
    result["video_model"] = resolved["models"].get("video")
    return result


def run_episode_review(episode_dir: str, context: str = "") -> dict[str, Any]:
    result = review_episode(resolve_repo_path(episode_dir), settings=get_settings(), context=context)
    output_path = resolve_repo_path(episode_dir) / "review.json"
    write_json(output_path, result)
    return {"path": repo_relative(output_path), "result": result}


def run_keyframe_review(episode_dir: str, context: str = "") -> dict[str, Any]:
    result = review_keyframe_set(resolve_repo_path(episode_dir), settings=get_settings(), context=context)
    output_path = resolve_repo_path(episode_dir) / "keyframe_review.json"
    write_json(output_path, result)
    return {"path": repo_relative(output_path), "result": result}


def run_master_scene_review(spec_path: str, candidate_image: str, context: str = "") -> dict[str, Any]:
    settings = get_settings()
    spec_file = resolve_repo_path(spec_path)
    bundle = load_shortform_bundle(spec_file)
    candidate_path = resolve_repo_path(candidate_image)
    client = OpenAICompatClient(settings)
    result = review_master_scene_image(
        client=client,
        anchor_image=bundle.anchor_image,
        candidate_image=candidate_path,
        context=context or bundle.spec.review_context,
    )
    output_path = candidate_path.with_suffix(".master_review.json")
    write_json(output_path, result)
    return {"path": repo_relative(output_path), "result": result}


def run_bridge_frame_selection(
    video_path: str,
    anchor_image: str,
    context: str = "",
    tail_ratio: float = 0.2,
    max_candidates: int = 6,
) -> dict[str, Any]:
    output_dir = resolve_repo_path(video_path).parent / "bridge"
    result = select_bridge_frame(
        video_path=resolve_repo_path(video_path),
        anchor_image=resolve_repo_path(anchor_image),
        settings=get_settings(),
        output_dir=output_dir,
        context=context,
        tail_ratio=tail_ratio,
        max_candidates=max_candidates,
    )
    output_path = output_dir / "bridge_selection.json"
    write_json(output_path, result)
    return {"path": repo_relative(output_path), "result": result}


def read_text_file(path: str) -> dict[str, Any]:
    file_path = resolve_repo_path(path)
    return {
        "path": repo_relative(file_path),
        "content": file_path.read_text(encoding="utf-8"),
    }


def resolve_repo_path(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    candidate.relative_to(REPO_ROOT)
    return candidate


def resolve_relative_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def file_url(path: Path) -> str:
    return f"/api/files/{repo_relative(path)}"


def relative_from(base_dir: Path, target: Path) -> str:
    return make_relative_path(target.resolve(), base_dir.resolve())


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "untitled"


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return fallback


def _markdown_preview(content: str) -> str:
    for line in content.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        return text[:180]
    return ""


def _serialize_reference(
    base_dir: Path,
    raw_path: str,
    view: str,
    expression: str | None,
) -> dict[str, Any]:
    resolved = resolve_relative_path(base_dir, raw_path)
    exists = resolved.exists()
    return {
        "view": view,
        "expression": expression,
        "path": repo_relative(resolved) if exists else raw_path,
        "url": file_url(resolved) if exists else None,
        "exists": exists,
    }


def _catalog_values(settings: dict[str, str], options_key: str, *fallback_values: str) -> list[str]:
    values: list[str] = []
    raw = settings.get(options_key, "")
    if raw:
        values.extend(item.strip() for item in raw.split(","))
    values.extend(value.strip() for value in fallback_values if value and value.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _script_length_guide(length_profile: str | None) -> str:
    mapping = {
        "flash": "快闪开场，估算成片约 3-5 秒，建议 1 到 2 个镜头节拍",
        "short": "标准短视频，估算成片约 8-12 秒，建议 3 到 5 个镜头节拍",
        "medium": "完整短段落，估算成片约 15-20 秒，建议 5 到 8 个镜头节拍",
        "long": "扩展叙事，估算成片约 25-35 秒，建议 8 到 12 个镜头节拍",
    }
    return mapping.get(length_profile or "", "标准短视频，估算成片约 8-12 秒，建议 3 到 5 个镜头节拍")


def _qa_lookup() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    root = ARTIFACTS_VIDEO_DIR
    if not root.exists():
        return result

    for search_path in root.rglob("search_summary.json"):
        payload = read_json(search_path)
        episode = payload.get("episode") or search_path.parent.name
        entry = result.setdefault(
            episode,
            {
                "episode": episode,
                "artifact_dir": repo_relative(search_path.parent),
                "updated_at": search_path.stat().st_mtime,
                "search_status": payload.get("status"),
                "master_scene": payload.get("master_scene", {}).get("selected"),
                "shot_count": len(payload.get("shots", [])),
                "selected_shots": [
                    {
                        "shot_id": item.get("shot_id"),
                        "selected": item.get("selected"),
                    }
                    for item in payload.get("shots", [])
                ],
            },
        )
        entry["updated_at"] = max(entry["updated_at"], search_path.stat().st_mtime)

    for manifest_path in root.rglob("manifest.json"):
        payload = read_json(manifest_path)
        episode = payload.get("episode") or manifest_path.parent.name
        entry = result.setdefault(
            episode,
            {
                "episode": episode,
                "artifact_dir": repo_relative(manifest_path.parent),
                "updated_at": manifest_path.stat().st_mtime,
            },
        )
        entry["manifest_path"] = repo_relative(manifest_path)
        entry["updated_at"] = max(entry.get("updated_at", 0), manifest_path.stat().st_mtime)
        entry["rendered_shots"] = payload.get("shots", [])

        keyframe_review_path = manifest_path.parent / "keyframe_review.json"
        if keyframe_review_path.exists():
            keyframe_review = read_json(keyframe_review_path)
            entry["keyframe_review"] = {
                "pass_gate": keyframe_review.get("pass_gate"),
                "overall_score": keyframe_review.get("overall_score"),
                "issues": keyframe_review.get("issues", []),
                "path": repo_relative(keyframe_review_path),
            }

        episode_review_path = manifest_path.parent / "review.json"
        if episode_review_path.exists():
            episode_review = read_json(episode_review_path)
            entry["episode_review"] = {
                "overall_identity_score": episode_review.get("overall_identity_score"),
                "overall_outfit_score": episode_review.get("overall_outfit_score"),
                "overall_atmosphere_score": episode_review.get("overall_atmosphere_score"),
                "path": repo_relative(episode_review_path),
            }

        final_reviews = []
        for final_path in manifest_path.parent.rglob("final_review.json"):
            final_payload = read_json(final_path)
            final_reviews.append(
                {
                    "path": repo_relative(final_path),
                    "pass_gate": final_payload.get("pass_gate"),
                    "overall_score": final_payload.get("overall_score"),
                    "issues": final_payload.get("issues", []),
                }
            )
        if final_reviews:
            entry["final_reviews"] = final_reviews
    return result
