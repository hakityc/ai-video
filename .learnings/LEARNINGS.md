# Learnings

## [LRN-20260312-001] best_practice

**Logged**: 2026-03-12T16:58:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Per-shot keyframes improve story progression, but they do not reliably preserve character identity across hard scene changes.

### Details
Episode 003 replaced the old "single shared anchor image" workflow with distinct keyframes for each shot.
This fixed the narrative issue and produced meaningful scene progression across morgue, apartment corridor, and auction hall.
However, automated review still showed heavy identity drift in shot-002 and shot-003, especially hair color and facial structure changes.
The workflow therefore needs an explicit identity-lock stage before video generation, not just better shot planning.

### Suggested Action
Add a preflight gate that checks each shot keyframe against the approved character reference pack and regenerates weak keyframes before submitting video jobs.

### Metadata
- Source: conversation
- Related Files: scripts/generate_seedance_episode.py, artifacts/video/seedance/tomb-raider-female/episode-003/review.json
- Tags: video, continuity, identity-drift, seedance

---

## [LRN-20260312-002] best_practice

**Logged**: 2026-03-12T16:58:00+08:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
Third-party skills with elevated risk scores must be reviewed before being allowed into the active generation-and-repair loop.

### Details
The `ffmpeg-analyse-video` skill installed successfully but was flagged as `High Risk` by the skills CLI.
For this project, analysis and repair tooling will be allowed only after inspecting the skill instructions and limiting usage to safe read-only or bounded operations.

### Suggested Action
Keep `continuity-ledger` available for state tracking, but treat `ffmpeg-analyse-video` as opt-in and review-only until its commands are explicitly whitelisted for the current workflow.

### Metadata
- Source: conversation
- Related Files: /Users/lebo/.agents/skills/continuity-ledger/SKILL.md, /Users/lebo/.agents/skills/ffmpeg-analyse-video/SKILL.md
- Tags: skills, safety, ffmpeg, review

---

## [LRN-20260312-003] best_practice

**Logged**: 2026-03-12T17:25:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Frame-level VLM review under-scores continuity when the sampled frame crops out the face or over-interprets scene mismatch from the single anchor image.

### Details
Episode 004 tightened the story into one morgue sequence and visually held the character much better than Episode 003.
However, the automated review still produced very low atmosphere and identity scores for shot-001 and shot-002 because some sampled frames cropped out the face and the VLM overemphasized scene mismatch against the single anchor reference.
This means the current `review-episode` output is useful for catching gross drift, but not yet trustworthy as a hard gate for cropped or partial-body frames.

### Suggested Action
Update review logic to compare against shot keyframes as well as the global anchor, and skip or down-weight frames where the protagonist face is not visible enough.

### Metadata
- Source: conversation
- Related Files: src/ai_video_control/review.py, artifacts/video/seedance/tomb-raider-female/episode-004/review.json
- Tags: review, vlm, frame-sampling, continuity

---

## [LRN-20260312-004] correction

**Logged**: 2026-03-12T17:31:00+08:00
**Priority**: critical
**Status**: pending
**Area**: backend

### Summary
Episode 004 keyframes do not meet continuity requirements even before video generation, because both the protagonist details and scene props drift across the three stills.

### Details
The user correctly pointed out that the problem is not only character identity.
Across the three morgue keyframes, the corpse pose and placement change too much, the overhead surgical lights change layout, the trolley and counter layout drift, and protagonist accessories such as pendant, watch, gloves, freckles, and boot shape are inconsistent.
This means the keyframes themselves fail the continuity gate and should not be used as video seeds.

### Suggested Action
Add a keyframe continuity gate before any video submission. Reject a shot set when shared scene anchors, corpse placement, lighting rig, and protagonist accessories are not stable enough across the stills.

### Metadata
- Source: user_feedback
- Related Files: artifacts/video/seedance/tomb-raider-female/episode-004/keyframes/shot-001.jpeg, artifacts/video/seedance/tomb-raider-female/episode-004/keyframes/shot-002.jpeg, artifacts/video/seedance/tomb-raider-female/episode-004/keyframes/shot-003.jpeg
- Tags: correction, keyframes, continuity, props, scene-consistency

---

## [LRN-20260312-005] best_practice

**Logged**: 2026-03-12T17:40:00+08:00
**Priority**: low
**Status**: pending
**Area**: infra

### Summary
Repository validation should prefer `uv run python` over bare `python3` because project-only dependencies such as `PyYAML` are not guaranteed in the system interpreter.

### Details
Attempting to validate new YAML asset packs with bare `python3` failed because the system interpreter did not have `yaml` installed.
The project environment already contains the needed dependencies through `uv`.

### Suggested Action
Use `uv run python` for repository-bound validation scripts.

### Metadata
- Source: error
- Related Files: examples/scenes/morgue-night.yaml
- Tags: uv, validation, environment

---

## [LRN-20260312-006] best_practice

**Logged**: 2026-03-12T18:52:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
This Ark account exposes `Seedream` image-to-image models in `/models`, but the usable image model is still `Seedream 3.0` text-to-image only, so shot-delta search must rely on `Seedance` reference-driven draft clips instead of direct image editing.

### Details
During workflow refactor, the plan called for master-scene-first asset generation and subtractive shot-delta derivation.
The account model list includes `doubao-seedream-4-0`, `doubao-seedream-4-5`, and `doubao-seedream-5-0` with `ImageToImage` capability, but probe requests returned `ModelNotOpen`.
The currently active image model `doubao-seedream-3-0-t2i-250415` rejects the `image` parameter entirely.
That makes pure image-edit keyframe search unavailable on this account even though the capability exists in the platform.

### Suggested Action
Use `Seedream` only for master-scene text-to-image search on this account, and generate shot-delta candidates through `Seedance` image-to-video drafts plus frame extraction until a real `Seedream` image-to-image model is activated.

### Metadata
- Source: error
- Related Files: src/ai_video_control/providers/openai_compat.py, src/ai_video_control/shortform.py
- Tags: ark, seedream, seedance, image-to-image, model-access

---

## [LRN-20260312-007] best_practice

**Logged**: 2026-03-12T19:16:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
For `doubao-seedance-1-5-pro-251215`, two-image video requests are accepted only when the image items are role-tagged as `first_frame` and `last_frame`.

### Details
The chain-render workflow originally appended both the current shot keyframe and the previous shot bridge frame as generic `image_url` entries.
Ark rejected that payload with: `expected at most one image content with unspecified role but got 2 instead`.
Probing the same endpoint showed that the request succeeds when the content items remain `type=image_url` but include `role=first_frame` and `role=last_frame`.

### Suggested Action
Build chain-referenced video requests with explicit frame roles. Use the bridge frame as `first_frame` and the approved shot keyframe as `last_frame` for `shot n > 1`.

### Metadata
- Source: error
- Related Files: src/ai_video_control/shortform.py
- Tags: ark, seedance, first_frame, last_frame, chain-reference

---

## [LRN-20260312-008] best_practice

**Logged**: 2026-03-12T19:36:00+08:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
`clawhub` CLI v0.7.0 can fail against the current registry because publish payloads do not include `acceptLicenseTerms: true`.

### Details
Publishing a skill through the installed CLI returned `Publish payload: acceptLicenseTerms: invalid value`.
Direct API probing showed the registry now requires a boolean `acceptLicenseTerms` field and only accepts `true`.
The local CLI implementation in `dist/cli/commands/publish.js` was missing that field.

### Suggested Action
Before future skill publishes, either upgrade the CLI to a version that includes `acceptLicenseTerms` or patch the publish payload locally to send `acceptLicenseTerms: true`.

### Metadata
- Source: error
- Related Files: /Users/lebo/.local/state/fnm_multishells/56865_1773282194249/lib/node_modules/clawhub/dist/cli/commands/publish.js
- Tags: clawhub, cli, registry, publish

---

## [LRN-20260312-009] correction

**Logged**: 2026-03-12T19:48:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
When the user asks for continuous `001 -> 006` story generation, do not substitute that with multiple variants of the same approved shot.

### Details
I generated six variants of the same convenience-store `shot-001` clip to explore motion quality, but the user wanted a continuous sequence of shots progressing the story.
Those are different tasks: one is candidate sampling, the other is chain-referenced story rollout.
The workflow already supports the latter conceptually, so the mistake was execution, not capability.

### Suggested Action
Treat “generate multiple variants” as an explicit branch for candidate search only. For story rollout, always create or reuse a shot list (`001..N`) and advance bridge-frame conditioning shot by shot.

### Metadata
- Source: user_feedback
- Related Files: scripts/generate_shot_variants.py, src/ai_video_control/shortform.py
- Tags: correction, sequencing, rollout, variants

---

## [LRN-20260312-010] best_practice

**Logged**: 2026-03-12T20:40:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
A continuity-safe cut can still fail as a drama scene if the workflow preserves scene stability but does not enforce shot-level beat legibility.

### Details
The completed convenience-store episode (`qiao-ning-ep002`) successfully chained six shots into one final artifact with stable protagonist appearance and reusable bridge frames.
However, full-cut review showed that shot-004 breaks the intended dramatic progression even though the earlier continuity gates accepted the sequence.
The shot introduces a low, feet-dominant framing and a barefoot read, which weakens the intended "look toward the entrance and notice wet footprints" beat.
More broadly, several later beats are technically present but not visually dominant enough to land as clear story events.

### Suggested Action
Extend the shortform workflow with a beat-legibility gate.
Each shot spec should declare `must_show`, `must_not_hide`, and `forbidden_compositions`, and candidate selection should fail when the main dramatic evidence is not clearly visible in frame.

### Metadata
- Source: conversation
- Related Files: docs/reviews/qiao-ning-ep002-postmortem.md, examples/episodes/qiao-ning-ep002.yaml, artifacts/output/qiao-ning/episode-002/episode-002-cut.mp4
- Tags: continuity, story, beat-legibility, shot-design, review

---

## [LRN-20260312-011] correction

**Logged**: 2026-03-12T20:40:00+08:00
**Priority**: critical
**Status**: pending
**Area**: backend

### Summary
The final convenience-store manifest still points to the wrong character anchor, which undermines identity QA trust even when the visible result looks acceptable.

### Details
The generated final manifest for `qiao-ning-ep002` uses:
`/Users/lebo/project/ai-video/assets/characters/tomb-raider-female/reference/front.jpeg`
as `anchor_local`.
That reference belongs to an older character path, not the active Qiao Ning asset pack.
This did not fully break the visible episode, but it means continuity review and future rerenders are operating with a polluted identity source.

### Suggested Action
Correct the episode and/or render pipeline so the formal manifest always writes the active episode character anchor, not a leftover reference from a previous storyline.

### Metadata
- Source: conversation
- Related Files: artifacts/video/seedance-rollout/qiao-ning/episode-002/manifest.json, examples/episodes/qiao-ning-ep002.yaml
- Tags: correction, anchor, identity, manifest, continuity

---

## [LRN-20260312-012] best_practice

**Logged**: 2026-03-12T20:48:00+08:00
**Priority**: critical
**Status**: pending
**Area**: backend

### Summary
Passing shot-delta keyframes do not guarantee that the final chain-rendered videos preserve the same composition or dramatic beat, so final renders need their own gate.

### Details
In `qiao-ning-ep002`, the selected shot-delta keyframes for shots 001 to 006 all passed continuity review.
However, the final rendered episode still developed serious story and composition failures, especially around shot-004 where the formal render collapsed into a feet-dominant framing and broke the intended entrance-threat beat.
This proves that keyframe-stage approval is necessary but insufficient.
The later video render step can reintroduce camera drift, action emphasis drift, or beat-legibility failure even when the seed stills were acceptable.

### Suggested Action
Add a final-render gate after `render-shortform` that compares the rendered video against:
- the approved shot keyframe
- the intended beat requirements from the episode spec
- the previous formal shot bridge state

Reject or regenerate final shots when composition, readable beat evidence, or actor state no longer matches the approved plan.

### Metadata
- Source: conversation
- Related Files: artifacts/video/seedance-rollout/qiao-ning/episode-002/manifest.json, artifacts/output/qiao-ning/episode-002/episode-002-cut.mp4, src/ai_video_control/shortform.py
- Tags: final-render, gate, continuity, beat-legibility, chain-render

---

## [LRN-20260312-013] best_practice

**Logged**: 2026-03-12T21:06:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Long-running video polling needs a hard timeout and in-progress search summary persistence, or one stuck provider task can hide the real failure point for an entire candidate search.

### Details
While running `search-keyframe-candidates` for `qiao-ning-ep003`, the new beat gate correctly rejected `shot-001/candidate-01`, but the overall process then appeared to stall without producing `candidate-02` or a final `search_summary.json`.
The root cause was that `_wait_for_video_result()` had no hard timeout, so a provider task that stayed pending could block the entire episode search indefinitely.
Because the summary was only written on final success/failure boundaries, there was also no durable progress record explaining where the search had stopped.

### Suggested Action
Always enforce a hard timeout for provider video polling and continuously persist `search_summary.json` during candidate search so stalled or partial runs remain debuggable and resumable.

### Metadata
- Source: conversation
- Related Files: src/ai_video_control/shortform.py, artifacts/video/seedance-rollout/qiao-ning/episode-003
- Tags: timeout, persistence, search, provider, resilience

---

## [LRN-20260312-014] best_practice

**Logged**: 2026-03-12T21:10:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
In locked wide-shot micro-stories, the first dramatic anomaly must be large and high-contrast enough to survive generation; subtle events like a single small practical light changing state are often too weak to be reliably legible.

### Details
After adding beat-legibility gating to `qiao-ning-ep003`, `shot-001` repeatedly failed even though identity, scene layout, and props were mostly stable.
The recurring problem was not continuity drift first, but that the required event "one refrigerator light goes dark" did not dominate enough in the wide composition.
This means the beat was under-designed for the model and the shot scale.

### Suggested Action
When designing opening anomalies for chain-referenced shortform scenes, prefer stronger, more readable changes:
- a whole bay flicker instead of a single small lamp
- a ceiling light stutter instead of a tiny practical detail
- one dominant visual event per shot with high contrast against the locked scene

### Metadata
- Source: conversation
- Related Files: examples/episodes/qiao-ning-ep003.yaml, docs/reviews/qiao-ning-ep003-gate-report.md
- Tags: beat-design, legibility, shot-design, wide-shot, anomaly

---

## [LRN-20260312-015] best_practice

**Logged**: 2026-03-12T21:24:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
For this project, explicit `ffmpeg` subprocess extraction is more reliable than relying on `imageio`'s implicit video backend chain.

### Details
During the `qiao-ning-ep003` search rerun, candidate review failed with a misleading `No such file or directory` error pointing at the bundled `imageio_ffmpeg` binary path.
The binary itself was present and executable, but the `imageio`-driven decode path was still brittle inside the workflow.
Replacing frame extraction with explicit `ffmpeg` subprocess calls made extraction deterministic and aligned the review path with the project's planned video concatenation and bridge-frame tooling.

### Suggested Action
Standardize video frame extraction and later concatenation on an explicit `ffmpeg` binary resolution flow:
- prefer system `ffmpeg` when installed
- otherwise use the bundled `imageio_ffmpeg` executable path directly
- avoid depending on implicit backend auto-selection for critical workflow steps

### Metadata
- Source: conversation
- Related Files: src/ai_video_control/review.py
- Tags: ffmpeg, extraction, reliability, backend, tooling

---

## [LRN-20260312-016] best_practice

**Logged**: 2026-03-12T22:25:00+08:00
**Priority**: medium
**Status**: pending
**Area**: backend

### Summary
When iterating quickly with `uv` and editable installs, prefer `uv run python -m ai_video_control.cli ...` over the generated `aivideo` entrypoint if the environment has just been rebuilt or used concurrently.

### Details
During the shot-level repair passes, a direct `uv run aivideo ...` invocation started failing with `ModuleNotFoundError: No module named 'ai_video_control.settings'` even though the source tree and local tests were intact.
This appeared after rapid iterative runs and concurrent `uv run` invocations.
Using the module entrypoint is more robust in this workflow because it bypasses a stale or partially refreshed console-script wrapper.

### Suggested Action
For long-running repair jobs or after package churn, run commands as:
`uv run python -m ai_video_control.cli ...`
and avoid launching multiple `uv run aivideo ...` installs in parallel.

### Metadata
- Source: conversation
- Related Files: src/ai_video_control/cli.py
- Tags: uv, cli, editable-install, reliability

---
