# Third-party notices

AZKimodo is MIT-licensed (see [LICENSE](LICENSE)). It builds on, includes material from, or downloads the following. Full license texts are in [`licenses/`](licenses/).

## Included in this repository

**kimodo.cpp** — Apache License 2.0, LocalAI contributors. https://github.com/localai-org/kimodo.cpp

- The skeleton definitions in `maya/azkimodo/az_kimodo_gen.py` (`SOMA30`, `G1SKEL34`: joint names, parent links, rest offsets) are copied from kimodo.cpp `demo/skeletons_extra.go`, which in turn copies NVIDIA Kimodo's Apache-2.0 skeleton definitions; the offsets are parent-local differences of NVIDIA's neutral-joint assets. Those tables remain under Apache-2.0 — [`licenses/Apache-2.0.txt`](licenses/Apache-2.0.txt), notices in [`licenses/kimodo.cpp-NOTICE.txt`](licenses/kimodo.cpp-NOTICE.txt).
- The `.kmdp` pose-file format and the motion-representation layout the Maya tool writes are interfaces of `kmd-constrain`, not copied code.

## Included in the release archive `kimodo-win64-vulkan.zip`

Binaries compiled from the [azigo45/kimodo.cpp](https://github.com/azigo45/kimodo.cpp) fork. Redistributed under their own licenses, whose texts travel inside the archive:

- **kimodo.cpp** (`kmd-generate`, `kmd-constrain`, `kmd-encode`, `kmd-inspect`) — Apache License 2.0. Modified from upstream; the modifications are listed in the fork's commit history and marked in the changed files.
- **ggml** (`ggml.dll`, `ggml-base.dll`, `ggml-cpu.dll`, `ggml-vulkan.dll`) — MIT License, Copyright (c) 2023-2026 The ggml authors. https://github.com/ggml-org/ggml

## Downloaded by `kimodo.bat`, not redistributed here

The installer fetches these from their publishers. By running it you obtain them under **their** terms, which you should read:

- **Kimodo SOMA RP v1.1 / SOMA SEED v1.1 / G1 RP v1 / G1 SEED v1** motion models — NVIDIA, under the [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/), as GGML conversions published by LocalAI (`LocalAI-io/Kimodo-*-GGML`). Commercially usable; outputs are yours. Only SOMA RP v1.1 is downloaded by default.
- **Kimodo SMPL-X RP v1** — NVIDIA Internal Scientific Research and Development Model License (non-commercial, no derivative redistribution). **Not downloaded** and not selectable for that reason.
- **Text encoder bundle** (`LocalAI-io/Llama-3-Kimodo-GGML`) — converted from Meta Llama-3-8B-Instruct with McGill LLM2Vec adapters (MIT). **Built with Meta Llama 3.** Subject to the [Meta Llama 3 Community License](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct); the bundle carries `LICENSE-META-LLAMA-3.txt` and `NOTICE`.
- **kimodo.cpp source** (the fork) — Apache-2.0, cloned by git.
- **huggingface_hub** — Apache-2.0, installed by pip.

## Installed by `kimodo.bat` under their vendors' terms

The installer runs these vendors' installers unattended (`winget --accept-package-agreements`, the Visual Studio bootstrapper with `--passive`). **Running `kimodo.bat` accepts these license agreements on your behalf**, exactly as clicking through them would:

- Microsoft Visual Studio 2022 Build Tools — Microsoft Software License Terms
- LunarG Vulkan SDK — LunarG SDK license (MIT / Apache-2.0 components)
- Git for Windows — GPL-2.0
- Python 3.12 — PSF License
- Go — BSD-3-Clause

## Trademarks

"Kimodo" is NVIDIA's model name and "Llama" is Meta's. They are used here only to describe what this software installs and works with. This project is not affiliated with, endorsed by, or sponsored by NVIDIA, Meta, or LocalAI.

## Author

Installer, Maya tool, documentation: © 2026 Alexander Antonov (AzRigTool), MIT.
