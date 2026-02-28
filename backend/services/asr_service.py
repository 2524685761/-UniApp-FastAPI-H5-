"""
ASR service based on FunASR.
- Lazy model load
- Optional async preload
- Multi-segment text merge
"""
import os
import re
import tempfile
import threading
from typing import Optional

try:
    from ..logger import log_info, log_warning, log_error
except ImportError:
    def log_info(ctx, msg, extra=None):
        print(f"[INFO] {ctx}: {msg}")

    def log_warning(ctx, msg, extra=None):
        print(f"[WARN] {ctx}: {msg}")

    def log_error(ctx, err, extra=None):
        print(f"[ERROR] {ctx}: {err}")

try:
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
except ImportError:
    FUNASR_AVAILABLE = False
    log_warning("ASR", "FunASR not installed. Run: pip install funasr modelscope")

_asr_model = None
_asr_model_lock = threading.Lock()
_asr_model_loading = False


def _get_asr_model():
    global _asr_model, _asr_model_loading

    if not FUNASR_AVAILABLE:
        return None
    if _asr_model is not None:
        return _asr_model

    with _asr_model_lock:
        if _asr_model is not None:
            return _asr_model
        if _asr_model_loading:
            return None

        try:
            _asr_model_loading = True
            log_info("ASR", "Loading FunASR model...")
            _asr_model = AutoModel(
                model="paraformer-zh",
                model_revision="v2.0.4",
                device="cpu",
                disable_update=True,
            )
            log_info("ASR", "FunASR model loaded")
            return _asr_model
        except Exception as e:
            log_error("ASR", e)
            return None
        finally:
            _asr_model_loading = False


def preload_model_async():
    if not FUNASR_AVAILABLE or _asr_model is not None:
        return

    def _load():
        _get_asr_model()

    threading.Thread(target=_load, daemon=True).start()
    log_info("ASR", "ASR preload started")


def _normalize_asr_text(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"\s+", " ", str(text)).strip()
    # remove spaces between CJK chars, e.g. "你 好" -> "你好"
    t = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", t)
    return t


def _extract_text_from_result(result) -> str:
    texts: list[str] = []

    def _walk(node):
        if node is None:
            return
        if isinstance(node, dict):
            # 只从明确的 ASR 文本字段提取，避免把临时文件名/路径混入识别结果
            for k in ("text",):
                txt = node.get(k)
                if isinstance(txt, str) and txt.strip():
                    texts.append(txt.strip())
            # 继续遍历结构化子节点，但不采集普通字符串值
            for v in node.values():
                if isinstance(v, (dict, list, tuple)):
                    _walk(v)
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                _walk(item)
            return

    _walk(result)

    merged: list[str] = []
    seen = set()
    for t in texts:
        n = _normalize_asr_text(t)
        if not n or n in seen:
            continue
        seen.add(n)
        merged.append(n)

    if not merged:
        return ""
    if len(merged) == 1:
        return merged[0]
    return "，".join(merged)


def recognize_speech(audio_content: bytes, audio_format: str = "webm") -> Optional[str]:
    if not audio_content or len(audio_content) < 100:
        log_warning("ASR", "Audio content too short or empty")
        return None

    model = _get_asr_model()
    if model is None:
        log_warning("ASR", "ASR model not ready")
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_format}") as tmp_file:
            tmp_file.write(audio_content)
            tmp_path = tmp_file.name

        result = model.generate(input=tmp_path)
        text = _normalize_asr_text(_extract_text_from_result(result))
        if text:
            log_info("ASR", f"Recognized: {text[:80]}")
            return text

        log_warning("ASR", "Recognition result is empty")
        return None
    except Exception as e:
        log_error("ASR", e)
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def recognize_speech_from_file(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            audio_content = f.read()
        return recognize_speech(audio_content)
    except Exception as e:
        log_error("ASR", e)
        return None
