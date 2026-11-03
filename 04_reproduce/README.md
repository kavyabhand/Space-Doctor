# 04 · Reproduce

> A Space is only a patient if it still fails when we rebuild it, untouched.

## A Spaces-like rebuild

[`sandbox.py`](sandbox.py) rebuilds a Space in Docker following the documented Spaces recipe:

1. `python:<version>` base image, from the README's `python_version`, else the version visible in Hugging Face's
   own traceback, else 3.10
2. apt packages from `packages.txt`
3. `pip install -r requirements.txt`
4. then the SDK at the README's `sdk_version` (gradio or streamlit) and `spaces`, **installed after the
   requirements**, as Spaces does. This order matters: the SDK install can silently re-upgrade a pin, so Beam is
   shown this exact Dockerfile.
5. boot under cpu-basic limits (2 vCPU, 16 GB), or on an NVIDIA A10G for GPU Spaces, and wait for HTTP 200

Deviation, documented: CPU Spaces build with CPU torch wheels (same Python API, no multi-GB CUDA libraries).

## Picking patients

[`reproduce.py`](reproduce.py) takes code-level failures from the census (CPU Gradio or Streamlit Spaces whose log
shows a traceback, minus platform, secret and quota failures) and rebuilds each one.

| | Spaces |
|---|---|
| Rebuilt | 239 |
| **Still broken in our rebuild** | **223** |
| Same exception as Hugging Face's log | 88 |
| Started fine (Hugging Face's failure was transient) | 16, left alone |

Most of the rest have "rotted further" since Hugging Face last built them: they now fail earlier, on a newer
incompatibility. Both kinds are real patients.

## Safety

Thousands of strangers' apps ran on our machines. The instances had no cloud credentials, and containers were
blocked from the instance metadata service.

**Next:** [05 · Repair with Beam →](../05_repair_with_beam)
