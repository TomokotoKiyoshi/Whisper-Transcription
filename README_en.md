# A multilingual speech-to-text/subtitle system powered by the OpenAI Whisper model

*(Windows GUI Version)*

## Table of Contents

1. [Project Overview](#project-overview)

2. [File Structure](#file-structure)

3. [System Requirements](#system-requirements)

4. [Quick Start](#quick-start)

5. [Whisper Model Guide](#whisper-model-guide)

6. [Adjustable Parameters](#adjustable-parameters)

7. [Output File Formats](#output-file-formats)

8. [FAQ](#faq)

---

## Project Overview

This project provides two independent Windows executable programs. Please download the full `.exe` files from the **Releases** section on the right when needed:

| Program                  | Function                                                               | Features                                                                                                                  |
| ------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **PyTorch_Download.exe** | One-click downloader and verifier for *PyTorch + Whisper* dependencies | Supports both CPU and GPU (CUDA) versions.  Multilingual GUI (Chinese / Japanese / English / Korean)                      |
| **Transcription.exe**    | GUI-based audio transcription and subtitle generator                   | Multilingual interface Auto-download/load Whisper models. Keyword hints, parameter tuning, and real-time progress display |

---

## File Structure

├─PyTorch_Download.exe      # Dependency downloader

├─Transcription.exe       # GUI for audio transcription

├─pytorch_libs\         # Stores offline dependencies after download └─Pycode\            # Source code and build scripts

  ├─PyTorch_Downloader.py      # Downloader source code

   ├─Transcription.py       # Transcription source code

   └─third_party_wheels\     # Optional third-party wheels

> **Note**
> 
> - You only need to use the `Pycode\` folder if you plan to modify or repackage the program yourself. Ignore it for daily `.exe` use.
> 
> - Downloaded dependencies will be extracted to `pytorch_libs\` next to the program for offline use.

---

## System Requirements

| Item           | Description                                                                                    |
| -------------- | ---------------------------------------------------------------------------------------------- |
| OS             | Windows 10/11 64-bit                                                                           |
| CPU / RAM      | Any modern x86-64 CPU / ≥ 4 GB RAM                                                             |
| GPU (Optional) | NVIDIA CUDA 11.8 / 12.x with corresponding drivers                                             |
| Others         | If using GPU, **install CUDA Toolkit** first (refer to online tutorials)                       |
| ffmpeg         | ffmpeg is an open-source multimedia toolkit. Install via command line: `winget install ffmpeg` |

---

## Quick Start

### 1. Download Dependencies

1. **Double-click** `PyTorch_Download.exe` → Choose **CPU version** or **CUDA version**.

2. Wait for the progress to complete, then click **Verify** (or simply close the window). Dependencies will be extracted to `pytorch_libs\`.

### 2. Start Transcription

1. **Double-click** `Transcription.exe`.

2. Click **📁 Select Audio File** and import an audio file (`.wav / .mp3 / .flac …`).

3. Select the model size under **Whisper Model** (see table below).

4. **Optional**:
   
   - **Keyword**: Input topic keywords to improve accuracy.
   
   - **⚙ Adjust Parameters**: Fine-tune advanced parameters (see next section).

5. Choose **Transcription Language** (or *auto* for auto-detection), then click **🎯 Start Transcription**.

6. Once finished, you can:
   
   - **💾 Save Transcription** as `.json` / `.txt`
   
   - **🎬 Export Subtitles** as `.srt` / `.vtt` (compatible with PotPlayer, VLC, etc.)

> **Model Cache**: The model will be automatically downloaded to  
> `C:\Users\<USERNAME>\.cache\whisper\` on first use. Reused afterward.

---

## Whisper Model Guide

| Size   | Parameters | English-only | Multilingual | Typical VRAM | Relative Speed* |
| ------ | ---------- | ------------ | ------------ | ------------ | --------------- |
| tiny   | 39 M       | `tiny.en`    | `tiny`       | ~1 GB        | ~10×            |
| base   | 74 M       | `base.en`    | `base`       | ~1 GB        | ~7×             |
| small  | 244 M      | `small.en`   | `small`      | ~2 GB        | ~4×             |
| medium | 769 M      | `medium.en`  | `medium`     | ~5 GB        | ~2×             |
| large  | 1550 M     | —            | `large`      | ~10 GB       | 1×              |
| turbo† | 809 M      | —            | `turbo`      | ~6 GB        | ~8×             |

- Speed is relative to `large` = 1×, for reference only.  
  † `turbo` is a distilled version of the large model offering a balance between speed and VRAM usage.

---

## Adjustable Parameters

| Parameter                    | Description                                 | Range / Type   | Default (optimized for Japanese) |
| ---------------------------- | ------------------------------------------- | -------------- | -------------------------------- |
| `temperature`                | Controls randomness (higher = more freedom) | 0 – 1 (float)  | 0.0                              |
| `best_of`                    | Sampling times, keep best result            | 1 – 10 (int)   | 10                               |
| `beam_size`                  | Beam Search width                           | 1 – 20 (int)   | 10                               |
| `logprob_threshold`          | Tokens below this are pruned                | −5 – 0 (float) | −1                               |
| `no_speech_threshold`        | Silence segment detection threshold         | 0 – 1 (float)  | 0.5                              |
| `condition_on_previous_text` | Use prior context                           | True / False   | False                            |

---

## Output File Formats

| Format  | Description                                             | Use Case                        |
| ------- | ------------------------------------------------------- | ------------------------------- |
| `.json` | Structured transcription result (with token timestamps) | Development, data analysis      |
| `.txt`  | Plain text + sentence timestamps                        | Quick view, full-text search    |
| `.srt`  | SubRip subtitles                                        | Video players, editing software |
| `.vtt`  | WebVTT subtitles                                        | HTML5 video, streaming          |

---

## FAQ

1. **How to change interface language?**  
   Use the `Language` dropdown at the top right to switch between Chinese, Japanese, English, or Korean.

2. **CUDA is installed, but Downloader doesn't detect it?**  
   Run `nvcc --version` in *PowerShell* to verify. If not found, reinstall CUDA or set environment variables.

3. **Model download is too slow?**
   
   - Use a faster internet or proxy.
   
   - Manually place the `.pt` model files into `~\.cache\whisper\`.

4. **How to batch process multiple audio files?**  
   The GUI currently supports one file at a time. Use `Pycode\Transcription.py` in command line to loop over files via `whisper.transcribe()`.

---

> **License**: MIT  
> **Author**: Tomokoto  
> **Contact**: [heu_xuyouyan@outlook.com](mailto:heu_xuyouyan@outlook.com)  
> **Last Update**: 2025-06-10
