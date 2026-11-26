<img src="maya/azkimodo/az_kimodo_logo.png" width="64" alt="AZ Kimodo Motion">

# AZKimodo — Kimodo text-to-motion for Windows and Maya

**Type a sentence, get a character animation — on your own GPU, baked onto your own rig.**

AZKimodo is the complete build around [kimodo.cpp](https://github.com/localai-org/kimodo.cpp), the community C++/GGML port of NVIDIA's **Kimodo** text-to-motion diffusion model. Three parts, one author:

| Part | What it is | Where |
|---|---|---|
| **`kimodo.bat`** | One-file Windows installer and launcher. Bare machine → GPU build → web demo in the browser. | this repo, [Releases](../../releases/latest) |
| **Engine fork** | kimodo.cpp with pose-constrained generation (`kmd-constrain`), hard pinning, weighted masks and a ~5× faster denoiser. | [azigo45/kimodo.cpp](https://github.com/azigo45/kimodo.cpp) |
| **AZ Kimodo Motion** | Maya tool: generate from text or from poses you key by hand, bake onto an Advanced Skeleton rig or an AZ Body Rig (FK or IK), correct the poses on the timeline, recalculate. | [AZ Tools](https://aztools.xyz) library, or `azkimodo-maya-1.50.1.zip` in [Releases](../../releases/latest); source in `maya/azkimodo/` |

Built by **Alexander Antonov — AzRigTool**. Download more of my tools at **[aztools.xyz](https://aztools.xyz)**. Not affiliated with NVIDIA or LocalAI.

**Installing for Maya takes two steps:** run `kimodo.bat` once ([section 1](#1-install-the-engine-kimodobat)), then install the Maya tool from [AZ Tools](https://aztools.xyz) or copy it by hand ([section 3](#3-the-maya-tool-az-kimodo-motion)). From AZ Tools it comes with KIMO, a ready rigged character, and the window opens with it ([Your character](#your-character)).

---

## 1. Install the engine: `kimodo.bat`

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
| 6 | Weights: SOMA RP v1.1 + the Llama-3 text encoder (~19 GB, at a pinned revision), checksum-verified, retried up to 12× | `hf` |
| 7 | Release build with Vulkan (CPU fallback if no SDK) — includes `kmd-constrain` | CMake + Ninja |
| 8 | Go (runs the web demo) | winget |
| 9 | Start the demo, open the browser | — |

Anything already present is detected and skipped. Default folder: `<drive of the .bat>\kimodo.cpp`; a drive letter or a non-empty folder at the prompt means "a `kimodo.cpp` folder inside it".

</details>

**Requirements:** Windows 10/11 x64 with winget, ~30 GB free, internet, a Vulkan-capable GPU for speed (CPU works, slowly). Non-ASCII user names are fine.

**Usage:** `kimodo.bat` — or `kimodo.bat D:\folder 8095` to pick the folder and port.

**Prebuilt binaries:** `kimodo-win64-vulkan.zip` in the release holds `kmd-generate`, `kmd-constrain`, `kmd-encode`, `kmd-inspect` and the ggml DLLs, if you would rather not compile. Unpack into your checkout; weights still come from `kimodo.bat`.

## 2. The engine fork: what changed

[azigo45/kimodo.cpp](https://github.com/azigo45/kimodo.cpp) is upstream `main` plus these changes:

- **`kmd-constrain`** (new) — generate *through* poses supplied from outside. Reads a `.kmdp` file: frames, world rotations per joint, root, and a per-element mask. Because the mask is per element, a pin can be a whole pose, the root row alone (follow a path, invent the gait), the feet, or an arm chain. Writes the text embedding beside the take so the next solve with the same prompt skips the 15 GB encoder.
- **Hard pinning** — `sample_motion_from_noise_conditioned` gains `project_observed`: masked channels of the clean prediction are forced back onto their observed values every step. Conditioning alone is a soft pull; projection makes a pin exact. Measured: a pinned key pose reproduced at 0.000 cm.
- **Weighted masks** — the mask is a float, not a flag. A fractional weight blends the pinned value with the prediction, which is what lets a held span ease in and out instead of switching on between two frames.
- **One denoiser graph** — the transformer used to build 18 per-layer GGML graphs on every denoising step. They are one graph now: **~5× faster on Vulkan (RTX 4080), output bit-identical.**
- **Step progress** — with `KIMODO_PROGRESS` set, the solver reports each denoising step, which drives the progress bar in Maya.

Apache-2.0, as upstream.

## 3. The Maya tool: AZ Kimodo Motion

Developed on Maya 2025 for Windows. Needs the engine from section 1.

### Install

**From AZ Tools (easiest).** Install [AZ Tools](https://aztools.xyz) — drag its installer into Maya and sign in, the account is free. On the **Animation** tab of the AZ Tools library install **AZ Kimodo Motion**: one install brings the tool and KIMO, a ready character. The tool appears in the AZ Tools menu, and updates come through AZ Tools.

**By hand:**

1. Download **`azkimodo-maya-1.50.1.zip`** from the [latest release](../../releases/latest) and unpack it.
2. Copy the **`azkimodo`** folder into `Documents\maya\2025\scripts\`. You should end up with `Documents\maya\2025\scripts\azkimodo\az_kimodo_gen.py`.
3. Start or restart Maya.
4. Open the Script Editor, paste this into a **Python** tab and run it:

```python
from azkimodo import az_kimodo_gen_qt
az_kimodo_gen_qt.show()
```

The window opens with `v1.50.1` in its header.

**Shelf button:** open the shelf you want it on and run this once. A button with the tool's icon appears there.

```python
from azkimodo import az_kimodo_gen_qt
az_kimodo_gen_qt.install_shelf_button()
```

The tool finds the engine by itself: `AZ_KIMODO_ROOT` if you set that environment variable, otherwise the first `<drive>:\kimodo.cpp` it sees, which is the default folder of `kimodo.bat`. Installed somewhere else? Set `AZ_KIMODO_ROOT` to that folder and restart Maya.

**To update:** replace the `azkimodo` folder and restart Maya.

**Ready character:** the copy by hand comes without one; install AZ Kimodo Motion from [AZ Tools](https://aztools.xyz) instead for KIMO — see [Your character](#your-character).

### Your character

The tool drives rigs it recognises by name:

- **Advanced Skeleton** controls: `RootX_M`, `FKChest_M`, `FKWrist_L`, `FKKnee_R`, `FKToes_L`, and the rest of the standard set.
- **AZ Body Rig** controls: `C_main_CTRL`, `C_root_CTRL`, `C_chest_FK_CTRL`, `L_wrist_FK_CTRL`, `R_knee_FK_CTRL`, `L_ball_FK_CTRL`, and the rest. Any spine length works.
- **UE5 Mannequin** skeleton: `pelvis`, `spine_05`, `clavicle_l`, `thigh_r`, `ball_l`, and the rest.

**KIMO, a ready character.** KIMO, an android on AZ Body Rig, comes free with **[AZ Tools](https://aztools.xyz)** — the installer and manager of my Maya tools:

1. Download AZ Tools from [aztools.xyz](https://aztools.xyz), drag its installer into Maya and sign in (the account is free).
2. In the AZ Tools library, on the **Animation** tab, install **AZ Kimodo Motion** — KIMO comes inside the same package.
3. Open AZ Kimodo Motion from the AZ Tools menu in an empty scene: KIMO comes in, is measured and becomes the target on its own.

Without AZ Tools no rig comes with the tool. **Your own rig:** open its scene first and the tool picks the rig up when its window opens. Otherwise press **Change...** in CHARACTER, then pick the rig file and press **Load**, or select any node of the rig and press **Use selected**. The rig should stand in its bind pose when it first arrives, because that pose becomes the reference for every bake.

### Use it

1. **Generate.** On the **PROMPT** tab write a prompt in English, third person, naming the side: *A person throws a fast front kick with their right leg and plants the foot back down.* Choose **Bake to** — FK controls, or IK for the legs, the arms and, on AZ Body Rig, the spine — then press **GENERATE MOTION**. Maya stays responsive while the GPU works, and the take lands on the controls. **Bake to** can be changed afterwards without generating again.
2. **Read the poses.** Set the step and press **ANALYZE POSES**. The frames are marked on the timeline and the pose list opens.
3. **Correct them.** Click a pose to go to its frame, adjust the controls and press **Update**. **New pose here** adds a pose on the current frame, **Delete** removes the selected one.
4. **Place the character with `Main`.** Drag it on the ground and the character goes there and stays. Lift it for a jump, or turn on **Main stays at this height** for a step up. Turn it and the character faces that way from that pose on.
5. **Press RECALCULATE.** The take is solved again through your poses, with the same prompt and seed, and baked onto the controls.

**Pose accuracy** in the pose list sets how closely the poses you edited are followed: 100 hits them, easing in and out over half a second around each one; 0 keeps what the model made. Lower it if the motion looks forced around a pose. It applies only to poses you edited, and takes effect when you press RECALCULATE.

A pose whose hips were turned round by accident while the IK hands stayed put is refused with an explanation: turn `Main` to turn the character.

### Pose to pose

The **POSE TO POSE** tab, next to PROMPT, is animation by hand with no prompt.

1. Open the tab. The timeline is set to the frames a take can cover, from frame 1 on; the old range returns when you go back to PROMPT.
2. Go to a frame, pose the character with its controls and press **New pose here**. The pose is listed in the tab and keyed on every channel you moved, and on every channel that was already animated.
3. Click a pose to go back to it — it is put on the character again, where it stood — adjust it and press **Update**, or **Delete** it together with its keys.
4. With two poses or more, press **GENERATE MOTION**. The motion between them is filled in, from frame 1 to the last pose, and baked. **Pose accuracy** sets how closely the poses are hit.

Afterwards the poses are the take's pose list, so ANALYZE POSES and RECALCULATE carry on from there. The poses are stored on the rig and come back when the scene is opened again.

The **?** button in the header opens the built-in help.

### Limits

- One take is at most 150 frames (5 seconds at the model's 30 Hz). Chain longer actions with **+ Add segment**; on POSE TO POSE the timeline is held to that length.
- Prompts are English only.
- Pose accuracy does not keep a sideways pelvis shift relative to `Main`, and feet may slide a little in the half second around a strongly corrected pose.
- The prebuilt `kimodo-win64-vulkan.zip` predates step progress: the bar shows activity rather than a percentage. A fresh `kimodo.bat` install builds the current fork and shows percentages; an older checkout needs `git pull` and a rebuild.

## If something goes wrong

- **Installer:** the window stays open with the reason; run the file again and it resumes. *Weights failed after 12 attempts* → Hugging Face throttling, run again later. *Running on the CPU* → install the Vulkan SDK, delete `<folder>\build`, run again. *"vcvars64.bat missing"* → Visual Studio Installer → Modify → **Desktop development with C++**.
- **GENERATE MOTION is grey and the window says `text bundle missing`:** `kimodo.bat` older than 2.2.1 finished without the text encoder, which its publisher moved on 2026-10-29. Download the current `kimodo.bat` and run it on the same folder. It fetches the missing 15 GB. You can also fetch them by hand: `hf download LocalAI-io/Llama-3-Kimodo-GGML --revision 3e8d958803beaddb6011ac534f2be972e2710c7d --include "generated/llm2vec-text-bundle/*" --local-dir <engine folder>`.
- **`No module named azkimodo`:** the folder is in the wrong place, or Maya has not been restarted since it was copied. Check the path in Install, step 2.
- **The window says the install root or `kmd-generate` was not found:** run `kimodo.bat`, or set `AZ_KIMODO_ROOT` as described above.
- **No character is found:** your rig's control names differ from those listed in *Your character* — or, for KIMO, AZ Kimodo Motion was copied by hand instead of installed from AZ Tools.
- **"the rig carries animation, so its bind pose cannot be measured":** press **Change...** in CHARACTER, then **Clear rig animation**; or put the rig at bind and press **Remember bind pose** there.
- **A solve stopped and the generated skeleton stayed in the scene:** press Ctrl+Z or generate again, and send the Script Editor output with your report.

## Licenses and credits

Full notices and license texts: [THIRD_PARTY.md](THIRD_PARTY.md) and [`licenses/`](licenses/).

- Installer and Maya tool: **MIT** ([LICENSE](LICENSE)), © Alexander Antonov (AzRigTool). The skeleton tables inside the Maya tool are copied from kimodo.cpp and stay **Apache-2.0**.
- Engine: [kimodo.cpp](https://github.com/localai-org/kimodo.cpp) by LocalAI contributors, **Apache-2.0**; the fork keeps its license and NOTICE, and marks the files it changed. The prebuilt binaries carry the Apache-2.0 and ggml (**MIT**) license texts inside the archive.
- Models — downloaded by the installer from their publishers, **not redistributed here**: Kimodo SOMA / G1 by NVIDIA under the [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) (commercially usable, outputs are yours); the SMPL-X model is non-commercial and is not downloaded; the text encoder is **built with Meta Llama 3** under the [Meta Llama 3 Community License](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct).
- **Running `kimodo.bat` accepts third-party license terms on your behalf** — Microsoft Visual Studio Build Tools, LunarG Vulkan SDK, Git for Windows, Python and Go are installed unattended, exactly as if you had clicked through their installers.
- "Kimodo" is NVIDIA's model name, used here only to say what this installs. Not affiliated with NVIDIA, Meta or LocalAI.
- The `.bat` is ASCII with CRLF on purpose — `cmd` cannot find labels in a file saved with LF.

## Changelog

- **2.5.1** — AZ Kimodo Motion 1.50.1: KIMO comes inside the AZ Kimodo Motion package of AZ Tools — one install brings the tool and the character. The hint without a character says so. New download `azkimodo-maya-1.50.1.zip`. Installer and engine unchanged.
- **2.5.0** — AZ Kimodo Motion 1.50.0: KIMO, a ready android on AZ Body Rig, comes free with [AZ Tools](https://aztools.xyz) as **AZ Kimodo Character**; with it installed the window opens with KIMO on the stage, and without a character it says where to get one. Textures of a loaded rig file that are missing on this machine are taken from beside the file. New download `azkimodo-maya-1.50.0.zip`. Installer and engine unchanged.
- **2.4.3** — AZ Kimodo Motion 1.49.4: same tool as 1.49.3, the version now matches the AZ Rig build. New download `azkimodo-maya-1.49.4.zip`. Installer and engine unchanged.
- **2.4.2** — AZ Kimodo Motion 1.49.3: the header shows the tool's own icon, which opens [aztools.xyz](https://aztools.xyz) when clicked; the site link is now a button, *Download more of my tools at aztools.xyz*, under the status line. New download `azkimodo-maya-1.49.3.zip`. Installer and engine unchanged.
- **2.4.1** — AZ Kimodo Motion 1.49.0: an icon of its own, on the window and on a shelf button that `install_shelf_button()` adds; the window keeps to what a newcomer needs, with Advanced settings left out; **Remember bind pose** and **Clear rig animation** moved to CHARACTER → **Change...**; a link to [aztools.xyz](https://aztools.xyz). New download `azkimodo-maya-1.49.0.zip`. Installer and engine unchanged.
- **2.4.0** — AZ Kimodo Motion 1.48.1. Drives AZ Body Rig as well as Advanced Skeleton: FK, IK legs and arms, and an IK spine. New POSE TO POSE tab: key poses by hand and the model fills in the motion between them. Fixes: feet stand flat on rigs whose ankle sits high above a short foot; a keyed FK/IK switch no longer takes a bake out of IK; a pose with the body turned round under IK hands is refused instead of spinning the character; a drag of `Main` keeps the poses placed before it; analyzed poses remember which way `Main` points. New download `azkimodo-maya-1.48.1.zip`. Installer and engine unchanged.
- **2.3.1** — `kimodo.bat` 2.2.1 and the engine fork: the text encoder comes from a pinned revision, because its publisher removed the split files from `main` on 2026-10-29 and installs ended without it. An empty download is now an error, and a machine that was left without the encoder repairs itself on the next run. Maya tool unchanged (1.44.1).
- **2.3.0** — AZ Kimodo Motion 1.44.1: pick-then-edit pose list on the timeline, RECALCULATE, Pose accuracy, IK bake, `Main` keys for jumps, turns and steps up, automatic character pick-up, keeping arms out of the body on cartoon rigs. New download `azkimodo-maya-1.44.1.zip` and step-by-step install. Engine fork reports step progress. `kimodo.bat` itself is unchanged.
- **2.2.0** — the complete build: engine fork published, installer clones it (so `kmd-constrain` is built), Maya tool published as the `azkimodo` package (1.29.0), prebuilt Windows binaries attached.
- **2.1.x** — installer: fixes from an adversarial review (bracket in the compiler path aborted the file; Python scripts folder unreadable on a Cyrillic user name; CPU-build remedy; Git Bash location), drive-root prompt, comments stripped, author line.
- **2.0.x** — installer and launcher merged into one file; fast path; window kept open on error; folder remembered.
