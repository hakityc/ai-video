# Continuity Workflow V2

## Why V1 failed

The first workflow used one static character anchor image for every shot.

That helps identity retention, but it creates two problems:

1. scene transitions feel abrupt because every shot is trying to regrow the world from the same neutral reference
2. the model overfits to the anchor pose/background logic instead of inheriting motion and spatial continuity from the prior shot

## Community-aligned principles

The most useful current workflow pattern is:

- one stable character identity anchor for the episode
- one scene-specific keyframe for each shot
- one transition anchor from the previous shot when narrative continuity matters

In practice:

- character anchor answers: who is this
- scene keyframe answers: where are we now
- transition anchor answers: how did we arrive here

## New generation hierarchy

### Layer 1: Character pack

Use once per episode or once per costume block.

Contains:

- face reference stills
- 3/4 view still
- outfit lock
- identity descriptors

This layer should stay stable.

### Layer 2: Shot keyframe

Generate one dedicated still for each shot before making video.

This keyframe should encode:

- current location
- current lighting
- current camera distance
- current emotional beat
- same character identity

Do not use the exact same keyframe for all shots.

### Layer 3: Transition guidance

For shot `N+1`, use one of these:

- last frame of shot `N`
- a regenerated bridge still derived from shot `N` ending composition
- a match-cut anchor if the scene changes hard

This is what makes cuts feel motivated instead of random.

## Correct shot workflow

### Shot 1

Input:

- character pack
- shot 1 text brief

Output:

- shot 1 keyframe
- shot 1 video
- selected last frame

### Shot 2

Input:

- character pack
- shot 2 text brief
- shot 1 last frame or bridge frame

Output:

- shot 2 keyframe
- shot 2 video
- selected last frame

### Shot 3

Input:

- character pack
- shot 3 text brief
- shot 2 last frame or bridge frame

Output:

- shot 3 keyframe
- shot 3 video

## When scenes change hard

If the next shot changes location significantly:

- exterior ruin -> narrow shaft
- narrow shaft -> flooded chamber

do not force direct reuse of the previous shot keyframe as the only visual input.

Instead:

1. generate a new shot keyframe for the new location
2. keep the same character anchor
3. preserve one compositional or lighting bridge from the previous shot

Examples of bridge signals:

- same flashlight direction
- same body orientation
- same emotional expression
- same dominant color cast

## Recommended prompt split

Each shot prompt should have four blocks:

1. identity block
2. environment block
3. action block
4. camera block

Example:

- identity: `Lin Yue, short ash-blonde bob, brown leather jacket over grey hoodie, black cargo pants, work boots, flashlight`
- environment: `flooded mural chamber, blue ghost fire, black reflective water, ancient painted walls`
- action: `steps forward carefully, turns slightly, breath held`
- camera: `wide cinematic reveal, low-angle dolly-in, grounded realism`

## QA implications

Continuity should be judged at two levels:

### Identity continuity

- face
- hair
- outfit
- props

### Narrative continuity

- does the next shot logically follow the previous one
- does the environment transition make sense
- does the emotional beat escalate correctly

V1 mostly tested identity continuity.
V2 must test both.

## What we should change in this repo

### Before generating an episode

Create:

- `episode manifest`
- `shot briefs`
- `shot keyframe prompts`

### During generation

Store per shot:

- keyframe still
- video clip
- ending frame
- review report

### Folder rule

Under each episode directory add:

- `anchor/`
- `shot-001/`
- `shot-002/`
- `shot-003/`

And inside each shot:

- `keyframe.*`
- `frames/`
- `clip.mp4`
- `review.json`

## Decision

Do not keep using:

- one neutral anchor image -> all shots

Use instead:

- character pack -> per-shot keyframe -> previous-shot transition anchor

