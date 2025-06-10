# -*- mode: python ; coding: utf-8 -*-
import sys, os, sysconfig, glob
from PyInstaller.utils.hooks import (
        collect_submodules, collect_data_files)

block_cipher = None

# -- 1) 保证 ensurepip/_bundled 下的两个 wheel 带进来 ------------
_ens_bundled = os.path.join(sys.base_prefix, 'Lib',
                            'ensurepip', '_bundled')
datas  = [(w, 'ensurepip/_bundled')
          for w in glob.glob(os.path.join(_ens_bundled, '*.whl'))]

# -- 2) 把 pip 运行时需要的 data 文件一并塞进来 --------------------
datas += collect_data_files('pip._vendor.certifi')   # cacert.pem
datas += collect_data_files('pip._vendor.distlib')   # resources.sqlite
datas += [
    ("third_party_wheels/*.whl", "third_party_wheels"),   # ★ 把整个目录打进去
]
# -- 3) 只排除真正的大块头 -------------------------------------
EXCLUDES = [
    'torch', 'torchvision', 'torchaudio', 'torchtext', 'torchgen',
    'tensorflow', 'keras', 'jax', 'flax',
    'opencv', 'cv2', 'scipy', 'sklearn', 'pandas',
]

hiddenimports = (
      collect_submodules('pip')
    + collect_submodules('pip._vendor')
    + ['ensurepip']
)

packages = ['pip._vendor.distlib']

a = Analysis(
        ['PyTorch_Downloader.py'],
        datas=datas,
        hiddenimports=hiddenimports,
        excludes=EXCLUDES,
        packages=packages,
        noarchive=True
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
          name='PyTorch_Downloader', console=False, icon='download.ico', strip=True, upx=True
)
