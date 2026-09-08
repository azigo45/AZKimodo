# Kimodo for Windows — one-file installer

**One `.bat` file. Double-click. Type a prompt, get a character animation.**

`kimodo.bat` takes a bare Windows machine to a working [kimodo.cpp](https://github.com/localai-org/kimodo.cpp) — the community C++/GGML port of NVIDIA's **Kimodo** text-to-motion model — running on the GPU through Vulkan, with the web demo open in your browser.

Built by **Alexander Antonov — AzRigTool**.

---

## Quick start

1. Download **`kimodo.bat`** from the [latest release](../../releases/latest) — or from this repository.
2. Put it anywhere (the Desktop is fine) and **double-click it**.
3. Press **Enter** when it asks where to install. Say **Yes** to the two or three Windows permission prompts.
4. Wait. The first run downloads about **19 GB** of model weights and compiles the engine — expect the best part of an hour on a decent connection.
5. The browser opens by itself when the demo is ready.

**Every run after that** finds the installation, skips all of it, and opens the demo in a few seconds.

Leave the window open while you use the demo — it *is* the server. Close it to stop.

## What it installs

Everything that is missing, and only that. Anything already on the machine is detected and skipped.

| Step | What | How |
|---|---|---|
| 1 | Git (with Git Bash), Python 3.12, curl | winget |
| 2 | Visual Studio 2022 Build Tools — C++ workload + CMake/Ninja | official bootstrapper, silent |
| 3 | Vulkan SDK | winget |
| 4 | `huggingface_hub` (the `hf` download client) | pip |
| 5 | kimodo.cpp source + ggml submodule | git clone |
| 6 | Model weights: SOMA RP v1.1 + the Llama-3 text encoder (~19 GB) | `hf`, checksum-verified, retried up to 12× |
| 7 | Release build with Vulkan (falls back to CPU if no SDK) | CMake + Ninja |
| 8 | Go (runs the web demo) | winget |
| 9 | Start the demo, open the browser | — |

Default install folder: `<drive of the .bat>\kimodo.cpp`. You can type another at the prompt, or drag a folder onto the `.bat` in Explorer.

## Requirements

- Windows 10 or 11, 64-bit, with **winget** (App Installer — ships with Windows 11 and current Windows 10).
- About **30 GB** free: 19 for the weights, the rest for the compiler, source and build.
- Internet. Hugging Face throttles anonymous downloads; if you have an account, `set HF_TOKEN=hf_...` in the same window before running speeds things up. Optional.
- A GPU with Vulkan drivers for fast generation. Without one it still works on the CPU, just much slower.

Tested on Windows 11 with a Russian locale and a user name containing Cyrillic and a space — paths like that are handled.

## Usage

```
kimodo.bat                    double-click: install if needed, then run the demo
kimodo.bat D:\somewhere       install into / run from a specific folder
kimodo.bat D:\somewhere 8095  ...and use a specific port (default 8090, walks upward if busy)
```

The demo is the upstream kimodo.cpp web UI: pick a model, type an English prompt (`A person runs forward and reaches out`), press Generate, watch the skeleton move, download an animated GLB.

## If something goes wrong

**The window stays open no matter what** — the last lines tell you which step failed and why. Nothing is deleted on failure. **Run the file again**: it resumes from where it stopped, keeping every finished download and build.

- *Weights failed after 12 attempts* — Hugging Face throttling. Run again later; only what is missing is fetched.
- *Running on the CPU* — the Vulkan SDK was not found at build time. Install it from [vulkan.lunarg.com](https://vulkan.lunarg.com/sdk/home), delete `<install folder>\build`, run again.
- *"vcvars64.bat missing"* — Visual Studio Build Tools is present but without the C++ workload. Open the Visual Studio Installer → Modify → tick **Desktop development with C++**.
- *Cannot find the repository* — it searches all drives; if your checkout lives somewhere unusual, drag the folder onto the `.bat`, or type the path at the prompt. The answer is remembered in `kimodo-path.txt` next to the `.bat`.

## Notes

- Not affiliated with NVIDIA or LocalAI. This is an installer for their work.
- [kimodo.cpp](https://github.com/localai-org/kimodo.cpp) is Apache-2.0. The model weights are published by NVIDIA under the [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) (SOMA and G1 models; the SMPL-X model is non-commercial and is not downloaded).
- The `.bat` is plain ASCII with CRLF line endings on purpose — `cmd` cannot find labels in a file saved with LF. If you edit it, keep CRLF.

## Changelog

- **2.1.3** — author line in the banner and window title.
- **2.1.2** — comments stripped from the script.
- **2.1.1** — a drive root (`C:\`) or a non-empty folder at the prompt now means "a `kimodo.cpp` folder inside it".
- **2.1.0** — four fixes from an adversarial review: a bracket in the compiler path (`Program Files (x86)`) aborted the file; Python's scripts folder came back unreadable on a Cyrillic user name; the CPU-build remedy did nothing; Git Bash was only looked for under Program Files.
- **2.0.x** — installer and demo launcher merged into one file; fast path; window kept open on error; install folder remembered.

## License

MIT — see [LICENSE](LICENSE).

---

## Кратко по-русски

Один файл `kimodo.bat`. Двойной клик. Первый запуск ставит всё, чего нет — Git, Python, компилятор Visual Studio, Vulkan SDK, Go, исходники, ~19 ГБ весов — и собирает движок; это около часа. Каждый следующий запуск находит установку и за секунды открывает демо в браузере: пишешь промпт по-английски, получаешь анимацию персонажа.

Окно не закрывать — это сервер. Если что-то упало, окно останется открытым с причиной; повторный запуск продолжит с места остановки. Нужно ~30 ГБ на диске и Windows 10/11 с winget. Кириллица и пробелы в имени пользователя — не проблема.

Сборка: **Alexander Antonov — AzRigTool**.
