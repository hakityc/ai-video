from __future__ import annotations

import json
import time
from pathlib import Path

import typer

from ai_video_control.io import write_json
from ai_video_control.providers.openai_compat import OpenAICompatClient
from ai_video_control.settings import get_settings
from ai_video_control.shortform import build_video_task_content

app = typer.Typer(no_args_is_help=True)


def wait_for_video_result(
    client: OpenAICompatClient,
    task_id: str,
    poll_interval_seconds: float = 8.0,
) -> dict:
    result = client.get_video_task(task_id)
    while result.get("status") not in {"succeeded", "failed", "cancelled"}:
        time.sleep(poll_interval_seconds)
        result = client.get_video_task(task_id)
    return result


@app.command()
def run(
    prompt: str = typer.Option(..., "--prompt"),
    keyframe: Path = typer.Option(..., "--keyframe", exists=True, readable=True),
    output_dir: Path = typer.Option(..., "--output-dir"),
    count: int = typer.Option(6, "--count", min=1, max=10),
    model: str = typer.Option("doubao-seedance-1-5-pro-251215", "--model"),
    ratio: str = typer.Option("16:9", "--ratio"),
    duration: int = typer.Option(5, "--duration"),
    resolution: str = typer.Option("720p", "--resolution"),
) -> None:
    settings = get_settings()
    client = OpenAICompatClient(settings)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "prompt": prompt,
        "keyframe": str(keyframe.resolve()),
        "model": model,
        "ratio": ratio,
        "duration": duration,
        "resolution": resolution,
        "count": count,
        "variants": [],
    }

    for index in range(1, count + 1):
        task = client.submit_video_task(
            model=model,
            ratio=ratio,
            duration=duration,
            resolution=resolution,
            content=build_video_task_content(prompt, keyframe.resolve()),
        )
        task_id = task["id"]
        result = wait_for_video_result(client, task_id)
        record = {
            "index": index,
            "task_id": task_id,
            "status": result.get("status"),
        }
        if result.get("status") == "succeeded":
            video_path = output_dir / f"variant-{index:02d}-{task_id}.mp4"
            client.download_file(result["content"]["video_url"], video_path)
            meta_path = output_dir / f"variant-{index:02d}-{task_id}.json"
            write_json(meta_path, result)
            record["video_path"] = str(video_path.resolve())
            record["meta_path"] = str(meta_path.resolve())
        else:
            record["error"] = result
        manifest["variants"].append(record)
        write_json(output_dir / "manifest.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
