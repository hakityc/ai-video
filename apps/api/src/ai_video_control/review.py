from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List

try:
    import imageio.v3 as iio
except ImportError:  # pragma: no cover - optional dependency in lean envs
    iio = None
from PIL import Image

from ai_video_control.providers.openai_compat import OpenAICompatClient
from ai_video_control.settings import Settings


def _to_data_url(image_path: Path, max_size: int = 768) -> str:
    image = Image.open(image_path).convert("RGB")
    image.thumbnail((max_size, max_size))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


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


def _probe_video_duration_seconds(video_path: Path) -> float:
    ffmpeg_bin = _resolve_ffmpeg_binary()
    result = subprocess.run(
        [ffmpeg_bin, "-hide_banner", "-i", str(video_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"Duration:\s+(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    if not match:
        raise RuntimeError(f"Could not determine video duration for {video_path}")
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def _extract_frame_at_ratio(
    video_path: Path,
    output_path: Path,
    frame_ratio: float,
) -> Path:
    ffmpeg_bin = _resolve_ffmpeg_binary()
    duration_seconds = _probe_video_duration_seconds(video_path)
    target_seconds = max(0.0, min(duration_seconds - 0.05, duration_seconds * frame_ratio))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{target_seconds:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ],
        check=True,
    )
    if not output_path.exists():
        raise RuntimeError(f"Frame extraction failed for {video_path} -> {output_path}")
    return output_path


def extract_sample_frames(
    video_path: Path,
    output_dir: Path,
    frame_points: List[float] | None = None,
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if frame_points is None:
        frame_points = [0.2, 0.5, 0.8]

    frame_paths: List[Path] = []
    seen_ratios = set()
    for idx, point in enumerate(frame_points, start=1):
        ratio = round(max(0.0, min(0.99, point)), 3)
        if ratio in seen_ratios:
            continue
        seen_ratios.add(ratio)
        path = output_dir / f"frame-{idx:02d}.jpg"
        frame_paths.append(_extract_frame_at_ratio(video_path, path, ratio))
    return frame_paths


def extract_single_frame(
    video_path: Path,
    output_path: Path,
    frame_point: float = 0.8,
) -> Path:
    return _extract_frame_at_ratio(video_path, output_path, frame_point)


def _extract_json_block(content: str) -> Dict[str, Any]:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not parse JSON from review response")
    return json.loads(content[start : end + 1])


def _chat_json(
    client: OpenAICompatClient,
    content: List[Dict[str, Any]],
    max_tokens: int = 900,
    retries: int = 3,
    retry_delay_seconds: float = 2.0,
) -> Dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            payload = {
                "model": client.settings.openai_model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0,
                "max_tokens": max_tokens,
            }
            response = client.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = _extract_json_block(raw_content)
            parsed["raw_response"] = raw_content
            return parsed
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == retries:
                break
            time.sleep(retry_delay_seconds)
    assert last_error is not None
    raise last_error


def review_frame_with_vlm(
    client: OpenAICompatClient,
    anchor_image: Path,
    frame_image: Path,
    context: str,
) -> Dict[str, Any]:
    anchor_data_url = _to_data_url(anchor_image)
    frame_data_url = _to_data_url(frame_image)
    prompt = (
        "You are evaluating continuity between a reference character image and a video frame. "
        "Return JSON only with keys: same_character (boolean), identity_score (0 to 1), "
        "outfit_score (0 to 1), atmosphere_score (0 to 1), issues (array of short strings), "
        "summary (short string). "
        "Focus on face identity, hair, outfit, and scene continuity. "
        f"Scene context: {context}"
    )
    return _chat_json(
        client,
        [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": anchor_data_url}},
            {"type": "image_url", "image_url": {"url": frame_data_url}},
        ],
        max_tokens=600,
    )


def review_episode(
    episode_dir: Path,
    settings: Settings,
    context: str = "",
) -> Dict[str, Any]:
    manifest_path = episode_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"剧集目录中未找到 manifest.json: {episode_dir}，请先确保该剧集已成功生成视频。")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    anchor_image = Path(manifest["anchor_local"])
    client = OpenAICompatClient(settings)

    reviews: List[Dict[str, Any]] = []
    for shot in manifest["shots"]:
        shot_dir = Path(shot["video_path"]).parent
        frames_dir = shot_dir / "frames"
        frame_paths = extract_sample_frames(Path(shot["video_path"]), frames_dir)
        frame_reviews = []
        for frame_path in frame_paths:
            review = review_frame_with_vlm(
                client=client,
                anchor_image=anchor_image,
                frame_image=frame_path,
                context=context or shot["prompt"],
            )
            review["frame_path"] = str(frame_path.resolve())
            frame_reviews.append(review)

        identity_scores = [float(item["identity_score"]) for item in frame_reviews]
        outfit_scores = [float(item["outfit_score"]) for item in frame_reviews]
        atmosphere_scores = [float(item["atmosphere_score"]) for item in frame_reviews]
        shot_review = {
            "shot_id": shot["shot_id"],
            "video_path": shot["video_path"],
            "average_identity_score": round(sum(identity_scores) / len(identity_scores), 3),
            "average_outfit_score": round(sum(outfit_scores) / len(outfit_scores), 3),
            "average_atmosphere_score": round(sum(atmosphere_scores) / len(atmosphere_scores), 3),
            "frames": frame_reviews,
        }
        reviews.append(shot_review)

    overall_identity = round(
        sum(item["average_identity_score"] for item in reviews) / len(reviews), 3
    )
    overall_outfit = round(
        sum(item["average_outfit_score"] for item in reviews) / len(reviews), 3
    )
    overall_atmosphere = round(
        sum(item["average_atmosphere_score"] for item in reviews) / len(reviews), 3
    )
    return {
        "episode": manifest["episode"],
        "anchor_image": str(anchor_image.resolve()),
        "overall_identity_score": overall_identity,
        "overall_outfit_score": overall_outfit,
        "overall_atmosphere_score": overall_atmosphere,
        "shots": reviews,
    }


def review_keyframe_set(
    episode_dir: Path,
    settings: Settings,
    context: str = "",
) -> Dict[str, Any]:
    manifest_path = episode_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"剧集目录中未找到 manifest.json: {episode_dir}，请先确保该剧集已成功生成关键帧。")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    anchor_image = Path(manifest["anchor_local"])
    client = OpenAICompatClient(settings)

    shot_entries = manifest["shots"]
    if not shot_entries:
        raise ValueError("No shots found in manifest")

    content: List[Dict[str, Any]] = []
    content.append(
        {
            "type": "text",
            "text": (
                "You are evaluating whether a set of AI-generated keyframes is stable enough "
                "to proceed to video generation. "
                "Assess character identity consistency, wardrobe/accessory consistency, "
                "scene layout consistency, prop continuity, and camera/framing continuity. "
                "Return JSON only with keys: "
                "pass_gate (boolean), overall_score (0 to 1), identity_score (0 to 1), "
                "wardrobe_score (0 to 1), scene_score (0 to 1), prop_score (0 to 1), "
                "camera_score (0 to 1), issues (array of short strings), strengths (array of short strings), "
                "shot_notes (array of objects with keys shot_id, score, issues), summary (short string). "
                "Be strict: fail the gate if shared scene layout, corpse state logic, lighting rig, "
                "or protagonist accessories drift in a way that would break a short-form sequence. "
                f"Sequence context: {context or manifest.get('review_context', '')}"
            ),
        }
    )
    content.append(
        {
            "type": "text",
            "text": "Reference anchor image for protagonist identity and base styling.",
        }
    )
    content.append(
        {"type": "image_url", "image_url": {"url": _to_data_url(anchor_image)}},
    )

    for shot in shot_entries:
        keyframe_path = Path(shot["keyframe_path"])
        content.append(
            {
                "type": "text",
                "text": f"Keyframe for {shot['shot_id']}.",
            }
        )
        content.append(
            {"type": "image_url", "image_url": {"url": _to_data_url(keyframe_path)}},
        )

    parsed = _chat_json(client, content, max_tokens=1200)
    parsed["episode"] = manifest["episode"]
    parsed["anchor_image"] = str(anchor_image.resolve())
    parsed["keyframes"] = [
        {
            "shot_id": shot["shot_id"],
            "keyframe_path": shot["keyframe_path"],
        }
        for shot in shot_entries
    ]
    return parsed


def review_master_scene_image(
    client: OpenAICompatClient,
    anchor_image: Path,
    candidate_image: Path,
    context: str,
) -> Dict[str, Any]:
    content = [
        {
            "type": "text",
            "text": (
                "You are evaluating whether a generated master scene frame is good enough to serve as "
                "the base visual anchor for a short AI video sequence. "
                "Return JSON only with keys: pass_gate (boolean), overall_score (0 to 1), "
                "clarity_score (0 to 1), identity_score (0 to 1), scene_score (0 to 1), "
                "prop_score (0 to 1), issues (array of short strings), strengths (array of short strings), "
                "summary (short string). Be strict. Fail if the scene layout, lighting rig, fixed props, "
                "or protagonist identity are not stable enough for reuse. "
                f"Context: {context}"
            ),
        },
        {"type": "text", "text": "Reference anchor for protagonist identity."},
        {"type": "image_url", "image_url": {"url": _to_data_url(anchor_image)}},
        {"type": "text", "text": "Candidate master scene frame."},
        {"type": "image_url", "image_url": {"url": _to_data_url(candidate_image)}},
    ]
    return _chat_json(client, content, max_tokens=900)


def review_shot_delta_candidate(
    client: OpenAICompatClient,
    anchor_image: Path,
    master_scene_image: Path,
    candidate_image: Path,
    allowed_changes: List[str],
    forbidden_changes: List[str],
    dramatic_purpose: str,
    emotional_state: str,
    must_show: List[str],
    must_not_hide: List[str],
    forbidden_compositions: List[str],
    context: str,
) -> Dict[str, Any]:
    content = [
        {
            "type": "text",
            "text": (
                "You are evaluating whether a shot-delta keyframe is valid relative to an approved master scene. "
                "Return JSON only with keys: pass_gate (boolean), overall_score (0 to 1), "
                "identity_score (0 to 1), scene_score (0 to 1), prop_score (0 to 1), camera_score (0 to 1), beat_score (0 to 1), "
                "issues (array of short strings), strengths (array of short strings), summary (short string). "
                "Fail if anything changes outside the allowed delta, if the intended dramatic beat is not visually legible, "
                "if required evidence is missing, or if forbidden compositions appear. "
                f"Allowed changes: {', '.join(allowed_changes) or 'none'}. "
                f"Forbidden changes: {', '.join(forbidden_changes) or 'none'}. "
                f"Dramatic purpose: {dramatic_purpose or 'none'}. "
                f"Emotional state: {emotional_state or 'none'}. "
                f"Must show: {', '.join(must_show) or 'none'}. "
                f"Must not hide: {', '.join(must_not_hide) or 'none'}. "
                f"Forbidden compositions: {', '.join(forbidden_compositions) or 'none'}. "
                f"Context: {context}"
            ),
        },
        {"type": "text", "text": "Reference anchor for protagonist identity."},
        {"type": "image_url", "image_url": {"url": _to_data_url(anchor_image)}},
        {"type": "text", "text": "Approved master scene frame."},
        {"type": "image_url", "image_url": {"url": _to_data_url(master_scene_image)}},
        {"type": "text", "text": "Candidate shot-delta keyframe."},
        {"type": "image_url", "image_url": {"url": _to_data_url(candidate_image)}},
    ]
    return _chat_json(client, content, max_tokens=1000)


def review_final_shot_frame(
    client: OpenAICompatClient,
    anchor_image: Path,
    approved_keyframe_image: Path,
    candidate_image: Path,
    shot_id: str,
    dramatic_purpose: str,
    emotional_state: str,
    must_show: List[str],
    must_not_hide: List[str],
    forbidden_compositions: List[str],
    context: str,
) -> Dict[str, Any]:
    content = [
        {
            "type": "text",
            "text": (
                "You are evaluating whether a final rendered video frame still preserves the approved shot design. "
                "Return JSON only with keys: pass_gate (boolean), overall_score (0 to 1), "
                "identity_score (0 to 1), scene_score (0 to 1), prop_score (0 to 1), camera_score (0 to 1), beat_score (0 to 1), "
                "issues (array of short strings), strengths (array of short strings), summary (short string). "
                "Fail if the final frame drifts away from the approved shot keyframe, if the intended beat is unclear, "
                "if required evidence is not visible, or if forbidden compositions appear. "
                f"Shot: {shot_id}. "
                f"Dramatic purpose: {dramatic_purpose or 'none'}. "
                f"Emotional state: {emotional_state or 'none'}. "
                f"Must show: {', '.join(must_show) or 'none'}. "
                f"Must not hide: {', '.join(must_not_hide) or 'none'}. "
                f"Forbidden compositions: {', '.join(forbidden_compositions) or 'none'}. "
                f"Context: {context}"
            ),
        },
        {"type": "text", "text": "Reference anchor for protagonist identity."},
        {"type": "image_url", "image_url": {"url": _to_data_url(anchor_image)}},
        {"type": "text", "text": "Approved shot keyframe."},
        {"type": "image_url", "image_url": {"url": _to_data_url(approved_keyframe_image)}},
        {"type": "text", "text": "Frame from the final rendered shot."},
        {"type": "image_url", "image_url": {"url": _to_data_url(candidate_image)}},
    ]
    return _chat_json(client, content, max_tokens=1000)


def extract_tail_frames(
    video_path: Path,
    output_dir: Path,
    tail_ratio: float = 0.2,
    max_frames: int = 6,
) -> List[Path]:
    if iio is None:
        raise RuntimeError("imageio is required for frame extraction. Install project dependencies before QA review.")
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = list(iio.imiter(video_path))
    if not frames:
        raise ValueError(f"No frames decoded from {video_path}")

    total = len(frames)
    start_index = max(0, int(total * (1 - tail_ratio)))
    indexes = list(range(start_index, total))
    if len(indexes) > max_frames:
        step = max(1, len(indexes) // max_frames)
        indexes = indexes[::step][:max_frames]

    frame_paths: List[Path] = []
    for idx, frame_index in enumerate(indexes, start=1):
        path = output_dir / f"tail-{idx:02d}.jpg"
        iio.imwrite(path, frames[frame_index])
        frame_paths.append(path)
    return frame_paths


def review_bridge_frame_candidate(
    client: OpenAICompatClient,
    anchor_image: Path,
    frame_image: Path,
    context: str,
) -> Dict[str, Any]:
    content = [
        {
            "type": "text",
            "text": (
                "You are evaluating whether a video frame is a strong bridge-frame candidate for the next shot. "
                "Return JSON only with keys: usable (boolean), overall_score (0 to 1), "
                "face_visibility (0 to 1), pose_stability (0 to 1), prop_completeness (0 to 1), "
                "motion_blur_score (0 to 1), continuity_usefulness (0 to 1), issues (array of short strings), "
                "summary (short string). Prefer frames with clear face visibility, stable pose, low motion blur, "
                "and useful continuity for the next shot. "
                f"Context: {context}"
            ),
        },
        {"type": "text", "text": "Reference anchor for protagonist identity."},
        {"type": "image_url", "image_url": {"url": _to_data_url(anchor_image)}},
        {"type": "text", "text": "Bridge-frame candidate."},
        {"type": "image_url", "image_url": {"url": _to_data_url(frame_image)}},
    ]
    return _chat_json(client, content, max_tokens=900)


def choose_best_review(
    reviews: List[Dict[str, Any]],
    pass_key: str,
    score_key: str,
) -> Dict[str, Any] | None:
    passing = [item for item in reviews if item.get(pass_key)]
    pool = passing or reviews
    if not pool:
        return None
    return max(pool, key=lambda item: float(item.get(score_key, 0.0)))


def select_bridge_frame(
    video_path: Path,
    anchor_image: Path,
    settings: Settings,
    output_dir: Path,
    context: str = "",
    tail_ratio: float = 0.2,
    max_candidates: int = 6,
) -> Dict[str, Any]:
    frame_paths = extract_tail_frames(
        video_path=video_path,
        output_dir=output_dir,
        tail_ratio=tail_ratio,
        max_frames=max_candidates,
    )
    if not frame_paths:
        raise ValueError("No bridge-frame candidates were extracted")
    best_path = frame_paths[-1].resolve()
    best = {
        "usable": True,
        "overall_score": 1.0,
        "face_visibility": 1.0,
        "pose_stability": 1.0,
        "prop_completeness": 1.0,
        "motion_blur_score": 1.0,
        "continuity_usefulness": 1.0,
        "issues": [],
        "summary": "Selected the latest extracted tail frame as the bridge frame using the fast heuristic mode.",
        "frame_path": str(best_path),
    }
    return {
        "video_path": str(video_path.resolve()),
        "selected_frame_path": str(best_path),
        "bridge_frame_score": 1.0,
        "selected_review": best,
        "candidates": [best],
    }
