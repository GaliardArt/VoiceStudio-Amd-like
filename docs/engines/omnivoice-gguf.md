# VoiceStudio — OmniVoice GGUF Engine

OmniVoice GGUF runs the same OmniVoice model as the [default
engine](omnivoice.md), but through a native binary
(`bin/omnivoice-tts-<platform>`) loading quantized GGUF weights. It is
hardware-adaptive: a probe picks the quantization that fits your machine, so
small GPUs and CPU-only hosts get a working OmniVoice instead of a paging,
timing-out one.

## When to pick it

- Your GPU is below the default engine's 6 GB VRAM floor.
- CPU-only machines that still want OmniVoice's voice and language coverage.
- You want generation isolated in a separate process (a crash or leak never
  takes the app down — each generation spawns the binary fresh).

## Quantization selection

Weights come from the `Serveurperso/OmniVoice-GGUF` HuggingFace repo, pinned
to an exact revision. The hardware probe selects:

| Hardware | Quant | Approx. VRAM use |
| --- | --- | --- |
| 12 GB+ VRAM | BF16 | ~1.6 GB (quality-first) |
| 4–12 GB VRAM | Q8_0 | ~945 MB (recommended balance) |
| 1–4 GB VRAM | Q4_K_M | ~659 MB (minimal footprint) |
| CPU-only | Q4_K_M | RAM-bound, latency-tolerable |

You can override the selection from Settings; overrides are allow-listed
against the same table (an F32 reference quant, ~3.2 GB, is override-only).

## Setup

The desktop installers (Windows, macOS, Linux packages) do **not** ship this
native binary yet, so on an installed app the engine shows *Unavailable* in
Model Catalogue ([#2780](https://github.com/debpalash/VoiceStudio/issues/2780)).
Use the default in-process OmniVoice engine, which is the same model, or run
from a source checkout and build the binary for your platform (below). Once
`bin/omnivoice-tts-<platform>` exists, select the engine via **Model Catalogue**
(TTS tab → **Use**) or `OMNIVOICE_TTS_BACKEND=omnivoice-gguf`. The quant weights
download on first use (see [downloading-models.md](../downloading-models.md)) —
install them ahead of time from **Model Catalogue (TTS tab → the engine's
Weights)** if you want the first generation to be quick; a long first render is
the download, not a hang.

**Source checkouts:** the repo ships zero-byte placeholders in `bin/` — real
binaries come from CI (`build-omnivoice-tts`) or a local build. The engine detects a placeholder and
reports unavailable with instructions
([#1172](https://github.com/debpalash/VoiceStudio/issues/1172)) instead of
failing at spawn time; build one with
`scripts/build-omnivoice-tts.sh --platform <slug>` or use the default
in-process engine.

**Linux ARM64 (Asahi Apple Silicon):** the `linux-aarch64` binary prefers
GGML's Vulkan backend when built on a host with `glslc` and the Khronos
SPIRV headers installed (Arch: `pacman -S shaderc spirv-headers`; Debian:
`apt install glslc libvulkan-dev spirv-headers`), so Apple GPUs accelerate
generation through the open-source Honeykrisp driver. Without those deps the
build falls back to CPU. Expect roughly 2–4x slower generation than macOS
Metal while upstream Mesa and llama.cpp Vulkan optimizations mature; still
well ahead of CPU-only.

## AMD Radeon Vulkan proof of concept

The default GGUF build remains unchanged. For an **experimental** Vulkan
build on Windows x86_64 or Linux x86_64, use a source checkout and pass
`--backend vulkan` to the pinned runtime build script:

```bash
scripts/build-omnivoice-tts.sh \
  --platform windows-x86_64 \
  --commit-sha 886fc079838ca7400cb2b42b36e2a65aa1daabe8 \
  --backend vulkan
```

On Linux, replace the platform with `linux-x86_64`. The build machine needs a
working C++ toolchain, CMake, the Vulkan SDK/development headers, and shader
compiler dependencies required by GGML Vulkan. The build is intentionally
opt-in and fails if the Vulkan configuration or compilation fails; it does
not silently label a CPU build as Vulkan.

**Important:** enabling Vulkan at compile time is only the first gate. The
installed Vulkan driver must expose the Radeon device, the runtime must
successfully load the model, and inference must actually offload work to the
GPU. Validate those separately with runtime logs/device diagnostics and a
real synthesis. The pinned runtime logs the selected backend at load time;
its low-level selector also supports `GGML_BACKEND=Vulkan0` to force the
first registered Vulkan device during a diagnostic run. This override is
intentionally not set by default: if that device is absent, initialization
can fail rather than falling back automatically. Remove the override to
return to automatic backend selection.

A detected adapter or a successful build alone is not proof of acceleration.
Older GPUs such as Polaris/RX 580 and newer Radeon families must be tested
individually; memory capacity, driver version, operating system and model
workload can change the result. CPU fallback remains the safe recovery path.

This is an engineering proof of concept, not a claim that every AMD GPU is
supported or that performance/quality has been validated. The GGUF model's
separate licensing terms still apply; a Vulkan build does not change them.

## Integrity and self-healing

Before reporting ready, the engine:

- verifies the binary against the SHA-256 manifest (`bin/checksums.sha256`);
- detects macOS Gatekeeper quarantine and prints the exact
  `xattr -cr '/Applications/VoiceStudio.app'` fix;
- restores a missing execute bit (a git clone or zip extract on POSIX can
  drop `+x`, which used to surface as a permission error mislabeled as
  out-of-memory — [#437](https://github.com/debpalash/VoiceStudio/issues/437)).
  The chmod runs only after the SHA check confirms it's the right file.

## Behaviour notes

- Output is 24 kHz mono — same model, same rate as in-process OmniVoice.
- Cloning from a reference clip (with optional transcript) and style
  instructions are supported; no voice design.
- Same multilingual surface as OmniVoice ([languages.md](../languages.md)).
- Because generation runs in another process, the app's own GPU counters
  don't see its allocations — diagnostics label it accordingly.

| Variable | Default | Meaning |
| --- | --- | --- |
| `OMNIVOICE_GGUF_GENERATE_TIMEOUT_S` | (generous built-in) | Per-generation timeout for the spawned binary |

## Troubleshooting

- "GGUF binary missing": the installer doesn't include the runtime (see
  Setup) — use the default engine, or build the binary from a source checkout.
  The log line `Engine health check failed; engine=omnivoice-gguf` withholds the
  reason by design; a missing binary is the usual cause on an installed app.
- Checksum mismatch or quarantine messages: follow the printed fix, or
  reinstall.
- Other issues: [install/troubleshooting.md](../install/troubleshooting.md).

See also: [benchmarks.md](../benchmarks.md),
[performance.md](../performance.md), [disk usage](disk-usage.md).
