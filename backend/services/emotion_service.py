"""Emotion detection service for speech learning.

This module keeps backward-compatible APIs while replacing corrupted legacy code
with a clean implementation:
- Rule-based emotion inference from audio features
- Optional AI fusion through HuggingFace pipeline
- Async preload entrypoint
- Fast path: short audio defaults to rule-based
"""

import os
import random
import tempfile
import threading
from io import BytesIO
from typing import Dict, Optional

try:
    from ..logger import log_error, log_info, log_warning
except Exception:
    def log_info(ctx, msg, extra=None):
        print(f"[INFO] {ctx}: {msg}")

    def log_warning(ctx, msg, extra=None):
        print(f"[WARN] {ctx}: {msg}")

    def log_error(ctx, err, extra=None):
        print(f"[ERROR] {ctx}: {err}")

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except Exception:
    NUMPY_AVAILABLE = False

try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except Exception:
    AudioSegment = None
    PYDUB_AVAILABLE = False

try:
    from transformers import pipeline

    TRANSFORMERS_AVAILABLE = True
except Exception:
    pipeline = None
    TRANSFORMERS_AVAILABLE = False
    log_warning("Emotion", "transformers not available, fallback to rule engine")


_emotion_model = None
_emotion_processor = None
_emotion_model_lock = threading.Lock()
_emotion_model_loading = False


def _env_truthy(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


EMOTION_AI_ENABLED = _env_truthy("EMOTION_AI_ENABLED", default=False)
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_hf_home = (os.getenv("HF_HOME") or "").strip()
if _hf_home:
    if not os.path.isabs(_hf_home):
        _hf_home = os.path.abspath(os.path.join(_ROOT, _hf_home))
    os.environ["HF_HOME"] = _hf_home

if _env_truthy("HF_HUB_OFFLINE", default=False) or _env_truthy("TRANSFORMERS_OFFLINE", default=False):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


LEARNING_EMOTIONS = {
    "confident": {
        "type": "happy",
        "label": "自信",
        "tip": "状态很好，继续保持这个节奏。",
        "encouragements": ["你读得很稳。", "发音很清晰，继续。", "节奏和气息都不错。"],
    },
    "neutral": {
        "type": "neutral",
        "label": "平稳",
        "tip": "继续专注，再来一遍会更自然。",
        "encouragements": ["不错，继续。", "整体稳定，继续练习。", "再来一遍会更好。"],
    },
    "hesitant": {
        "type": "confused",
        "label": "犹豫",
        "tip": "先慢一点，跟着示范读。",
        "encouragements": ["慢一点没关系。", "先听一遍，再跟读。", "你在进步，继续。"],
    },
    "confused": {
        "type": "confused",
        "label": "困惑",
        "tip": "把句子拆开读，一段一段来。",
        "encouragements": ["这个点我们拆开练。", "先稳住节奏。", "再试一次就会好很多。"],
    },
    "frustrated": {
        "type": "frustrated",
        "label": "挫败",
        "tip": "先放松，调整呼吸后再读。",
        "encouragements": ["别急，先缓一缓。", "这个难点很常见。", "你已经做得不错了。"],
    },
    "anxious": {
        "type": "confused",
        "label": "紧张",
        "tip": "不赶时间，放慢语速会更准。",
        "encouragements": ["慢一点会更稳。", "放松肩膀和呼吸。", "你可以的，继续。"],
    },
}


class AudioFeatureAnalyzer:
    """Extract robust, lightweight features from audio bytes."""

    def __init__(self, audio_content: bytes, audio_format: str = "webm"):
        self.audio_content = audio_content
        self.audio_format = audio_format
        self.audio_segment = None

    def load_audio(self) -> bool:
        if not PYDUB_AVAILABLE:
            return False
        try:
            fmt = self.audio_format if self.audio_format != "webm" else None
            self.audio_segment = AudioSegment.from_file(BytesIO(self.audio_content), format=fmt)
            return True
        except Exception as exc:
            log_warning("Emotion", f"audio load failed: {exc}")
            return False

    def extract_features(self) -> Dict:
        if self.audio_segment is None and not self.load_audio():
            return self._default_features()

        audio = self.audio_segment
        duration_ms = len(audio)
        duration_sec = duration_ms / 1000.0
        max_possible = float(1 << (8 * audio.sample_width - 1))
        silence_threshold = max_possible * 0.02

        frame_ms = 100
        frame_energies = []
        silent_flags = []

        for start in range(0, max(1, duration_ms), frame_ms):
            chunk = audio[start : start + frame_ms]
            energy = float(chunk.rms or 0)
            frame_energies.append(energy)
            silent_flags.append(energy < silence_threshold)

        total_frames = max(1, len(silent_flags))
        silent_frames = sum(1 for v in silent_flags if v)
        silence_ratio = min(1.0, silent_frames / total_frames)

        silence_segment_count = 0
        max_silence_frames = 0
        current = 0
        for is_silent in silent_flags:
            if is_silent:
                current += 1
            elif current > 0:
                silence_segment_count += 1
                if current > max_silence_frames:
                    max_silence_frames = current
                current = 0
        if current > 0:
            silence_segment_count += 1
            if current > max_silence_frames:
                max_silence_frames = current

        half = max(1, len(frame_energies) // 2)
        first = frame_energies[:half] or [0.0]
        second = frame_energies[half:] or [0.0]
        first_mean = sum(first) / len(first)
        second_mean = sum(second) / len(second)

        if second_mean > first_mean * 1.15:
            energy_trend = "increasing"
        elif second_mean < first_mean * 0.85:
            energy_trend = "decreasing"
        else:
            energy_trend = "stable"

        if NUMPY_AVAILABLE and frame_energies:
            mean_e = float(np.mean(frame_energies))
            std_e = float(np.std(frame_energies))
        else:
            mean_e = (sum(frame_energies) / len(frame_energies)) if frame_energies else 0.0
            var = (
                sum((x - mean_e) ** 2 for x in frame_energies) / max(1, len(frame_energies))
                if frame_energies
                else 0.0
            )
            std_e = var ** 0.5

        energy_consistency = max(0.0, min(1.0, 1.0 - (std_e / (mean_e + 1.0))))

        threshold = mean_e * 0.7
        peaks = 0
        was_above = False
        for energy in frame_energies:
            is_above = energy > threshold
            if is_above and not was_above:
                peaks += 1
            was_above = is_above

        speaking_rate = peaks / duration_sec if duration_sec > 0 else 0.0

        return {
            "duration_sec": duration_sec,
            "duration_ms": duration_ms,
            "rms_energy": float(audio.rms or 0),
            "sample_rate": int(audio.frame_rate),
            "silence_ratio": float(silence_ratio),
            "silence_segment_count": int(silence_segment_count),
            "max_silence_duration": float((max_silence_frames * frame_ms) / 1000.0),
            "energy_trend": energy_trend,
            "energy_consistency": float(energy_consistency),
            "speaking_rate": float(speaking_rate),
        }

    @staticmethod
    def _default_features() -> Dict:
        return {
            "duration_sec": 0.0,
            "duration_ms": 0,
            "rms_energy": 0.0,
            "sample_rate": 0,
            "silence_ratio": 0.5,
            "silence_segment_count": 0,
            "max_silence_duration": 0.0,
            "energy_trend": "unknown",
            "energy_consistency": 0.5,
            "speaking_rate": 0.0,
        }


class EmotionInferenceEngine:
    """Rule engine tuned for language-learning speech."""

    def infer_emotion(self, features: Dict, score: Optional[int] = None, attempt_count: int = 1) -> Dict:
        indicators = {
            "confident": 0,
            "neutral": 0,
            "hesitant": 0,
            "confused": 0,
            "frustrated": 0,
            "anxious": 0,
        }

        duration = float(features.get("duration_sec", 0) or 0)
        rms = float(features.get("rms_energy", 0) or 0)
        silence_ratio = float(features.get("silence_ratio", 0) or 0)
        silence_count = int(features.get("silence_segment_count", 0) or 0)
        max_silence = float(features.get("max_silence_duration", 0) or 0)
        energy_trend = str(features.get("energy_trend", "stable"))
        energy_consistency = float(features.get("energy_consistency", 0.5) or 0.5)
        speaking_rate = float(features.get("speaking_rate", 0) or 0)

        if 1.0 <= duration <= 3.5:
            indicators["confident"] += 2
            indicators["neutral"] += 1
        elif duration < 0.6:
            indicators["hesitant"] += 2
            indicators["anxious"] += 1
        elif duration > 5.0:
            indicators["confused"] += 2

        if rms > 500:
            indicators["confident"] += 2
        elif rms < 150:
            indicators["hesitant"] += 2
            indicators["frustrated"] += 1
        else:
            indicators["neutral"] += 1

        if silence_ratio > 0.5:
            indicators["confused"] += 2
            indicators["hesitant"] += 1
        if silence_count > 3:
            indicators["hesitant"] += 1
            indicators["anxious"] += 1
        if max_silence > 1.0:
            indicators["confused"] += 1

        if energy_trend == "decreasing":
            indicators["frustrated"] += 1
            indicators["hesitant"] += 1
        elif energy_trend == "increasing":
            indicators["anxious"] += 1

        if energy_consistency > 0.7:
            indicators["confident"] += 1
        elif energy_consistency < 0.4:
            indicators["confused"] += 1

        if speaking_rate > 6:
            indicators["anxious"] += 2
        elif speaking_rate < 1:
            indicators["hesitant"] += 1
        elif 2 <= speaking_rate <= 5:
            indicators["confident"] += 1
            indicators["neutral"] += 1

        if score is not None:
            if score >= 85:
                indicators["confident"] += 3
            elif score >= 70:
                indicators["neutral"] += 2
            elif score >= 50:
                indicators["hesitant"] += 1
                indicators["confused"] += 1
            else:
                indicators["frustrated"] += 2
                indicators["confused"] += 1

        if attempt_count >= 3:
            indicators["frustrated"] += 2
        elif attempt_count == 2:
            indicators["hesitant"] += 1

        emotion_key, strength = max(indicators.items(), key=lambda item: item[1])
        confidence = min(1.0, strength / 10.0)

        if strength < 2:
            emotion_key = "neutral"
            confidence = 0.5

        result = LEARNING_EMOTIONS.get(emotion_key, LEARNING_EMOTIONS["neutral"]).copy()
        result["confidence"] = float(confidence)
        result["indicators"] = indicators
        result["features_used"] = list(features.keys())
        return result


def _get_emotion_model():
    global _emotion_model, _emotion_processor, _emotion_model_loading

    if not TRANSFORMERS_AVAILABLE or not EMOTION_AI_ENABLED:
        return None, None

    if _emotion_model is not None:
        return _emotion_model, _emotion_processor

    with _emotion_model_lock:
        if _emotion_model is not None:
            return _emotion_model, _emotion_processor
        if _emotion_model_loading:
            return None, None

        try:
            _emotion_model_loading = True
            log_info("Emotion", "loading emotion model")
            model_name = (
                (os.getenv("EMOTION_MODEL_PATH") or "").strip()
                or "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
            )
            if not os.path.isabs(model_name) and os.path.exists(os.path.join(_ROOT, model_name)):
                model_name = os.path.abspath(os.path.join(_ROOT, model_name))

            _emotion_model = pipeline("audio-classification", model=model_name, device=-1)
            log_info("Emotion", "emotion model loaded")
        except Exception as exc:
            log_error("Emotion", exc)
            _emotion_model = None
            _emotion_processor = None
        finally:
            _emotion_model_loading = False

    return _emotion_model, _emotion_processor


def preload_model_async():
    if not TRANSFORMERS_AVAILABLE or _emotion_model is not None:
        return

    def _load():
        _get_emotion_model()

    thread = threading.Thread(target=_load, daemon=True)
    thread.start()
    log_info("Emotion", "emotion preload started")


def detect_emotion(
    audio_content: bytes,
    audio_format: str = "webm",
    score: Optional[int] = None,
    attempt_count: int = 1,
) -> Dict:
    """Detect emotion from audio bytes with rule-first short-audio behavior."""

    analyzer = AudioFeatureAnalyzer(audio_content, audio_format)
    features = analyzer.extract_features()

    rule_result = _detect_with_rules(
        audio_content,
        audio_format,
        score=score,
        attempt_count=attempt_count,
        features_override=features,
    )

    short_audio_threshold = float(os.getenv("EMOTION_AI_SHORT_AUDIO_SEC", "1.8") or 1.8)
    use_ai_for_short = _env_truthy("EMOTION_AI_USE_FOR_SHORT", default=False)
    duration_sec = float(features.get("duration_sec", 0) or 0)
    should_try_ai = not (0 < duration_sec <= short_audio_threshold and not use_ai_for_short)

    ai_result = None
    if should_try_ai:
        model, _ = _get_emotion_model()
        if model is not None:
            ai_result = _detect_with_ai_model(audio_content, audio_format, model)

    result = rule_result if ai_result is None else _merge_emotion_results(ai_result, rule_result)

    emotion_key = _get_emotion_key(result.get("type", "neutral"))
    encouragements = LEARNING_EMOTIONS.get(emotion_key, LEARNING_EMOTIONS["neutral"]).get("encouragements", [])
    if encouragements:
        result["encouragement"] = random.choice(encouragements)

    return result


def _detect_with_ai_model(audio_content: bytes, audio_format: str, model) -> Optional[Dict]:
    try:
        suffix = f".{audio_format or 'wav'}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(audio_content)
            tmp_path = tmp_file.name

        try:
            results = model(tmp_path)
            if not results:
                return None

            top = results[0]
            emotion_label = str(top.get("label", "neutral")).lower()
            confidence = float(top.get("score", 0.5))

            emotion_map = {
                "happy": "confident",
                "sad": "frustrated",
                "angry": "frustrated",
                "fear": "anxious",
                "surprise": "neutral",
                "neutral": "neutral",
                "disgust": "confused",
            }
            mapped_key = emotion_map.get(emotion_label, "neutral")

            result = LEARNING_EMOTIONS.get(mapped_key, LEARNING_EMOTIONS["neutral"]).copy()
            result["confidence"] = confidence
            result["ai_detected"] = True
            result["original_label"] = emotion_label
            return result
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as exc:
        log_error("Emotion", exc)
        return None


def _detect_with_rules(
    audio_content: bytes,
    audio_format: str,
    score: Optional[int] = None,
    attempt_count: int = 1,
    features_override: Optional[Dict] = None,
) -> Dict:
    if features_override is None:
        features = AudioFeatureAnalyzer(audio_content, audio_format).extract_features()
    else:
        features = features_override

    engine = EmotionInferenceEngine()
    result = engine.infer_emotion(features, score=score, attempt_count=attempt_count)
    result["rule_based"] = True
    result["audio_features"] = {
        key: features.get(key)
        for key in ("duration_sec", "silence_ratio", "speaking_rate", "energy_trend")
    }
    return result


def _merge_emotion_results(ai_result: Dict, rule_result: Dict) -> Dict:
    ai_conf = float(ai_result.get("confidence", 0) or 0)
    rule_conf = float(rule_result.get("confidence", 0) or 0)

    if ai_conf >= 0.7:
        merged = ai_result.copy()
        merged["rule_features"] = rule_result.get("audio_features", {})
        return merged

    if rule_conf >= 0.6 and ai_conf < 0.5:
        merged = rule_result.copy()
        merged["ai_suggestion"] = ai_result.get("original_label")
        return merged

    merged = ai_result.copy()
    merged["rule_features"] = rule_result.get("audio_features", {})
    if rule_result.get("type") in ("confused", "frustrated") and rule_conf > 0.5:
        merged["type"] = rule_result.get("type")
        merged["label"] = rule_result.get("label")
        merged["tip"] = rule_result.get("tip")
    return merged


def _get_emotion_key(emotion_type: str) -> str:
    mapping = {
        "happy": "confident",
        "neutral": "neutral",
        "confused": "confused",
        "frustrated": "frustrated",
    }
    return mapping.get(emotion_type, "neutral")


def _default_emotion() -> Dict:
    result = LEARNING_EMOTIONS["neutral"].copy()
    result["confidence"] = 0.5
    return result


def detect_emotion_from_file(file_path: str, **kwargs) -> Dict:
    try:
        with open(file_path, "rb") as f:
            audio_content = f.read()
        return detect_emotion(audio_content, **kwargs)
    except Exception as exc:
        log_error("Emotion", exc)
        return _default_emotion()


def get_adaptive_encouragement(emotion_type: str, attempt_count: int = 1) -> str:
    emotion_key = _get_emotion_key(emotion_type)
    encouragements = list(
        LEARNING_EMOTIONS.get(emotion_key, LEARNING_EMOTIONS["neutral"]).get("encouragements", [])
    )

    if attempt_count >= 3 and emotion_type in ("confused", "frustrated"):
        encouragements.extend([
            "先休息一下也可以。",
            "我们可以先跳过，稍后再回来看。",
            "你已经很努力了，慢慢来。",
        ])

    return random.choice(encouragements) if encouragements else "继续加油。"
