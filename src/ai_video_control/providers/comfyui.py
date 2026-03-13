from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from string import Template
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx

from ai_video_control.io import read_json, write_json
from ai_video_control.models import CharacterBible, RenderResult, VideoJob


class ComfyUIClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout_seconds)

    def upload_image(self, image_path: Path) -> str:
        with image_path.open("rb") as handle:
            response = self.client.post(
                f"{self.base_url}/upload/image",
                files={"image": (image_path.name, handle, "application/octet-stream")},
                data={"type": "input", "overwrite": "true"},
            )
        response.raise_for_status()
        payload = response.json()
        return str(payload["name"])

    def queue_prompt(self, prompt: Dict[str, Any], prompt_id: str) -> Dict[str, Any]:
        payload = {
            "client_id": str(uuid.uuid4()),
            "prompt": prompt,
            "prompt_id": prompt_id,
        }
        response = self.client.post(f"{self.base_url}/prompt", json=payload)
        response.raise_for_status()
        return response.json()

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        response = self.client.get(f"{self.base_url}/history/{prompt_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_history(
        self,
        prompt_id: str,
        timeout_seconds: int,
        poll_interval_seconds: float,
    ) -> Dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(poll_interval_seconds)
        raise TimeoutError(f"Timed out waiting for ComfyUI prompt {prompt_id}")

    def download_asset(self, asset: Dict[str, Any], output_path: Path) -> Path:
        query = urlencode(
            {
                "filename": asset["filename"],
                "subfolder": asset.get("subfolder", ""),
                "type": asset.get("type", "output"),
            }
        )
        response = self.client.get(f"{self.base_url}/view?{query}")
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return output_path


def _resolve_template_value(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        return Template(value).safe_substitute(context)
    return value


def _apply_workflow_overrides(
    workflow: Dict[str, Any],
    overrides: List[Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    patched = json.loads(json.dumps(workflow))
    for override in overrides:
        node = patched.get(override.node_id)
        if node is None:
            raise KeyError(f"workflow node {override.node_id} not found")
        inputs = node.setdefault("inputs", {})
        inputs[override.input_name] = _resolve_template_value(override.value, context)
    return patched


def _extract_assets(history_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    assets: List[Dict[str, Any]] = []
    outputs = history_entry.get("outputs", {})
    for node_id, node_output in outputs.items():
        for key, value in node_output.items():
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, dict) and "filename" in item:
                    asset = dict(item)
                    asset["node_id"] = node_id
                    asset["kind"] = key
                    assets.append(asset)
    return assets


def render_with_comfyui(
    job_path: Path,
    job: VideoJob,
    character: CharacterBible,
    base_url: str,
) -> RenderResult:
    assert job.comfyui is not None

    prompt = job.prompt(character)
    negative_prompt = job.combined_negative_prompt(character)
    workflow_path = Path(job.comfyui.workflow_path)
    if not workflow_path.is_absolute():
        workflow_path = (job_path.parent / workflow_path).resolve()

    workflow = read_json(workflow_path)

    input_image_name = job.input_image.source
    client = ComfyUIClient(base_url=base_url)
    if job.input_image.source_type == "local_path" and job.input_image.upload_to_comfyui:
        input_path = Path(job.input_image.source)
        if not input_path.is_absolute():
            input_path = (job_path.parent / input_path).resolve()
        input_image_name = client.upload_image(input_path)

    context = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "seed": job.seed,
        "fps": job.fps,
        "num_frames": job.num_frames,
        "width": job.width or "",
        "height": job.height or "",
        "output_prefix": job.output_prefix,
        "input_image_name": input_image_name,
        "scene_prompt": job.scene_prompt,
        "character_name": character.name,
    }

    patched_workflow = _apply_workflow_overrides(
        workflow=workflow,
        overrides=job.comfyui.workflow_overrides,
        context=context,
    )
    prompt_id = str(uuid.uuid4())
    queue_response = client.queue_prompt(patched_workflow, prompt_id)
    history_entry = client.wait_for_history(
        prompt_id=queue_response["prompt_id"],
        timeout_seconds=job.comfyui.timeout_seconds,
        poll_interval_seconds=job.comfyui.poll_interval_seconds,
    )

    output_paths: List[str] = []
    assets = _extract_assets(history_entry)
    output_dir = Path(job.comfyui.output_dir)
    if not output_dir.is_absolute():
        output_dir = (job_path.parent / output_dir).resolve()

    if job.comfyui.download_outputs:
        for asset in assets:
            local_path = output_dir / asset["filename"]
            downloaded_path = client.download_asset(asset, local_path)
            output_paths.append(str(downloaded_path))

    manifest_path = output_dir / f"{job.id}-{queue_response['prompt_id']}.json"
    write_json(
        manifest_path,
        {
            "job_id": job.id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "prompt_id": queue_response["prompt_id"],
            "queue_response": queue_response,
            "history": history_entry,
            "downloaded_outputs": output_paths,
        },
    )

    return RenderResult(
        provider="comfyui",
        prompt=prompt,
        negative_prompt=negative_prompt,
        prompt_id=queue_response["prompt_id"],
        output_paths=output_paths,
        metadata={
            "manifest_path": str(manifest_path),
            "workflow_path": str(workflow_path),
            "asset_count": len(assets),
        },
    )

