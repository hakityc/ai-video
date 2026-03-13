# Qiao Ning EP003 Gate Report

## Summary

`qiao-ning-ep003` did not advance past `shot-001`.
This is a useful failure, not a regression:
the new workflow correctly rejects shots that keep identity and scene continuity
but fail to land the intended dramatic beat.

Result artifact:
- `artifacts/video/seedance-rollout/qiao-ning/episode-003/search_summary.json`

Status:
- `shot_delta_failed`

## What Passed

- The master-scene stage is now good enough to anchor the sequence.
- `master-scene/candidate-02.jpeg` passed with a reusable layout.
- Identity, scene layout, and fixed props are much more stable than in the old episode-002 cut.

## What Failed

### Shot 001 Candidate 01

Main failure:
- camera drift and tight reframing
- beat evidence missing

Observed gate result:
- `overall_score = 0.38`
- `identity_score = 0.94`
- `scene_score = 0.62`
- `prop_score = 0.91`
- `camera_score = 0.18`
- `beat_score = 0.15`

Interpretation:
- the protagonist and room are largely correct
- the shot still fails because it no longer reads as the opening wide beat
- the electrical anomaly is not visible enough to count as story information

### Shot 001 Candidate 02

Main failure:
- the beat itself is still not legible enough, even when continuity is better

Observed gate result:
- best frame stayed below pass threshold
- one reviewed frame opened a refrigerator door, which is a forbidden change
- another kept identity and set continuity but still failed because the wide composition tightened and the electrical anomaly was not visible

Interpretation:
- the current `shot-001` beat is under-designed for the model
- "one refrigerator light goes dark" is too subtle relative to the amount of wide-scene continuity we are also forcing

## Director-Level Diagnosis

This confirms a more important point than the old `episode-002` review:

1. The earlier pipeline accepted continuity-safe shots that were not dramatically readable.
2. The new pipeline now catches that problem early.
3. The current first beat is still too weak and too subtle to survive generation.

This is not only a model-quality issue.
It is also a shot-design issue.

The scene is trying to do all of these at once:
- preserve a locked wide aisle composition
- preserve protagonist floor mark
- preserve store geography
- preserve room props
- preserve character visibility from head to upper legs
- add a tiny refrigerator-light anomaly

That last event is visually too small.
The model can keep the person and room stable, but the dramatic event does not dominate enough to survive the render.

## Required Fixes

### 1. Redesign Shot 001 beat

Replace the current beat:
- `one refrigerator door light goes dark`

With a more legible first anomaly such as one of:
- one whole refrigerator bay flickers noticeably darker for a beat
- a strong reflected flicker runs across the refrigerator doors
- one ceiling light above the aisle flickers while the refrigerator wall remains readable

The event must be readable in a locked wide shot.

### 2. Tighten camera instruction further

For `shot-001`, add stronger negative framing constraints:
- no push-in
- no tighter crop than master scene
- keep ceiling light band visible
- keep full refrigerator top line visible

The current "avoid close-up framing" rule is directionally correct but not strong enough.

### 3. Use a stronger opening event hierarchy

The first three beats should progress like this:

1. clearly readable light anomaly
2. reaction hold on same anomaly
3. physical clue on the floor

Right now beat 1 is weaker than beat 3.
That reverses the scene's tension curve.

### 4. Treat final render as suspect even after keyframe pass

The EP003 test reinforces the EP002 finding:
- passing candidate stills are necessary
- they are not sufficient

Final formal shots still require their own gate.

## Recommendation

Do not continue into shots 002 to 006 yet.

First fix `shot-001` in the spec:
- enlarge the anomaly
- strengthen anti-crop constraints
- preserve the locked wide geometry

Only after `shot-001` passes should the sequence continue.
