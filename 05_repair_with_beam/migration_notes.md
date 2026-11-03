Common reasons Spaces that used to work now fail on rebuild. Spaces reinstalls unpinned dependencies at their
latest versions on every rebuild, so old code meets new libraries.

### gradio
- 4.0 removed `gr.inputs.*` / `gr.outputs.*` (use `gr.Textbox`, `gr.Image`, ...), `.style(...)`, `gr.Box`
  (use `gr.Group`), `gr.Variable` (use `gr.State`), `gr.Image(source=..., tool=...)` (now `sources=[...]`).
- `launch(enable_queue=...)` and `Interface(enable_queue=...)` were removed; call `.queue()` instead.
- `queue(concurrency_count=N)` was removed in 4.0; use `queue(default_concurrency_limit=N)`.
- `Interface(allow_flagging=...)` was renamed `flagging_mode` in 5.0.
- `gr.update(...)` in place of `gr.Component.update(...)` (the classmethod `.update` was removed in 4.0).
- 6.0 moved app-level options such as `css` from the `Blocks`/`Interface` constructor to `launch()` (gradio prints
  a UserWarning naming them), and `allow_flagging` is no longer accepted. Check the warning text in the log.
- Spaces whose README pins the newest `sdk_version` get gradio 6 even if the code was written for 3.x.
- In 5.x, `gr.Chatbot` defaults changed; tuple-format history is deprecated in favour of `type="messages"`.
- Old gradio 3.x pins can break against newer `huggingface_hub`, `httpx` (0.28 removed `proxies=`),
  `pydantic` 2, `fastapi`/`starlette`, or `jinja2`. Either pin those transitive packages or bump `sdk_version`.
- gradio's `audioop`: Python 3.13 removed the stdlib `audioop` module; pydub falls back to `pyaudioop`.
  Fix: add `audioop-lts` to requirements (provides `audioop` on 3.13+) or pin `python_version: "3.10"`.

### huggingface_hub
- 1.0 removed `cached_download` (use `hf_hub_download`), `HfFolder` (use `get_token` / `login`),
  `Repository` (use `HfApi.upload_*` / `snapshot_download`), `InferenceApi` (use `InferenceClient`), and the
  `use_auth_token=` argument (use `token=`). Libraries that import these (old diffusers, old gradio,
  old sentence-transformers) need upgrading or `huggingface_hub<1.0` pinned.

### torch / torchvision
- torch 2.6 made `torch.load(weights_only=True)` the default; old checkpoints raise
  `UnpicklingError` / `WeightsUnpickler error`. For a checkpoint the Space author trusts, pass
  `weights_only=False`, or pin `torch<2.6`.
- torchvision 0.17 removed `torchvision.transforms.functional_tensor` (breaks `basicsr`, used by GFPGAN /
  Real-ESRGAN). Patch the import to `torchvision.transforms.functional` or pin `torchvision<0.17`.

### numpy
- numpy 2 breaks extensions compiled against numpy 1 (`numpy.core.multiarray failed to import`,
  `numpy.dtype size changed`, `_ARRAY_API not found`). Pin `numpy<2` unless the extensions are upgraded.
- `np.float`, `np.int`, `np.bool`, `np.object` were removed in 1.24; use the builtins.

### others
- `datasets` 3/4 removed `LargeList` re-exports and changed loading scripts (`trust_remote_code`).
- `openai` 1.0 removed `openai.ChatCompletion`/`openai.Completion` (use the client object).
- `transformers` drops long-deprecated modules and kwargs; pin to the version era of the code if it fails on import.
- `setuptools` 80+ no longer provides `pkg_resources` in some setups; pin `setuptools<81` if `pkg_resources` is missing.
- `tomli`: Python 3.11+ has `tomllib`; on 3.10 `tomli` must be installed explicitly if a package expects it.
