# Project Structure

## Goal

Keep content grouped by character or output type so the repository stays usable once multiple protagonists and many shots exist.

## Layout

### Character assets

- `assets/characters/<slug>/reference/`
  - approved reference stills only
- `assets/characters/<slug>/generation.json`
  - source prompts and generation metadata for those stills

### Character configs

- `examples/characters/<slug>.yaml`
  - the working character bible for prompts and jobs

### Scene packs

- `examples/scenes/*.yaml`
  - fixed reusable location packs

### Prop packs

- `examples/props/*.yaml`
  - reusable prop definitions and allowed state changes

### Shot templates

- `examples/shot-templates/*.yaml`
  - locked framing, blocking, and allowed shot deltas

### Shot configs

- `examples/jobs/*.yaml`
  - runnable shot/job definitions
- `examples/episodes/*.yaml`
  - episode or chapter specs that reference reusable packs

### Story docs

- `docs/stories/<slug>.md`
  - story world, pilot beat, and first-shot targets tied to a character or concept

### Rendered media

- `artifacts/video/<provider>/<group-or-slug>/`
  - generated videos and their task metadata

Current examples:

- `artifacts/video/seedance/text-to-video/`
- `artifacts/video/seedance/tomb-raider-female/`

## Rule of thumb

Do not create flat directories like `assets/reference` once there is more than one character.
Always group new assets under the relevant character slug.
Do not start a new sequence from raw prompts if the scene pack and shot template do not exist.
