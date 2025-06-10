#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_in_exe.py
---------------
• 解析“真实的” pytorch_libs 目录 （脚本 vs. EXE 两种运行模式）
• 把它插到 sys.path[0]
• 强制重新 import torch / whisper
• 打印所有关键信息
"""

import sys, os, inspect, importlib, pathlib, time, traceback

def headline(t): print("\n" + "="*8, t, "="*8)

# ---------- 1. 解析路径 ----------
if getattr(sys, 'frozen', False):          # 运行在 PyInstaller 打包的 EXE 里
    base_dir = pathlib.Path(sys.executable).parent
else:                                      # 普通 .py 运行
    base_dir = pathlib.Path(__file__).resolve().parent
lib_dir  = (base_dir / "pytorch_libs").resolve()

headline("运行环境 / Runtime Env")
print("os.getcwd()      :", os.getcwd())
print("sys.argv[0]      :", sys.argv[0])
print("__file__         :", globals().get('__file__'))
print("sys.executable   :", sys.executable)
print("base_dir         :", base_dir)
print("pytorch_libs dir :", lib_dir, "| exists?", lib_dir.exists())

# ---------- 2. 准备 sys.path 并 purge 旧模块 ----------
sys.path.insert(0, str(lib_dir))           # 把我们的 wheel 目录放到最前
for name in list(sys.modules):
    if name.startswith(("torch", "whisper")):
        del sys.modules[name]

# ---------- 3. 开始导入 ----------
def try_import(name):
    try:
        return importlib.import_module(name)
    except Exception as e:
        print(f"  ✘  import {name} 失败: {e}")
        traceback.print_exc()
        return None

headline("尝试导入 / Import Trial")
torch   = try_import("torch")
vision  = try_import("torchvision")
audio   = try_import("torchaudio")
whisper = try_import("whisper")

headline("加载结果 / Load Result")
if torch:
    print("Torch version   :", torch.__version__)
    print("Torch file      :", inspect.getfile(torch))
    print("CUDA is avail   :", torch.cuda.is_available())
    print("cuda tag        :", torch.version.cuda)
    try:
        print("torch._C .pyd   :", torch._C.__file__)
    except Exception as e:
        print("torch._C 载入失败:", e)

if whisper:
    print("Whisper file    :", inspect.getfile(whisper))

# ---------- 4. 额外自测 ----------
if torch and torch.cuda.is_available():
    headline("GPU 张量自测 / GPU Tensor Test")
    a = torch.randn(2, 4, device="cuda")
    b = torch.randn(4, 2, device="cuda")
    c = a @ b
    torch.cuda.synchronize()
    print("  ✔  GPU MatMul OK, result shape:", c.shape)

if torch:
    headline("CPU 张量自测 / CPU Tensor Test")
    a = torch.eye(3)
    print("  ✔  CPU Eye OK :", a)

print("\n全部结束 / Finished")
input("Press any key to exit…")   # ← 等待用户按回车后再退出