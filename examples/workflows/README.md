# ComfyUI workflow template notes

The file `comfyui_i2v_template.json` is only a patchable placeholder.

For a real run:

1. build a working image-to-video graph in ComfyUI
2. use `File -> Export (API)` in the ComfyUI UI
3. replace the placeholder JSON with that exported workflow
4. update the `workflow_overrides` node ids in the job YAML

The control-plane code expects an API workflow JSON and then patches node inputs such as:

- input image name
- positive prompt
- negative prompt
- seed
- output filename prefix

