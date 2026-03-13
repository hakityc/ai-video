# Tomb-Raider Female Episode 004 Review

## Result

This version is structurally better than Episode 003.
The story is now a coherent single mini-chapter instead of three chapter jumps.

## What improved

- one location instead of three unrelated locations
- one short action chain with clear escalation
- stronger visual continuity in keyframes
- better cinematic framing with `16:9`

## What still failed

- shot-002 contains sampled frames where the protagonist face is cropped or partially missing
- pendant and accessory details still drift
- the current VLM review pipeline over-penalizes cropped frames and is not yet a reliable hard gate

## Practical assessment

By human inspection, Episode 004 is a better continuity test than Episode 003.
The clips feel like one short scene.
But it still needs:

- tighter face visibility in shot-002
- a better identity-checking method than the current single-anchor VLM comparison
