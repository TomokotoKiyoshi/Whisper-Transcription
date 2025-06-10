import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import io
import re
import queue
import subprocess
import platform

# Dynamic library loading configuration
PYTORCH_DIR = Path("pytorch_libs")
WHISPER_AVAILABLE = False
whisper = None
torch = None

def setup_pytorch_path():
    """Setup PyTorch library path for dynamic loading"""
    global WHISPER_AVAILABLE, whisper, torch
    
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent
    
    PYTORCH_DIR = base_path / "pytorch_libs"
    
    if PYTORCH_DIR.exists():
        pytorch_path = str(PYTORCH_DIR.absolute())
        if pytorch_path not in sys.path:
            sys.path.insert(0, pytorch_path)
        
        try:
            import torch as torch_module
            import whisper as whisper_module
            torch = torch_module
            whisper = whisper_module
            WHISPER_AVAILABLE = True
            print(f"Successfully loaded PyTorch from: {pytorch_path}")
            return True
        except ImportError as e:
            print(f"Failed to import PyTorch/Whisper: {e}")
            return False
    else:
        print(f"PyTorch directory not found at: {PYTORCH_DIR}")
    return False

class ProgressCapture(io.StringIO):
    """Custom StringIO class to capture and parse Whisper progress output"""
    def __init__(self, callback, segment_callback=None, text_callback=None):
        super().__init__()
        self.callback = callback
        self.segment_callback = segment_callback
        self.text_callback = text_callback
        self.buffer = ""
        self.current_segment = ""
        
    def write(self, text):
        super().write(text)
        self.buffer += text
        self.current_segment += text
    
        lines = self.current_segment.split('\n')
        complete = lines[:-1]
        self.current_segment = lines[-1]
        
        for line in complete:
            self.process_line(line)
    
        return len(text)
    
    def process_line(self, text):
        """Process a line of text for patterns"""
        progress_pattern = r'(\d+)%\s*\|[^|]*\|\s*(\d+)/(\d+)'
        match = re.search(progress_pattern, text)
        
        if match:
            percentage = int(match.group(1))
            current_frames = int(match.group(2))
            total_frames = int(match.group(3))
            
            time_pattern = r'\[(\d+:\d+)<(\d+:\d+),'
            time_match = re.search(time_pattern, text)
            
            elapsed_str = ""
            remaining_str = ""
            
            if time_match:
                elapsed_str = time_match.group(1)
                remaining_str = time_match.group(2)
            
            if self.callback:
                self.callback(percentage, current_frames, total_frames, elapsed_str, remaining_str)
        
        segment_pattern = r'\[(\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}\.\d{3})\]\s*(.+?)(?=\n|\Z)'
        segment_matches = re.finditer(segment_pattern, text, re.DOTALL)
        
        for segment_match in segment_matches:
            start_time_str = segment_match.group(1)
            end_time_str = segment_match.group(2)
            segment_text = segment_match.group(3).strip()
            
            def time_str_to_seconds(time_str):
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            
            end_seconds = time_str_to_seconds(end_time_str)
            
            if self.segment_callback:
                self.segment_callback(end_seconds)
            
            if self.text_callback and segment_text:
                self.text_callback(start_time_str, end_time_str, segment_text)

class AudioSubtitleSystem:
    """Audio Transcription System with multilingual support and responsive design"""
    def __init__(self):
        # State management
        self.current_file = None
        self.transcription_results = []
        self.whisper_model = None
        self.device = "cuda"
        self.audio_duration = 0
        self.transcription_start_time = None
        self.is_transcribing = False
        self.is_downloading = False
        self.is_loading_model = False
        self.update_timer = None
        self.original_stderr = None
        self.message_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.current_language = "en"  # Default language
        
        # Initialize translations
        self.init_translations()
        
        # Model processing speed factors
        self.model_speed_factors = {
            "tiny": 0.5,
            "base": 0.8,
            "small": 1.2,
            "medium": 2.0,
            "large": 3.5,
            "large-v2": 3.5,
            "large-v3": 3.5,
            "large-v3-turbo": 2.5
        }
        
        # Color theme
        self.colors = {
            'primary': '#2E3440',
            'accent': '#5E81AC',
            'success': '#A3BE8C',
            'warning': '#EBCB8B',
            'danger': '#BF616A',
            'text': '#2E3440',
            'text_light': '#4C566A',
            'background': '#ECEFF4',
            'surface': '#FFFFFF',
            'border': '#D8DEE9'
        }

        # Check for PyTorch/Whisper availability
        self.check_dependencies()
        
        # Setup GUI with responsive design
        self.setup_responsive_gui()

    def init_translations(self):
        """Initialize all UI text translations"""
        self.translations = {
            "en": {
                "window_title": "Audio Subtitle System",
                "header_title": "Audio Subtitle System",
                "header_subtitle": "Audio Transcription & Subtitle Generation",
                "language": "Language:",
                "audio_file_selection": "Audio File Selection:",
                "select_file": "📁 Select Audio File",
                "start_transcription": "🎯 Start Transcription",
                "no_file_selected": "No file selected",
                "adjust_parameters": "⚙️ Adjust Parameters",
                "parameter_settings": "Parameter Settings",
                "ok": "OK",
                "parameters_updated": "Parameters updated:",
                "dependency_warning": "⚠️ PyTorch/Whisper Not Installed",
                "dependency_message": "Please run PyTorch Downloader to install required dependencies",
                "run_downloader": "🔧 Run PyTorch Downloader",
                "recheck": "🔄 Recheck",
                "whisper_model": "Whisper Model Selection:",
                "keyword_optional": "Keyword (Optional):",
                "transcription_language": "Transcription Language:",
                "system_status": "System Status:",
                "waiting_to_start": "Waiting to Start",
                "elapsed": "Elapsed:",
                "duration": "Duration:",
                "transcription_output": "Transcription Output:",
                "clear": "🗑️ Clear",
                "save_transcription": "💾 Save Transcription",
                "save_subtitle": "🎬 Save Subtitle File",
                "warning": "Warning",
                "error": "Error",
                "success": "Success",
                "info": "Info",
                "confirm": "Confirm",
                "please_select_audio": "Please select an audio file",
                "whisper_not_installed": "Whisper not installed, please run PyTorch Downloader first",
                "starting_transcription": "Starting audio transcription...",
                "preparing": "Preparing...",
                "transcription_complete": "Transcription complete! Segments: {}, Processing time: {}",
                "transcription_completed": "Transcription completed",
                "transcription_success": "Transcription completed successfully",
                "transcription_error": "Transcription error:",
                "model_download_confirm": "{} model ({}) not found. Download now?",
                "model_download_title": "Download Model?",
                "model_download_cancelled": "Model download cancelled",
                "downloading_model": "Downloading model: {} ({})",
                "loading_model": "Loading model: {}",
                "model_loaded": "Model '{}' loaded successfully (Device: {})",
                "model_loading_error": "Model loading error",
                "model_loading_failed": "Model loading failed:",
                "downloader_launched": "PyTorch Downloader launched",
                "downloader_launch_failed": "Failed to launch downloader:",
                "downloader_not_found": "Cannot find pytorch_downloader.exe or .py",
                "dependencies_loaded": "PyTorch/Whisper loaded successfully!",
                "dependencies_not_installed": "PyTorch/Whisper still not installed",
                "no_results_to_save": "No transcription results to save",
                "save_as": "Save As",
                "results_saved": "Transcription results saved:",
                "subtitle_saved": "Subtitle file saved:",
                "save_error": "Save error:",
                "no_subtitles": "No subtitles to save",
                "file_selected": "Audio file selected: {} (Estimated time: {})",
                "file_selected_no_duration": "Audio file selected: {} (Whisper not installed, cannot get duration)",
                "model_not_found": "Model '{}' not found. Checking download...",
                "confirming_download": "Confirming model download: {}",
                "unable_to_get_duration": "Unable to get audio duration:",
                "downloading": "Downloading model '{}' (Size: {})",
                "loading": "Loading model '{}'...",
                "language_codes": {
                    "ja": "Japanese",
                    "en": "English", 
                    "zh": "Chinese",
                    "ko": "Korean",
                    "es": "Spanish",
                    "fr": "French",
                    "de": "German",
                    "ru": "Russian",
                    "auto": "Auto-detect"
                }
            },
            "ja": {
                "window_title": "音声字幕システム",
                "header_title": "音声字幕システム",
                "header_subtitle": "音声ファイルの転写と字幕生成",
                "language": "言語:",
                "audio_file_selection": "音声ファイル選択:",
                "select_file": "📁 ファイルを選択",
                "start_transcription": "🎯 転写開始",
                "no_file_selected": "ファイル未選択",
                "adjust_parameters": "⚙️ 調整パラメータ",
                "parameter_settings": "パラメータ設定",
                "ok": "OK",
                "parameters_updated": "パラメータ更新済み:",
                "dependency_warning": "⚠️ PyTorch/Whisperがインストールされていません",
                "dependency_message": "必要な依存関係をインストールするにはPyTorchダウンローダを実行してください",
                "run_downloader": "🔧 PyTorchダウンローダを実行",
                "recheck": "🔄 再チェック",
                "whisper_model": "Whisperモデル選択:",
                "keyword_optional": "キーワード (オプション):",
                "transcription_language": "転写言語:",
                "system_status": "システム状態:",
                "waiting_to_start": "開始待ち",
                "elapsed": "経過時間:",
                "duration": "音声長さ:",
                "transcription_output": "転写結果:",
                "clear": "🗑️ クリア",
                "save_transcription": "💾 転写結果を保存",
                "save_subtitle": "🎬 字幕ファイルを保存",
                "warning": "警告",
                "error": "エラー",
                "success": "成功",
                "info": "情報",
                "confirm": "確認",
                "please_select_audio": "音声ファイルを選択してください",
                "whisper_not_installed": "Whisperがインストールされていません。先にPyTorchダウンローダを実行してください",
                "starting_transcription": "音声の転写を開始します...",
                "preparing": "準備中...",
                "transcription_complete": "転写が完了しました！ セグメント数: {}, 処理時間: {}",
                "transcription_completed": "転写完了",
                "transcription_success": "転写が完了しました",
                "transcription_error": "転写エラーが発生しました:",
                "model_download_confirm": "{}モデル({})が見つかりません。ダウンロードしますか？",
                "model_download_title": "モデルをダウンロードしますか？",
                "model_download_cancelled": "モデルダウンロードがキャンセルされました",
                "downloading_model": "モデルダウンロード中: {} ({})",
                "loading_model": "モデル読み込み中: {}",
                "model_loaded": "モデル'{}'の読み込みが完了しました (デバイス: {})",
                "model_loading_error": "モデル読み込みエラー",
                "model_loading_failed": "モデル読み込みに失敗しました:",
                "downloader_launched": "PyTorchダウンローダを起動しました",
                "downloader_launch_failed": "ダウンローダを起動できません:",
                "downloader_not_found": "pytorch_downloader.exeまたは.pyが見つかりません",
                "dependencies_loaded": "PyTorch/Whisperが正常にロードされました！",
                "dependencies_not_installed": "PyTorch/Whisperはまだインストールされていません",
                "no_results_to_save": "保存する転写結果がありません",
                "save_as": "名前を付けて保存",
                "results_saved": "転写結果が保存されました:",
                "subtitle_saved": "字幕ファイルが保存されました:",
                "save_error": "保存エラーが発生しました:",
                "no_subtitles": "保存する字幕がありません",
                "file_selected": "音声ファイルが選択されました: {} (推定時間: {})",
                "file_selected_no_duration": "音声ファイルが選択されました: {} (Whisperがインストールされていないため長さ取得不可)",
                "model_not_found": "モデル'{}'が見つかりません。ダウンロード確認中...",
                "confirming_download": "モデルダウンロードを確認中: {}",
                "unable_to_get_duration": "音声長を取得できません:",
                "downloading": "モデル'{}'をダウンロードしています... (サイズ: {})",
                "loading": "モデル'{}'を読み込み中...",
                "language_codes": {
                    "ja": "日本語",
                    "en": "英語",
                    "zh": "中国語",
                    "ko": "韓国語",
                    "es": "スペイン語",
                    "fr": "フランス語",
                    "de": "ドイツ語",
                    "ru": "ロシア語",
                    "auto": "自動検出"
                }
            },
            "zh": {
                "window_title": "音频字幕系统",
                "header_title": "音频字幕系统",
                "header_subtitle": "音频转录和字幕生成",
                "language": "语言:",
                "audio_file_selection": "音频文件选择:",
                "select_file": "📁 选择音频文件",
                "start_transcription": "🎯 开始转录",
                "no_file_selected": "未选择文件",
                "adjust_parameters": "⚙️ 调整参数",
                "parameter_settings": "参数设置",
                "ok": "确定",
                "parameters_updated": "参数已更新:",
                "dependency_warning": "⚠️ PyTorch/Whisper 未安装",
                "dependency_message": "请运行 PyTorch 下载器以安装所需的依赖项",
                "run_downloader": "🔧 运行 PyTorch 下载器",
                "recheck": "🔄 重新检查",
                "whisper_model": "Whisper 模型选择:",
                "keyword_optional": "关键词 (可选):",
                "transcription_language": "转录语言:",
                "system_status": "系统状态:",
                "waiting_to_start": "等待开始",
                "elapsed": "已用时间:",
                "duration": "音频时长:",
                "transcription_output": "转录输出:",
                "clear": "🗑️ 清除",
                "save_transcription": "💾 保存转录结果",
                "save_subtitle": "🎬 保存字幕文件",
                "warning": "警告",
                "error": "错误",
                "success": "成功",
                "info": "信息",
                "confirm": "确认",
                "please_select_audio": "请选择音频文件",
                "whisper_not_installed": "Whisper 未安装，请先运行 PyTorch 下载器",
                "starting_transcription": "开始音频转录...",
                "preparing": "准备中...",
                "transcription_complete": "转录完成！片段数: {}，处理时间: {}",
                "transcription_completed": "转录完成",
                "transcription_success": "转录成功完成",
                "transcription_error": "转录错误:",
                "model_download_confirm": "{} 模型 ({}) 未找到。现在下载吗？",
                "model_download_title": "下载模型？",
                "model_download_cancelled": "模型下载已取消",
                "downloading_model": "正在下载模型: {} ({})",
                "loading_model": "正在加载模型: {}",
                "model_loaded": "模型 '{}' 加载成功 (设备: {})",
                "model_loading_error": "模型加载错误",
                "model_loading_failed": "模型加载失败:",
                "downloader_launched": "PyTorch 下载器已启动",
                "downloader_launch_failed": "无法启动下载器:",
                "downloader_not_found": "找不到 pytorch_downloader.exe 或 .py",
                "dependencies_loaded": "PyTorch/Whisper 加载成功！",
                "dependencies_not_installed": "PyTorch/Whisper 仍未安装",
                "no_results_to_save": "没有要保存的转录结果",
                "save_as": "另存为",
                "results_saved": "转录结果已保存:",
                "subtitle_saved": "字幕文件已保存:",
                "save_error": "保存错误:",
                "no_subtitles": "没有要保存的字幕",
                "file_selected": "已选择音频文件: {} (预计时间: {})",
                "file_selected_no_duration": "已选择音频文件: {} (Whisper 未安装，无法获取时长)",
                "model_not_found": "未找到模型 '{}'。正在检查下载...",
                "confirming_download": "确认模型下载: {}",
                "unable_to_get_duration": "无法获取音频时长:",
                "downloading": "正在下载模型 '{}' (大小: {})",
                "loading": "正在加载模型 '{}'...",
                "language_codes": {
                    "ja": "日语",
                    "en": "英语",
                    "zh": "中文",
                    "ko": "韩语",
                    "es": "西班牙语",
                    "fr": "法语",
                    "de": "德语",
                    "ru": "俄语",
                    "auto": "自动检测"
                }
            },
            "ko": {
                "window_title": "오디오 자막 시스템",
                "header_title": "오디오 자막 시스템",
                "header_subtitle": "오디오 전사 및 자막 생성",
                "language": "언어:",
                "audio_file_selection": "오디오 파일 선택:",
                "select_file": "📁 오디오 파일 선택",
                "start_transcription": "🎯 전사 시작",
                "no_file_selected": "파일이 선택되지 않음",
                "adjust_parameters": "⚙️ 매개변수 조정",
                "parameter_settings": "매개변수 설정",
                "ok": "확인",
                "parameters_updated": "매개변수 업데이트됨:",
                "dependency_warning": "⚠️ PyTorch/Whisper가 설치되지 않음",
                "dependency_message": "필요한 종속성을 설치하려면 PyTorch 다운로더를 실행하세요",
                "run_downloader": "🔧 PyTorch 다운로더 실행",
                "recheck": "🔄 다시 확인",
                "whisper_model": "Whisper 모델 선택:",
                "keyword_optional": "키워드 (선택 사항):",
                "transcription_language": "전사 언어:",
                "system_status": "시스템 상태:",
                "waiting_to_start": "시작 대기 중",
                "elapsed": "경과 시간:",
                "duration": "오디오 길이:",
                "transcription_output": "전사 출력:",
                "clear": "🗑️ 지우기",
                "save_transcription": "💾 전사 결과 저장",
                "save_subtitle": "🎬 자막 파일 저장",
                "warning": "경고",
                "error": "오류",
                "success": "성공",
                "info": "정보",
                "confirm": "확인",
                "please_select_audio": "오디오 파일을 선택하세요",
                "whisper_not_installed": "Whisper가 설치되지 않았습니다. 먼저 PyTorch 다운로더를 실행하세요",
                "starting_transcription": "오디오 전사를 시작합니다...",
                "preparing": "준비 중...",
                "transcription_complete": "전사 완료! 세그먼트: {}, 처리 시간: {}",
                "transcription_completed": "전사 완료",
                "transcription_success": "전사가 성공적으로 완료되었습니다",
                "transcription_error": "전사 오류:",
                "model_download_confirm": "{} 모델 ({})을 찾을 수 없습니다. 지금 다운로드하시겠습니까?",
                "model_download_title": "모델 다운로드?",
                "model_download_cancelled": "모델 다운로드가 취소되었습니다",
                "downloading_model": "모델 다운로드 중: {} ({})",
                "loading_model": "모델 로드 중: {}",
                "model_loaded": "'{}' 모델이 성공적으로 로드되었습니다 (장치: {})",
                "model_loading_error": "모델 로드 오류",
                "model_loading_failed": "모델 로드 실패:",
                "downloader_launched": "PyTorch 다운로더가 시작되었습니다",
                "downloader_launch_failed": "다운로더를 시작할 수 없습니다:",
                "downloader_not_found": "pytorch_downloader.exe 또는 .py를 찾을 수 없습니다",
                "dependencies_loaded": "PyTorch/Whisper가 성공적으로 로드되었습니다!",
                "dependencies_not_installed": "PyTorch/Whisper가 아직 설치되지 않았습니다",
                "no_results_to_save": "저장할 전사 결과가 없습니다",
                "save_as": "다른 이름으로 저장",
                "results_saved": "전사 결과 저장됨:",
                "subtitle_saved": "자막 파일 저장됨:",
                "save_error": "저장 오류:",
                "no_subtitles": "저장할 자막이 없습니다",
                "file_selected": "오디오 파일 선택됨: {} (예상 시간: {})",
                "file_selected_no_duration": "오디오 파일 선택됨: {} (Whisper가 설치되지 않아 길이를 가져올 수 없음)",
                "model_not_found": "'{}' 모델을 찾을 수 없습니다. 다운로드 확인 중...",
                "confirming_download": "모델 다운로드 확인 중: {}",
                "unable_to_get_duration": "오디오 길이를 가져올 수 없습니다:",
                "downloading": "'{}' 모델 다운로드 중... (크기: {})",
                "loading": "'{}' 모델 로드 중...",
                "language_codes": {
                    "ja": "일본어",
                    "en": "영어",
                    "zh": "중국어", 
                    "ko": "한국어",
                    "es": "스페인어",
                    "fr": "프랑스어",
                    "de": "독일어",
                    "ru": "러시아어",
                    "auto": "자동 감지"
                }
            }
        }

    def t(self, key):
        """Get translated text for current language"""
        return self.translations.get(self.current_language, self.translations["en"]).get(key, key)

    def check_dependencies(self):
        """Check if PyTorch and Whisper are available"""
        global WHISPER_AVAILABLE
        
        if not setup_pytorch_path():
            WHISPER_AVAILABLE = False
        else:
            if torch and torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

    def calculate_scaling(self):
        """Calculate scaling factors based on screen size"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Base dimensions for scaling (designed for 1920x1080)
        base_width = 1920
        base_height = 1080
        
        # Calculate scaling factors
        self.scale_x = screen_width / base_width
        self.scale_y = screen_height / base_height
        self.scale = min(self.scale_x, self.scale_y)  # Use minimum to maintain aspect ratio
        
        # Ensure minimum scaling
        self.scale = max(self.scale, 0.75)
        
        # Font scaling
        self.base_font_sizes = {
            'title': 22,
            'header': 13,
            'normal': 11,
            'small': 10
        }
        
        self.scaled_fonts = {}
        for key, size in self.base_font_sizes.items():
            self.scaled_fonts[key] = max(int(size * self.scale), 8)
        
        # Widget dimensions
        self.scaled_dimensions = {
            'window_width': int(1000 * self.scale),
            'window_height': int(1000 * self.scale),
            'min_width': int(800 * self.scale),
            'min_height': int(700 * self.scale),
            'padding_large': int(15 * self.scale),
            'padding_medium': int(12 * self.scale),
            'padding_small': int(8 * self.scale),
            'button_padding_x': int(20 * self.scale),
            'button_padding_y': int(10 * self.scale),
            'entry_padding': int(12 * self.scale),
            'progress_length': int(500 * self.scale),
            'output_height': int(8 * self.scale),
            'combo_width': int(30 * self.scale),
            'lang_combo_width': int(10 * self.scale)
        }

    def setup_responsive_gui(self):
        self.root = tk.Tk()
        self.root.title(self.t("window_title"))
        
        # Calculate scaling before setting up GUI
        self.calculate_scaling()
        
        # Set window size based on screen dimensions
        window_width = self.scaled_dimensions['window_width']
        window_height = self.scaled_dimensions['window_height']
        min_width = self.scaled_dimensions['min_width']
        min_height = self.scaled_dimensions['min_height']
        
        # Set minimum window size
        self.root.minsize(min_width, min_height)
        
        # Center window on screen
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.update_idletasks()
        
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (window_width // 2)
        y = (hs // 2) - (window_height // 2) - 20
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.root.configure(bg=self.colors['background'])
        
        # Configure grid weights for responsive layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_responsive_styles()

        # Main container with responsive padding
        main = tk.Frame(self.root, bg=self.colors['background'])
        main.pack(fill=tk.BOTH, expand=True, 
                  padx=self.scaled_dimensions['padding_large'], 
                  pady=self.scaled_dimensions['padding_large'])

        # Create responsive sections
        self.create_responsive_header(main)
        self.create_responsive_file_section(main)
        
        if not WHISPER_AVAILABLE:
            self.create_responsive_dependency_warning(main)
            
        self.create_responsive_model_section(main)
        self.create_responsive_topic_section(main)
        self.create_responsive_status_section(main)
        self.create_responsive_transcription_output_section(main)
        self.create_responsive_save_section(main)

        # Bind resize event for dynamic updates
        self.root.bind('<Configure>', self.on_window_resize)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_message_queue()
        self.update_status(self.t("waiting_to_start"), self.colors['text_light'])

    def on_window_resize(self, event=None):
        """Handle window resize events"""
        if hasattr(self, '_last_resize_time'):
            # Debounce resize events
            if time.time() - self._last_resize_time < 0.1:
                return
        self._last_resize_time = time.time()

    def configure_responsive_styles(self):
        """Configure styles with responsive dimensions"""
        button_pad_x = self.scaled_dimensions['button_padding_x']
        button_pad_y = self.scaled_dimensions['button_padding_y']
        
        self.style.configure('Primary.TButton',
                             background=self.colors['accent'],
                             foreground='white',
                             borderwidth=0,
                             focuscolor='none',
                             padding=(button_pad_x, button_pad_y),
                             font=('Yu Gothic', self.scaled_fonts['normal']))
        self.style.map('Primary.TButton',
                       background=[('active', '#4C7EA3'),
                                   ('pressed', '#3E6D8F')])
        
        self.style.configure('Success.TButton',
                             background=self.colors['success'],
                             foreground='white',
                             borderwidth=0,
                             focuscolor='none',
                             padding=(button_pad_x, button_pad_y),
                             font=('Yu Gothic', self.scaled_fonts['normal']))
        
        self.style.configure('Danger.TButton',
                             background=self.colors['danger'],
                             foreground='white',
                             borderwidth=0,
                             focuscolor='none',
                             padding=(button_pad_x, button_pad_y),
                             font=('Yu Gothic', self.scaled_fonts['normal']))
        
        entry_pad = self.scaled_dimensions['entry_padding']
        self.style.configure('Modern.TEntry',
                             fieldbackground=self.colors['surface'],
                             borderwidth=2,
                             relief='solid',
                             bordercolor=self.colors['border'],
                             padding=(entry_pad, entry_pad // 2),
                             font=('Yu Gothic', self.scaled_fonts['normal']))

    def create_responsive_header(self, parent):
        """Create header with responsive layout"""
        hf = tk.Frame(parent, bg=self.colors['background'])
        hf.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_large']))
        
        # Create a frame for the subtitle and language selector
        title_frame = tk.Frame(hf, bg=self.colors['background'])
        title_frame.pack(fill=tk.X)
        
        # Left side - subtitle only
        left_frame = tk.Frame(title_frame, bg=self.colors['background'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.header_subtitle_label = tk.Label(
            left_frame, 
            text=self.t("header_subtitle"),
            font=('Segoe UI', self.scaled_fonts['header'], 'bold'),
            fg=self.colors['text'], 
            bg=self.colors['background']
        )
        self.header_subtitle_label.pack()
        
        # Right side - language selector
        lang_frame = tk.Frame(title_frame, bg=self.colors['background'])
        lang_frame.pack(side=tk.RIGHT, padx=self.scaled_dimensions['padding_medium'])
        
        self.lang_label = tk.Label(
            lang_frame,
            text=self.t("language"),
            font=('Yu Gothic', self.scaled_fonts['small']),
            fg=self.colors['text'],
            bg=self.colors['background']
        )
        self.lang_label.pack(side=tk.LEFT, padx=(0, self.scaled_dimensions['padding_small'] // 2))
        
        # Language display names
        self.language_display = {
            "en": "en - English",
            "ja": "ja - 日本語",
            "zh": "cn - 中文",
            "ko": "ko - 한국어"
        }
        
        self.ui_language_var = tk.StringVar(value=self.language_display[self.current_language])
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.ui_language_var,
            values=list(self.language_display.values()),
            state="readonly",
            width=self.scaled_dimensions['lang_combo_width'],
            font=('Segoe UI', self.scaled_fonts['small'])
        )
        self.language_combo.pack(side=tk.LEFT)
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_change)

    def create_responsive_file_section(self, parent):
        """Create file section with responsive layout"""
        ff = tk.Frame(parent, bg=self.colors['surface'], relief='solid', bd=1)
        ff.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_medium']))
        
        inner = tk.Frame(ff, bg=self.colors['surface'])
        inner.pack(fill=tk.X, 
                   padx=self.scaled_dimensions['padding_large'], 
                   pady=self.scaled_dimensions['padding_medium'])
        
        # Header row with title on left and parameter button on right
        header_row = tk.Frame(inner, bg=self.colors['surface'])
        header_row.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_small'] // 2))
        
        self.file_section_label = tk.Label(
            header_row, 
            text=self.t("audio_file_selection"),
            font=('Yu Gothic', self.scaled_fonts['header'], 'bold'),
            fg=self.colors['text'], 
            bg=self.colors['surface']
        )
        self.file_section_label.pack(side=tk.LEFT)
        
        self.param_btn = ttk.Button(
            header_row,
            text=self.t("adjust_parameters"),
            command=self.open_parameter_window,
            style='Primary.TButton'
        )
        self.param_btn.pack(side=tk.RIGHT)
        
        btnf = tk.Frame(inner, bg=self.colors['surface'])
        btnf.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_small']))
        
        self.select_file_btn = ttk.Button(
            btnf,
            text=self.t("select_file"),
            command=self.select_audio_file,
            style='Primary.TButton'
        )
        self.select_file_btn.pack(side=tk.LEFT, padx=(0, self.scaled_dimensions['padding_medium']))
        
        self.transcribe_btn = ttk.Button(
            btnf,
            text=self.t("start_transcription"),
            command=self.transcribe_audio,
            style='Success.TButton',
            state=tk.DISABLED if not WHISPER_AVAILABLE else tk.DISABLED
        )
        self.transcribe_btn.pack(side=tk.LEFT)
        
        self.file_path_label = tk.Label(
            inner,
            text=self.t("no_file_selected"),
            font=('Yu Gothic', self.scaled_fonts['small']),
            fg=self.colors['text_light'],
            bg=self.colors['surface']
        )
        self.file_path_label.pack(anchor=tk.W)


    def create_responsive_dependency_warning(self, parent):
        """Create responsive warning section for missing dependencies"""
        wf = tk.Frame(parent, bg=self.colors['warning'], relief='solid', bd=2)
        wf.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_large']))
        
        inner = tk.Frame(wf, bg=self.colors['warning'])
        inner.pack(fill=tk.X, 
                   padx=self.scaled_dimensions['padding_large'], 
                   pady=self.scaled_dimensions['padding_medium'])
        
        self.dep_warning_label = tk.Label(
            inner, 
            text=self.t("dependency_warning"),
            font=('Yu Gothic', self.scaled_fonts['header'], 'bold'),
            fg='white', 
            bg=self.colors['warning']
        )
        self.dep_warning_label.pack(anchor=tk.W, pady=(0, self.scaled_dimensions['padding_small'] // 2))
        
        self.dep_message_label = tk.Label(
            inner, 
            text=self.t("dependency_message"),
            font=('Yu Gothic', self.scaled_fonts['normal']),
            fg='white', 
            bg=self.colors['warning']
        )
        self.dep_message_label.pack(anchor=tk.W, pady=(0, self.scaled_dimensions['padding_medium']))
        
        btn_frame = tk.Frame(inner, bg=self.colors['warning'])
        btn_frame.pack(anchor=tk.W)
        
        self.run_downloader_btn = ttk.Button(
            btn_frame,
            text=self.t("run_downloader"),
            command=self.run_pytorch_downloader
        )
        self.run_downloader_btn.pack(side=tk.LEFT, padx=(0, self.scaled_dimensions['padding_medium']))
        
        self.recheck_btn = ttk.Button(
            btn_frame,
            text=self.t("recheck"),
            command=self.recheck_dependencies
        )
        self.recheck_btn.pack(side=tk.LEFT)

    def create_responsive_model_section(self, parent):
        """Create model section with responsive layout"""
        mf = tk.Frame(parent, bg=self.colors['surface'], relief='solid', bd=1)
        mf.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_medium']))
        
        inner = tk.Frame(mf, bg=self.colors['surface'])
        inner.pack(fill=tk.X, 
                   padx=self.scaled_dimensions['padding_large'], 
                   pady=self.scaled_dimensions['padding_medium'])
        
        self.model_section_label = tk.Label(
            inner, 
            text=self.t("whisper_model"),
            font=('Yu Gothic', self.scaled_fonts['header'], 'bold'),
            fg=self.colors['text'], 
            bg=self.colors['surface']
        )
        self.model_section_label.pack(anchor=tk.W, pady=(0, self.scaled_dimensions['padding_small'] // 2))
        
        self.model_var = tk.StringVar(value="large-v3")
        opts = ["tiny","base","small","medium","large","large-v2","large-v3","large-v3-turbo"]
        self.model_combo = ttk.Combobox(
            inner,
            textvariable=self.model_var,
            values=opts,
            font=('Yu Gothic', self.scaled_fonts['normal']),
            state="readonly" if WHISPER_AVAILABLE else "disabled",
            width=self.scaled_dimensions['combo_width']
        )
        self.model_combo.set("large-v3")
        self.model_combo.pack(fill=tk.X)

    def create_responsive_topic_section(self, parent):
        """Create topic section with responsive layout"""
        tf = tk.Frame(parent, bg=self.colors['surface'], relief='solid', bd=1)
        tf.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_medium']))
        
        inner = tk.Frame(tf, bg=self.colors['surface'])
        inner.pack(fill=tk.X, 
                   padx=self.scaled_dimensions['padding_large'], 
                   pady=self.scaled_dimensions['padding_medium'])
        
        self.keyword_label = tk.Label(
            inner, 
            text=self.t("keyword_optional"),
            font=('Yu Gothic', self.scaled_fonts['header'], 'bold'),
            fg=self.colors['text'], 
            bg=self.colors['surface']
        )
        self.keyword_label.pack(anchor=tk.W, pady=(0, self.scaled_dimensions['padding_small'] // 2))
        
        self.topic_entry = ttk.Entry(inner, font=('Yu Gothic', self.scaled_fonts['normal']), style='Modern.TEntry')
        self.topic_entry.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_medium']))
        
        self.trans_lang_label = tk.Label(
            inner, 
            text=self.t("transcription_language"),
            font=('Yu Gothic', self.scaled_fonts['header'], 'bold'),
            fg=self.colors['text'], 
            bg=self.colors['surface']
        )
        self.trans_lang_label.pack(anchor=tk.W, pady=(0, self.scaled_dimensions['padding_small'] // 2))
        
        self.transcription_lang_var = tk.StringVar(value="ja")
        self.transcription_language_combo = ttk.Combobox(
            inner,
            textvariable=self.transcription_lang_var,
            font=('Yu Gothic', self.scaled_fonts['normal']),
            state="readonly" if WHISPER_AVAILABLE else "disabled",
            width=self.scaled_dimensions['combo_width']
        )
        self.update_language_combo()
        self.transcription_language_combo.pack(fill=tk.X)

    def create_responsive_status_section(self, parent):
        """Create status section with responsive layout"""
        sf = tk.Frame(parent, bg=self.colors['surface'], relief='solid', bd=1)
        sf.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_medium']))
        
        sin = tk.Frame(sf, bg=self.colors['surface'])
        sin.pack(fill=tk.X, 
                 padx=self.scaled_dimensions['padding_large'], 
                 pady=self.scaled_dimensions['padding_medium'])
        
        row = tk.Frame(sin, bg=self.colors['surface'])
        row.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_small']))
        
        self.status_section_label = tk.Label(
            row, 
            text=self.t("system_status"),
            font=('Yu Gothic', self.scaled_fonts['normal'], 'bold'),
            fg=self.colors['text'], 
            bg=self.colors['surface']
        )
        self.status_section_label.pack(side=tk.LEFT)
        
        self.status_label = tk.Label(
            row,
            text=self.t("waiting_to_start"),
            font=('Yu Gothic', self.scaled_fonts['normal']),
            fg=self.colors['text_light'],
            bg=self.colors['surface']
        )
        self.status_label.pack(side=tk.RIGHT)
        
        self.progress_bar = ttk.Progressbar(
            sin, 
            length=self.scaled_dimensions['progress_length'], 
            mode='indeterminate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_small']))
        
        trow = tk.Frame(sin, bg=self.colors['surface'])
        trow.pack(fill=tk.X)
        
        self.elapsed_label = tk.Label(
            trow,
            text=f"{self.t('elapsed')} 00:00",
            font=('Yu Gothic', self.scaled_fonts['small']),
            fg=self.colors['text_light'],
            bg=self.colors['surface']
        )
        self.elapsed_label.pack(side=tk.LEFT)
        
        self.duration_label = tk.Label(
            trow,
            text=f"{self.t('duration')} 00:00",
            font=('Yu Gothic', self.scaled_fonts['small']),
            fg=self.colors['text_light'],
            bg=self.colors['surface']
        )
        self.duration_label.pack(side=tk.RIGHT)

    def create_responsive_transcription_output_section(self, parent):
        """Create the real-time transcription output section with responsive layout"""
        tf = tk.Frame(parent, bg=self.colors['surface'], relief='solid', bd=1)
        tf.pack(fill=tk.BOTH, expand=True, pady=(0, self.scaled_dimensions['padding_medium']))
        
        inner = tk.Frame(tf, bg=self.colors['surface'])
        inner.pack(fill=tk.BOTH, expand=True, 
                   padx=self.scaled_dimensions['padding_large'], 
                   pady=self.scaled_dimensions['padding_medium'])
        
        header_frame = tk.Frame(inner, bg=self.colors['surface'])
        header_frame.pack(fill=tk.X, pady=(0, self.scaled_dimensions['padding_small'] // 2))
        
        self.output_section_label = tk.Label(
            header_frame, 
            text=self.t("transcription_output"),
            font=('Yu Gothic', self.scaled_fonts['header'], 'bold'),
            fg=self.colors['text'], 
            bg=self.colors['surface']
        )
        self.output_section_label.pack(side=tk.LEFT)
        
        self.clear_output_btn = ttk.Button(
            header_frame,
            text=self.t("clear"),
            command=self.clear_transcription_output
        )
        self.clear_output_btn.pack(side=tk.RIGHT)
        
        # Calculate dynamic height for output text
        output_height = max(self.scaled_dimensions['output_height'], 6)
        
        self.output_text = scrolledtext.ScrolledText(
            inner,
            height=output_height,
            font=('Yu Gothic', self.scaled_fonts['small']),
            bg=self.colors['surface'],
            fg=self.colors['text'],
            wrap=tk.WORD,
            relief='solid',
            borderwidth=1,
            state=tk.DISABLED
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags with responsive fonts
        self.output_text.tag_configure(
            "timestamp", 
            foreground=self.colors['accent'], 
            font=('Yu Gothic', self.scaled_fonts['small'], 'bold')
        )
        self.output_text.tag_configure(
            "text", 
            foreground=self.colors['text']
        )
        self.output_text.tag_configure(
            "status", 
            foreground=self.colors['warning'], 
            font=('Yu Gothic', self.scaled_fonts['small'], 'italic')
        )

    def create_responsive_save_section(self, parent):
        """Create save section with responsive layout"""
        slf = tk.Frame(parent, bg=self.colors['background'])
        slf.pack(pady=self.scaled_dimensions['padding_small'])
        
        tf = tk.Frame(slf, bg=self.colors['background'])
        tf.pack(pady=(0, self.scaled_dimensions['padding_small']))
        
        self.save_transcription_btn = ttk.Button(
            tf,
            text=self.t("save_transcription"),
            command=self.save_transcription,
            style='Primary.TButton',
            state=tk.DISABLED
        )
        self.save_transcription_btn.pack(side=tk.LEFT, padx=(0, self.scaled_dimensions['padding_medium']))
        
        self.save_subtitle_btn = ttk.Button(
            tf,
            text=self.t("save_subtitle"),
            command=self.save_subtitle_file,
            style='Success.TButton',
            state=tk.DISABLED
        )
        self.save_subtitle_btn.pack(side=tk.LEFT)

    def open_parameter_window(self):
        """Open parameter settings window with responsive layout"""
        win = tk.Toplevel(self.root)
        win.title(self.t("parameter_settings"))
        
        # Calculate window size
        param_width = int(500 * self.scale)
        param_height = int(460 * self.scale)
        win.geometry(f"{param_width}x{param_height}")
        win.configure(bg=self.colors['surface'])
        
        # Center the parameter window
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (param_width // 2)
        y = (win.winfo_screenheight() // 2) - (param_height // 2)
        win.geometry(f"{param_width}x{param_height}+{x}+{y}")
        
        pad = self.scaled_dimensions['padding_large']
        small_pad = self.scaled_dimensions['padding_small']
        
        # Temperature
        tk.Label(win, text="Temperature:",
                 bg=self.colors['surface'], 
                 fg=self.colors['text'],
                 font=('Yu Gothic', self.scaled_fonts['normal'])).pack(anchor=tk.W, padx=pad, pady=(pad,0))
        self.temp_var = tk.DoubleVar(value=0.0)
        tk.Scale(win, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL,
                 variable=self.temp_var, 
                 font=('Yu Gothic', self.scaled_fonts['small'])).pack(fill=tk.X, padx=pad)

        # best_of
        tk.Label(win, text="best_of:",
                 bg=self.colors['surface'], 
                 fg=self.colors['text'],
                 font=('Yu Gothic', self.scaled_fonts['normal'])).pack(anchor=tk.W, padx=pad, pady=(pad,0))
        self.best_of_var = tk.IntVar(value=10)
        tk.Spinbox(win, from_=1, to=10, textvariable=self.best_of_var,
                   font=('Yu Gothic', self.scaled_fonts['normal'])).pack(fill=tk.X, padx=pad)

        # beam_size
        tk.Label(win, text="beam_size:",
                 bg=self.colors['surface'], 
                 fg=self.colors['text'],
                 font=('Yu Gothic', self.scaled_fonts['normal'])).pack(anchor=tk.W, padx=pad, pady=(pad,0))
        self.beam_var = tk.IntVar(value=10)
        tk.Spinbox(win, from_=1, to=20, textvariable=self.beam_var,
                   font=('Yu Gothic', self.scaled_fonts['normal'])).pack(fill=tk.X, padx=pad)

        # logprob_threshold
        tk.Label(win, text="logprob_threshold:",
                 bg=self.colors['surface'], 
                 fg=self.colors['text'],
                 font=('Yu Gothic', self.scaled_fonts['normal'])).pack(anchor=tk.W, padx=pad, pady=(pad,0))
        self.logp_var = tk.DoubleVar(value=-1)
        tk.Scale(win, from_=-5.0, to=0.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.logp_var,
                 font=('Yu Gothic', self.scaled_fonts['small'])).pack(fill=tk.X, padx=pad)

        # no_speech_threshold
        tk.Label(win, text="no_speech_threshold:",
                 bg=self.colors['surface'], 
                 fg=self.colors['text'],
                 font=('Yu Gothic', self.scaled_fonts['normal'])).pack(anchor=tk.W, padx=pad, pady=(pad,0))
        self.nospeech_var = tk.DoubleVar(value=0.5)
        tk.Scale(win, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL,
                 variable=self.nospeech_var,
                 font=('Yu Gothic', self.scaled_fonts['small'])).pack(fill=tk.X, padx=pad)

        # condition_on_previous_text
        self.cond_prev_var = tk.BooleanVar(value=False)
        tk.Checkbutton(win,
                       text="condition_on_previous_text",
                       variable=self.cond_prev_var,
                       bg=self.colors['surface'],
                       fg=self.colors['text'],
                       font=('Yu Gothic', self.scaled_fonts['normal'])).pack(anchor=tk.W, padx=pad, pady=(pad,0))

        # OK button
        def apply_params():
            self.whisper_params = {
                "temperature": self.temp_var.get(),
                "best_of": self.best_of_var.get(),
                "beam_size": self.beam_var.get(),
                "logprob_threshold": self.logp_var.get(),
                "no_speech_threshold": self.nospeech_var.get(),
                "condition_on_previous_text": self.cond_prev_var.get(),
            }
            win.destroy()
            self.append_status_message(f"{self.t('parameters_updated')} {self.whisper_params}")

        ttk.Button(win, text=self.t("ok"), command=apply_params, style='Success.TButton')\
            .pack(pady=self.scaled_dimensions['padding_large'])

    def on_language_change(self, event=None):
        """Handle language change event"""
        display_name = self.ui_language_var.get()
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
        self.header_subtitle_label.config(text=self.t("header_subtitle"))
        self.lang_label.config(text=self.t("language"))
        
        # Update file section
        self.file_section_label.config(text=self.t("audio_file_selection"))
        self.select_file_btn.config(text=self.t("select_file"))
        self.transcribe_btn.config(text=self.t("start_transcription"))
        if not self.current_file:
            self.file_path_label.config(text=self.t("no_file_selected"))
        
        # Update parameter button
        self.param_btn.config(text=self.t("adjust_parameters"))
        
        # Update dependency warning if present
        if hasattr(self, 'dep_warning_label'):
            self.dep_warning_label.config(text=self.t("dependency_warning"))
            self.dep_message_label.config(text=self.t("dependency_message"))
            self.run_downloader_btn.config(text=self.t("run_downloader"))
            self.recheck_btn.config(text=self.t("recheck"))
        
        # Update model section
        self.model_section_label.config(text=self.t("whisper_model"))
        
        # Update topic section
        self.keyword_label.config(text=self.t("keyword_optional"))
        self.trans_lang_label.config(text=self.t("transcription_language"))
        self.update_language_combo()
        
        # Update status section
        self.status_section_label.config(text=self.t("system_status"))
        self.elapsed_label.config(text=f"{self.t('elapsed')} 00:00")
        if self.audio_duration > 0:
            duration_str = str(timedelta(seconds=int(self.audio_duration)))
            self.duration_label.config(text=f"{self.t('duration')} {duration_str}")
        else:
            self.duration_label.config(text=f"{self.t('duration')} 00:00")
        
        # Update transcription output section
        self.output_section_label.config(text=self.t("transcription_output"))
        self.clear_output_btn.config(text=self.t("clear"))
        
        # Update save section
        self.save_transcription_btn.config(text=self.t("save_transcription"))
        self.save_subtitle_btn.config(text=self.t("save_subtitle"))

    def update_language_combo(self):
        """Update transcription language combo box with translated names"""
        lang_codes = self.t("language_codes")
        langs = [
            f"ja - {lang_codes['ja']}",
            f"en - {lang_codes['en']}",
            f"zh - {lang_codes['zh']}",
            f"ko - {lang_codes['ko']}",
            f"es - {lang_codes['es']}",
            f"fr - {lang_codes['fr']}",
            f"de - {lang_codes['de']}",
            f"ru - {lang_codes['ru']}",
            f"auto - {lang_codes['auto']}"
        ]
        self.transcription_language_combo['values'] = langs
        self.transcription_language_combo.set(f"ja - {lang_codes['ja']}")

    def run_pytorch_downloader(self):
        """Launch PyTorch downloader"""
        downloader_path = Path("pytorch_downloader.exe")
        if not downloader_path.exists():
            downloader_path = Path("pytorch_downloader.py")
        
        if downloader_path.exists():
            try:
                if platform.system() == "Windows" and downloader_path.suffix == ".exe":
                    subprocess.Popen([str(downloader_path)])
                else:
                    subprocess.Popen([sys.executable, str(downloader_path)])
                messagebox.showinfo(self.t("info"), self.t("downloader_launched"))
            except Exception as e:
                messagebox.showerror(self.t("error"), f"{self.t('downloader_launch_failed')} {e}")
        else:
            messagebox.showerror(self.t("error"), self.t("downloader_not_found"))

    def recheck_dependencies(self):
        """Recheck PyTorch/Whisper availability"""
        self.check_dependencies()
        if WHISPER_AVAILABLE:
            messagebox.showinfo(self.t("success"), self.t("dependencies_loaded"))
            self.root.destroy()
            app = AudioSubtitleSystem()
            app.run()
        else:
            messagebox.showwarning(self.t("warning"), self.t("dependencies_not_installed"))

    def update_status(self, message, color=None):
        """Thread-safe status update"""
        if color is None:
            color = self.colors['accent']
        
        def update():
            self.status_label.config(text=message, fg=color)
        
        self.update_ui_safe(update)

    def append_status_message(self, message):
        """Append a status message to the transcription output"""
        def update():
            self.output_text.config(state=tk.NORMAL)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.output_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.output_text.insert(tk.END, f"{message}\n", "status")
            
            self.output_text.see(tk.END)
            self.output_text.config(state=tk.DISABLED)
            
        self.update_ui_safe(update)

    def append_transcription_text(self, start_time, end_time, text):
        """Append transcribed text to the output display"""
        def update():
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, f"[{start_time} --> {end_time}] ", "timestamp")
            self.output_text.insert(tk.END, f"{text}\n\n", "text")
            self.output_text.see(tk.END)
            self.output_text.config(state=tk.DISABLED)
            
        self.update_ui_safe(update)

    def append_transcription_text_with_offset(self, start_str, end_str, text, offset):
        def ts2s(ts):
            m, s = ts.split(':')
            return int(m) * 60 + float(s)
        start = ts2s(start_str) + offset
        end   = ts2s(end_str)   + offset
    
        def fmt(t):
            m = int(t // 60)
            s = t - m * 60
            return f"{m:02d}:{s:06.3f}"
        new_start = fmt(start)
        new_end   = fmt(end)
    
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"[{new_start} --> {new_end}] ", "timestamp")
        self.output_text.insert(tk.END, f"{text}\n\n", "text")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def clear_transcription_output(self):
        """Clear the transcription output display"""
        def update():
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete(1.0, tk.END)
            self.output_text.config(state=tk.DISABLED)
        self.update_ui_safe(update)

    def get_audio_duration(self, file_path):
        """Get duration of audio file in seconds using whisper.load_audio for all formats."""
        if not WHISPER_AVAILABLE:
            messagebox.showerror(self.t("error"), self.t("whisper_not_installed"))
            return 0
            
        try:
            audio = whisper.load_audio(file_path)
            duration = audio.shape[0] / 16000.0
            return duration
        except Exception as e:
            messagebox.showerror(self.t("error"), f"{self.t('unable_to_get_duration')} {e}")
            return 0

    def select_audio_file(self):
        ftypes = [
            ("Audio files", "*.mp3 *.wav *.m4a *.aac *.ogg *.flac"), 
            ("All files", "*.*")
        ]
        fp = filedialog.askopenfilename(title="Select Audio File", filetypes=ftypes)
        if fp:
            self.current_file = fp
            self.file_path_label.config(text=os.path.basename(fp))
            
            if WHISPER_AVAILABLE:
                self.audio_duration = self.get_audio_duration(fp)
                duration_str = str(timedelta(seconds=int(self.audio_duration)))
                self.duration_label.config(text=f"{self.t('duration')} {duration_str}")
                self.transcribe_btn.config(state=tk.NORMAL)
                self.clear_transcription_output()
                self.append_status_message(self.t("file_selected").format(os.path.basename(fp), duration_str))
            else:
                self.append_status_message(self.t("file_selected_no_duration").format(os.path.basename(fp)))

    def check_model_exists(self, ms):
        cache_dir = Path.home()/".cache"/"whisper"
        return (cache_dir/f"{ms}.pt").exists()

    def load_whisper_model(self, model_size):
        if not WHISPER_AVAILABLE:
            self.update_ui_safe(lambda: messagebox.showerror(self.t("error"), self.t("whisper_not_installed")))
            return None
            
        model_sizes = {
            "tiny":  "~75 MB",
            "base":  "~142 MB",
            "small": "~466 MB",
            "medium":"~1.46 GB",
            "large": "~2.96 GB",
            "large-v2": "~2.96 GB",
            "large-v3": "~3.09 GB",
            "large-v3-turbo": "~1.6 GB"
        }
        
        if not self.check_model_exists(model_size):
            self.update_status(self.t("confirming_download").format(model_size), self.colors['warning'])
            self.append_status_message(self.t("model_not_found").format(model_size))
            
            self.message_queue.put(("ask_download", model_size, model_sizes.get(model_size)))
            
            response_queue = queue.Queue()
            self.model_download_response_queue = response_queue
            ok = response_queue.get()
            
            if not ok:
                self.update_status(self.t("model_download_cancelled"), self.colors['danger'])
                self.append_status_message(self.t("model_download_cancelled"))
                return None
            
            self.is_downloading = True
            self.update_status(self.t("downloading_model").format(model_size, model_sizes.get(model_size)), self.colors['warning'])
            self.append_status_message(self.t("downloading").format(model_size, model_sizes.get(model_size)))
                
        try:
            self.is_loading_model = True
            self.update_status(self.t("loading_model").format(model_size), self.colors['accent'])
            self.append_status_message(self.t("loading").format(model_size))
            
            # Save original stdout/stderr
            orig_stdout = sys.stdout
            orig_stderr = sys.stderr
            
            # Create a simple capture for model loading/downloading
            try:
                # Redirect output to avoid write errors during download
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                
                # Load the model
                model = whisper.load_model(model_size, device=self.device)
                
            finally:
                # Always restore stdout/stderr
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
            
            self.is_downloading = False
            self.is_loading_model = False
            
            device_info = "GPU (CUDA)" if self.device == "cuda" else "CPU"
            self.append_status_message(self.t("model_loaded").format(model_size, device_info))
            
            return model
        except Exception as e:
            self.is_downloading = False
            self.is_loading_model = False
            err_msg = str(e)
            self.update_status(self.t("model_loading_error"), self.colors['danger'])
            self.append_status_message(f"{self.t('model_loading_error')}: {err_msg}")
            self.update_ui_safe(lambda err=err_msg: 
                messagebox.showerror(self.t("error"), f"{self.t('model_loading_failed')} {err}")
            )
            return None

    def process_message_queue(self):
        """Process messages from background threads"""
        try:
            while True:
                msg = self.message_queue.get_nowait()
                if msg[0] == "ask_download":
                    model_size = msg[1]
                    size_str = msg[2]
                    response = messagebox.askyesno(
                        self.t("model_download_title"),
                        self.t("model_download_confirm").format(model_size, size_str)
                    )
                    if hasattr(self, 'model_download_response_queue'):
                        self.model_download_response_queue.put(response)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_message_queue)

    def handle_segment_progress(self, current_seconds):
        """Handle progress updates based on transcribed segment timestamps"""
        if self.audio_duration > 0:
            progress_percentage = (current_seconds / self.audio_duration) * 100
            progress_percentage = min(progress_percentage, 100)
            
            def update_gui():
                elapsed = time.time() - self.transcription_start_time if self.transcription_start_time else 0
                elapsed_str = str(timedelta(seconds=int(elapsed)))
                self.elapsed_label.config(text=f"{self.t('elapsed')} {elapsed_str}")
                
            self.update_ui_safe(update_gui)

    def handle_progress_update(self, percentage, current_frames, total_frames, elapsed_str, remaining_str):
        """Handle progress updates from Whisper console output"""
        def update_gui():
            if elapsed_str:
                self.elapsed_label.config(text=f"{self.t('elapsed')} {elapsed_str}")
            
        self.update_ui_safe(update_gui)

    def update_elapsed_time(self):
        """Periodic update for elapsed time"""
        if self.is_transcribing and self.transcription_start_time:
            elapsed = time.time() - self.transcription_start_time
            elapsed_str = str(timedelta(seconds=int(elapsed)))
            self.elapsed_label.config(text=f"{self.t('elapsed')} {elapsed_str}")
            
            if self.is_downloading:
                status_text = f"{self.t('downloading_model').split(':')[0]}..."
            elif self.is_loading_model:
                status_text = f"{self.t('loading_model').split(':')[0]}..."
            else:
                status_text = f"{self.t('transcription_completed').split()[0]}..."
            
            self.update_status(status_text, self.colors['accent'])
            self.update_timer = self.root.after(1000, self.update_elapsed_time)
    
    def update_ui_safe(self, callback):
        """Safely update UI from any thread"""
        self.root.after(0, callback)
        
    def transcribe_audio(self):
        if not self.current_file:
            messagebox.showwarning(self.t("warning"), self.t("please_select_audio"))
            return
            
        if not WHISPER_AVAILABLE:
            messagebox.showerror(self.t("error"), self.t("whisper_not_installed"))
            return
            
        def task():
            self.update_ui_safe(lambda: self.transcribe_btn.config(state=tk.DISABLED))
            self.update_ui_safe(lambda: self.save_transcription_btn.config(state=tk.DISABLED))
            self.update_ui_safe(lambda: self.save_subtitle_btn.config(state=tk.DISABLED))
            
            self.update_ui_safe(self.clear_transcription_output)
            
            self.update_ui_safe(lambda: self.progress_bar.start(10))
            
            self.transcription_start_time = time.time()
            self.is_transcribing = True
            
            self.append_status_message(self.t("starting_transcription"))
            self.update_status(self.t("preparing"), self.colors['accent'])
            
            self.update_ui_safe(self.update_elapsed_time)

            lang = self.transcription_language_combo.get().split(' - ')[0]
            if lang == 'auto': 
                lang = None

            ms = self.model_combo.get()
            self.whisper_model = self.load_whisper_model(ms)
            if not self.whisper_model:
                self.is_transcribing = False
                self.is_downloading = False
                self.is_loading_model = False
                if self.update_timer:
                    self.root.after_cancel(self.update_timer)
                    self.update_timer = None
                self.update_ui_safe(lambda: self.progress_bar.stop())
                self.update_ui_safe(lambda: self.transcribe_btn.config(state=tk.NORMAL))
                self.update_status(self.t("model_loading_failed").split(':')[0], self.colors['danger'])
                return

            kw = self.topic_entry.get().strip()
            prompt = None
            if kw and lang:
                lang_prompts = {
                    'ja': f"この音声は『{kw}』に関連しています。",
                    'en': f"The following audio is related to '{kw}'.",
                    'zh': f"以下音频与'{kw}'相关。",
                    'ko': f"다음 오디오는 '{kw}'와 관련이 있습니다."
                }
                prompt = lang_prompts.get(lang, lang_prompts['en'])

            try:
                self.append_status_message(self.t("starting_transcription"))
                self.update_status(f"{self.t('transcription_completed').split()[0]}...", self.colors['accent'])
                
                self.transcription_results = []
                
                capture = ProgressCapture(
                    self.handle_progress_update,
                    self.handle_segment_progress,
                    self.append_transcription_text)
                orig_stdout, orig_stderr = sys.stdout, sys.stderr
                sys.stdout = sys.stderr = capture
                try:
                    audio = whisper.load_audio(self.current_file)
                    sr = 16000
                    chunk_size = 30 * 60 * sr
                    
                    segments_data = [
                        audio[i : i + chunk_size]
                        for i in range(0, audio.shape[0], chunk_size)
                    ]
                    
                    self.transcription_results = []
                    offset = 0.0
                    
                    for seg_index, seg_audio in enumerate(segments_data):
                        offset = seg_index * (chunk_size / sr)
                    
                        capture = ProgressCapture(
                            self.handle_progress_update,
                            self.handle_segment_progress,
                            lambda st, et, tx, off=offset: self.append_transcription_text_with_offset(st, et, tx, off)
                        )
                        orig_stdout, orig_stderr = sys.stdout, sys.stderr
                        sys.stdout = sys.stderr = capture
                    
                        params = getattr(self, 'whisper_params', {})
                        result_seg = self.whisper_model.transcribe(
                            seg_audio,
                            language=lang,
                            task="transcribe",
                            initial_prompt=prompt,
                            verbose=True,
                            temperature=params.get("temperature", 0.0),
                            best_of=params.get("best_of", 10),
                            beam_size=params.get("beam_size", 10),
                            logprob_threshold=params.get("logprob_threshold", -1),
                            no_speech_threshold=params.get("no_speech_threshold", 0.5),
                            condition_on_previous_text=params.get("condition_on_previous_text", False),
                            fp16=params.get("fp16", False)
                        )
                        sys.stdout, sys.stderr = orig_stdout, orig_stderr
                    
                        for seg in result_seg["segments"]:
                            self.transcription_results.append({
                                "start": seg["start"] + offset,
                                "end":   seg["end"]   + offset,
                                "text":  seg["text"].strip()
                            })

                        offset += seg_audio.shape[0] / sr
                    
                finally:
                    sys.stdout, sys.stderr = orig_stdout, orig_stderr
                
                self.update_ui_safe(lambda: self.progress_bar.stop())
                
                if self.transcription_start_time:
                    total_time = time.time() - self.transcription_start_time
                    elapsed_str = str(timedelta(seconds=int(total_time)))
                    self.update_ui_safe(lambda: self.elapsed_label.config(text=f"{self.t('elapsed')} {elapsed_str}"))
                
                self.append_status_message(self.t("transcription_complete").format(len(self.transcription_results), elapsed_str))
                
                self.update_status(self.t("transcription_completed"), self.colors['success'])
                self.update_ui_safe(lambda: self.transcribe_btn.config(state=tk.NORMAL))
                self.update_ui_safe(lambda: self.save_transcription_btn.config(state=tk.NORMAL))
                self.update_ui_safe(lambda: self.save_subtitle_btn.config(state=tk.NORMAL))
                self.update_ui_safe(lambda: messagebox.showinfo(self.t("success"), self.t("transcription_success")))
                
            except Exception as e:
                err_msg = str(e)
                self.update_ui_safe(lambda: self.progress_bar.stop())
                self.append_status_message(f"{self.t('transcription_error')} {err_msg}")
                self.update_ui_safe(lambda err=err_msg: 
                    messagebox.showerror(
                        self.t("error"),
                        f"{self.t('transcription_error')} {err}"
                    )
                )
                self.update_ui_safe(lambda: self.transcribe_btn.config(state=tk.NORMAL))
                self.update_status(self.t("error"), self.colors['danger'])
            finally:
                self.is_transcribing = False
                self.is_downloading = False
                self.is_loading_model = False
                if self.update_timer:
                    self.root.after_cancel(self.update_timer)
                    self.update_timer = None
                self.update_ui_safe(lambda: self.progress_bar.stop())
                
        threading.Thread(target=task, daemon=True).start()
    
    def save_transcription(self):
        if not self.transcription_results:
            messagebox.showwarning(self.t("warning"), self.t("no_results_to_save"))
            return
            
        fp = filedialog.asksaveasfilename(
            title=self.t("save_as"),
            defaultextension=".json",
            filetypes=[("JSON files","*.json"), ("Text files","*.txt"), ("All files","*.*")]
        )
        if not fp: 
            return
            
        try:
            if fp.endswith('.json'):
                data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source_file": os.path.basename(self.current_file),
                    "keyword": self.topic_entry.get().strip(),
                    "language": self.transcription_language_combo.get(),
                    "model": self.model_combo.get(),
                    "device": self.device,
                    "transcription": self.transcription_results
                }
                with open(fp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                with open(fp, 'w', encoding='utf-8') as f:
                    f.write(f"Transcription of: {os.path.basename(self.current_file)}\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Language: {self.transcription_language_combo.get()}\n")
                    f.write(f"Model: {self.model_combo.get()}\n")
                    f.write("-" * 50 + "\n\n")
                    
                    for seg in self.transcription_results:
                        start_time = str(timedelta(seconds=int(seg['start'])))
                        end_time = str(timedelta(seconds=int(seg['end'])))
                        f.write(f"[{start_time} --> {end_time}]\n")
                        f.write(f"{seg['text']}\n\n")
                        
            self.append_status_message(f"{self.t('results_saved')} {os.path.basename(fp)}")
            messagebox.showinfo(self.t("success"), f"{self.t('results_saved')} {os.path.basename(fp)}")
        except Exception as e:
            messagebox.showerror(self.t("error"), f"{self.t('save_error')} {str(e)}")

    def save_subtitle_file(self):
        if not self.transcription_results:
            messagebox.showwarning(self.t("warning"), self.t("no_subtitles"))
            return
            
        fp = filedialog.asksaveasfilename(
            title=self.t("save_as"),
            defaultextension=".srt",
            filetypes=[("SRT files","*.srt"), ("VTT files","*.vtt"), ("All files","*.*")]
        )
        if not fp: 
            return
            
        try:
            if fp.endswith('.srt'):
                with open(fp, 'w', encoding='utf-8') as f:
                    for i, seg in enumerate(self.transcription_results, 1):
                        start_time = self.seconds_to_srt_time(seg['start'])
                        end_time = self.seconds_to_srt_time(seg['end'])
                        
                        f.write(f"{i}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{seg['text']}\n\n")
                        
            elif fp.endswith('.vtt'):
                with open(fp, 'w', encoding='utf-8') as f:
                    f.write("WEBVTT\n\n")
                    for seg in self.transcription_results:
                        start_time = self.seconds_to_vtt_time(seg['start'])
                        end_time = self.seconds_to_vtt_time(seg['end'])
                        
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{seg['text']}\n\n")
                        
            self.append_status_message(f"{self.t('subtitle_saved')} {os.path.basename(fp)}")
            messagebox.showinfo(self.t("success"), f"{self.t('subtitle_saved')} {os.path.basename(fp)}")
        except Exception as e:
            messagebox.showerror(self.t("error"), f"{self.t('save_error')} {str(e)}")

    def seconds_to_srt_time(self, seconds):
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def seconds_to_vtt_time(self, seconds):
        """Convert seconds to WebVTT timestamp format (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def on_closing(self):
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        if self.original_stderr:
            sys.stderr = self.original_stderr
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    setup_pytorch_path()
    app = AudioSubtitleSystem()
    try:
        app.run()
    except KeyboardInterrupt:
        sys.exit(1)