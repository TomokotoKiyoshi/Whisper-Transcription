# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Create a comprehensive list of standard library modules
# that PyTorch and Whisper might need
stdlib_modules = [
    # Core modules
    'os', 'sys', 'io', 'time', 'datetime', 're', 'json', 'glob',
    'timeit',  # CRITICAL: Add timeit module
    
    # File and path operations
    'pathlib', 'stat', 'fnmatch', 'posixpath', 'ntpath', 'genericpath',
    'fileinput', 'filecmp', 'tempfile', 'shutil',
    
    # Data structures and algorithms
    'collections', 'collections.abc', 'itertools', 'functools',
    'operator', 'bisect', 'heapq', 'array', 'queue',
    
    # Type system and introspection
    'types', 'typing', 'abc', 'inspect', 'dis', 'ast',
    
    # Math and numbers
    'math', 'cmath', 'decimal', 'fractions', 'random', 'statistics',
    'numbers',
    
    # String and text processing
    'string', 'textwrap', 'unicodedata', 'stringprep', 'difflib',
    
    # Import system
    'importlib', 'importlib.util', 'importlib.machinery', 'importlib.abc',
    'pkgutil', 'modulefinder', 'runpy', '__import__',
    
    # System and platform
    'platform', 'sysconfig', 'site', 'getpass', 'uuid', 'socket',
    'signal', 'resource', 'gc', 'atexit',
    
    # Encoding and serialization
    'codecs', 'encodings', 'base64', 'binascii', 'pickle', 'copyreg',
    'shelve', 'marshal', 'struct',
    
    # Error handling and debugging
    'traceback', 'warnings', 'contextlib', 'weakref', 'logging',
    'logging.config', 'logging.handlers', 'pdb', 'profile', 'cProfile',
    
    # Threading and concurrency
    'threading', 'multiprocessing', 'concurrent', 'subprocess',
    '_thread', 'dummy_threading',
    
    # Built-in modules
    'builtins', '__future__', '__main__', 'keyword', 'token', 'tokenize',
    
    # Other utilities
    'copy', 'pprint', 'reprlib', 'enum', 'dataclasses', 'contextvars',
    'secrets', 'hashlib', 'hmac', 'zlib', 'gzip', 'bz2', 'lzma',
    'zipfile', 'tarfile',
    
    # Windows-specific modules (if on Windows)
    'winreg', 'msvcrt', '_winapi',
    
    # Additional modules that might be needed
    'select', 'selectors', 'errno', 'fcntl', 'mmap', 'readline',
    'rlcompleter', 'termios', 'tty', 'pty', 'pipes','asyncio','pickletools',
    'urllib.error', 'urllib.request', 'unittest',  'unittest.mock', 'importlib.resources',
    'html', 'html.parser', 'xml', 'xml.etree', 'xml.etree.ElementTree', 'colorsys'
]

# GUI and system modules for the main application
gui_modules = [
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.scrolledtext',
    'tkinter.filedialog', 'tkinter.constants', 'tkinter.dialog',
    'tkinter.commondialog', 'tkinter.simpledialog',
    'ctypes', '_ctypes',
]

# Combine all modules
all_hidden_imports = stdlib_modules + gui_modules

a = Analysis(
    ['check_in_exe.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=all_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Scientific computing libraries (loaded dynamically from pytorch_libs)
        'numpy', 'scipy', 'pandas', 'matplotlib', 'torch', 'whisper',
        'tensorflow', 'keras', 'sklearn',
        
        # Development and testing
        'pytest', 'test', 'tests', 'testing',
        'setuptools', 'wheel', 'distutils', 'pip',
        
        # Web frameworks and tools
        'requests', 'urllib3', 'http.server', 'wsgiref', 'xmlrpc',
        'django', 'flask', 'bottle',
        
        # Development environments
        'IPython', 'jupyter', 'notebook', 'ipykernel', 'ipywidgets',
        'spyder', 'pylint', 'pycodestyle', 'mypy',
        
        # Documentation tools
        'sphinx', 'docutils', 'pydoc', 'doctest',
        
        # Image and multimedia (not needed for audio transcription)
        'PIL', 'Pillow', 'cv2', 'opencv', 'imageio', 'skimage',
        
        # Database drivers
        'pymongo', 'psycopg2', 'mysql', 'sqlite3', 'sqlalchemy',
        
        # Other large packages
        'sympy', 'networkx', 'nltk', 'gensim', 'transformers',
        
        # Unnecessary standard library modules
        'turtle', 'antigravity', 'this', 'brokenaxes',
        'idlelib', 'lib2to3', 'ensurepip',
        
        # Test modules
        'tkinter.test', 'ctypes.test', 'distutils.tests',
        'email.test', 'json.tests', 'lib2to3.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Collect all encodings to ensure proper text handling
from PyInstaller.utils.hooks import collect_submodules
a.hiddenimports.extend(collect_submodules('encodings'))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='check_in_exe',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version_file=None,
)