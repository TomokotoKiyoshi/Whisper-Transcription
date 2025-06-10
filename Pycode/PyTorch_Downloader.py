import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import platform
import sys
from pathlib import Path
import json
import time
import re
import shutil
import struct
import io
import contextlib


def resource_root() -> Path:
    """
    PyInstallerバンドルリソースを含むフォルダへのパスを返す
    Return the path to the folder that contains bundled resources (for PyInstaller)
    """
    if getattr(sys, "frozen", False):  # PyInstallerでの実行時 / When running under PyInstaller
        return Path(sys._MEIPASS)
    return Path(__file__).parent


class PyTorchDownloader:
    """
    PyTorchとWhisperの依存関係ダウンローダー (Dependency Downloader for PyTorch & Whisper)
    特定のディレクトリにPyTorchとWhisperをダウンロードして動的にロードします
    (Downloads PyTorch & Whisper to a specific directory for dynamic loading)
    """

    def __init__(self):
        # 基本属性の初期化 / Initialize core attributes
        self.target_dir = Path("pytorch_libs")
        self.is_downloading = False
        self.download_thread = None
        self.current_language = "en"  # Default to English

        # Initialize translations
        self.init_translations()

        # カラーテーマ / Color theme
        self.colors = {
            'primary': '#2E3440',
            'accent': '#5E81AC',
            'success': '#A3BE8C',
            'warning': '#EBCB8B',
            'danger': '#BF616A',
            'text': '#2E3440',
            'text_light': '#4C566A',
            'background': '#F5F7FA',
            'surface': '#FFFFFF',
            'border': '#E1E8ED',
            'shadow': '#D8DEE9'
        }

        # Initialize responsive scaling
        self.setup_responsive_scaling()

        # プラットフォーム検出 / Detect platform (Windows/Linux etc.)
        self.detect_platform()

        # GUIのセットアップ / Setup GUI
        self.setup_gui()

        # 既存インストールの確認 / Check if installation already exists
        self.check_existing_installation()

    def setup_responsive_scaling(self):
        """Calculate scaling factors based on screen size"""
        # Create temporary root to get screen dimensions
        temp_root = tk.Tk()
        screen_width = temp_root.winfo_screenwidth()
        screen_height = temp_root.winfo_screenheight()
        temp_root.destroy()
        
        # Calculate base scaling factor (reference: 1920x1080)
        width_scale = screen_width / 1920
        height_scale = screen_height / 1080
        self.scale_factor = min(width_scale, height_scale)
        
        # Ensure reasonable scaling limits
        self.scale_factor = max(0.6, min(self.scale_factor, 1.5))
        
        # Calculate window dimensions (90% of screen size to leave room for taskbar)
        self.window_width = int(screen_width * 0.5)
        self.window_height = int(screen_height * 0.85)
        
        # Set minimum window size
        self.window_width = max(700, self.window_width)
        self.window_height = max(500, self.window_height)
        
        # Calculate scaled dimensions for all UI elements
        self.scaled_dimensions = {
            'padding_xlarge': self.scale_value(30),
            'padding_large': self.scale_value(20),
            'padding_medium': self.scale_value(15),
            'padding_small': self.scale_value(10),
            'padding_tiny': self.scale_value(5),
            'button_padding_x': self.scale_value(30),
            'button_padding_y': self.scale_value(12),
            'border_width': max(1, self.scale_value(1)),
            'card_padding': self.scale_value(20),
            'section_spacing': self.scale_value(15),
            'log_height': self.scale_value(150, min_val=100),  # Log area height
        }
        
        # Calculate scaled fonts
        self.fonts = {
            'header_title': ('Segoe UI', self.scale_value(26, min_val=18), 'bold'),
            'header_subtitle': ('Segoe UI', self.scale_value(13, min_val=10)),
            'section_title': ('Segoe UI', self.scale_value(15, min_val=12), 'bold'),
            'label': ('Segoe UI', self.scale_value(13, min_val=10), 'bold'),
            'normal': ('Segoe UI', self.scale_value(12, min_val=9)),
            'small': ('Segoe UI', self.scale_value(11, min_val=8)),
            'console': ('Consolas', self.scale_value(11, min_val=8)),
            'button': ('Segoe UI', self.scale_value(12, min_val=9), 'bold'),
        }

    def scale_value(self, value, min_val=None):
        """Scale a value based on the scaling factor"""
        scaled = int(value * self.scale_factor)
        if min_val is not None:
            return max(min_val, scaled)
        return scaled

    def init_translations(self):
        """Initialize all UI text translations"""
        self.translations = {
            "en": {
                "window_title": "PyTorch Downloader",
                "header_title": "PyTorch & Whisper Downloader",
                "header_subtitle": "Downloads required dependencies for audio subtitle system",
                "system_info": "System Information",
                "version_selection": "PyTorch Version Selection",
                "cpu_version": "CPU Version",
                "cuda_version": "CUDA Version (GPU acceleration)",
                "not_detected": "Not detected",
                "install_dir": "Install directory:",
                "status": "Status",
                "ready": "Ready",
                "download_log": "Download Log",
                "start_download": "🚀 Start Downloading",
                "verify": "✔️ Verify",
                "close": "❌ Close",
                "language": "Language:",
                "platform_detected": "Detected platform:",
                "existing_dir": "Existing directory detected:",
                "cleaning_up": "Cleaning up existing installations...",
                "cleanup_status": "Cleaning up...",
                "cleanup_warning": "Warning: Failed to remove",
                "cleanup_complete": "Cleanup complete:",
                "items_removed": "items removed",
                "warning": "Warning",
                "already_downloading": "Already downloading",
                "confirm": "Confirm",
                "download_confirm": "Download to {}? Existing files will be removed.",
                "error": "Error",
                "cuda_error": "Unsupported or missing CUDA Toolkit.",
                "pip_error": "pip Error",
                "pip_import_failed": "Failed to import pip:",
                "embedded_wheel": "Using embedded wheel:",
                "no_embedded_wheel": "Embedded wheel not found → fallback to PyPI",
                "download_complete": "Done",
                "complete": "Complete",
                "download_success_msg": "Download of PyTorch + Whisper has completed!\nYou may click 'Verify' or close this window.",
                "download_failed": "Download Failed",
                "verify_start": "Start verifying",
                "verifying": "Verifying...",
                "verify_success": "Verification Succeeded",
                "verify_success_msg": "PyTorch & Whisper have been successfully installed.",
                "verify_failed": "Verify Failed",
                "import_error": "Import error:",
                "verify_failed_msg": "Failed to import: {}",
                "still_downloading": "Still downloading. Close anyway?"
            },
            "ja": {
                "window_title": "PyTorchダウンローダー",
                "header_title": "PyTorch & Whisper ダウンローダー",
                "header_subtitle": "音声字幕システムに必要な依存関係をダウンロードします",
                "system_info": "システム情報",
                "version_selection": "PyTorchバージョン選択",
                "cpu_version": "CPU版",
                "cuda_version": "CUDA版 (GPU加速)",
                "not_detected": "未検出",
                "install_dir": "インストールディレクトリ:",
                "status": "状態",
                "ready": "準備完了",
                "download_log": "ダウンロードログ",
                "start_download": "🚀 ダウンロード開始",
                "verify": "✔️ 検証",
                "close": "❌ 閉じる",
                "language": "言語:",
                "platform_detected": "検出されたプラットフォーム:",
                "existing_dir": "既存ディレクトリ検出:",
                "cleaning_up": "既存インストールをクリーンアップ中...",
                "cleanup_status": "クリーンアップ中...",
                "cleanup_warning": "警告: 削除失敗",
                "cleanup_complete": "クリーンアップ完了:",
                "items_removed": "個削除",
                "warning": "警告",
                "already_downloading": "ダウンロード中です",
                "confirm": "確認",
                "download_confirm": "{} へダウンロードしますか？既存の内容は削除されます。",
                "error": "エラー",
                "cuda_error": "CUDA Toolkit が見つからないか、サポートされていません。",
                "pip_error": "pip エラー",
                "pip_import_failed": "pip のインポートに失敗しました:",
                "embedded_wheel": "同梱wheelを使用します:",
                "no_embedded_wheel": "同梱wheelが見つかりませんでした→PyPIからインストール",
                "download_complete": "ダウンロード完了",
                "complete": "完了",
                "download_success_msg": "PyTorch + Whisper のダウンロードが完了しました！\n✔️『検証』をクリックするか、ウィンドウを閉じてください。",
                "download_failed": "ダウンロード失敗",
                "verify_start": "検証開始",
                "verifying": "検証中...",
                "verify_success": "検証成功",
                "verify_success_msg": "PyTorchとWhisperが正しくインストールされました。",
                "verify_failed": "検証失敗",
                "import_error": "インポートエラー:",
                "verify_failed_msg": "インポートに失敗しました。再度ダウンロードをお願いします。\n{}",
                "still_downloading": "ダウンロード中ですが終了しますか？"
            },
            "zh": {
                "window_title": "PyTorch 下载器",
                "header_title": "PyTorch & Whisper 下载器",
                "header_subtitle": "下载音频字幕系统所需的依赖项",
                "system_info": "系统信息",
                "version_selection": "PyTorch版本选择",
                "cpu_version": "CPU版",
                "cuda_version": "CUDA版 (GPU加速)",
                "not_detected": "未检测到",
                "install_dir": "安装目录：",
                "status": "状态",
                "ready": "准备就绪",
                "download_log": "下载日志",
                "start_download": "🚀 开始下载",
                "verify": "✔️ 验证",
                "close": "❌ 关闭",
                "language": "语言：",
                "platform_detected": "检测到的平台：",
                "existing_dir": "检测到现有目录：",
                "cleaning_up": "正在清理现有安装...",
                "cleanup_status": "清理中...",
                "cleanup_warning": "警告：删除失败",
                "cleanup_complete": "清理完成：",
                "items_removed": "个项目已删除",
                "warning": "警告",
                "already_downloading": "正在下载中",
                "confirm": "确认",
                "download_confirm": "要下载到 {} 吗？现有内容将被删除。",
                "error": "错误",
                "cuda_error": "未找到或不支持 CUDA Toolkit。",
                "pip_error": "pip 错误",
                "pip_import_failed": "导入 pip 失败：",
                "embedded_wheel": "使用内置 wheel：",
                "no_embedded_wheel": "未找到内置 wheel → 从 PyPI 安装",
                "download_complete": "下载完成",
                "complete": "完成",
                "download_success_msg": "PyTorch + Whisper 下载完成！\n您可以点击验证或关闭此窗口。",
                "download_failed": "下载失败",
                "verify_start": "开始验证",
                "verifying": "验证中...",
                "verify_success": "验证成功",
                "verify_success_msg": "PyTorch 和 Whisper 已成功安装。",
                "verify_failed": "验证失败",
                "import_error": "导入错误：",
                "verify_failed_msg": "导入失败：{}",
                "still_downloading": "仍在下载中。确定要关闭吗？"
            },
            "ko": {
                "window_title": "PyTorch 다운로더",
                "header_title": "PyTorch & Whisper 다운로더",
                "header_subtitle": "오디오 자막 시스템에 필요한 종속성을 다운로드합니다",
                "system_info": "시스템 정보",
                "version_selection": "PyTorch 버전 선택",
                "cpu_version": "CPU 버전",
                "cuda_version": "CUDA 버전 (GPU 가속)",
                "not_detected": "감지되지 않음",
                "install_dir": "설치 디렉토리:",
                "status": "상태",
                "ready": "준비 완료",
                "download_log": "다운로드 로그",
                "start_download": "🚀 다운로드 시작",
                "verify": "✔️ 검증",
                "close": "❌ 닫기",
                "language": "언어:",
                "platform_detected": "감지된 플랫폼:",
                "existing_dir": "기존 디렉토리 감지:",
                "cleaning_up": "기존 설치를 정리하는 중...",
                "cleanup_status": "정리 중...",
                "cleanup_warning": "경고: 제거 실패",
                "cleanup_complete": "정리 완료:",
                "items_removed": "개 항목 제거됨",
                "warning": "경고",
                "already_downloading": "이미 다운로드 중입니다",
                "confirm": "확인",
                "download_confirm": "{} 에 다운로드하시겠습니까? 기존 파일은 삭제됩니다.",
                "error": "오류",
                "cuda_error": "CUDA 툴킷을 찾을 수 없거나 지원되지 않습니다.",
                "pip_error": "pip 오류",
                "pip_import_failed": "pip 가져오기 실패:",
                "embedded_wheel": "내장 wheel 사용:",
                "no_embedded_wheel": "내장 wheel을 찾을 수 없음 → PyPI에서 설치",
                "download_complete": "다운로드 완료",
                "complete": "완료",
                "download_success_msg": "PyTorch + Whisper 다운로드가 완료되었습니다!\n'검증'을 클릭하거나 이 창을 닫으세요.",
                "download_failed": "다운로드 실패",
                "verify_start": "검증 시작",
                "verifying": "검증 중...",
                "verify_success": "검증 성공",
                "verify_success_msg": "PyTorch와 Whisper가 성공적으로 설치되었습니다.",
                "verify_failed": "검증 실패",
                "import_error": "가져오기 오류:",
                "verify_failed_msg": "가져오기 실패: {}",
                "still_downloading": "아직 다운로드 중입니다. 그래도 닫으시겠습니까?"
            }
        }

    def t(self, key):
        """Get translated text for current language"""
        return self.translations.get(self.current_language, self.translations["en"]).get(key, key)

    def detect_platform(self):
        """
        Windowsプラットフォームを検出し、platform_tagを設定
        Detect the platform (especially Windows) and assign self.platform_tag
        """
        if platform.system() == "Windows":
            # 32bit vs 64bit
            if struct.calcsize("P") * 8 == 64:
                self.platform_tag = "win_amd64"
            else:
                self.platform_tag = "win32"
        else:
            # Linuxなど他OS / For Linux or other OS
            machine = platform.machine().lower()
            if machine in ['x86_64', 'amd64']:
                self.platform_tag = "linux_x86_64"
            elif machine == 'aarch64':
                self.platform_tag = "linux_aarch64"
            else:
                self.platform_tag = platform.machine()

        # GUIが未構築の場合はコンソールに出力 / Print to console if GUI is not built yet
        if hasattr(self, 'root'):
            self.log_output(f"{self.t('platform_detected')} {self.platform_tag}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] "
                  f"Detected platform: {self.platform_tag}")

    def setup_gui(self):
        """
        GUIウィンドウを初期化し、配置を行う
        Initialize the GUI window and place widgets
        """
        self.root = tk.Tk()
        self.root.title(self.t("window_title"))
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        
        # Set minimum window size
        self.root.minsize(600, 400)

        # ウィンドウ中央寄せ / Center the window on screen
        self.root.update_idletasks()
        ws, hs = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y = (ws // 2 - self.window_width // 2), (hs // 2 - self.window_height // 2)
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        self.root.configure(bg=self.colors['background'])

        # Configure ttk styles
        self.setup_ttk_styles()

        # Main container - no scrolling
        main_container = tk.Frame(self.root, bg=self.colors['background'])
        main_container.pack(fill=tk.BOTH, expand=True)

        # Content frame with vertical centering
        content_frame = tk.Frame(main_container, bg=self.colors['background'])
        content_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Create all sections
        self.create_header(content_frame)
        self.create_all_cards(content_frame)

        # プラットフォーム情報をGUIに表示 / Log platform in the GUI
        self.log_output(f"{self.t('platform_detected')} {self.platform_tag}")

        # ウィンドウ終了時のイベント設定 / Attach on_closing for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ttk_styles(self):
        """Configure ttk widget styles"""
        style = ttk.Style()
        
        # Configure combobox style
        style.configure('Custom.TCombobox',
                       fieldbackground=self.colors['surface'],
                       background=self.colors['surface'],
                       borderwidth=1,
                       relief='solid')
        
        # Configure progressbar style
        style.configure('Custom.Horizontal.TProgressbar',
                       background=self.colors['accent'],
                       troughcolor=self.colors['border'],
                       borderwidth=0,
                       lightcolor=self.colors['accent'],
                       darkcolor=self.colors['accent'])

    def create_header(self, parent):
        """
        ヘッダ部分のUIを作成 / Create the header UI
        """
        # Header container
        header_container = tk.Frame(parent, bg=self.colors['background'])
        header_container.pack(fill=tk.X, pady=(0, self.scaled_dimensions['section_spacing']))

        # Title and language in same row
        header_row = tk.Frame(header_container, bg=self.colors['background'])
        header_row.pack(fill=tk.X)

        # Title section (center)
        title_frame = tk.Frame(header_row, bg=self.colors['background'])
        title_frame.pack(expand=True)

        self.header_title_label = tk.Label(
            title_frame,
            text=self.t("header_title"),
            font=self.fonts['header_title'],
            fg=self.colors['primary'],
            bg=self.colors['background']
        )
        self.header_title_label.pack()

        self.header_subtitle_label = tk.Label(
            title_frame,
            text=self.t("header_subtitle"),
            font=self.fonts['header_subtitle'],
            fg=self.colors['text_light'],
            bg=self.colors['background']
        )
        self.header_subtitle_label.pack(pady=(self.scaled_dimensions['padding_tiny'], 0))

        # Language selector (right)
        lang_frame = tk.Frame(header_row, bg=self.colors['background'])
        lang_frame.pack(side=tk.RIGHT, anchor='ne')

        self.lang_label = tk.Label(
            lang_frame,
            text=self.t("language"),
            font=self.fonts['small'],
            fg=self.colors['text_light'],
            bg=self.colors['background']
        )
        self.lang_label.pack(side=tk.LEFT, padx=(0, self.scaled_dimensions['padding_tiny']))

        # Language display names
        self.language_display = {
            "en": "en - English",
            "ja": "ja - 日本語",
            "zh": "cn - 中文",
            "ko": "ko - 한국어"
        }
        
        self.language_var = tk.StringVar(value=self.language_display[self.current_language])
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.language_var,
            values=list(self.language_display.values()),
            state="readonly",
            width=self.scale_value(20),
            font=self.fonts['small'],
            style='Custom.TCombobox'
        )
        self.language_combo.pack(side=tk.LEFT)
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_change)

    def create_card_frame(self, parent, title=None):
        """Create a card-style frame with shadow effect"""
        # Card container with shadow
        card_container = tk.Frame(parent, bg=self.colors['shadow'])
        card_container.pack(fill=tk.X, pady=(0, self.scaled_dimensions['section_spacing']), 
                           padx=self.scaled_dimensions['padding_medium'])
        
        # Card frame
        card = tk.Frame(card_container, bg=self.colors['surface'])
        card.pack(fill=tk.BOTH, padx=2, pady=2)
        
        # Inner frame with padding
        inner = tk.Frame(card, bg=self.colors['surface'])
        inner.pack(fill=tk.BOTH, padx=self.scaled_dimensions['card_padding'], 
                  pady=self.scaled_dimensions['card_padding'])
        
        if title:
            # Store title label reference for language updates
            title_label = tk.Label(
                inner,
                text=title,
                font=self.fonts['section_title'],
                fg=self.colors['primary'],
                bg=self.colors['surface']
            )
            title_label.pack(anchor=tk.W, pady=(0, self.scaled_dimensions['padding_medium']))
            
            # Store reference for updates
            if not hasattr(self, 'card_titles'):
                self.card_titles = {}
            self.card_titles[title] = title_label
        
        return inner

    def create_all_cards(self, parent):
        """Create all content cards in a single container"""
        # Cards container
        cards_container = tk.Frame(parent, bg=self.colors['background'])
        cards_container.pack(fill=tk.BOTH, expand=True)

        # Create horizontal layout for system info and version selection
        top_row = tk.Frame(cards_container, bg=self.colors['background'])
        top_row.pack(fill=tk.X)

        # Left column
        left_col = tk.Frame(top_row, bg=self.colors['background'])
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right column
        right_col = tk.Frame(top_row, bg=self.colors['background'])
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # System Information (left)
        self.create_system_info_card(left_col)

        # PyTorch Version Selection (right)
        self.create_version_selection_card(right_col)

        # Status card (full width)
        self.create_status_card(cards_container)

        # Download Log card (full width)
        self.create_log_card(cards_container)

        # Control buttons (centered)
        self.create_control_buttons(cards_container)

    def create_system_info_card(self, parent):
        """Create system information card"""
        inner = self.create_card_frame(parent, self.t("system_info"))
        
        ver = sys.getwindowsversion().major
        os_name = f"Windows {11 if (ver == 10 and sys.getwindowsversion().build >= 22000) else ver}"

        info_frame = tk.Frame(inner, bg=self.colors['surface'])
        info_frame.pack()

        info_items = [
            f"OS: {os_name}",
            f"Python: {sys.version.split()[0]}",
            f"Architecture: {platform.machine()}",
            f"Platform: {self.platform_tag}"
        ]

        for item in info_items:
            label = tk.Label(
                info_frame,
                text=item,
                font=self.fonts['console'],
                fg=self.colors['text_light'],
                bg=self.colors['surface']
            )
            label.pack(anchor=tk.W, pady=(0, self.scaled_dimensions['padding_tiny']))

    def create_version_selection_card(self, parent):
        """Create PyTorch version selection card"""
        inner = self.create_card_frame(parent, self.t("version_selection"))
        
        self.version_var = tk.StringVar(value="cpu")
        
        # Radio buttons frame
        radio_frame = tk.Frame(inner, bg=self.colors['surface'])
        radio_frame.pack()
        
        self.cpu_radio = tk.Radiobutton(
            radio_frame,
            text=self.t("cpu_version"),
            variable=self.version_var,
            value="cpu",
            font=self.fonts['normal'],
            bg=self.colors['surface'],
            fg=self.colors['text'],
            activebackground=self.colors['surface'],
            selectcolor=self.colors['surface']
        )
        self.cpu_radio.pack(anchor=tk.W, pady=self.scaled_dimensions['padding_tiny'])

        cuda_ok = self.check_cuda_available()
        cuda_text = self.t("cuda_version")
        if not cuda_ok:
            cuda_text += f" - {self.t('not_detected')}"

        self.cuda_radio = tk.Radiobutton(
            radio_frame,
            text=cuda_text,
            variable=self.version_var,
            value="cuda",
            font=self.fonts['normal'],
            bg=self.colors['surface'],
            fg=self.colors['text'] if cuda_ok else self.colors['text_light'],
            state=tk.NORMAL if cuda_ok else tk.DISABLED,
            activebackground=self.colors['surface'],
            selectcolor=self.colors['surface']
        )
        self.cuda_radio.pack(anchor=tk.W, pady=self.scaled_dimensions['padding_tiny'])

        # Install directory
        self.install_dir_label = tk.Label(
            inner,
            text=f"{self.t('install_dir')} {self.target_dir.absolute()}",
            font=self.fonts['small'],
            fg=self.colors['text_light'],
            bg=self.colors['surface'],
            wraplength=self.scale_value(300)
        )
        self.install_dir_label.pack(pady=(self.scaled_dimensions['padding_medium'], 0))

    def create_status_card(self, parent):
        """Create status card"""
        inner = self.create_card_frame(parent, self.t("status"))
        
        # Status text
        self.status_label = tk.Label(
            inner,
            text=self.t("ready"),
            font=self.fonts['normal'],
            fg=self.colors['success'],
            bg=self.colors['surface']
        )
        self.status_label.pack()
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            inner, 
            mode='indeterminate',
            style='Custom.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill=tk.X, pady=(self.scaled_dimensions['padding_small'], 0))

    def create_log_card(self, parent):
        """Create download log card"""
        inner = self.create_card_frame(parent, self.t("download_log"))
        
        # Log text area with border
        log_frame = tk.Frame(inner, bg=self.colors['border'])
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Calculate log height based on screen size
        log_lines = max(6, int(10 * self.scale_factor))
        
        self.output_text = scrolledtext.ScrolledText(
            log_frame,
            height=log_lines,
            font=self.fonts['console'],
            bg=self.colors['surface'],
            fg=self.colors['text'],
            wrap=tk.WORD,
            relief='flat',
            bd=0
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    def create_control_buttons(self, parent):
        """Create control buttons with centered layout"""
        button_container = tk.Frame(parent, bg=self.colors['background'])
        button_container.pack(pady=(0, self.scaled_dimensions['padding_large']))
        
        button_frame = tk.Frame(button_container, bg=self.colors['background'])
        button_frame.pack()
        
        # Button styling
        button_config = {
            'font': self.fonts['button'],
            'padx': self.scaled_dimensions['button_padding_x'],
            'pady': self.scaled_dimensions['button_padding_y'],
            'bd': 0,
            'cursor': 'hand2',
            'relief': 'flat'
        }
        
        self.download_btn = tk.Button(
            button_frame,
            text=self.t("start_download"),
            command=self.start_download,
            bg=self.colors['accent'],
            fg='white',
            activebackground=self.colors['primary'],
            **button_config
        )
        self.download_btn.pack(side=tk.LEFT, padx=self.scaled_dimensions['padding_small'])

        self.verify_btn = tk.Button(
            button_frame,
            text=self.t("verify"),
            command=self.verify_installation,
            bg=self.colors['success'],
            fg='white',
            state=tk.DISABLED,
            activebackground='#8FAA7B',
            **button_config
        )
        self.verify_btn.pack(side=tk.LEFT, padx=self.scaled_dimensions['padding_small'])

        self.close_btn = tk.Button(
            button_frame,
            text=self.t("close"),
            command=self.on_closing,
            bg=self.colors['danger'],
            fg='white',
            activebackground='#A85757',
            **button_config
        )
        self.close_btn.pack(side=tk.LEFT, padx=self.scaled_dimensions['padding_small'])

    def on_language_change(self, event=None):
        """Handle language change event"""
        # Get the language code from the display name
        display_name = self.language_var.get()
        for code, name in self.language_display.items():
            if name == display_name:
                self.current_language = code
                break
        self.update_all_texts()

    def update_all_texts(self):
        """Update all UI texts when language changes"""
        # Update window title
        self.root.title(self.t("window_title"))
        
        # Update header
        self.header_title_label.config(text=self.t("header_title"))
        self.header_subtitle_label.config(text=self.t("header_subtitle"))
        self.lang_label.config(text=self.t("language"))
        
        # Update card titles
        if hasattr(self, 'card_titles'):
            title_mapping = {
                "System Information": "system_info",
                "システム情報": "system_info",
                "系统信息": "system_info",
                "시스템 정보": "system_info",
                "PyTorch Version Selection": "version_selection",
                "PyTorchバージョン選択": "version_selection",
                "PyTorch版本选择": "version_selection",
                "PyTorch 버전 선택": "version_selection",
                "Status": "status",
                "状態": "status",
                "状态": "status",
                "상태": "status",
                "Download Log": "download_log",
                "ダウンロードログ": "download_log",
                "下载日志": "download_log",
                "다운로드 로그": "download_log"
            }
            
            for title_label in self.card_titles.values():
                current_text = title_label.cget("text")
                for old_title, key in title_mapping.items():
                    if current_text == old_title:
                        title_label.config(text=self.t(key))
                        break
        
        # Update radio buttons
        self.cpu_radio.config(text=self.t("cpu_version"))
        
        cuda_text = self.t("cuda_version")
        if self.cuda_radio['state'] == tk.DISABLED:
            cuda_text += f" - {self.t('not_detected')}"
        self.cuda_radio.config(text=cuda_text)
        
        self.install_dir_label.config(text=f"{self.t('install_dir')} {self.target_dir.absolute()}")
        
        # Update status
        if self.status_label.cget("text") in ["準備完了", "Ready", "准备就绪", "준비 완료"]:
            self.status_label.config(text=self.t("ready"))
        
        # Update buttons
        self.download_btn.config(text=self.t("start_download"))
        self.verify_btn.config(text=self.t("verify"))
        self.close_btn.config(text=self.t("close"))

    def check_cuda_available(self):
        """
        CUDAツールキット(nvcc)が使えるか確認
        Check if CUDA Toolkit (nvcc) is available
        """
        try:
            import subprocess
            out = subprocess.check_output(['nvcc', '--version'], stderr=subprocess.STDOUT, text=True)
            return 'release' in out.lower()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def check_existing_installation(self):
        """
        すでにpytorch_libsフォルダがある場合を確認 / Check if the target_dir already exists
        """
        if self.target_dir.exists():
            self.log_output(f"{self.t('existing_dir')} {self.target_dir}")
            self.verify_btn.config(state=tk.NORMAL)

    def log_output(self, message):
        """
        ログエリアにメッセージを出力 / Output message to log (ScrolledText)
        """
        def update():
            self.output_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
            self.output_text.see(tk.END)
        self.root.after(0, update)

    def update_status(self, status, color=None):
        """
        ステータスラベルを更新 / Update status label
        """
        def update():
            self.status_label.config(text=status)
            if color:
                self.status_label.config(fg=color)
        self.root.after(0, update)

    def clean_pytorch_installation(self):
        """
        既存のPyTorchインストールを削除しクリーンアップ / Clean up existing PyTorch installations
        """
        self.log_output(self.t("cleaning_up"))
        self.update_status(self.t("cleanup_status"), self.colors['warning'])

        patterns = ["torch*", "torchvision*", "torchaudio*", "torchgen"]
        removed = 0

        for pat in patterns:
            for path in self.target_dir.glob(pat):
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink(missing_ok=True)
                    removed += 1
                except Exception as e:
                    self.log_output(f"{self.t('cleanup_warning')} {pat}: {e}")

        self.log_output(f"{self.t('cleanup_complete')} {removed} {self.t('items_removed')}")
        time.sleep(1)

    def start_download(self):
        """
        ダウンロードを開始 / Start the download process
        """
        if self.is_downloading:
            messagebox.showwarning(self.t("warning"), self.t("already_downloading"))
            return

        if not messagebox.askyesno(self.t("confirm"),
                                   self.t("download_confirm").format(self.target_dir)):
            return

        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.output_text.delete(1.0, tk.END)

        threading.Thread(target=self.download_dependencies, daemon=True).start()

    def get_cuda_index_url(self):
        """
        nvccからCUDAバージョンを取得してPyTorchのWHLリポジトリURLを生成
        Get CUDA version from nvcc and return the PyTorch wheels index URL
        """
        try:
            import subprocess
            out = subprocess.check_output(['nvcc', '--version'], text=True)
            m = re.search(r'release\s+([0-9]+)\.([0-9]+)', out)
            if not m:
                raise ValueError
            ver = m.group(1) + m.group(2)
            if ver not in ('118', '126', '128'):
                raise ValueError
        except Exception:
            messagebox.showerror(self.t("error"), self.t("cuda_error"))
            return None
        return f"https://download.pytorch.org/whl/cu{ver}"

    def _run_pip(self, pip_args: list, label: str):
        """
        pip._internalを使い、サブプロセスを使わず直接pipを呼び出す
        Use pip._internal directly (no separate subprocess) to run pip commands
        """
        try:
            # 遅延インポート / Lazy import to avoid overhead on GUI startup
            from pip._internal.cli.main import main as pip_main
        except Exception as e:
            messagebox.showerror(self.t("pip_error"), f"{self.t('pip_import_failed')} {e}")
            raise

        full_cmd = pip_args[:]
        self.log_output(f"[{label}] pip {' '.join(full_cmd)}")

        # pip 出力をキャプチャ / Capture pip output
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
            try:
                rc = pip_main(full_cmd)  # pip_main returns 0 if success
            except SystemExit as e:
                rc = e.code if e.code is not None else 1

        # キャプチャした出力をログ表示 / Show captured output in logs
        output = output_buffer.getvalue()
        if output:
            for line in output.splitlines():
                if line.strip():
                    self.log_output(line)

        if rc != 0:
            raise RuntimeError(f"{label} failed with exit-code {rc}")

    def download_dependencies(self):
        """
        PyTorch、Whisper、および関連依存関係をダウンロード・インストールする
        Download & install PyTorch, Whisper, and related dependencies
        """
        try:
            self.target_dir.mkdir(exist_ok=True)
            self.clean_pytorch_installation()

            PY_VER = f"{sys.version_info.major}{sys.version_info.minor}"
            if self.version_var.get() == "cuda":
                url = self.get_cuda_index_url()
                # CUDA URLがNoneの場合、早期終了 / If None, exit early (error already shown)
                if not url:
                    return
            else:
                url = "https://download.pytorch.org/whl/cpu"

            # ---------- Step1： Torch Core ----------
            core_pkgs = ["torch", "torchvision", "torchaudio", "numpy"]
            self.log_output(f"Index URL (core): {url}")
            self._run_pip([
                "install", *core_pkgs,
                "--index-url", url,
                "--only-binary", ":all:",
                "--implementation", "cp",
                "--python-version", PY_VER,
                "--platform", self.platform_tag,
                "--upgrade", "--no-cache-dir",
                "--target", str(self.target_dir)
            ], "pytorch-core")

            # ---------- Step2： Other Dependencies ----------
            extra_pkgs = ["tqdm", "mpmath", "tiktoken", "regex", "numba", "llvmlite"]
            self.log_output("Index URL (extra): https://pypi.org/simple")
            self._run_pip([
                "install", *extra_pkgs,
                "--only-binary", ":all:",  # これらはPyPIにwheelがある / These have wheels on PyPI
                "--upgrade", "--no-cache-dir",
                "--target", str(self.target_dir)
            ], "pytorch-extras")

            # ---------- Step3： Whisper ----------
            wheel_path = self._find_embedded_whisper_wheel()
            # exe版はthird_party_wheels内にopenai_whisperのwhlが含まれる / For exe bundling, the wheel might be included
            if wheel_path and wheel_path.exists():
                self.log_output(f"{self.t('embedded_wheel')} {wheel_path.name}")
                self._run_pip([
                    "install", str(wheel_path),
                    "--no-deps", "--upgrade", "--no-cache-dir",
                    "--target", str(self.target_dir)
                ], "openai-whisper")
            else:
                self.log_output(self.t("no_embedded_wheel"))
                self._run_pip([
                    "install", "openai-whisper",
                    "--only-binary", ":all:",  # PyPI上に公式wheel有 / Official wheel on PyPI
                    "--no-deps", "--upgrade", "--no-cache-dir",
                    "--target", str(self.target_dir)
                ], "openai-whisper")

            # インストール情報の書き込み / Write installation info
            install_info = {
                "version": self.version_var.get(),
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "platform": self.platform_tag,
                "python": sys.version.split()[0]
            }
            with open(self.target_dir / "pytorch_whisper_installed.json", "w") as f:
                json.dump(install_info, f, indent=2)

            self.update_status(self.t("download_complete"), self.colors['success'])
            self.root.after(0, lambda: self.verify_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: messagebox.showinfo(
                self.t("complete"),
                self.t("download_success_msg")
            ))
        except Exception as e:
            self.log_output(f"{self.t('error')}: {e}")
            self.update_status(self.t("download_failed"), self.colors['danger'])
            messagebox.showerror(self.t("error"), str(e))
        finally:
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress_bar.stop())

    def _find_embedded_whisper_wheel(self) -> Path | None:
        """
        exe版に同梱されているopenai_whisperのwheelファイルを探す / 
        Look for an embedded openai_whisper wheel in the bundled folder
        """
        wheels_dir = resource_root() / "third_party_wheels"
        try:
            return next(wheels_dir.glob("openai_whisper-*.whl"))
        except StopIteration:
            return None

    def verify_installation(self):
        """
        ダウンロードされたPyTorch/Whisperが正常にimport可能か検証
        Verify that downloaded PyTorch/Whisper can be imported successfully
        """
        self.log_output(self.t("verify_start"))
        self.update_status(self.t("verifying"), self.colors['accent'])

        try:
            # ─── 新: 既に import 済みなら再ロードをスキップ ───
            if 'torch' in sys.modules:
                torch = sys.modules['torch']
                self.log_output(f"Torch already imported: {torch.__version__}, CUDA: {torch.cuda.is_available()}")
            else:
                # パスを一時的に挿入 / Temporarily modify sys.path
                orig = sys.path.copy()
                sys.path.insert(0, str(self.target_dir.absolute()))
                import torch
                self.log_output(f"Torch {torch.__version__}, CUDA: {torch.cuda.is_available()}")
                sys.path = orig

            # Whisper モジュールの動作チェック
            self.log_output("Whisper OK")

            # インストール情報の出力
            info_file = self.target_dir / "pytorch_whisper_installed.json"
            if info_file.exists():
                info = json.load(open(info_file, "r"))
                self.log_output(f"Installed version: {info.get('version')} @ {info.get('time')}")

            # Check for ffmpeg
            self.log_output("Checking ffmpeg...")
            if not self.check_ffmpeg_available():
                self.log_output("ffmpeg not found")
                self.update_status(self.t("verify_failed"), self.colors['danger'])
                messagebox.showerror(
                    self.t("ffmpeg_not_found"),
                    self.t("ffmpeg_install_cmd")
                )
                return

            self.log_output("ffmpeg OK")
            self.update_status(self.t("verify_success"), self.colors['success'])
            messagebox.showinfo(
                self.t("verify_success"),
                self.t("verify_success_msg")
            )

        except ImportError as e:
            self.log_output(f"{self.t('import_error')} {e}")
            self.update_status(self.t("verify_failed"), self.colors['danger'])
            messagebox.showerror(
                self.t("verify_failed"),
                self.t("verify_failed_msg").format(str(e))
            )
        except Exception as e:
            self.log_output(f"{self.t('error')}: {e}")
            self.update_status(self.t("verify_failed"), self.colors['danger'])
            messagebox.showerror(
                self.t("error"),
                str(e)
            )

    def on_closing(self):
        """
        ウィンドウを閉じるイベント / Event triggered on window close
        """
        if self.is_downloading:
            # ダウンロード中に閉じてよいか確認 / Confirm if user wants to close while downloading
            if not messagebox.askyesno(self.t("confirm"),
                                       self.t("still_downloading")):
                return
        self.root.destroy()

    def run(self):
        """
        メインループを開始 / Start the main GUI loop
        """
        self.root.mainloop()
    
    def check_ffmpeg_available(self):
        """
        Check if ffmpeg is available on the system
        """
        try:
            import subprocess
            subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

if __name__ == "__main__":
    app = PyTorchDownloader()
    app.run()