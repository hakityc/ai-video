from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

import typer
import yaml

from ai_video_control.io import write_json
from ai_video_control.providers.openai_compat import OpenAICompatClient
from ai_video_control.settings import get_settings

app = typer.Typer(no_args_is_help=True)


def _load_spec(spec_path: Path) -> Dict[str, Any]:
    with spec_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _poll_task(
    client: OpenAICompatClient,
    task_id: str,
    poll_interval: int,
    timeout_seconds: int,
) -> Dict[str, Any]:
    started_at = time.time()
    while True:
        result = client.get_video_task(task_id)
        status = result.get("status")
        if status == "succeeded":
            return result
        if status in {"failed", "cancelled"}:
            raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))
        if time.time() - started_at > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for task {task_id}")
        time.sleep(poll_interval)


def _episode_dir_name(episode: str) -> str:
    if episode.startswith("episode-"):
        return episode
    if episode.startswith("ep") and episode[2:].isdigit():
        return f"episode-{episode[2:]}"
    return episode


@app.command()
def run(
    spec: Path = typer.Argument(..., exists=True, readable=True),
    output_root: Path = typer.Option(
        Path("artifacts/video/seedance"),
        help="Base directory for generated episode artifacts.",
    ),
    image_model: str = typer.Option(
        "",
        help="Optional override for the image model.",
    ),
    video_model: str = typer.Option(
        "doubao-seedance-1-5-pro-251215",
        help="Video generation model id.",
    ),
    ratio: str = typer.Option("1:1"),
    duration: int = typer.Option(5),
    resolution: str = typer.Option("720p"),
    poll_interval: int = typer.Option(8),
    timeout_seconds: int = typer.Option(1800),
    keyframes_only: bool = typer.Option(
        False,
        "--keyframes-only",
        help="Generate only keyframes and manifest metadata. Skip video generation.",
    ),
) -> None:
    settings = get_settings()
    client = OpenAICompatClient(settings)
    spec_data = _load_spec(spec.resolve())

    episode = spec_data["episode"]
    character_slug = spec_data["character_slug"]
    episode_key = episode.replace(f"{character_slug}-", "")
    episode_dir = output_root.resolve() / character_slug / _episode_dir_name(episode_key)
    episode_dir.mkdir(parents=True, exist_ok=True)

    anchor_image = (Path.cwd() / spec_data["anchor_image"]).resolve()
    manifest: Dict[str, Any] = {
        "episode": episode,
        "character": character_slug,
        "provider": video_model,
        "story_mainline": spec_data.get("story_mainline", ""),
        "anchor_local": str(anchor_image),
        "review_context": spec_data.get("review_context", ""),
        "shots": [],
    }

    keyframe_dir = episode_dir / "keyframes"
    keyframe_dir.mkdir(parents=True, exist_ok=True)

    for shot in spec_data["shots"]:
        shot_id = shot["shot_id"]
        shot_dir = episode_dir / shot_id
        shot_dir.mkdir(parents=True, exist_ok=True)

        keyframe_path = keyframe_dir / f"{shot_id}.jpeg"
        image_meta = client.generate_image_with_meta(
            prompt=shot["keyframe_prompt"],
            output_path=keyframe_path,
            model=image_model or None,
            size="1024x1024",
        )
        write_json(
            shot_dir / "keyframe.json",
            {
                "shot_id": shot_id,
                "prompt": shot["keyframe_prompt"],
                "image_model": image_model or settings.openai_image_model,
                **image_meta,
            },
        )

        shot_manifest: Dict[str, Any] = {
            "shot_id": shot_id,
            "keyframe_path": str(keyframe_path.resolve()),
            "keyframe_meta_path": str((shot_dir / "keyframe.json").resolve()),
            "prompt": shot.get("video_prompt", ""),
            "status": "keyframe_only" if keyframes_only else "pending_video",
        }

        if not keyframes_only:
            task = client.submit_video_task(
                model=video_model,
                ratio=ratio,
                duration=duration,
                resolution=resolution,
                content=[
                    {"type": "text", "text": shot["video_prompt"]},
                    {"type": "image_url", "image_url": {"url": image_meta["url"]}},
                ],
            )
            task_id = task["id"]
            result = _poll_task(
                client=client,
                task_id=task_id,
                poll_interval=poll_interval,
                timeout_seconds=timeout_seconds,
            )
            video_url = result["content"]["video_url"]
            video_path = shot_dir / f"{task_id}.mp4"
            client.download_file(video_url, video_path)

            meta_path = shot_dir / f"{task_id}.json"
            write_json(meta_path, result)
            shot_manifest.update(
                {
                    "task_id": task_id,
                    "status": result["status"],
                    "video_path": str(video_path.resolve()),
                    "meta_path": str(meta_path.resolve()),
                    "duration": result.get("duration"),
                    "resolution": result.get("resolution"),
                    "ratio": result.get("ratio"),
                    "fps": result.get("framespersecond"),
                    "seed": result.get("seed"),
                }
            )

        manifest["shots"].append(shot_manifest)
        write_json(episode_dir / "manifest.json", manifest)

    write_json(episode_dir / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
