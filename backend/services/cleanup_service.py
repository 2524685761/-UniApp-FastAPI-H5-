import os
import time
from pathlib import Path


def cleanup_dir_older_than(directory: str, max_age_seconds: int) -> dict:
    """
    删除目录下超过 max_age_seconds 的文件（递归），返回统计信息。
    只删文件，不删目录；失败会跳过。
    """
    if max_age_seconds <= 0:
        return {"deleted": 0, "kept": 0, "errors": 0}

    p = Path(directory)
    if not p.exists() or not p.is_dir():
        return {"deleted": 0, "kept": 0, "errors": 0}

    now = time.time()
    deleted = 0
    kept = 0
    errors = 0

    for f in p.rglob("*"):
        try:
            if not f.is_file():
                continue
            age = now - f.stat().st_mtime
            if age >= max_age_seconds:
                f.unlink(missing_ok=True)
                deleted += 1
            else:
                kept += 1
        except Exception:
            errors += 1

    return {"deleted": deleted, "kept": kept, "errors": errors}


def cleanup_uploads_from_env() -> dict:
    """
    根据环境变量执行清理：
    - UPLOAD_RETENTION_HOURS: 默认 72 小时（3天）
    清理目录：
    - uploads/tts
    - uploads/recordings
    """
    raw = os.getenv("UPLOAD_RETENTION_HOURS", "72").strip()
    try:
        hours = int(raw)
    except Exception:
        hours = 72
    hours = max(1, hours)
    max_age_seconds = hours * 3600

    return {
        "uploads_tts": cleanup_dir_older_than(os.path.join("uploads", "tts"), max_age_seconds),
        "uploads_recordings": cleanup_dir_older_than(os.path.join("uploads", "recordings"), max_age_seconds),
        "retention_hours": hours,
    }


