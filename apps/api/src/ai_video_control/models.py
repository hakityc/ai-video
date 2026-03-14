from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ReferenceImage(BaseModel):
    path: str
    view: str
    expression: Optional[str] = None
    approved: bool = True
    notes: Optional[str] = None


class IdentityAnchors(BaseModel):
    face: List[str] = Field(default_factory=list)
    hair: List[str] = Field(default_factory=list)
    body: List[str] = Field(default_factory=list)
    outfit: List[str] = Field(default_factory=list)
    accessories: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_non_empty(self) -> "IdentityAnchors":
        if not any(
            [
                self.face,
                self.hair,
                self.body,
                self.outfit,
                self.accessories,
            ]
        ):
            raise ValueError("identity_anchors must contain at least one anchor")
        return self

    def flattened(self) -> List[str]:
        return self.face + self.hair + self.body + self.outfit + self.accessories


class CharacterBible(BaseModel):
    version: Literal["1"] = "1"
    slug: str
    name: str
    identity_anchors: IdentityAnchors
    style_descriptors: List[str] = Field(default_factory=list)
    color_palette: List[str] = Field(default_factory=list)
    prompt_template: str
    negative_prompt: str = ""
    reference_images: List[ReferenceImage] = Field(default_factory=list)

    @field_validator("reference_images")
    @classmethod
    def validate_reference_images(
        cls, value: List[ReferenceImage]
    ) -> List[ReferenceImage]:
        if not value:
            raise ValueError("reference_images must contain at least one image")
        return value

    def identity_text(self) -> str:
        return ", ".join(self.identity_anchors.flattened())

    def style_text(self) -> str:
        parts = list(self.style_descriptors)
        if self.color_palette:
            parts.append("color palette " + ", ".join(self.color_palette))
        return ", ".join(parts)

    def render_prompt(self, scene_prompt: str, prompt_override: Optional[str]) -> str:
        if prompt_override:
            return prompt_override

        template = Template(self.prompt_template)
        return template.safe_substitute(
            {
                "name": self.name,
                "identity": self.identity_text(),
                "style": self.style_text(),
                "scene_prompt": scene_prompt,
            }
        )

    def render_negative_prompt(self, extra_negative_prompt: str) -> str:
        parts = [part.strip() for part in [self.negative_prompt, extra_negative_prompt] if part]
        return ", ".join(parts)


class InputImage(BaseModel):
    source: str
    source_type: Literal["local_path", "url", "comfyui_input_name"] = "local_path"
    upload_to_comfyui: bool = True


class WorkflowPatch(BaseModel):
    node_id: str
    input_name: str
    value: Any


class ComfyUIJobConfig(BaseModel):
    workflow_path: str
    workflow_overrides: List[WorkflowPatch] = Field(default_factory=list)
    output_dir: str = "artifacts/comfyui"
    poll_interval_seconds: float = 5.0
    timeout_seconds: int = 1800
    download_outputs: bool = True


class CogVideoXJobConfig(BaseModel):
    model_id: str = "THUDM/CogVideoX-5b-I2V"
    output_path: str = "artifacts/cogvideox/output.mp4"
    torch_dtype: Literal["float16", "bfloat16", "float32"] = "bfloat16"
    device: Literal["auto", "cuda", "mps", "cpu"] = "auto"
    guidance_scale: float = 6.0
    num_inference_steps: int = 50
    use_dynamic_cfg: bool = True
    enable_model_cpu_offload: bool = False
    enable_vae_tiling: bool = True
    enable_vae_slicing: bool = True


class VideoJob(BaseModel):
    version: Literal["1"] = "1"
    id: str
    character_bible: str
    provider: Literal["comfyui", "cogvideox"]
    scene_prompt: str
    prompt_override: Optional[str] = None
    script_path: Optional[str] = None
    script_excerpt: Optional[str] = None
    storyboard_notes: Optional[str] = None
    camera_plan: Optional[str] = None
    negative_prompt: str = ""
    seed: int = 42
    input_image: InputImage
    reference_images: List[InputImage] = Field(default_factory=list)
    fps: int = 16
    num_frames: int = 81
    width: Optional[int] = None
    height: Optional[int] = None
    output_prefix: str = "shot"
    comfyui: Optional[ComfyUIJobConfig] = None
    cogvideox: Optional[CogVideoXJobConfig] = None

    @model_validator(mode="after")
    def validate_provider_config(self) -> "VideoJob":
        if self.provider == "comfyui" and self.comfyui is None:
            raise ValueError("comfyui config is required when provider is comfyui")
        if self.provider == "cogvideox" and self.cogvideox is None:
            raise ValueError("cogvideox config is required when provider is cogvideox")
        return self

    def prompt(self, character: CharacterBible) -> str:
        return character.render_prompt(self.scene_prompt, self.prompt_override)

    def combined_negative_prompt(self, character: CharacterBible) -> str:
        return character.render_negative_prompt(self.negative_prompt)

    def resolve_character_bible_path(self, job_path: Path) -> Path:
        candidate = Path(self.character_bible)
        if candidate.is_absolute():
            return candidate
        return (job_path.parent / candidate).resolve()


class RenderResult(BaseModel):
    provider: str
    prompt: str
    negative_prompt: str = ""
    prompt_id: Optional[str] = None
    output_paths: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


DimensionMode = Literal["locked_by_reference", "locked_by_pack", "open_for_text"]


class DimensionControl(BaseModel):
    mode: DimensionMode
    text: str = ""


class FiveDimensionSpec(BaseModel):
    subject_motion: DimensionControl
    environment_light: DimensionControl
    medium_rendering: DimensionControl
    temporal_state: DimensionControl
    camera_optics: DimensionControl

    def as_dict(self) -> Dict[str, DimensionControl]:
        return {
            "subject_motion": self.subject_motion,
            "environment_light": self.environment_light,
            "medium_rendering": self.medium_rendering,
            "temporal_state": self.temporal_state,
            "camera_optics": self.camera_optics,
        }

    def texts_for_modes(self, *modes: DimensionMode) -> List[str]:
        items: List[str] = []
        for value in self.as_dict().values():
            if value.mode in modes and value.text.strip():
                items.append(value.text.strip())
        return items

    def open_dimension_names(self) -> List[str]:
        return [
            name
            for name, value in self.as_dict().items()
            if value.mode == "open_for_text" and value.text.strip()
        ]


class ScenePack(BaseModel):
    version: Literal["2"] = "2"
    id: str
    name: str
    dimensions: FiveDimensionSpec
    fixed_elements: List[str] = Field(default_factory=list)
    forbidden_drift: List[str] = Field(default_factory=list)
    allowed_camera_templates: List[str] = Field(default_factory=list)


class PropPack(BaseModel):
    version: Literal["2"] = "2"
    id: str
    name: str
    scene_pack: str
    fixed_props: List[str] = Field(default_factory=list)
    allowed_temporal_changes: List[str] = Field(default_factory=list)
    forbidden_drift: List[str] = Field(default_factory=list)


class ShotTemplate(BaseModel):
    version: Literal["2"] = "2"
    id: str
    name: str
    scene_pack: str
    dimensions: FiveDimensionSpec
    framing: List[str] = Field(default_factory=list)
    blocking_rules: List[str] = Field(default_factory=list)
    allowed_changes: List[str] = Field(default_factory=list)
    forbidden_changes: List[str] = Field(default_factory=list)
    prompt_suffix: List[str] = Field(default_factory=list)


class BridgeFrameSelection(BaseModel):
    tail_ratio: float = 0.2
    max_candidates: int = 6

    @field_validator("tail_ratio")
    @classmethod
    def validate_tail_ratio(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError("tail_ratio must be between 0 and 1")
        return value

    @field_validator("max_candidates")
    @classmethod
    def validate_max_candidates(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_candidates must be >= 1")
        return value


class MasterSceneSpec(BaseModel):
    dimensions: FiveDimensionSpec
    negative_prompt: str = ""


class ShotCard(BaseModel):
    beat: str = ""
    shot_size: str = ""
    angle: str = ""
    lens_feel: str = ""
    movement: str = ""
    blocking: str = ""
    screen_direction: str = ""
    must_show: List[str] = Field(default_factory=list)
    continuity_notes: List[str] = Field(default_factory=list)
    bridge_frame_goal: str = ""
    edit_seam: str = ""


class ShotDeltaSpec(BaseModel):
    shot_id: str
    dimensions: FiveDimensionSpec
    allowed_changes: List[str] = Field(default_factory=list)
    forbidden_changes: List[str] = Field(default_factory=list)
    video_prompt_hint: str = ""
    dramatic_purpose: str = ""
    emotional_state: str = ""
    must_show: List[str] = Field(default_factory=list)
    must_not_hide: List[str] = Field(default_factory=list)
    forbidden_compositions: List[str] = Field(default_factory=list)
    shot_card: ShotCard = Field(default_factory=ShotCard)


class ContinuityLedgerShot(BaseModel):
    shot_id: str
    status: str = "planned"
    shot_card: ShotCard = Field(default_factory=ShotCard)
    dramatic_purpose: str = ""
    emotional_state: str = ""
    locked_context: List[str] = Field(default_factory=list)
    allowed_changes: List[str] = Field(default_factory=list)
    forbidden_changes: List[str] = Field(default_factory=list)
    must_show: List[str] = Field(default_factory=list)
    must_not_hide: List[str] = Field(default_factory=list)
    prompt_pollution_issues: List[str] = Field(default_factory=list)
    selected_keyframe_path: str | None = None
    selected_keyframe_score: float | None = None
    rendered_video_path: str | None = None
    final_review_path: str | None = None
    reference_mode: str | None = None
    bridge_in_path: str | None = None
    bridge_out_path: str | None = None
    bridge_frame_score: float | None = None
    notes: List[str] = Field(default_factory=list)


class ContinuityLedger(BaseModel):
    version: Literal["1"] = "1"
    episode: str
    character: str
    scene_pack: str
    prop_pack: str
    shot_template: str
    review_context: str = ""
    anchor_image: str
    initial_bridge_frame: str | None = None
    master_scene_path: str | None = None
    search_summary_path: str | None = None
    manifest_path: str | None = None
    shots: List[ContinuityLedgerShot] = Field(default_factory=list)


class ShortformEpisodeSpec(BaseModel):
    version: Literal["2"] = "2"
    episode: str
    character_bible: str
    scene_pack: str
    prop_pack: str
    shot_template: str
    provider: Literal["seedance"] = "seedance"
    anchor_image: str
    initial_bridge_frame: str | None = None
    review_context: str = ""
    master_scene_candidates: int = 4
    shot_delta_candidates: int = 3
    bridge_frame_selection: BridgeFrameSelection = Field(
        default_factory=BridgeFrameSelection
    )
    master_scene: MasterSceneSpec
    shots: List[ShotDeltaSpec]

    @field_validator("shots")
    @classmethod
    def validate_shots(cls, value: List[ShotDeltaSpec]) -> List[ShotDeltaSpec]:
        if not value:
            raise ValueError("shots must contain at least one shot")
        return value

    def resolve_character_bible_path(self, spec_path: Path) -> Path:
        candidate = Path(self.character_bible)
        if candidate.is_absolute():
            return candidate
        return (spec_path.parent / candidate).resolve()

    def resolve_scene_pack_path(self, spec_path: Path) -> Path:
        candidate = Path(self.scene_pack)
        if candidate.is_absolute():
            return candidate
        return (spec_path.parent / candidate).resolve()

    def resolve_prop_pack_path(self, spec_path: Path) -> Path:
        candidate = Path(self.prop_pack)
        if candidate.is_absolute():
            return candidate
        return (spec_path.parent / candidate).resolve()

    def resolve_shot_template_path(self, spec_path: Path) -> Path:
        candidate = Path(self.shot_template)
        if candidate.is_absolute():
            return candidate
        return (spec_path.parent / candidate).resolve()

    def resolve_anchor_image_path(self, spec_path: Path) -> Path:
        candidate = Path(self.anchor_image)
        if candidate.is_absolute():
            return candidate
        return (spec_path.parent / candidate).resolve()

    def resolve_initial_bridge_frame_path(self, spec_path: Path) -> Path | None:
        if not self.initial_bridge_frame:
            return None
        candidate = Path(self.initial_bridge_frame)
        if candidate.is_absolute():
            return candidate
        return (spec_path.parent / candidate).resolve()
