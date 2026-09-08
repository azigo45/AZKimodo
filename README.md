# AZKimodo — Kimodo text-to-motion for Windows and Maya

**Type a sentence, get a character animation — on your own GPU, baked onto your own rig.**

AZKimodo is the complete build around [kimodo.cpp](https://github.com/localai-org/kimodo.cpp), the community C++/GGML port of NVIDIA's **Kimodo** text-to-motion diffusion model. Three parts, one author:

| Part | What it is | Where |
|---|---|---|
| **`kimodo.bat`** | One-file Windows installer and launcher. Bare machine → GPU build → web demo in the browser. | this repo, [Releases](../../releases/latest) |
| **Engine fork** | kimodo.cpp with pose-constrained generation (`kmd-constrain`), hard pinning, weighted masks and a ~5× faster denoiser. | [azigo45/kimodo.cpp](https://github.com/azigo45/kimodo.cpp) |
| **AZ Kimodo Motion** | Maya tool: generate from text, retarget onto an Advanced Skeleton rig, pin poses read off the rig, hold them, regenerate. | `maya/azkimodo/` in this repo |

Built by **Alexander Antonov — AzRigTool**. Not affiliated with NVIDIA or LocalAI.

---

## 1. Install everything: `kimodo.bat`

1. Download **`kimodo.bat`** from the [latest release](../../releases/latest).
2. Put it anywhere and **double-click**. Press **Enter** at the folder prompt. Say **Yes** to the Windows permission prompts.
3. Wait — the first run installs what is missing and downloads about **19 GB** of weights. Expect the best part of an hour.
4. The browser opens on the demo when it is ready. **Every later run opens it in seconds.**

Leave the window open while you use the demo; it *is* the server.

<details>
<summary>What it installs, step by step</summary>

| Step | What | How |
|---|---|---|
| 1 | Git (with Git Bash), Python 3.12, curl | winget |
| 2 | Visual Studio 2022 Build Tools — C++ workload + CMake/Ninja | official bootstrapper, silent |
| 3 | Vulkan SDK | winget |
| 4 | `huggingface_hub` (the `hf` download client) | pip |
| 5 | The engine fork + ggml submodule | git clone |
| 6 | Weights: SOMA RP v1.1 + the Llama-3 text encoder (~19 GB), checksum-verified, retried up to 12× | `hf` |
| 7 | Release build with Vulkan (CPU fallback if no SDK) — includes `kmd-constrain` | CMake + Ninja |
| 8 | Go (runs the web demo) | winget |
| 9 | Start the demo, open the browser | — |

Anything already present is detected and skipped. Default folder: `<drive of the .bat>\kimodo.cpp`; a drive letter or a non-empty folder at the prompt means "a `kimodo.cpp` folder inside it".

</details>

**Requirements:** Windows 10/11 x64 with winget, ~30 GB free, internet, a Vulkan-capable GPU for speed (CPU works, slowly). Non-ASCII user names are fine.

**Usage:** `kimodo.bat` — or `kimodo.bat D:\folder 8095` to pick the folder and port.

**Prebuilt binaries:** `kimodo-win64-vulkan.zip` in the release holds `kmd-generate`, `kmd-constrain`, `kmd-encode`, `kmd-inspect` and the ggml DLLs, if you would rather not compile. Unpack into your checkout; weights still come from `kimodo.bat`.

## 2. The engine fork: what changed

[azigo45/kimodo.cpp](https://github.com/azigo45/kimodo.cpp) is upstream `main` plus one commit, four files:

- **`kmd-constrain`** (new) — generate *through* poses supplied from outside. Reads a `.kmdp` file: frames, world rotations per joint, root, and a per-element mask. Because the mask is per element, a pin can be a whole pose, the root row alone (follow a path, invent the gait), the feet, or an arm chain. Writes the text embedding beside the take so the next solve with the same prompt skips the 15 GB encoder.
- **Hard pinning** — `sample_motion_from_noise_conditioned` gains `project_observed`: masked channels of the clean prediction are forced back onto their observed values every step. Conditioning alone is a soft pull; projection makes a pin exact. Measured: a pinned key pose reproduced at 0.000 cm.
- **Weighted masks** — the mask is a float, not a flag. A fractional weight blends the pinned value with the prediction, which is what lets a held span ease in and out instead of switching on between two frames.
- **One denoiser graph** — the transformer used to build 18 per-layer GGML graphs on every denoising step. They are one graph now: **~5× faster on Vulkan (RTX 4080), output bit-identical.**

Apache-2.0, as upstream.

## 3. The Maya tool: AZ Kimodo Motion

`maya/azkimodo/` — two files, Maya 2025, PySide6/PySide2.

**Install:** copy the `azkimodo` folder into `Documents\maya\2025\scripts\` (or anywhere on Maya's Python path). Then in the Script Editor:

```python
from azkimodo import az_kimodo_gen_qt
az_kimodo_gen_qt.show()
```

The tool finds the engine on its own: `$AZ_KIMODO_ROOT` if set, otherwise the first `kimodo.cpp` checkout on any drive — which is wherever `kimodo.bat` put it.

**What it does**

- **Generate** from a text prompt (several segments with transitions), at your scene's frame rate, non-blocking — Maya stays responsive while the GPU solves.
- **Retarget** the take onto a rig. Ships with maps for the UE5 Mannequin skeleton and for an Advanced Skeleton rig built on it: animation is baked onto the **FK controls**, root travel goes on the `Main` control, limbs are switched to FK for the bake and switched back when you clear.
- **Pose pins.** Pose the rig at a frame, press *Pose*, and the next generation has to pass through that pose. Modes: whole pose, exact, root only, feet, hands, hands locked, upper body, lower body. A pin can **hold** across a span — a hand grabs something and stays. A ghost skeleton shows each pin on its frame.
- **Regenerate** as many times as you like: edit a pin, re-read the pose, solve again, the take replaces the previous one on the rig. Round-trip measured at 0.0000° across all mapped joints — reading a pose off the rig and writing it back does not drift.
- **Honest defaults, measured.** Hard pinning is off unless a mode needs it, because on a 20-frame hold it held the arm no better than soft pinning and lurched 130 cm in one frame where soft moved 36. Eased holds fade in and out over three frames. Travel between pins is filled with root-only pins so the character walks the distance instead of loitering and bolting.

**Versioning:** the tool prints its version in the window title and in every log line (`[AZ Kimodo Motion 1.29.0]`).

## If something goes wrong

- **Installer:** the window stays open with the reason; run the file again and it resumes. *Weights failed after 12 attempts* → Hugging Face throttling, run again later. *Running on the CPU* → install the Vulkan SDK, delete `<folder>\build`, run again. *"vcvars64.bat missing"* → Visual Studio Installer → Modify → **Desktop development with C++**.
- **Maya tool:** *no bind pose was recorded* → put the rig at bind and press *Remember bind pose*. *the rig carries animation, so its bind pose cannot be measured* → retarget a take once, or *Clear rig animation* while at bind. Pins captured with an older version carry that version's reference; re-read them with *Pose*.

## Licenses and credits

- Installer and Maya tool: **MIT** ([LICENSE](LICENSE)), © Alexander Antonov (AzRigTool).
- Engine: [kimodo.cpp](https://github.com/localai-org/kimodo.cpp) by LocalAI contributors, **Apache-2.0**; the fork keeps its license and notices.
- Model: **Kimodo** by NVIDIA. SOMA and G1 weights under the [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/); the SMPL-X model is non-commercial and is not downloaded.
- The `.bat` is ASCII with CRLF on purpose — `cmd` cannot find labels in a file saved with LF.

## Changelog

- **2.2.0** — the complete build: engine fork published, installer clones it (so `kmd-constrain` is built), Maya tool published as the `azkimodo` package (1.29.0), prebuilt Windows binaries attached.
- **2.1.x** — installer: fixes from an adversarial review (bracket in the compiler path aborted the file; Python scripts folder unreadable on a Cyrillic user name; CPU-build remedy; Git Bash location), drive-root prompt, comments stripped, author line.
- **2.0.x** — installer and launcher merged into one file; fast path; window kept open on error; folder remembered.

---

## Кратко по-русски

Полная сборка text-to-motion Kimodo под Windows: **один установщик** `kimodo.bat` (двойной клик — через час GPU-сборка и демо в браузере, потом за секунды), **форк движка** с генерацией через заданные позы (`kmd-constrain`), жёстким пиннингом и слитым графом денойзера (~5× быстрее, бит в бит), и **инструмент для Maya**: генерация из текста, ретаргет на риг Advanced Skeleton с запеканием в контролы, пины поз, снятые прямо с рига, холды, перегенерация без дрейфа.

Установка Maya-части: папку `maya/azkimodo` в `Documents\maya\2025\scripts\`, в Script Editor — `from azkimodo import az_kimodo_gen_qt; az_kimodo_gen_qt.show()`.

Сборка: **Alexander Antonov — AzRigTool**.
