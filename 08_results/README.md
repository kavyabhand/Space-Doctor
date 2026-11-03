# 08 · Results

> 34 broken Spaces work again, each verified by calling its API and reviewed by a person.

## Outcomes

| Outcome | Spaces |
|---|---|
| Treated by Beam | 222 |
| **Revived and verified** | **34** (3,425 likes) |
| Boots, inference unverified | 53 |
| Beam: "unfixable" | 71 |
| Not revived | 58 |
| Rejected at review | 6 |

Hardware: 18 of the treated Spaces ran on an NVIDIA A10G; the rest under cpu-basic limits.

## Every revival

| Space | Likes | Hardware | Fix | What the revived app returned | PR |
|---|---|---|---|---|---|
| [bookbot/Image-Upscaling-Playground](https://huggingface.co/spaces/bookbot/Image-Upscaling-Playground) | 873 | CPU | code: `app.py` | a 2x upscale of the Space's own example | [open](https://huggingface.co/spaces/bookbot/Image-Upscaling-Playground/discussions/7) |
| [daspartho/prompt-extend](https://huggingface.co/spaces/daspartho/prompt-extend) | 423 | CPU | code: `app.py` | an extended prompt | [open](https://huggingface.co/spaces/daspartho/prompt-extend/discussions/22) |
| [mms-meta/MMS](https://huggingface.co/spaces/mms-meta/MMS) | 277 | A10G | lockfile 2024-09-01 | with the Space's own Burmese clip and 'mya (Burmese)' selected: a Burmese-script transcript | [open](https://huggingface.co/spaces/mms-meta/MMS/discussions/7) |
| [kadirnar/Video-Diffusion-WebUI](https://huggingface.co/spaces/kadirnar/Video-Diffusion-WebUI) | 265 | A10G | lockfile 2024-03-15 + code: `video_diffusion/damo/damo_text2_video.py` | a generated video | [open](https://huggingface.co/spaces/kadirnar/Video-Diffusion-WebUI/discussions/14) |
| [clem/Image_Face_Upscale_Restoration-GFPGAN](https://huggingface.co/spaces/clem/Image_Face_Upscale_Restoration-GFPGAN) | 131 | CPU | lockfile 2024-01-15 | restored image returned | [open](https://huggingface.co/spaces/clem/Image_Face_Upscale_Restoration-GFPGAN/discussions/5) |
| [tomg-group-umd/pez-dispenser](https://huggingface.co/spaces/tomg-group-umd/pez-dispenser) | 130 | A10G | lockfile 2024-08-01 | an optimized hard prompt for the Space's own sample image (PEZ prompts are deliberately odd-looking) | [open](https://huggingface.co/spaces/tomg-group-umd/pez-dispenser/discussions/9) |
| [stabilityai/stablelm-2-1_6b-zephyr](https://huggingface.co/spaces/stabilityai/stablelm-2-1_6b-zephyr) | 115 | CPU | lockfile 2024-06-01 | a coherent chat reply from the model | [open](https://huggingface.co/spaces/stabilityai/stablelm-2-1_6b-zephyr/discussions/9) |
| [SRDdev/Image-Caption](https://huggingface.co/spaces/SRDdev/Image-Caption) | 108 | CPU | lockfile 2024-06-15 + code: `app.py` | a correct caption of the Space's own example1.jpg | [open](https://huggingface.co/spaces/SRDdev/Image-Caption/discussions/3) |
| [nateraw/background-remover](https://huggingface.co/spaces/nateraw/background-remover) | 104 | CPU | code: `app.py` | the background cleanly removed from the Space's own example photo | [open](https://huggingface.co/spaces/nateraw/background-remover/discussions/2) |
| [adirik/OWL-ViT](https://huggingface.co/spaces/adirik/OWL-ViT) | 89 | CPU | lockfile 2023-03-10 | with the query 'astronaut, rocket, flag' on the Space's own example image: boxes drawn around the flag and the | [open](https://huggingface.co/spaces/adirik/OWL-ViT/discussions/5) |
| [mikonvergence/theaTRON](https://huggingface.co/spaces/mikonvergence/theaTRON) | 86 | A10G | lockfile 2024-07-15 + code: `src/synthesis.py` | a generated image | [open](https://huggingface.co/spaces/mikonvergence/theaTRON/discussions/3) |
| [havas79/Real-ESRGAN_Demo](https://huggingface.co/spaces/havas79/Real-ESRGAN_Demo) | 74 | CPU | pins | upscaled image returned | [open](https://huggingface.co/spaces/havas79/Real-ESRGAN_Demo/discussions/6) |
| [Amrrs/openai-whisper-live-transcribe](https://huggingface.co/spaces/Amrrs/openai-whisper-live-transcribe) | 68 | CPU | lockfile 2023-06-15 | a test tone transcribed | [open](https://huggingface.co/spaces/Amrrs/openai-whisper-live-transcribe/discussions/1) |
| [microsoft/wavlm-speaker-verification](https://huggingface.co/spaces/microsoft/wavlm-speaker-verification) | 50 | CPU | lockfile 2023-07-15 | the speaker-similarity result for two audio clips | [open](https://huggingface.co/spaces/microsoft/wavlm-speaker-verification/discussions/2) |
| [microsoft/unispeech-speaker-verification](https://huggingface.co/spaces/microsoft/unispeech-speaker-verification) | 49 | CPU | lockfile 2023-07-15 + code: `app.py` | but no pull request was opened; adding sox to packages.txt would have been the closer fix. | – |
| [danielsapit/JPEG_Artifacts_Removal](https://huggingface.co/spaces/danielsapit/JPEG_Artifacts_Removal) | 48 | CPU | lockfile 2023-07-15 + code: `app.py` | before/after images | [open](https://huggingface.co/spaces/danielsapit/JPEG_Artifacts_Removal/discussions/5) |
| [nielsr/CLIPSeg](https://huggingface.co/spaces/nielsr/CLIPSeg) | 46 | CPU | lockfile 2023-03-01 | a segmentation map for the Space's own example image | [open](https://huggingface.co/spaces/nielsr/CLIPSeg/discussions/6) |
| [rendchevi11/nix-tts](https://huggingface.co/spaces/rendchevi11/nix-tts) | 40 | CPU | lockfile 2021-12-15 | 2021-12-15; no code changed. Streamlit render check: the app page loads with no error box. | [open](https://huggingface.co/spaces/rendchevi11/nix-tts/discussions/3) |
| [obi/Medical-Note-Deidentification](https://huggingface.co/spaces/obi/Medical-Note-Deidentification) | 39 | CPU | lockfile 2023-10-01 | on a realistic note: PATIENT, DATE, HOSPITAL, STAFF and PHONE spans all tagged | [open](https://huggingface.co/spaces/obi/Medical-Note-Deidentification/discussions/3) |
| [nielsr/vilt-vqa](https://huggingface.co/spaces/nielsr/vilt-vqa) | 37 | CPU | pins + code: `app.py` | 'How many cats are there?' on the Space's own cats.jpg returns '2' | [open](https://huggingface.co/spaces/nielsr/vilt-vqa/discussions/2) |
| [arcee-ai/mergekit-config-generator](https://huggingface.co/spaces/arcee-ai/mergekit-config-generator) | 35 | CPU | lockfile 2024-05-15 | a generated merge config | [open](https://huggingface.co/spaces/arcee-ai/mergekit-config-generator/discussions/2) |
| [johko/capdec-image-captioning](https://huggingface.co/spaces/johko/capdec-image-captioning) | 34 | CPU | lockfile 2023-01-15 | 'A man holding a cell phone up to the side of his head.' for the Space's own example | [open](https://huggingface.co/spaces/johko/capdec-image-captioning/discussions/36) |
| [swzamir/Restormer](https://huggingface.co/spaces/swzamir/Restormer) | 33 | CPU | lockfile 2023-11-01 + code: `app.py` | a restored image | [open](https://huggingface.co/spaces/swzamir/Restormer/discussions/10) |
| [Huage001/LinFusion-SD-v1.5](https://huggingface.co/spaces/Huage001/LinFusion-SD-v1.5) | 32 | CPU | lockfile 2024-09-01 | an image-to-image result | [open](https://huggingface.co/spaces/Huage001/LinFusion-SD-v1.5/discussions/2) |
| [hynt/F5-TTS-Vietnamese-100h](https://huggingface.co/spaces/hynt/F5-TTS-Vietnamese-100h) | 30 | CPU | pins | synthesized speech | [open](https://huggingface.co/spaces/hynt/F5-TTS-Vietnamese-100h/discussions/5) |
| [yhshin/latex-ocr](https://huggingface.co/spaces/yhshin/latex-ocr) | 29 | CPU | lockfile 2024-09-20 + code: `app.py` | LaTeX read from the Space's own example image | – |
| [menghanxia/disco](https://huggingface.co/spaces/menghanxia/disco) | 25 | CPU | lockfile 2023-11-01 | a colorized image | – |
| [flax-sentence-embeddings/sentence-embeddings](https://huggingface.co/spaces/flax-sentence-embeddings/sentence-embeddings) | 24 | CPU | lockfile 2023-07-20 + code: `backend/inference.py` | jaxlib cannot be installed). Streamlit render check: the app page loads with no error box. | – |
| [Geonmo/laion-aesthetic-predictor](https://huggingface.co/spaces/Geonmo/laion-aesthetic-predictor) | 23 | CPU | lockfile 2023-01-15 | an aesthetic score of 6.77 for the Space's own example | – |
| [stable-diffusion-ai/OLD_upscaling](https://huggingface.co/spaces/stable-diffusion-ai/OLD_upscaling) | 23 | CPU | lockfile 2024-07-15 + code: `app.py` | an upscaled image | – |
| [dt/ascii-art](https://huggingface.co/spaces/dt/ascii-art) | 22 | CPU | code: `app.py` | an image and its ASCII art | – |
| [JayRaghav/Image_segmentation](https://huggingface.co/spaces/JayRaghav/Image_segmentation) | 21 | CPU | pins + code: `app.py` | a segmented image | – |
| [keras-io/Object-Detection-Using-RetinaNet](https://huggingface.co/spaces/keras-io/Object-Detection-Using-RetinaNet) | 21 | CPU | lockfile 2023-11-01 | detections drawn on a test image | – |
| [kevinwang676/E2-F5-TTS](https://huggingface.co/spaces/kevinwang676/E2-F5-TTS) | 21 | CPU | lockfile 2024-10-01 | synthesized speech | – |

The fix column: **lockfile** means Beam asked for a fully pinned `requirements.txt` resolved as of that date;
**pins** means it edited `requirements.txt` by hand; **code** lists the source files it changed. Every patch also
pins `python_version` in the README to the interpreter we verified with. Full diffs and outputs are in the
[gallery](../10_gallery) and the [SpaceRot dataset](https://huggingface.co/datasets/kavyabhand/spacerot).

## Pull requests

We opened a pull request for each approved revival with 30 or more likes (patches for the rest are in the dataset).
Each contains only the changed files and the evidence: the error, Beam's diagnosis, how we tested, and what the
app returned.

| Space | Pull request |
|---|---|
| adirik/OWL-ViT | [#5](https://huggingface.co/spaces/adirik/OWL-ViT/discussions/5) |
| Amrrs/openai-whisper-live-transcribe | [#1](https://huggingface.co/spaces/Amrrs/openai-whisper-live-transcribe/discussions/1) |
| arcee-ai/mergekit-config-generator | [#2](https://huggingface.co/spaces/arcee-ai/mergekit-config-generator/discussions/2) |
| bookbot/Image-Upscaling-Playground | [#7](https://huggingface.co/spaces/bookbot/Image-Upscaling-Playground/discussions/7) |
| clem/Image_Face_Upscale_Restoration-GFPGAN | [#5](https://huggingface.co/spaces/clem/Image_Face_Upscale_Restoration-GFPGAN/discussions/5) |
| danielsapit/JPEG_Artifacts_Removal | [#5](https://huggingface.co/spaces/danielsapit/JPEG_Artifacts_Removal/discussions/5) |
| daspartho/prompt-extend | [#22](https://huggingface.co/spaces/daspartho/prompt-extend/discussions/22) |
| havas79/Real-ESRGAN_Demo | [#6](https://huggingface.co/spaces/havas79/Real-ESRGAN_Demo/discussions/6) |
| Huage001/LinFusion-SD-v1.5 | [#2](https://huggingface.co/spaces/Huage001/LinFusion-SD-v1.5/discussions/2) |
| hynt/F5-TTS-Vietnamese-100h | [#5](https://huggingface.co/spaces/hynt/F5-TTS-Vietnamese-100h/discussions/5) |
| johko/capdec-image-captioning | [#36](https://huggingface.co/spaces/johko/capdec-image-captioning/discussions/36) |
| kadirnar/Video-Diffusion-WebUI | [#14](https://huggingface.co/spaces/kadirnar/Video-Diffusion-WebUI/discussions/14) |
| microsoft/wavlm-speaker-verification | [#2](https://huggingface.co/spaces/microsoft/wavlm-speaker-verification/discussions/2) |
| mikonvergence/theaTRON | [#3](https://huggingface.co/spaces/mikonvergence/theaTRON/discussions/3) |
| mms-meta/MMS | [#7](https://huggingface.co/spaces/mms-meta/MMS/discussions/7) |
| nateraw/background-remover | [#2](https://huggingface.co/spaces/nateraw/background-remover/discussions/2) |
| nielsr/CLIPSeg | [#6](https://huggingface.co/spaces/nielsr/CLIPSeg/discussions/6) |
| nielsr/vilt-vqa | [#2](https://huggingface.co/spaces/nielsr/vilt-vqa/discussions/2) |
| obi/Medical-Note-Deidentification | [#3](https://huggingface.co/spaces/obi/Medical-Note-Deidentification/discussions/3) |
| rendchevi11/nix-tts | [#3](https://huggingface.co/spaces/rendchevi11/nix-tts/discussions/3) |
| SRDdev/Image-Caption | [#3](https://huggingface.co/spaces/SRDdev/Image-Caption/discussions/3) |
| stabilityai/stablelm-2-1_6b-zephyr | [#9](https://huggingface.co/spaces/stabilityai/stablelm-2-1_6b-zephyr/discussions/9) |
| swzamir/Restormer | [#10](https://huggingface.co/spaces/swzamir/Restormer/discussions/10) |
| tomg-group-umd/pez-dispenser | [#9](https://huggingface.co/spaces/tomg-group-umd/pez-dispenser/discussions/9) |

| File | What it is |
|---|---|
| [`report.py`](report.py) | Builds `summary.json` from the census, case files, baseline and reviews |
| [`summary.json`](summary.json) | Every headline number |
| [`prs.json`](prs.json) | The pull requests we opened |

**Next:** [09 · Honesty →](../09_honesty)
