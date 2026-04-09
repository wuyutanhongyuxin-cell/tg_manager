"""媒体文件处理工具函数

提供文件大小格式化、媒体类型识别、格式验证和下载目录管理功能。
"""

import logging
import os

logger = logging.getLogger(__name__)

# 支持的图片格式
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}

# 支持的视频格式
_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}

# 支持的音频格式
_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".wma", ".m4a"}

# 文件大小单位
_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]


def get_file_size_str(size_bytes: int) -> str:
    """将字节数转换为人类可读的文件大小字符串

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化的大小字符串，如 "1.5 MB"
    """
    if size_bytes < 0:
        return "0 B"

    size = float(size_bytes)
    for unit in _SIZE_UNITS:
        if size < 1024.0:
            # 整数不显示小数点
            if size == int(size):
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0

    # 超出 TB 范围时使用 TB 单位
    return f"{size:.1f} PB"


def get_media_type(filename: str) -> str:
    """根据文件扩展名判断媒体类型

    Args:
        filename: 文件名或文件路径

    Returns:
        媒体类型字符串: "photo", "video", "audio", "document"
    """
    if not filename:
        return "document"

    ext = os.path.splitext(filename)[1].lower()

    if ext in _IMAGE_EXTENSIONS:
        return "photo"
    if ext in _VIDEO_EXTENSIONS:
        return "video"
    if ext in _AUDIO_EXTENSIONS:
        return "audio"

    return "document"


def is_supported_image(filename: str) -> bool:
    """检查文件是否为支持的图片格式

    Args:
        filename: 文件名或文件路径

    Returns:
        是否为支持的图片格式
    """
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in _IMAGE_EXTENSIONS


def is_supported_video(filename: str) -> bool:
    """检查文件是否为支持的视频格式

    Args:
        filename: 文件名或文件路径

    Returns:
        是否为支持的视频格式
    """
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in _VIDEO_EXTENSIONS


def ensure_download_dir(path: str) -> str:
    """确保下载目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        创建后的目录绝对路径
    """
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        os.makedirs(abs_path, exist_ok=True)
        logger.info(f"已创建下载目录: {abs_path}")
    return abs_path
