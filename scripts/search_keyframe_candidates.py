from __future__ import annotations

import json
from pathlib import Path

import typer

from ai_video_control.shortform import load_shortform_bundle, search_keyframe_candidates
from ai_video_control.settings import get_settings

app = typer.Typer(no_args_is_help=True)


@app.command()
def run(
    spec: Path = typer.Argument(..., exists=True, readable=True),
    output_root: Path = typer.Option(Path("artifacts/video/seedance")),
    image_model: str = typer.Option("", "--image-model"),
    video_model: str = typer.Option(
        "doubao-seedance-1-5-pro-251215",
        "--video-model",
    ),
    ratio: str = typer.Option("16:9", "--ratio"),
    duration: int = typer.Option(5, "--duration"),
    resolution: str = typer.Option("720p", "--resolution"),
) -> None:
    settings = get_settings()
    bundle = load_shortform_bundle(spec)
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
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
