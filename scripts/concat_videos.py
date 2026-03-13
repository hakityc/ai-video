from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import typer

from ai_video_control.io import write_json

app = typer.Typer(no_args_is_help=True)


def _resolve_ffmpeg_binary() -> str:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg  # type: ignore

        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if bundled.exists():
            return str(bundled)
    except Exception:  # noqa: BLE001
        pass
    raise RuntimeError("No usable ffmpeg binary was found")


@app.command()
def run(
    manifest: Path = typer.Option(..., "--manifest", exists=True, readable=True),
    output: Path = typer.Option(..., "--output"),
) -> None:
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    items = manifest_data.get("variants")
    if items is None:
        items = manifest_data.get("shots", [])
    video_paths = [
        Path(item["video_path"]).resolve()
        for item in items
        if item.get("status") == "succeeded"
    ]
    if not video_paths:
        raise typer.BadParameter("No succeeded videos found in manifest.")

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = _resolve_ffmpeg_binary()

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        concat_list = Path(handle.name)
        for video_path in video_paths:
            handle.write(f"file '{video_path.as_posix()}'\n")

    try:
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(output),
            ],
            check=True,
        )
    finally:
        concat_list.unlink(missing_ok=True)

    summary = {
        "manifest": str(manifest.resolve()),
        "output": str(output),
        "clips": [str(path) for path in video_paths],
    }
    write_json(output.with_suffix(".json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
