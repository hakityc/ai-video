from __future__ import annotations

import copy
import unittest
from pathlib import Path

from ai_video_control.review import choose_best_review
from ai_video_control.shortform import (
    build_continuity_ledger,
    build_video_task_content,
    build_shot_card,
    build_master_scene_prompt,
    build_shot_delta_prompt,
    build_video_prompt,
    load_shortform_bundle,
    validate_prompt_pollution,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "examples" / "episodes" / "tomb-raider-female-ep007.yaml"
QIAO_SPEC_PATH = ROOT / "examples" / "episodes" / "qiao-ning-ep003.yaml"


class ShortformWorkflowTests(unittest.TestCase):
    def test_master_scene_prompt_is_non_empty(self) -> None:
        bundle = load_shortform_bundle(SPEC_PATH)
        prompt = build_master_scene_prompt(bundle)
        self.assertIn("Lin Xia", prompt)
        self.assertIn("cold blue-green clinical lighting", prompt)

    def test_shot_delta_prompt_omits_locked_identity_details(self) -> None:
        bundle = load_shortform_bundle(SPEC_PATH)
        prompt = build_shot_delta_prompt(bundle, "shot-001").lower()
        self.assertNotIn("brown leather jacket", prompt)
        self.assertNotIn("corpse table centered toward camera", prompt)

    def test_prompt_pollution_flags_repeated_locked_details(self) -> None:
        bundle = load_shortform_bundle(SPEC_PATH)
        polluted = copy.deepcopy(bundle)
        polluted.spec.shots[0].dimensions.subject_motion.text = (
            "same brown leather jacket beside the corpse table centered toward camera"
        )
        issues = validate_prompt_pollution(polluted, stage="shot_delta", shot_id="shot-001")
        self.assertTrue(issues)

    def test_prompt_pollution_flags_forbidden_new_prop_terms(self) -> None:
        bundle = load_shortform_bundle(SPEC_PATH)
        polluted = copy.deepcopy(bundle)
        polluted.spec.shots[0].forbidden_changes = ["new props"]
        polluted.spec.shots[0].dimensions.subject_motion.text = (
            "Lin Xia holds a paper file over the corpse table"
        )
        issues = validate_prompt_pollution(polluted, stage="shot_delta", shot_id="shot-001")
        self.assertTrue(any("new prop or accessory" in issue for issue in issues))

    def test_choose_best_review_prefers_passing_item(self) -> None:
        reviews = [
            {"pass_gate": False, "overall_score": 0.9, "name": "bad-high-score"},
            {"pass_gate": True, "overall_score": 0.7, "name": "good"},
        ]
        best = choose_best_review(reviews, pass_key="pass_gate", score_key="overall_score")
        self.assertEqual(best["name"], "good")

    def test_build_video_task_content_uses_frame_roles(self) -> None:
        first = ROOT / "assets" / "characters" / "tomb-raider-female" / "reference" / "front.jpeg"
        last = ROOT / "assets" / "characters" / "tomb-raider-female" / "reference" / "three-quarter.jpeg"
        content = build_video_task_content("same protagonist", first, last)
        self.assertEqual(content[1]["role"], "first_frame")
        self.assertEqual(content[2]["role"], "last_frame")

    def test_video_prompt_keeps_generic_continuity_constraints(self) -> None:
        bundle = load_shortform_bundle(SPEC_PATH)
        prompt = build_video_prompt(bundle, "shot-001").lower()
        self.assertIn("same camera framing", prompt)
        self.assertIn("do not introduce new props", prompt)
        self.assertNotIn("brown leather jacket", prompt)

    def test_video_prompt_includes_beat_legibility_constraints(self) -> None:
        bundle = load_shortform_bundle(QIAO_SPEC_PATH)
        prompt = build_video_prompt(bundle, "shot-004").lower()
        self.assertIn("must clearly show the entrance glass and the wet footprint trail", prompt)
        self.assertIn("forbidden composition: feet-dominant framing", prompt)

    def test_build_shot_card_uses_prompt_fields_as_fallbacks(self) -> None:
        bundle = load_shortform_bundle(SPEC_PATH)
        shot_card = build_shot_card(bundle, "shot-001")
        self.assertEqual(shot_card.beat, bundle.spec.shots[0].video_prompt_hint)
        self.assertIn("restrained calm before dread", shot_card.bridge_frame_goal)

    def test_build_continuity_ledger_scaffolds_entries_for_all_shots(self) -> None:
        bundle = load_shortform_bundle(SPEC_PATH)
        ledger = build_continuity_ledger(bundle)
        self.assertEqual(ledger.episode, bundle.spec.episode)
        self.assertEqual(len(ledger.shots), len(bundle.spec.shots))
        self.assertEqual(ledger.shots[0].status, "planned")


if __name__ == "__main__":
    unittest.main()
