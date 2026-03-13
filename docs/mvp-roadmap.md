# MVP Roadmap

## Milestone 0

Goal: generate one short clip with one fixed character from one approved reference image.

Deliverables:

- character bible for 1 protagonist
- 4-8 approved reference images
- 1 image-to-video workflow
- 1 output clip
- 1 QA report with identity score

Out of scope:

- multi-character shots
- full episode continuity
- automatic repair
- full story-state graph

## Milestone 1

Goal: add identity validation as a gate, not as a manual review habit.

Pipeline:

1. ingest reference pack
2. build reference embeddings with InsightFace
3. generate clip
4. sample frames every N frames
5. score identity similarity
6. produce pass/warn/fail report

Exit criteria:

- same character remains recognizable across sampled frames
- QA output is machine-readable

## Milestone 2

Goal: add targeted repair for failed frames or failed regions.

Pipeline:

1. locate low-score frames
2. generate face/clothes masks with SAM 2
3. run local inpainting only on masked region
4. re-score repaired result

Exit criteria:

- repair preserves body motion and background
- repaired frame passes the identity threshold more often than full regeneration

## Milestone 3

Goal: support cross-shot continuity.

Add:

- shot-end anchor frame generation
- next-shot start seeded from anchor frame
- shared style prompt template
- LUT / global color guidance

Exit criteria:

- shot transition feels visually continuous
- color drift and pose jump are reduced

## Milestone 4

Goal: support cross-episode continuity.

Add:

- story state document
- carry-over of scene, costume, props, injuries, emotion, and timeline state
- script generation constraints from previous ending state

Exit criteria:

- next episode starts from a known state
- continuity mistakes are machine-detectable

## Recommended next build step

If we continue from here, the next concrete implementation should be:

1. scaffold a Python control-plane project
2. define the character bible schema
3. define the generation job schema
4. implement a first QA command around InsightFace
5. connect that QA command to a ComfyUI or Diffusers generation job

