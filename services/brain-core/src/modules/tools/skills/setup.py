"""技能注册初始化 — 在应用启动时调用"""

from .skill_engine import SkillEngine

# 日常类 (15个)
from .daily.calculator import CalculatorSkill
from .daily.unit_converter import UnitConverterSkill
from .daily.password_generator import PasswordGeneratorSkill
from .daily.bmi_calculator import BMICalculatorSkill
from .daily.random_generator import RandomGeneratorSkill
from .daily.countdown_timer import CountdownTimerSkill
from .daily.color_converter import ColorConverterSkill
from .daily.morse_code import MorseCodeSkill
from .daily.zodiac_lookup import ZodiacLookupSkill
from .daily.calorie_calculator import CalorieCalculatorSkill
from .daily.tip_calculator import TipCalculatorSkill
from .daily.decision_maker import DecisionMakerSkill
from .daily.datetime_calc import DatetimeCalcSkill
from .daily.habit_tracker import HabitTrackerSkill
from .daily.dice_roller import DiceRollerSkill

# 办公类 (15个)
from .office.todo_manager import TodoManagerSkill
from .office.pomodoro_timer import PomodoroTimerSkill
from .office.json_formatter import JsonFormatterSkill
from .office.cron_parser import CronParserSkill
from .office.expense_tracker import ExpenseTrackerSkill
from .office.csv_analyzer import CsvAnalyzerSkill
from .office.email_template import EmailTemplateSkill
from .office.meeting_minutes import MeetingMinutesSkill
from .office.yaml_processor import YamlProcessorSkill
from .office.schedule_planner import SchedulePlannerSkill
from .office.time_tracker import TimeTrackerSkill
from .office.invoice_generator import InvoiceGeneratorSkill
from .office.kanban_board import KanbanBoardSkill
from .office.gantt_chart import GanttChartSkill
from .office.contact_manager import ContactManagerSkill

# 编程类 (15个)
from .coding.base64_codec import Base64CodecSkill
from .coding.url_codec import UrlCodecSkill
from .coding.hash_generator import HashGeneratorSkill
from .coding.uuid_generator import UuidGeneratorSkill
from .coding.jwt_decoder import JwtDecoderSkill
from .coding.sql_formatter import SqlFormatterSkill
from .coding.json_validator import JsonValidatorSkill
from .coding.ip_calculator import IpCalculatorSkill
from .coding.html_entity_codec import HtmlEntityCodecSkill
from .coding.env_parser import EnvParserSkill
from .coding.code_formatter import CodeFormatterSkill
from .coding.code_minifier import CodeMinifierSkill
from .coding.file_hasher import FileHasherSkill
from .coding.diff_patch import DiffPatchSkill
from .coding.regex_tester import RegexTesterSkill

# 文档类 (13个)
from .document.markdown_processor import MarkdownProcessorSkill
from .document.text_statistics import TextStatisticsSkill
from .document.text_diff import TextDiffSkill
from .document.regex_builder import RegexBuilderSkill
from .document.template_engine import TemplateEngineSkill
from .document.csv_to_table import CsvToTableSkill
from .document.json_to_csv import JsonToCsvSkill
from .document.xml_parser import XmlParserSkill
from .document.html_cleaner import HtmlCleanerSkill
from .document.text_encryptor import TextEncryptorSkill
from .document.text_translator_dict import TextTranslatorDictSkill
from .document.word_counter import WordCounterSkill
from .document.text_summarizer import TextSummarizerSkill

# 娱乐类 (12个)
from .entertainment.coin_flipper import CoinFlipperSkill
from .entertainment.fortune_teller import FortuneTellerSkill
from .entertainment.name_generator import NameGeneratorSkill
from .entertainment.lorem_ipsum import LoremIpsumSkill
from .entertainment.ascii_art import AsciiArtSkill
from .entertainment.number_trivia import NumberTriviaSkill
from .entertainment.emoji_art import EmojiArtSkill
from .entertainment.maze_generator import MazeGeneratorSkill
from .entertainment.sudoku_solver import SudokuSolverSkill
from .entertainment.anagram_solver import AnagramSolverSkill
from .entertainment.word_game import WordGameSkill
from .entertainment.rock_paper_scissors import RockPaperScissorsSkill

# 图像类 (12个) — Pillow + qrcode，graceful skip
_image_skills = []
try:
    from .image.image_resize import ImageResizeSkill
    from .image.image_crop import ImageCropSkill
    from .image.image_rotate import ImageRotateSkill
    from .image.image_watermark import ImageWatermarkSkill
    from .image.image_compress import ImageCompressSkill
    from .image.image_format_convert import ImageFormatConvertSkill
    from .image.image_metadata import ImageMetadataSkill
    from .image.image_thumbnail import ImageThumbnailSkill
    from .image.image_collage import ImageCollageSkill
    from .image.image_filter import ImageFilterSkill
    from .image.image_color_palette import ImageColorPaletteSkill
    from .image.qrcode_generator import QrcodeGeneratorSkill
    _image_skills = [
        ImageResizeSkill, ImageCropSkill, ImageRotateSkill, ImageWatermarkSkill,
        ImageCompressSkill, ImageFormatConvertSkill, ImageMetadataSkill,
        ImageThumbnailSkill, ImageCollageSkill, ImageFilterSkill,
        ImageColorPaletteSkill, QrcodeGeneratorSkill,
    ]
except ImportError:
    print("  ⚠ Image skills skipped (Pillow/qrcode not available)")

# 音频类 (10个) — pydub 需要 audioop，Python 3.13+ 已移除，graceful skip
_audio_skills = []
try:
    from .audio.audio_info import AudioInfoSkill
    from .audio.audio_convert import AudioConvertSkill
    from .audio.audio_trim import AudioTrimSkill
    from .audio.audio_merge import AudioMergeSkill
    from .audio.audio_volume import AudioVolumeSkill
    from .audio.audio_split import AudioSplitSkill
    from .audio.audio_fade import AudioFadeSkill
    from .audio.audio_speed import AudioSpeedSkill
    from .audio.audio_reverse import AudioReverseSkill
    from .audio.audio_silence_detect import AudioSilenceDetectSkill
    _audio_skills = [
        AudioInfoSkill, AudioConvertSkill, AudioTrimSkill, AudioMergeSkill,
        AudioVolumeSkill, AudioSplitSkill, AudioFadeSkill, AudioSpeedSkill,
        AudioReverseSkill, AudioSilenceDetectSkill,
    ]
except ImportError:
    print("  ⚠ Audio skills skipped (pydub/audioop not available on this Python version)")

# 视频类 (8个) — subprocess ffmpeg，正常导入
from .video.video_info import VideoInfoSkill
from .video.video_thumbnail import VideoThumbnailSkill
from .video.video_trim import VideoTrimSkill
from .video.video_merge import VideoMergeSkill
from .video.video_to_gif import VideoToGifSkill
from .video.video_extract_audio import VideoExtractAudioSkill
from .video.video_resize import VideoResizeSkill
from .video.video_rotate import VideoRotateSkill

# 系统类
from .system.shell_exec import ShellExecSkill

def register_all_skills():
    """注册所有技能 — 共 101 个"""
    skills = [
        # 系统类 (特权执行)
        ShellExecSkill(),
        # 日常类 15个
        CalculatorSkill(),
        UnitConverterSkill(),
        PasswordGeneratorSkill(),
        BMICalculatorSkill(),
        RandomGeneratorSkill(),
        CountdownTimerSkill(),
        ColorConverterSkill(),
        MorseCodeSkill(),
        ZodiacLookupSkill(),
        CalorieCalculatorSkill(),
        TipCalculatorSkill(),
        DecisionMakerSkill(),
        DatetimeCalcSkill(),
        HabitTrackerSkill(),
        DiceRollerSkill(),
        # 办公类 15个
        TodoManagerSkill(),
        PomodoroTimerSkill(),
        JsonFormatterSkill(),
        CronParserSkill(),
        ExpenseTrackerSkill(),
        CsvAnalyzerSkill(),
        EmailTemplateSkill(),
        MeetingMinutesSkill(),
        YamlProcessorSkill(),
        SchedulePlannerSkill(),
        TimeTrackerSkill(),
        InvoiceGeneratorSkill(),
        KanbanBoardSkill(),
        GanttChartSkill(),
        ContactManagerSkill(),
        # 编程类 15个
        Base64CodecSkill(),
        UrlCodecSkill(),
        HashGeneratorSkill(),
        UuidGeneratorSkill(),
        JwtDecoderSkill(),
        SqlFormatterSkill(),
        JsonValidatorSkill(),
        IpCalculatorSkill(),
        HtmlEntityCodecSkill(),
        EnvParserSkill(),
        CodeFormatterSkill(),
        CodeMinifierSkill(),
        FileHasherSkill(),
        DiffPatchSkill(),
        RegexTesterSkill(),
        # 文档类 13个
        MarkdownProcessorSkill(),
        TextStatisticsSkill(),
        TextDiffSkill(),
        RegexBuilderSkill(),
        TemplateEngineSkill(),
        CsvToTableSkill(),
        JsonToCsvSkill(),
        XmlParserSkill(),
        HtmlCleanerSkill(),
        TextEncryptorSkill(),
        TextTranslatorDictSkill(),
        WordCounterSkill(),
        TextSummarizerSkill(),
        # 娱乐类 12个
        CoinFlipperSkill(),
        FortuneTellerSkill(),
        NameGeneratorSkill(),
        LoremIpsumSkill(),
        AsciiArtSkill(),
        NumberTriviaSkill(),
        EmojiArtSkill(),
        MazeGeneratorSkill(),
        SudokuSolverSkill(),
        AnagramSolverSkill(),
        WordGameSkill(),
        RockPaperScissorsSkill(),
        # 图像类 (动态，需要 Pillow/qrcode)
        # 音频类 (动态，可能因 Python 3.13+ 缺少 audioop 而跳过)
        # 视频类 8个
        VideoInfoSkill(),
        VideoThumbnailSkill(),
        VideoTrimSkill(),
        VideoMergeSkill(),
        VideoToGifSkill(),
        VideoExtractAudioSkill(),
        VideoResizeSkill(),
        VideoRotateSkill(),
    ]

    # 动态追加图像技能（如果 Pillow 可用）
    skills.extend(cls() for cls in _image_skills)
    # 动态追加音频技能（如果 pydub 可用）
    skills.extend(cls() for cls in _audio_skills)

    for skill in skills:
        SkillEngine.register(skill)

    cats = SkillEngine.categories()
    print(f"  ✓ Registered {len(SkillEngine._skills)} skills: {dict(cats)}")

    # 桥接: 所有技能 → ToolRegistry，使 Agent 可自动发现和调用
    from ..skill_tool_adapter import bridge_skills_to_tools
    bridge_skills_to_tools()
