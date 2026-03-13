# Tomb-Raider Female Episode 001 Review

## What was generated

Three consecutive `image-to-video` shots were generated with the same anchor image using `doubao-seedance-1-5-pro-251215`.

Files:

- `artifacts/video/seedance/tomb-raider-female/episode-001/shot-001/`
- `artifacts/video/seedance/tomb-raider-female/episode-001/shot-002/`
- `artifacts/video/seedance/tomb-raider-female/episode-001/shot-003/`

## What this validates

- The account can run a high-end hosted video model end-to-end
- A single character anchor can drive multiple consecutive shots
- Episode-level organization and manifesting now work

## What is still not fully validated

- Frame-level face consistency scoring is not wired yet
- Automatic visual review is not implemented yet
- Cross-shot continuity is inferred from shared anchor and prompt constraints, but still needs human review of the rendered clips

## Current assessment

This is a valid first continuity test because:

- all three shots use the same anchor image
- outfit and lighting constraints were held constant
- the shots progress through one coherent tomb scene

The next technical step should be:

1. sample frames from each clip
2. compare them against the anchor image with face similarity scoring
3. flag drift before moving to longer episodes

