from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from ai_video_control.health_policy import classify_exception, keep_healthy_only, next_model_status
from ai_video_control.provider_runtime import build_model_health_entries, resolve_task_defaults


class HealthPolicyTests(unittest.TestCase):
    def test_classify_http_401_as_fatal_config(self) -> None:
        request = httpx.Request("POST", "https://example.com/v1/chat/completions")
        response = httpx.Response(401, request=request, text='{"error":"unauthorized"}')
        error = httpx.HTTPStatusError("401", request=request, response=response)
        classified = classify_exception(error)
        self.assertEqual(classified["error_class"], "fatal_config")

    def test_classify_http_404_model_not_found_as_fatal_model(self) -> None:
        request = httpx.Request("POST", "https://example.com/v1/chat/completions")
        response = httpx.Response(404, request=request, text='{"error":"model not found"}')
        error = httpx.HTTPStatusError("404", request=request, response=response)
        classified = classify_exception(error)
        self.assertEqual(classified["error_class"], "fatal_model")

    def test_transient_second_failure_disables_automatically(self) -> None:
        self.assertEqual(next_model_status("transient", 1), "degraded")
        self.assertEqual(next_model_status("transient", 2), "disabled_auto")


class ProviderRuntimeTests(unittest.TestCase):
    def test_build_model_health_entries_marks_partial_character_failure_unhealthy(self) -> None:
        providers = [
            {
                "id": "ark",
                "name": "Ark",
                "provider_type": "openai-compatible",
                "manual_enabled": True,
            }
        ]
        policies = [
            {
                "provider_id": "ark",
                "model_id": "text-a",
                "kind": "text",
                "manual_enabled": True,
                "supported_abilities": ["script_text", "character_text_json"],
            }
        ]
        model_health_states = [
            {
                "provider_id": "ark",
                "model_id": "text-a",
                "kind": "text",
                "ability": "script_text",
                "status": "healthy",
                "reason": None,
                "error_class": None,
                "error_code": None,
                "last_checked_at": None,
                "last_healthy_at": None,
                "consecutive_failures": 0,
            },
            {
                "provider_id": "ark",
                "model_id": "text-a",
                "kind": "text",
                "ability": "character_text_json",
                "status": "unhealthy",
                "reason": "json invalid",
                "error_class": "fatal_capability",
                "error_code": "400",
                "last_checked_at": None,
                "last_healthy_at": None,
                "consecutive_failures": 1,
            },
        ]
        entries = build_model_health_entries(
            providers=providers,
            policies=policies,
            model_health_states=model_health_states,
        )
        self.assertEqual(entries[0]["overall_status"], "unhealthy")

    def test_resolve_task_defaults_falls_back_to_other_healthy_provider(self) -> None:
        providers = [
            {
                "id": "bad",
                "name": "Bad",
                "provider_type": "openai-compatible",
                "manual_enabled": True,
                "default_models": {"text": "bad-text", "image": "", "video": "", "local": ""},
                "base_url": "https://bad.example/v1",
                "api_key": "bad",
            },
            {
                "id": "good",
                "name": "Good",
                "provider_type": "openai-compatible",
                "manual_enabled": True,
                "default_models": {"text": "good-text", "image": "", "video": "", "local": ""},
                "base_url": "https://good.example/v1",
                "api_key": "good",
            },
        ]
        policies = [
            {
                "provider_id": "bad",
                "kind": "text",
                "model_id": "bad-text",
                "manual_enabled": True,
            },
            {
                "provider_id": "good",
                "kind": "text",
                "model_id": "good-text",
                "manual_enabled": True,
            },
        ]
        model_entries = [
            {
                "provider_id": "bad",
                "kind": "text",
                "model_id": "bad-text",
                "manual_enabled": True,
                "provider_manual_enabled": True,
                "overall_status": "unhealthy",
                "ability_states": [{"ability": "script_text", "status": "unhealthy"}],
            },
            {
                "provider_id": "good",
                "kind": "text",
                "model_id": "good-text",
                "manual_enabled": True,
                "provider_manual_enabled": True,
                "overall_status": "healthy",
                "ability_states": [{"ability": "script_text", "status": "healthy"}],
            },
        ]
        resolved = resolve_task_defaults(
            task_name="script_generation",
            selected_provider_id="bad",
            providers=providers,
            policies=policies,
            model_entries=model_entries,
        )
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved["provider_id"], "good")
        self.assertEqual(resolved["models"]["text"], "good-text")

    def test_keep_healthy_only_disables_unhealthy_provider_and_preserves_healthy_defaults(self) -> None:
        provider_state = {
            "selected_provider_id": "bad",
            "providers": [
                {
                    "id": "bad",
                    "name": "Bad",
                    "provider_type": "openai-compatible",
                    "manual_enabled": True,
                    "enabled": True,
                    "default_models": {"text": "bad-text", "image": "", "video": "", "local": ""},
                    "text_model": "bad-text",
                    "image_model": "",
                    "video_model": "",
                    "local_model": "",
                },
                {
                    "id": "good",
                    "name": "Good",
                    "provider_type": "openai-compatible",
                    "manual_enabled": True,
                    "enabled": True,
                    "default_models": {"text": "good-text", "image": "", "video": "", "local": ""},
                    "text_model": "good-text",
                    "image_model": "",
                    "video_model": "",
                    "local_model": "",
                },
            ],
        }
        model_entries = [
            {
                "provider_id": "bad",
                "kind": "text",
                "model_id": "bad-text",
                "manual_enabled": True,
                "provider_manual_enabled": True,
                "overall_status": "unhealthy",
                "supported_abilities": ["script_text"],
            },
            {
                "provider_id": "good",
                "kind": "text",
                "model_id": "good-text",
                "manual_enabled": True,
                "provider_manual_enabled": True,
                "overall_status": "healthy",
                "supported_abilities": ["script_text"],
            },
        ]
        provider_summaries = [
            {"provider_id": "bad", "status": "unhealthy"},
            {"provider_id": "good", "status": "healthy"},
        ]

        with patch("ai_video_control.health_policy.read_provider_settings", return_value=provider_state), patch(
            "ai_video_control.health_policy.build_model_health_entries",
            return_value=model_entries,
        ), patch(
            "ai_video_control.health_policy.build_provider_health_summary",
            return_value=provider_summaries,
        ), patch(
            "ai_video_control.health_policy.list_provider_health_states",
            return_value=[],
        ), patch(
            "ai_video_control.health_policy.list_provider_model_policies",
            return_value=[],
        ), patch(
            "ai_video_control.health_policy.list_model_health_states",
            return_value=[],
        ), patch(
            "ai_video_control.health_policy.upsert_provider_model_policy",
        ) as upsert_policy, patch(
            "ai_video_control.health_policy.update_provider_settings",
            side_effect=lambda selected_provider_id, providers: {
                "selected_provider_id": selected_provider_id,
                "providers": providers,
            },
        ):
            result = keep_healthy_only()

        self.assertEqual(result["selected_provider_id"], "good")
        bad_provider = next(item for item in result["providers"] if item["id"] == "bad")
        good_provider = next(item for item in result["providers"] if item["id"] == "good")
        self.assertFalse(bad_provider["manual_enabled"])
        self.assertTrue(good_provider["manual_enabled"])
        self.assertEqual(good_provider["default_models"]["text"], "good-text")
        self.assertEqual(upsert_policy.call_count, 2)


if __name__ == "__main__":
    unittest.main()
