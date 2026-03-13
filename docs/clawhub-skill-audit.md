# ClawHub Skill Audit For AI Video Skills

Date: 2026-03-12

## Goal

Review external skills for patterns that improve this project's AI short-drama skills without breaking the repo's subtractive prompting and chain-reference workflow.

## Skills inspected

### Strongly relevant

- `storyboard-creation`
- `cinematic-script-writer`
- `video-production`
- `seedance-guide`
- `seedance-prompt-en`

### Useful but not central

- `photography`
- `cine-cog`
- `video-cog`

## What was imported

### From `storyboard-creation`

- shot vocabulary
- camera angle vocabulary
- camera movement vocabulary
- 180-degree rule awareness
- panel / shot-card mindset

### From `cinematic-script-writer`

- better cinematography language
- stronger lighting and lens vocabulary
- production-minded framing of beats and emotion

### From `video-production`

- approval-ledger mindset
- review and revision discipline
- treating bridgeability and editability as first-class concerns

### From `seedance-guide` and `seedance-prompt-en`

- explicit reference-role thinking
- time segmentation for shots or beats
- camera verbs that are clearer than generic prompt prose

## What was rejected

### Rejected pattern: full re-description in every shot

Several generic cinematic skills encourage repeating the full character and set description in every prompt. That is incompatible with this repo.

Why it fails here:

- increases prompt pollution
- reopens locked identity and set facts
- encourages drift across chained shots

This repo works better when:

- master scene owns locked facts
- shot delta owns only the allowed change
- bridge frame carries continuity between clips

## Resulting repo changes

- `skills/chain-referenced-shortform-video/SKILL.md`
  - upgraded from continuity-only workflow to continuity + film-language + review skill
- `skills/chain-referenced-shortform-video/references/film-language.md`
  - added shot-card, blocking, lens, movement, geography guidance
- `skills/chain-referenced-shortform-video/references/review-rubric.md`
  - added gate and failure-triage rubric
- `skills/chain-referenced-shortform-video/references/repo-mapping.md`
  - added mapping from film-language concepts to current YAML fields

## Remaining gaps

- no automated review scoring for staging readability or screen-direction breaks yet
- no example episode spec uses explicit `shot_card` fields yet
- no CLI scaffold writes shot-card values back into the episode YAML yet

## Best next additions

1. Add review checks for geography, blocking readability, and cut compatibility.
2. Add a CLI scaffold that writes shot-card placeholders back into the episode YAML.
3. Add an example episode spec that uses explicit `shot_card` fields end to end.
4. Add a CLI command that prints a per-shot preproduction checklist before rendering.
