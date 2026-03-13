# Qiao Ning Episode 002 Postmortem

## Scope

- Final cut: `/Users/lebo/project/ai-video/artifacts/output/qiao-ning/episode-002/episode-002-cut.mp4`
- Formal manifest: `/Users/lebo/project/ai-video/artifacts/video/seedance-rollout/qiao-ning/episode-002/manifest.json`
- Episode spec: `/Users/lebo/project/ai-video/examples/episodes/qiao-ning-ep002.yaml`
- Full contact sheet: `/Users/lebo/project/ai-video/artifacts/review/qiao-ning/episode-002/full/full-cut-contact-sheet.jpg`
- Shot storyboard: `/Users/lebo/project/ai-video/artifacts/review/qiao-ning/episode-002/storyboard.jpg`

## High-Level Judgment

The current cut is acceptable as a continuity engineering demo, but not as a story-faithful short drama scene.

The main issue is not raw identity drift. The protagonist, wardrobe, and overall store location remain mostly stable.
The larger failure is that the generated shots do not consistently execute the intended story beats from the outline, so the episode reads like a sequence of related visual states rather than a clearly escalating incident.

## Expected Beat vs Actual Beat

### Shot 001

Expected:
- Qiao Ning notices a refrigerator-side anomaly.
- The first beat should establish the locked room and the small disturbance.

Actual:
- This beat works.
- The locked-off aisle setup is clear, and the subtle hand/attention change reads correctly.

### Shot 002

Expected:
- Same dark refrigerator light remains off.
- Qiao Ning freezes and narrows her gaze, increasing tension without changing position.

Actual:
- This mostly works.
- The emotional escalation is visible, but the beat is still visually close to shot 001, so the progression is present but weak.

### Shot 003

Expected:
- Qiao Ning looks down.
- A dropped instant noodle cup appears near the aisle floor.

Actual:
- This works well.
- The new floor clue reads clearly and the protagonist response remains coherent.

### Shot 004

Expected:
- Qiao Ning looks toward the entrance.
- Wet footprints appear from the door toward the aisle.
- The shot should escalate fear while preserving camera continuity and body continuity.

Actual:
- This is the biggest failure point.
- The camera collapses into a low, partial-body framing.
- The protagonist appears barefoot in the selected beat, which breaks wardrobe continuity and scene logic.
- The fear beat becomes ambiguous because attention shifts from "entrance threat" to "feet on floor."
- This is where the episode stops feeling like one locked shot sequence.

### Shot 005

Expected:
- Eye-line shifts toward the cashier counter.
- A receipt strip extends from the till.

Actual:
- The protagonist returns to a stronger aisle composition, but the causal bridge from shot 004 is weak because shot 004 already broke framing continuity.
- The receipt beat is present, but not visually dominant enough to land as the main event.

### Shot 006

Expected:
- The till display glows on.
- Qiao Ning raises the phone slightly and realizes the store is "answering back."

Actual:
- The pose and expression work, but the counter-display payoff is not visually forceful enough.
- The emotional ending reads as "checking phone in store" more than "silent confirmation of supernatural response."

## Root Causes

### 1. The workflow optimized continuity harder than narrative salience

The system is now good at keeping the protagonist and store in roughly the same place.
But the text deltas are too subtle and too evenly weighted, so the model often preserves the scene while under-expressing the actual dramatic change.

### 2. Shot 004 required a stronger structural constraint than the current shot-delta gate enforces

The gate allowed shot 004 candidate 02 because it matched enough of the intended change, but the selected frame still introduced a low-angle, partial-body read that damages sequence readability.
The existing gate is too tolerant of frames that are technically similar but narratively wrong.

### 3. The story outline and the generated visual beat sheet are not aligned strongly enough

The current YAML spec describes allowed changes, but it does not define what the viewer must clearly perceive in each shot.
That is why some beats are "technically present" but not cinematically legible.

### 4. The project is still carrying a wrong identity anchor

The formal manifest still points `anchor_local` to:
- `/Users/lebo/project/ai-video/assets/characters/tomb-raider-female/reference/front.jpeg`

Even though this episode is Qiao Ning.
The rendered result survived this, but it is still a pipeline bug and weakens downstream QA trust.

## Concrete Problems to Fix

1. Replace the global anchor for this episode with a Qiao Ning-specific approved reference pack.
2. Add a "beat legibility" gate per shot, not just identity/scene/prop/camera continuity.
3. Forbid partial-body or feet-dominant framings in locked-shot episodes unless explicitly requested.
4. Add shot-level required evidence checks:
   - shot 003 must clearly show the dropped cup
   - shot 004 must clearly show both the entrance and the wet footprints
   - shot 005 must clearly show the extended receipt strip
   - shot 006 must clearly show the till display glow and the phone raise
5. Strengthen shot 004 prompt and template constraints so the camera cannot collapse downward.

## Recommended Solution Plan

### Phase 1: Correct the asset foundation

1. Replace `anchor_local` for this episode with Qiao Ning references only.
2. Simplify Qiao Ning accessory requirements so the model does not waste capacity on irrelevant identity details.
3. Update the convenience-store prop pack to mark "bare feet" and "low-angle floor framing" as explicit forbidden drift.

### Phase 2: Upgrade the shot gate

1. Add a new review dimension: `beat_score`.
2. Require each shot to declare:
   - `must_show`
   - `must_not_hide`
   - `forbidden_compositions`
3. Reject any candidate where the main dramatic evidence is not plainly visible.

### Phase 3: Rebuild shot 004 as the keystone shot

1. Keep shots 001 to 003 as near-baseline.
2. Re-generate shot 004 until it satisfies:
   - same camera height as shot 003
   - full protagonist torso visible
   - entrance door visible
   - wet footprints clearly readable
   - shoes/boots preserved
3. Only after shot 004 is fixed, regenerate shots 005 and 006 using shot 004 as the actual bridge parent.

### Phase 4: Add outline-faithfulness review

Create a post-render check that compares:
- intended beat text from the episode spec
- selected shot keyframe
- final rendered video representative frames

The output should score not only continuity, but also:
- whether the beat is visible
- whether the beat is the dominant event in frame
- whether the emotional escalation reads in the intended order

## Bottom Line

This cut proves the pipeline can now generate and chain six shots into one finished artifact.
But it does not yet prove that the system can faithfully adapt a narrative outline into a clear dramatic sequence.

The failure is concentrated in shot 004 and in the absence of a story-legibility gate.
