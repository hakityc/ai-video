from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

from ai_video_control.io import read_yaml, write_json
from ai_video_control.models import (
    CharacterBible,
    ContinuityLedger,
    ContinuityLedgerShot,
    PropPack,
    ScenePack,
    ShotCard,
    ShortformEpisodeSpec,
    ShotDeltaSpec,
    ShotTemplate,
)
from ai_video_control.providers.openai_compat import OpenAICompatClient
from ai_video_control.review import (
    choose_best_review,
    extract_single_frame,
    extract_sample_frames,
    review_final_shot_frame,
    review_master_scene_image,
    review_shot_delta_candidate,
    select_bridge_frame,
)
from ai_video_control.settings import Settings


@dataclass
class ShortformBundle:
    spec_path: Path
    spec: ShortformEpisodeSpec
    character: CharacterBible
    scene_pack: ScenePack
    prop_pack: PropPack
    shot_template: ShotTemplate
    anchor_image: Path
    initial_bridge_frame: Path | None


MASTER_SCENE_EARLY_STOP_SCORE = 0.8
SHOT_DELTA_EARLY_STOP_SCORE = 0.8
VIDEO_TASK_TIMEOUT_SECONDS = 480.0


def load_shortform_bundle(spec_path: Path) -> ShortformBundle:
    spec_path = spec_path.resolve()
    spec = ShortformEpisodeSpec.model_validate(read_yaml(spec_path))
    character_path = spec.resolve_character_bible_path(spec_path)
    character = CharacterBible.model_validate(read_yaml(character_path))
    scene_pack = ScenePack.model_validate(read_yaml(spec.resolve_scene_pack_path(spec_path)))
    prop_pack = PropPack.model_validate(read_yaml(spec.resolve_prop_pack_path(spec_path)))
    shot_template = ShotTemplate.model_validate(
        read_yaml(spec.resolve_shot_template_path(spec_path))
    )
    anchor_image = spec.resolve_anchor_image_path(spec_path)
    initial_bridge_frame = spec.resolve_initial_bridge_frame_path(spec_path)
    return ShortformBundle(
        spec_path=spec_path,
        spec=spec,
        character=character,
        scene_pack=scene_pack,
        prop_pack=prop_pack,
        shot_template=shot_template,
        anchor_image=anchor_image,
        initial_bridge_frame=initial_bridge_frame,
    )


def _unique_parts(parts: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for part in parts:
        item = part.strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _core_identity_parts(bundle: ShortformBundle) -> List[str]:
    anchors = bundle.character.identity_anchors
    parts: List[str] = []
    parts.extend(anchors.face[:4])
    parts.extend(anchors.hair[:3])
    parts.extend(anchors.outfit[:3])
    return _unique_parts(parts)


def _episode_dir_name(episode: str) -> str:
    if episode.startswith("episode-"):
        return episode
    if episode.startswith("ep") and episode[2:].isdigit():
        return f"episode-{episode[2:]}"
    return episode


def _shot_lookup(bundle: ShortformBundle, shot_id: str) -> ShotDeltaSpec:
    for shot in bundle.spec.shots:
        if shot.shot_id == shot_id:
            return shot
    raise KeyError(f"Unknown shot_id: {shot_id}")


def _shot_card_lookup(bundle: ShortformBundle, shot_id: str) -> ShotCard:
    shot = _shot_lookup(bundle, shot_id)
    explicit = shot.shot_card.model_copy(deep=True)
    if not explicit.beat:
        explicit.beat = shot.dramatic_purpose or shot.video_prompt_hint or shot.emotional_state
    if not explicit.must_show:
        explicit.must_show = list(shot.must_show)
    else:
        explicit.must_show = _unique_parts(explicit.must_show + shot.must_show)
    shot_camera_optics = (
        shot.dimensions.camera_optics.text.strip()
        if shot.dimensions.camera_optics.mode == "open_for_text"
        else ""
    )
    template_camera_optics = (
        bundle.shot_template.dimensions.camera_optics.text.strip()
        if bundle.shot_template.dimensions.camera_optics.mode == "open_for_text"
        else ""
    )
    if not explicit.lens_feel:
        explicit.lens_feel = shot_camera_optics or template_camera_optics
    if not explicit.bridge_frame_goal:
        explicit.bridge_frame_goal = shot.video_prompt_hint
    if not explicit.continuity_notes:
        explicit.continuity_notes = _unique_parts(
            bundle.shot_template.blocking_rules
            + shot.forbidden_changes
            + shot.forbidden_compositions
        )
    if not explicit.edit_seam:
        explicit.edit_seam = "End on a readable pose and prop state for the next cut."
    return explicit


def _normalize_phrase_list(values: List[str]) -> List[str]:
    items = []
    for value in values:
        text = value.strip()
        if len(text) < 10:
            continue
        if len(text.split()) < 2:
            continue
        items.append(text.lower())
    return items


def build_shot_card(bundle: ShortformBundle, shot_id: str) -> ShotCard:
    return _shot_card_lookup(bundle, shot_id)


def build_continuity_ledger(bundle: ShortformBundle) -> ContinuityLedger:
    shots: List[ContinuityLedgerShot] = []
    for shot in bundle.spec.shots:
        shot_card = build_shot_card(bundle, shot.shot_id)
        issues = validate_prompt_pollution(bundle, stage="shot_delta", shot_id=shot.shot_id)
        locked_context = _unique_parts(
            bundle.scene_pack.fixed_elements
            + bundle.prop_pack.fixed_props
            + bundle.shot_template.framing
            + bundle.shot_template.blocking_rules
        )
        notes = [shot.video_prompt_hint] if shot.video_prompt_hint else []
        shots.append(
            ContinuityLedgerShot(
                shot_id=shot.shot_id,
                shot_card=shot_card,
                dramatic_purpose=shot.dramatic_purpose,
                emotional_state=shot.emotional_state,
                locked_context=locked_context,
                allowed_changes=list(shot.allowed_changes),
                forbidden_changes=_unique_parts(
                    shot.forbidden_changes
                    + bundle.shot_template.forbidden_changes
                    + bundle.prop_pack.forbidden_drift
                ),
                must_show=list(shot.must_show),
                must_not_hide=list(shot.must_not_hide),
                prompt_pollution_issues=issues,
                notes=notes,
            )
        )
    return ContinuityLedger(
        episode=bundle.spec.episode,
        character=bundle.character.slug,
        scene_pack=bundle.scene_pack.id,
        prop_pack=bundle.prop_pack.id,
        shot_template=bundle.shot_template.id,
        review_context=bundle.spec.review_context,
        anchor_image=str(bundle.anchor_image.resolve()),
        initial_bridge_frame=(
            str(bundle.initial_bridge_frame.resolve())
            if bundle.initial_bridge_frame is not None
            else None
        ),
        shots=shots,
    )


def _ledger_entry_lookup(ledger: ContinuityLedger, shot_id: str) -> ContinuityLedgerShot:
    for shot in ledger.shots:
        if shot.shot_id == shot_id:
            return shot
    raise KeyError(f"Unknown shot_id: {shot_id}")


def _write_ledger(path: Path, ledger: ContinuityLedger) -> None:
    write_json(path, ledger.model_dump(mode="json"))


def build_master_scene_prompt(bundle: ShortformBundle) -> str:
    parts = [
        bundle.character.name,
        *_core_identity_parts(bundle),
        *bundle.scene_pack.dimensions.texts_for_modes("locked_by_pack"),
        *bundle.shot_template.dimensions.texts_for_modes("locked_by_pack"),
        *bundle.scene_pack.fixed_elements,
        *bundle.prop_pack.fixed_props,
        *bundle.shot_template.framing,
        *bundle.shot_template.blocking_rules,
        *bundle.shot_template.prompt_suffix,
        *bundle.spec.master_scene.dimensions.texts_for_modes(
            "locked_by_pack", "open_for_text"
        ),
    ]
    return ", ".join(_unique_parts(parts))


def build_shot_delta_prompt(bundle: ShortformBundle, shot_id: str) -> str:
    shot = _shot_lookup(bundle, shot_id)
    parts = [
        "same protagonist, same wardrobe, same room layout, same lighting rig as approved master scene",
        "change only the allowed delta for this shot",
        shot.dramatic_purpose,
        shot.emotional_state,
        *shot.dimensions.texts_for_modes("open_for_text"),
        *shot.allowed_changes,
        *[f"viewer must clearly see {item}" for item in shot.must_show],
        *[f"do not hide {item}" for item in shot.must_not_hide],
        *[f"avoid {item}" for item in shot.forbidden_compositions],
    ]
    if bundle.shot_template.dimensions.camera_optics.mode == "open_for_text":
        parts.extend(bundle.shot_template.dimensions.texts_for_modes("open_for_text"))
    return ", ".join(_unique_parts(parts))


def build_video_prompt(bundle: ShortformBundle, shot_id: str) -> str:
    shot = _shot_lookup(bundle, shot_id)
    parts = [
        "single-scene micro-story continuation",
        "same protagonist and same room as the provided references",
        "preserve the same camera framing and actor floor marks from the provided references",
        "do not introduce new props or room changes beyond the allowed delta",
        shot.dramatic_purpose,
        shot.emotional_state,
        *shot.dimensions.texts_for_modes("open_for_text"),
        *shot.allowed_changes,
        *[f"must clearly show {item}" for item in shot.must_show],
        *[f"must not hide {item}" for item in shot.must_not_hide],
        *[f"forbidden composition: {item}" for item in shot.forbidden_compositions],
        shot.video_prompt_hint,
    ]
    return ", ".join(_unique_parts(parts))


def validate_prompt_pollution(
    bundle: ShortformBundle,
    stage: str,
    shot_id: str | None = None,
) -> List[str]:
    issues: List[str] = []
    if stage == "master_scene":
        open_count = len(bundle.spec.master_scene.dimensions.open_dimension_names())
        if open_count > 3:
            issues.append("master scene opens too many dimensions at once")
        return issues

    if shot_id is None:
        raise ValueError("shot_id is required for shot_delta validation")

    prompt = build_shot_delta_prompt(bundle, shot_id).lower()
    shot = _shot_lookup(bundle, shot_id)

    for phrase in _normalize_phrase_list(bundle.character.identity_anchors.flattened()):
        if phrase in prompt:
            issues.append(f"shot delta restates locked identity detail: {phrase}")
    for phrase in _normalize_phrase_list(bundle.scene_pack.fixed_elements):
        if phrase in prompt:
            issues.append(f"shot delta restates locked scene detail: {phrase}")
    for phrase in _normalize_phrase_list(bundle.prop_pack.fixed_props):
        if phrase in prompt:
            issues.append(f"shot delta restates locked prop detail: {phrase}")
    for phrase in bundle.prop_pack.forbidden_drift + bundle.shot_template.forbidden_changes:
        if phrase.strip() and phrase.lower() in prompt:
            issues.append(f"shot delta includes forbidden drift phrase: {phrase}")

    open_count = len(shot.dimensions.open_dimension_names())
    if open_count > 2:
        issues.append("shot delta opens too many dimensions at once")

    forbidden_lower = [item.strip().lower() for item in shot.forbidden_changes]
    open_text = " ".join(shot.dimensions.texts_for_modes("open_for_text")).lower()
    if "new props" in forbidden_lower:
        risky_terms = ["report", "file", "clipboard", "recorder", "flashlight", "glove", "gloves"]
        for term in risky_terms:
            if term in open_text:
                issues.append(
                    "shot delta text introduces a likely new prop or accessory while "
                    f"'new props' is forbidden: {term}"
                )
    return issues


def _candidate_dir(
    bundle: ShortformBundle,
    output_root: Path,
    suffix: str = "",
) -> Path:
    base = output_root.resolve() / bundle.character.slug
    episode_name = bundle.spec.episode + suffix
    return base / _episode_dir_name(episode_name.replace(f"{bundle.character.slug}-", ""))


def _generate_image_candidate(
    client: OpenAICompatClient,
    prompt: str,
    output_path: Path,
    image_model: str | None = None,
) -> Dict[str, Any]:
    metadata = client.generate_image_with_meta(
        prompt=prompt,
        output_path=output_path,
        model=image_model or None,
        size="1024x1024",
    )
    metadata["prompt"] = prompt
    return metadata


def _to_data_url(image_path: Path, max_size: int = 1024) -> str:
    image = Image.open(image_path).convert("RGB")
    image.thumbnail((max_size, max_size))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def build_video_task_content(
    prompt: str,
    first_frame_path: Path,
    last_frame_path: Path | None = None,
) -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    content.append(
        {
            "type": "image_url",
            "role": "first_frame",
            "image_url": {"url": _to_data_url(first_frame_path)},
        }
    )
    if last_frame_path is not None:
        content.append(
            {
                "type": "image_url",
                "role": "last_frame",
                "image_url": {"url": _to_data_url(last_frame_path)},
            }
        )
    return content


def _selected_candidate(
    candidates: List[Dict[str, Any]],
    pass_key: str = "pass_gate",
    score_key: str = "overall_score",
) -> Dict[str, Any] | None:
    if not candidates:
        return None
    passing = [item for item in candidates if item.get(pass_key)]
    pool = passing or candidates
    return max(pool, key=lambda item: float(item.get(score_key, 0.0)))


def _load_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _should_stop_early(candidate: Dict[str, Any] | None, threshold: float) -> bool:
    if not candidate or not candidate.get("pass_gate"):
        return False
    return float(candidate.get("overall_score", 0.0)) >= threshold


def _upsert_manifest_shot(manifest: Dict[str, Any], shot_entry: Dict[str, Any]) -> None:
    shots = manifest.setdefault("shots", [])
    for index, existing in enumerate(shots):
        if existing.get("shot_id") == shot_entry.get("shot_id"):
            shots[index] = shot_entry
            return
    shots.append(shot_entry)


def _is_transient_candidate_error(candidate_payload: Dict[str, Any] | None) -> bool:
    if not candidate_payload:
        return False
    selected = candidate_payload.get("selected_frame") or {}
    error_text = str(selected.get("error") or candidate_payload.get("error") or "").lower()
    if not error_text:
        return False
    transient_markers = ["ssl", "eof", "timeout", "connection reset", "transport"]
    return any(marker in error_text for marker in transient_markers)


def _wait_for_video_result(
    client: OpenAICompatClient,
    task_id: str,
    poll_interval_seconds: float = 8.0,
    timeout_seconds: float = VIDEO_TASK_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    started_at = time.monotonic()
    result = client.get_video_task(task_id)
    while result.get("status") not in {"succeeded", "failed", "cancelled"}:
        if time.monotonic() - started_at > timeout_seconds:
            raise TimeoutError(
                "Timed out waiting for video task "
                f"{task_id} after {int(timeout_seconds)}s with last status "
                f"{result.get('status', 'unknown')}"
            )
        time.sleep(poll_interval_seconds)
        result = client.get_video_task(task_id)
    if result.get("status") != "succeeded":
        raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def _review_shot_candidate_frames(
    client: OpenAICompatClient,
    bundle: ShortformBundle,
    master_scene_image: Path,
    candidate_video_path: Path,
    output_dir: Path,
    shot: ShotDeltaSpec,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    frame_reviews: List[Dict[str, Any]] = []
    primary_frame_path = extract_single_frame(
        candidate_video_path,
        output_dir / "frame-01.jpg",
        frame_point=0.8,
    )
    review = review_shot_delta_candidate(
        client=client,
        anchor_image=bundle.anchor_image,
        master_scene_image=master_scene_image,
        candidate_image=primary_frame_path,
        allowed_changes=shot.allowed_changes or bundle.shot_template.allowed_changes,
        forbidden_changes=shot.forbidden_changes
        + bundle.shot_template.forbidden_changes
        + bundle.prop_pack.forbidden_drift,
        dramatic_purpose=shot.dramatic_purpose,
        emotional_state=shot.emotional_state,
        must_show=shot.must_show,
        must_not_hide=shot.must_not_hide,
        forbidden_compositions=shot.forbidden_compositions,
        context=bundle.spec.review_context,
    )
    review["frame_path"] = str(primary_frame_path.resolve())
    frame_reviews.append(review)

    best_primary = choose_best_review(
        frame_reviews,
        pass_key="pass_gate",
        score_key="overall_score",
    )
    if best_primary is not None and _should_stop_early(best_primary, SHOT_DELTA_EARLY_STOP_SCORE):
        return best_primary, frame_reviews

    fallback_frame_paths = extract_sample_frames(
        candidate_video_path,
        output_dir,
        frame_points=[0.2, 0.5],
    )
    seen_paths = {item["frame_path"] for item in frame_reviews}
    for frame_path in fallback_frame_paths:
        resolved_frame = str(frame_path.resolve())
        if resolved_frame in seen_paths:
            continue
        review = review_shot_delta_candidate(
            client=client,
            anchor_image=bundle.anchor_image,
            master_scene_image=master_scene_image,
            candidate_image=frame_path,
            allowed_changes=shot.allowed_changes or bundle.shot_template.allowed_changes,
            forbidden_changes=shot.forbidden_changes
            + bundle.shot_template.forbidden_changes
            + bundle.prop_pack.forbidden_drift,
            dramatic_purpose=shot.dramatic_purpose,
            emotional_state=shot.emotional_state,
            must_show=shot.must_show,
            must_not_hide=shot.must_not_hide,
            forbidden_compositions=shot.forbidden_compositions,
            context=bundle.spec.review_context,
        )
        review["frame_path"] = resolved_frame
        frame_reviews.append(review)

    best_frame = choose_best_review(
        frame_reviews,
        pass_key="pass_gate",
        score_key="overall_score",
    )
    if best_frame is None:
        raise ValueError(f"No candidate frames were reviewed for {candidate_video_path}")
    return best_frame, frame_reviews


def search_keyframe_candidates(
    bundle: ShortformBundle,
    settings: Settings,
    output_root: Path,
    image_model: str | None = None,
    video_model: str = "doubao-seedance-1-5-pro-251215",
    ratio: str = "16:9",
    duration: int = 5,
    resolution: str = "720p",
) -> Dict[str, Any]:
    client = OpenAICompatClient(settings)
    episode_dir = _candidate_dir(bundle, output_root)
    episode_dir.mkdir(parents=True, exist_ok=True)
    search_summary_path = episode_dir / "search_summary.json"
    ledger_path = episode_dir / "continuity_ledger.json"
    ledger = build_continuity_ledger(bundle)
    ledger.search_summary_path = str(search_summary_path.resolve())

    summary: Dict[str, Any] = {
        "episode": bundle.spec.episode,
        "character": bundle.character.slug,
        "status": "in_progress",
        "search_config": {
            "image_model": image_model or settings.openai_image_model,
            "video_model": video_model,
            "ratio": ratio,
            "duration": duration,
            "resolution": resolution,
        },
        "master_scene": {},
        "shots": [],
    }

    master_prompt = build_master_scene_prompt(bundle)
    master_dir = episode_dir / "master-scene"
    master_dir.mkdir(parents=True, exist_ok=True)
    master_candidates: List[Dict[str, Any]] = []
    summary["master_scene"] = {
        "prompt": master_prompt,
        "candidates": master_candidates,
        "selected": None,
    }
    write_json(search_summary_path, summary)
    _write_ledger(ledger_path, ledger)
    if bundle.initial_bridge_frame is not None:
        bridge_candidate = {
            "pass_gate": True,
            "overall_score": 1.0,
            "clarity_score": 1.0,
            "identity_score": 1.0,
            "scene_score": 1.0,
            "prop_score": 1.0,
            "issues": [],
            "strengths": [
                "Continuation episode reuses the approved previous-shot bridge frame as its master scene"
            ],
            "summary": "Initial bridge frame reused as continuation master scene anchor.",
            "candidate_path": str(bundle.initial_bridge_frame.resolve()),
            "metadata_path": None,
            "reference_mode": "initial_bridge_frame",
        }
        master_candidates.append(bridge_candidate)
        summary["master_scene"]["selected"] = bridge_candidate
        ledger.master_scene_path = bridge_candidate["candidate_path"]
        write_json(search_summary_path, summary)
        _write_ledger(ledger_path, ledger)
    else:
        for index in range(1, bundle.spec.master_scene_candidates + 1):
            candidate_path = master_dir / f"candidate-{index:02d}.jpeg"
            candidate_json_path = master_dir / f"candidate-{index:02d}.json"
            existing_payload = _load_json(candidate_json_path)
            if existing_payload and existing_payload.get("review"):
                review = existing_payload["review"]
            else:
                metadata = _generate_image_candidate(client, master_prompt, candidate_path, image_model)
                review = review_master_scene_image(
                    client=client,
                    anchor_image=bundle.anchor_image,
                    candidate_image=candidate_path,
                    context=bundle.spec.review_context,
                )
                review["candidate_path"] = str(candidate_path.resolve())
                review["metadata_path"] = str(candidate_json_path.resolve())
                write_json(candidate_json_path, {"metadata": metadata, "review": review})
            master_candidates.append(review)
            summary["master_scene"]["selected"] = _selected_candidate(master_candidates)
            selected_master = summary["master_scene"]["selected"]
            ledger.master_scene_path = (
                selected_master["candidate_path"] if selected_master else None
            )
            write_json(search_summary_path, summary)
            _write_ledger(ledger_path, ledger)
            if _should_stop_early(review, MASTER_SCENE_EARLY_STOP_SCORE):
                break

    best_master = _selected_candidate(master_candidates)
    summary["master_scene"]["selected"] = best_master
    ledger.master_scene_path = best_master["candidate_path"] if best_master else None
    if best_master is None or not best_master.get("pass_gate"):
        summary["status"] = "master_scene_failed"
        write_json(search_summary_path, summary)
        _write_ledger(ledger_path, ledger)
        return summary

    for shot in bundle.spec.shots:
        shot_delta_prompt = build_shot_delta_prompt(bundle, shot.shot_id)
        video_prompt = build_video_prompt(bundle, shot.shot_id)
        shot_dir = episode_dir / shot.shot_id
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot_candidates: List[Dict[str, Any]] = []
        reference_image = Path(best_master["candidate_path"])
        shot_summary = {
            "shot_id": shot.shot_id,
            "prompt": shot_delta_prompt,
            "video_prompt": video_prompt,
            "candidates": shot_candidates,
            "selected": None,
        }
        summary["shots"].append(shot_summary)
        ledger_entry = _ledger_entry_lookup(ledger, shot.shot_id)
        ledger_entry.status = "searching"
        write_json(search_summary_path, summary)
        _write_ledger(ledger_path, ledger)
        for index in range(1, bundle.spec.shot_delta_candidates + 1):
            candidate_stem = shot_dir / f"candidate-{index:02d}"
            video_path = candidate_stem.with_suffix(".mp4")
            task_id: str | None = None
            candidate_json_path = candidate_stem.with_suffix(".json")
            existing_payload = _load_json(candidate_json_path)
            if (
                existing_payload
                and existing_payload.get("selected_frame")
                and not _is_transient_candidate_error(existing_payload)
            ):
                shot_candidates.append(existing_payload["selected_frame"])
                shot_summary["selected"] = _selected_candidate(shot_candidates)
                selected_frame = shot_summary["selected"]
                if selected_frame:
                    ledger_entry.selected_keyframe_path = selected_frame.get("candidate_path")
                    if selected_frame.get("overall_score") is not None:
                        ledger_entry.selected_keyframe_score = float(
                            selected_frame["overall_score"]
                        )
                write_json(search_summary_path, summary)
                _write_ledger(ledger_path, ledger)
                if _should_stop_early(existing_payload["selected_frame"], SHOT_DELTA_EARLY_STOP_SCORE):
                    break
                continue
            try:
                if video_path.exists():
                    result = (
                        existing_payload.get("video_result")
                        if existing_payload and existing_payload.get("video_result")
                        else {"status": "succeeded", "content": {"video_url": None}}
                    )
                    task_id = (
                        existing_payload.get("selected_frame", {}).get("task_id")
                        if existing_payload
                        else None
                    )
                else:
                    task = client.submit_video_task(
                        model=video_model,
                        ratio=ratio,
                        duration=duration,
                        resolution=resolution,
                        content=build_video_task_content(video_prompt, reference_image),
                    )
                    task_id = task["id"]
                    result = _wait_for_video_result(client, task_id)
                    client.download_file(result["content"]["video_url"], video_path)

                selected_frame, frame_reviews = _review_shot_candidate_frames(
                    client=client,
                    bundle=bundle,
                    master_scene_image=Path(best_master["candidate_path"]),
                    candidate_video_path=video_path,
                    output_dir=shot_dir / f"candidate-{index:02d}-frames",
                    shot=shot,
                )
                candidate_summary = dict(selected_frame)
                candidate_summary.update(
                    {
                        "candidate_path": selected_frame["frame_path"],
                        "selected_frame_path": selected_frame["frame_path"],
                        "video_path": str(video_path.resolve()),
                        "task_id": task_id,
                        "reference_image_path": str(reference_image.resolve()),
                        "reference_mode": "master_scene",
                        "metadata_path": str(candidate_json_path.resolve()),
                        "shot_delta_prompt": shot_delta_prompt,
                        "video_prompt": video_prompt,
                        "frame_reviews": frame_reviews,
                    }
                )
                write_json(
                    candidate_json_path,
                    {
                        "video_result": result,
                        "reference_image_path": str(reference_image.resolve()),
                        "shot_delta_prompt": shot_delta_prompt,
                        "video_prompt": video_prompt,
                        "selected_frame": candidate_summary,
                        "frame_reviews": frame_reviews,
                    },
                )
                shot_candidates.append(candidate_summary)
                ledger_entry.selected_keyframe_path = candidate_summary.get("candidate_path")
                if candidate_summary.get("overall_score") is not None:
                    ledger_entry.selected_keyframe_score = float(
                        candidate_summary["overall_score"]
                    )
            except Exception as exc:  # noqa: BLE001
                failure_summary = {
                    "pass_gate": False,
                    "overall_score": 0.0,
                    "candidate_path": None,
                    "selected_frame_path": None,
                    "video_path": str(video_path.resolve()) if video_path.exists() else None,
                    "task_id": task_id,
                    "reference_image_path": str(reference_image.resolve()),
                    "reference_mode": "master_scene",
                    "metadata_path": str(candidate_json_path.resolve()),
                    "shot_delta_prompt": shot_delta_prompt,
                    "video_prompt": video_prompt,
                    "error": str(exc),
                }
                write_json(
                    candidate_json_path,
                    {
                        "reference_image_path": str(reference_image.resolve()),
                        "shot_delta_prompt": shot_delta_prompt,
                        "video_prompt": video_prompt,
                        "selected_frame": failure_summary,
                        "frame_reviews": [],
                        "error": str(exc),
                    },
                )
                shot_candidates.append(failure_summary)
            shot_summary["selected"] = _selected_candidate(shot_candidates)
            write_json(search_summary_path, summary)
            _write_ledger(ledger_path, ledger)
            if shot_candidates and _should_stop_early(shot_candidates[-1], SHOT_DELTA_EARLY_STOP_SCORE):
                break

        best_shot = _selected_candidate(shot_candidates)
        shot_summary["selected"] = best_shot
        if best_shot:
            ledger_entry.selected_keyframe_path = best_shot.get("candidate_path")
            if best_shot.get("overall_score") is not None:
                ledger_entry.selected_keyframe_score = float(best_shot["overall_score"])
        write_json(search_summary_path, summary)
        if best_shot is None or not best_shot.get("pass_gate"):
            summary["status"] = "shot_delta_failed"
            ledger_entry.status = "keyframe_failed"
            write_json(search_summary_path, summary)
            _write_ledger(ledger_path, ledger)
            return summary
        ledger_entry.status = "keyframe_passed"
        _write_ledger(ledger_path, ledger)

    summary["status"] = "ok"
    write_json(search_summary_path, summary)
    _write_ledger(ledger_path, ledger)
    return summary


def render_shortform_episode(
    bundle: ShortformBundle,
    settings: Settings,
    output_root: Path,
    image_model: str | None = None,
    video_model: str = "doubao-seedance-1-5-pro-251215",
    ratio: str = "16:9",
    duration: int = 5,
    resolution: str = "720p",
) -> Dict[str, Any]:
    search_summary = search_keyframe_candidates(
        bundle=bundle,
        settings=settings,
        output_root=output_root,
        image_model=image_model,
        video_model=video_model,
        ratio=ratio,
        duration=duration,
        resolution=resolution,
    )
    if search_summary.get("status") != "ok":
        raise RuntimeError("No gate-passing keyframe candidates were found")

    client = OpenAICompatClient(settings)
    episode_dir = _candidate_dir(bundle, output_root)
    selected_master = search_summary["master_scene"]["selected"]
    manifest: Dict[str, Any] = {
        "episode": bundle.spec.episode,
        "character": bundle.character.slug,
        "provider": video_model,
        "anchor_local": str(bundle.anchor_image.resolve()),
        "master_scene_path": selected_master["candidate_path"],
        "shots": [],
    }
    manifest_path = episode_dir / "manifest.json"
    ledger_path = episode_dir / "continuity_ledger.json"
    existing_manifest = _load_json(manifest_path)
    if existing_manifest:
        manifest = existing_manifest
    ledger = build_continuity_ledger(bundle)
    ledger.search_summary_path = str((episode_dir / "search_summary.json").resolve())
    ledger.manifest_path = str(manifest_path.resolve())
    ledger.master_scene_path = selected_master["candidate_path"]

    previous_bridge: Dict[str, Any] | None = None
    if bundle.initial_bridge_frame is not None:
        previous_bridge = {
            "selected_frame_path": str(bundle.initial_bridge_frame.resolve()),
            "bridge_frame_score": None,
        }
    for shot_summary in search_summary["shots"]:
        shot_id = shot_summary["shot_id"]
        shot_spec = _shot_lookup(bundle, shot_id)
        existing_shot = next(
            (item for item in manifest.get("shots", []) if item.get("shot_id") == shot_id),
            None,
        )
        if existing_shot and existing_shot.get("status") == "succeeded":
            ledger_entry = _ledger_entry_lookup(ledger, shot_id)
            ledger_entry.status = "rendered"
            ledger_entry.selected_keyframe_path = existing_shot.get("shot_delta_keyframe_path")
            ledger_entry.rendered_video_path = existing_shot.get("video_path")
            ledger_entry.final_review_path = existing_shot.get("final_review_path")
            ledger_entry.reference_mode = existing_shot.get("reference_mode")
            bridge_path = existing_shot.get("bridge_frame_path")
            if bridge_path:
                previous_bridge = {
                    "selected_frame_path": bridge_path,
                    "bridge_frame_score": existing_shot.get("bridge_frame_score"),
                }
                ledger_entry.bridge_out_path = bridge_path
                ledger_entry.bridge_frame_score = existing_shot.get("bridge_frame_score")
            else:
                previous_bridge = None
            _write_ledger(ledger_path, ledger)
            continue

        selected = shot_summary["selected"]
        shot_keyframe_path = Path(selected["candidate_path"])
        ledger_entry = _ledger_entry_lookup(ledger, shot_id)
        ledger_entry.selected_keyframe_path = str(shot_keyframe_path.resolve())
        if selected.get("overall_score") is not None:
            ledger_entry.selected_keyframe_score = float(selected["overall_score"])

        video_prompt = build_video_prompt(bundle, shot_id)
        reference_mode = "master_scene"
        bridge_frame_path = None
        bridge_frame_score = None
        if previous_bridge is None:
            content = build_video_task_content(video_prompt, shot_keyframe_path)
        else:
            reference_mode = "previous_video_bridge"
            ledger_entry.bridge_in_path = previous_bridge["selected_frame_path"]
            content = build_video_task_content(
                video_prompt,
                Path(previous_bridge["selected_frame_path"]),
                last_frame_path=shot_keyframe_path,
            )

        task = client.submit_video_task(
            model=video_model,
            ratio=ratio,
            duration=duration,
            resolution=resolution,
            content=content,
        )
        task_id = task["id"]
        result = _wait_for_video_result(client, task_id)

        shot_dir = episode_dir / shot_id
        video_path = shot_dir / f"{task_id}.mp4"
        client.download_file(result["content"]["video_url"], video_path)
        meta_path = shot_dir / f"{task_id}.json"
        write_json(meta_path, result)

        final_frame_dir = shot_dir / "final-review"
        final_frame_path = extract_single_frame(
            video_path,
            final_frame_dir / "frame-01.jpg",
            frame_point=0.8,
        )
        final_review = review_final_shot_frame(
            client=client,
            anchor_image=bundle.anchor_image,
            approved_keyframe_image=shot_keyframe_path,
            candidate_image=final_frame_path,
            shot_id=shot_id,
            dramatic_purpose=shot_spec.dramatic_purpose,
            emotional_state=shot_spec.emotional_state,
            must_show=shot_spec.must_show,
            must_not_hide=shot_spec.must_not_hide,
            forbidden_compositions=shot_spec.forbidden_compositions,
            context=shot_spec.video_prompt_hint or bundle.spec.review_context,
        )
        final_review["frame_path"] = str(final_frame_path.resolve())
        final_review_path = shot_dir / "final_review.json"
        write_json(final_review_path, final_review)
        if not final_review.get("pass_gate"):
            ledger_entry.status = "render_failed"
            ledger_entry.rendered_video_path = str(video_path.resolve())
            ledger_entry.final_review_path = str(final_review_path.resolve())
            ledger_entry.reference_mode = reference_mode
            _write_ledger(ledger_path, ledger)
            raise RuntimeError(
                f"Final render gate failed for {shot_id}: "
                + "; ".join(final_review.get("issues", []))
            )

        if shot_id != bundle.spec.shots[-1].shot_id:
            bridge_dir = shot_dir / "bridge"
            bridge_review_path = shot_dir / "bridge_frame_review.json"
            existing_bridge = _load_json(bridge_review_path)
            if existing_bridge and Path(existing_bridge["selected_frame_path"]).exists():
                previous_bridge = existing_bridge
            else:
                previous_bridge = select_bridge_frame(
                    video_path=video_path,
                    anchor_image=bundle.anchor_image,
                    settings=settings,
                    output_dir=bridge_dir,
                    context=shot_spec.video_prompt_hint or bundle.spec.review_context,
                    tail_ratio=bundle.spec.bridge_frame_selection.tail_ratio,
                    max_candidates=bundle.spec.bridge_frame_selection.max_candidates,
                )
                write_json(bridge_review_path, previous_bridge)
            bridge_frame_path = previous_bridge["selected_frame_path"]
            bridge_frame_score = previous_bridge["bridge_frame_score"]
            ledger_entry.bridge_out_path = bridge_frame_path
            ledger_entry.bridge_frame_score = bridge_frame_score

        _upsert_manifest_shot(
            manifest,
            {
                "shot_id": shot_id,
                "shot_delta_keyframe_path": str(shot_keyframe_path.resolve()),
                "reference_mode": reference_mode,
                "video_prompt": video_prompt,
                "task_id": task_id,
                "status": result["status"],
                "video_path": str(video_path.resolve()),
                "meta_path": str(meta_path.resolve()),
                "final_review_path": str(final_review_path.resolve()),
                "bridge_frame_path": bridge_frame_path,
                "bridge_frame_score": bridge_frame_score,
            },
        )
        ledger_entry.status = "rendered"
        ledger_entry.rendered_video_path = str(video_path.resolve())
        ledger_entry.final_review_path = str(final_review_path.resolve())
        ledger_entry.reference_mode = reference_mode
        write_json(manifest_path, manifest)
        _write_ledger(ledger_path, ledger)

    write_json(manifest_path, manifest)
    _write_ledger(ledger_path, ledger)
    return manifest
