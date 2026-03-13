# Asset-Driven Shortform Workflow

## Why the earlier approach failed

Generating three prompts and hoping the model preserves everything is not how the stronger short-form AI creators work.

The failure pattern we observed was:

- keyframes drifted before video even started
- props and room layout changed between shots
- the protagonist was treated as "similar style" instead of a fixed asset
- long narrative jumps created too many moving variables

## Working method

Build reusable visual assets first, then generate shots from those assets.

The prompt system should use a five-dimension scan for every shot:

- subject and motion
- environment and light
- medium and rendering
- temporal state
- camera optics

Only the dimensions that are still "open" should be described in text.
Everything already locked by a reference image or asset pack should be omitted from delta prompts.

The minimal stack should be:

1. character pack
2. scene pack
3. prop pack
4. shot template pack
5. keyframe gate
6. short video generation
7. frame QA and repair

## Asset packs

### Character pack

Must lock:

- face
- hair
- body silhouette
- jacket / hoodie / pants / boots
- watch / pendant / gloves

### Scene pack

Must lock:

- room type
- camera-safe layout
- fixed background objects
- lighting rig
- color temperature
- allowed camera positions

### Prop pack

Must lock:

- corpse state variants
- report sheet
- recorder
- tray trolley
- autopsy table

### Shot template pack

Must define:

- lens / framing
- actor blocking
- visible prop set
- change allowed in this shot
- change forbidden in this shot

## Correct production order

1. build packs
2. generate candidate master-scene frames
3. reject any master-scene frame with pack drift
4. generate shot-delta draft clips from the approved master-scene reference with subtractive prompts
5. extract candidate frames from each draft clip
6. reject any shot-delta keyframe that changes non-whitelisted details
7. generate final 3-5 second clips
8. select a bridge frame from the tail of clip `n`
9. submit clip `n+1` with the bridge frame as `first_frame` and the approved shot keyframe as `last_frame`
10. sample frames
11. score identity and scene continuity
12. regenerate only the failing stage

## Gate rules

Do not move from keyframe stage to video stage unless:

- protagonist identity is stable
- wardrobe and accessories are stable
- scene layout is stable
- required props are stable
- only story-state deltas change across shots

## What changes between shots

In a good single-scene sequence, only these should change:

- pose
- expression
- one story-state prop
- one supernatural event state

Everything else should stay fixed.
