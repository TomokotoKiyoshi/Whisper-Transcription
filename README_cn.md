# 利用OpenAI-Whisper模型实现的多国语言音频转文字/字幕系统

*(Windows GUI 版)*

## 目录

1. [项目简介](#%E9%A1%B9%E7%9B%AE%E7%AE%80%E4%BB%8B)
2. [文件结构](#%E6%96%87%E4%BB%B6%E7%BB%93%E6%9E%84)
3. [运行环境](#%E8%BF%90%E8%A1%8C%E7%8E%AF%E5%A2%83)
4. [快速使用](#%E5%BF%AB%E9%80%9F%E4%BD%BF%E7%94%A8)
5. [Whisper 模型说明](#whisper-%E6%A8%A1%E5%9E%8B%E8%AF%B4%E6%98%8E)
6. [可调节参数](#%E5%8F%AF%E8%B0%83%E8%8A%82%E5%8F%82%E6%95%B0)
7. [输出文件格式](#%E8%BE%93%E5%87%BA%E6%96%87%E4%BB%B6%E6%A0%BC%E5%BC%8F)
8. [常见问题](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)

---

## 项目简介

本项目包含两款独立的 Windows 可执行程序，需要使用时请在右侧 `Releases` 栏中下载完整的exe可执行文件：

| 程序                       | 作用                             | 特色                                                                                          |
| ------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------- |
| **PyTorch_Download.exe** | 一键下载并验证 *PyTorch + Whisper* 依赖 | • 支持 CPU / GPU (CUDA) 双版本<br>• 多语言 GUI（中/日/英/韩） :contentReference[oaicite:0]{index=0}       |
| **Transcription.exe**    | 图形化音频转录与字幕生成器                  | • 多语言界面<br>• Whisper 模型自动下载/加载<br>• 关键词提示、参数微调、进度实时显示 :contentReference[oaicite:1]{index=1} |

---

## 文件结构

├─PyTorch_Download.exe         # 依赖下载器  
├─Transcription.exe          # 音频转录 GUI  
├─pytorch_libs\            # 下载后生成，存放离线依赖  
└─Pycode\              # 源码与打包脚本所在目录  
    ├─PyTorch_Downloader.py    # Downloader 源代码  
    ├─Transcription.py      # Transcription 源代码  
    └─third_party_wheels\     # 内置第三方 wheel（可选）

> **说明**
> 
> - 只有当你想自行修改、重新打包程序时才需要关注 `Pycode\`；日常使用 `.exe` 时可忽略。
> - 依赖下载后会自动放置在项目同级目录的 `pytorch_libs\` 中，便于离线运行。

---

## 运行环境

| 项        | 说明                                                               |
| -------- | ---------------------------------------------------------------- |
| 操作系统     | Windows 10/11 64-bit                                             |
| CPU / 内存 | 任意现代 x86-64 处理器 / ≥ 4 GB RAM                                     |
| GPU (可选) | NVIDIA CUDA 11.8 / 12.x 及对应驱动                                    |
| 其它       | 若使用 GPU，请 **先安装** CUDA Toolkit（安装方法可参考网络教程）                      |
| ffmpeg   | ffmpeg 是一个开源的音视频处理工具套件，使用命令提示符（CMD）执行 `winget install ffmpeg` 安装 |

---

## 快速使用

### 1. 下载依赖

1. **双击** `PyTorch_Download.exe` → 选择 **CPU 版**或**CUDA 版**。
2. 等待进度完成并点击 **Verify**（或直接关闭窗口）。依赖即被解压至 `pytorch_libs\`。

### 2. 开始转录

1. **双击** `Transcription.exe`。
2. 点击 **📁 选择音频文件**，导入待转录的音频（`.wav / .mp3 / .flac …`）。
3. 在 **Whisper Model** 下拉框中选择模型尺寸（见下表）。
4. **可选**：
   - **Keyword**：填写音频主题关键词，提升识别精度。
   - **⚙ Adjust Parameters**：微调高级参数（下一节说明）。
5. 选择 **Transcription Language**（或 *auto* 自动检测），点击 **🎯 Start Transcription**。
6. 完成后可：
   - **💾 保存转录**为 `.json` / `.txt`
   - **🎬 导出字幕**为 `.srt` / `.vtt`（PotPlayer、VLC 均可直接加载）。

> **模型缓存**：首次调用某模型会自动下载至  
> `C:\Users\<USERNAME>\.cache\whisper\`，后续复用不再下载。

---

## Whisper 模型说明

| Size   | 参数量    | English-only | Multilingual | 典型显存   | 相对速度* |
| ------ | ------ | ------------ | ------------ | ------ | ----- |
| tiny   | 39 M   | `tiny.en`    | `tiny`       | ~1 GB  | ~10×  |
| base   | 74 M   | `base.en`    | `base`       | ~1 GB  | ~7×   |
| small  | 244 M  | `small.en`   | `small`      | ~2 GB  | ~4×   |
| medium | 769 M  | `medium.en`  | `medium`     | ~5 GB  | ~2×   |
| large  | 1550 M | —            | `large`      | ~10 GB | 1×    |
| turbo† | 809 M  | —            | `turbo`      | ~6 GB  | ~8×   |

* 速度以 `large`＝1× 为基准，仅供参考。  
  † `turbo` 为蒸馏版大型模型，兼顾速度与显存占用。

---

## 可调节参数

| 参数                           | 作用               | 范围 / 类型        | 默认值（针对日语优化） |
| ---------------------------- | ---------------- | -------------- | ----------- |
| `temperature`                | 控制随机性（越高越自由）     | 0 – 1 (float)  | 0.0         |
| `best_of`                    | 采样次数，取最佳结果       | 1 – 10 (int)   | 10          |
| `beam_size`                  | Beam Search 宽度   | 1 – 20 (int)   | 10          |
| `logprob_threshold`          | 低于该阈值的 token 被剪除 | −5 – 0 (float) | −1          |
| `no_speech_threshold`        | 静音段判定阈值          | 0 – 1 (float)  | 0.5         |
| `condition_on_previous_text` | 是否利用前文上下文        | True / False   | False       |

---

## 输出文件格式

| 格式      | 描述                   | 典型用途            |
| ------- | -------------------- | --------------- |
| `.json` | 结构化转录结果（含 token 时间戳） | 二次开发、数据分析       |
| `.txt`  | 纯文本 + 整句时间戳          | 快速查看、全文检索       |
| `.srt`  | SubRip 字幕            | 视频播放器、剪辑软件      |
| `.vtt`  | WebVTT 字幕            | HTML5 Video、流媒体 |

---

## 常见问题

1. **界面语言如何切换？**  
   右上角 `Language` 下拉框可随时切换中/日/英/韩。

2. **已装 CUDA，但 Downloader 识别不到？**  
   在 *PowerShell* 输入 `nvcc --version`，确保能输出版本号；若无，需重装或设置环境变量。

3. **模型下载速度过慢？**
   
   - 使用更快的网络或代理；
   - 手动将 `.pt` 模型放入 `~\.cache\whisper\`。

4. **如何批量处理多个音频？**  
   GUI 目前一次只处理一个文件。可直接使用 `Pycode\Transcription.py` 在命令行循环调用 `whisper.transcribe()` 实现批量。

---

> **License**：MIT  
> **Author**：Tomokoto **Contact**：heu_xuyouyan@outlook.com  
> **Last Update**：2025-06-10
