import os
import time
from io import BytesIO
from typing import Optional

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

# 导入AI服务
from . import asr_service, pronunciation_service, emotion_service
# 导入自适应反馈服务
try:
    from . import adaptive_service
    ADAPTIVE_AVAILABLE = True
except ImportError:
    ADAPTIVE_AVAILABLE = False

def _safe_filename(name: str) -> str:
    """避免路径穿越/奇怪字符导致写文件风险。"""
    base = os.path.basename(name or "recording")
    # 只保留常见安全字符
    keep = []
    for ch in base:
        if ch.isalnum() or ch in ("-", "_", ".", " "):
            keep.append(ch)
        else:
            keep.append("_")
    out = "".join(keep).strip().replace(" ", "_")
    return out or "recording"


def _should_keep_recordings() -> bool:
    return os.getenv("KEEP_RECORDINGS", "false").strip().lower() in ("1", "true", "yes", "y")


def _ensure_dir(p: str) -> None:
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)


# 录音文件默认不落盘（上架/生产更合规）；本地调试可通过 KEEP_RECORDINGS=true 开启
RECORDINGS_DIR = os.path.join("uploads", "recordings")
_ensure_dir(RECORDINGS_DIR)

def analyze_audio_file(file_content: bytes, filename: str, reference_text: Optional[str] = None, attempt_count: int = 1) -> dict:
    """
    AI增强的音频分析：
    1. 使用FunASR进行语音识别（ASR）
    2. 使用发音评分服务（讯飞API或本地算法）
    3. 使用情感识别服务（emotion2vec + 规则引擎）
    4. 结合音频特征分析作为补充
    5. 自适应反馈机制
    
    Args:
        file_content: 音频文件字节内容
        filename: 文件名
        reference_text: 标准文本（用于发音评分对比）
        attempt_count: 当前词的尝试次数
    
    Returns:
        分析结果字典，包含 score, emotion, feedback, issues, adaptive 等
    """
    # 录音文件处理：
    # - 默认不持久化落盘（减少隐私风险/避免被公开访问）
    # - 仅在 KEEP_RECORDINGS=true 时保存到 uploads/recordings
    file_path = ""
    if _should_keep_recordings():
        safe = _safe_filename(filename)
        file_path = os.path.join(RECORDINGS_DIR, f"{int(time.time())}_{safe}")
        with open(file_path, "wb") as f:
            f.write(file_content)

    # 1. 语音识别（ASR）
    recognized_text = None
    try:
        recognized_text = asr_service.recognize_speech(file_content)
        if recognized_text:
            print(f"ASR识别结果: {recognized_text}")
    except Exception as e:
        print(f"ASR识别失败: {e}")

    # 2. 发音评分
    pronunciation_result = None
    if reference_text:
        try:
            pronunciation_result = pronunciation_service.score_pronunciation(
                file_content, 
                reference_text, 
                recognized_text
            )
            print(f"发音评分结果: {pronunciation_result}")
        except Exception as e:
            print(f"发音评分失败: {e}")
    
    # 3. 情感识别（传入评分辅助判断）
    emotion = None
    try:
        # 传入评分和尝试次数，提高识别准确性
        temp_score = pronunciation_result.get("score") if pronunciation_result else None
        emotion = emotion_service.detect_emotion(
            file_content, 
            score=temp_score,
            attempt_count=attempt_count
        )
        print(f"情感识别结果: {emotion}")
    except Exception as e:
        print(f"情感识别失败: {e}")

    # 4. 音频特征分析（作为补充）
    audio_segment = _load_audio_segment(file_content)
    metrics = _collect_metrics(audio_segment)
    
    # 5. 综合评分和问题分析
    score, issues = _compute_final_score(
        pronunciation_result, 
        metrics, 
        recognized_text, 
        reference_text
    )
    
    # 6. 如果AI情感识别失败，使用规则判断
    if emotion is None:
        emotion = _pick_emotion(score, issues, metrics)
    
    # 7. 生成反馈
    feedback = build_feedback(score, issues, emotion, recognized_text, reference_text)

    # 8. 自适应反馈机制
    adaptive_feedback = None
    if ADAPTIVE_AVAILABLE:
        try:
            adaptive_feedback = adaptive_service.get_adaptive_feedback(
                score=score,
                emotion_type=emotion["type"],
                attempt_count=attempt_count,
                issues=issues
            )
            # 使用自适应反馈增强主反馈
            if adaptive_feedback and adaptive_feedback.get("strategy_message"):
                feedback = f"{adaptive_feedback['strategy_message']} {feedback}"
        except Exception as e:
            print(f"自适应反馈失败: {e}")

    return {
        "score": score,
        "emotion": emotion,
        "feedback": feedback,
        "audio_path": file_path,
        "strategy_adjusted": emotion["type"] in ['confused', 'frustrated'],
        "issues": issues,
        "recognized_text": recognized_text,  # 新增：识别的文本
        "pronunciation_details": pronunciation_result,  # 新增：详细评分信息
        "adaptive": adaptive_feedback  # 新增：自适应反馈信息
    }


def _load_audio_segment(file_content: bytes) -> AudioSegment:
    try:
        # 尝试直接加载
        return AudioSegment.from_file(BytesIO(file_content))
    except (CouldntDecodeError, Exception) as exc:
        # 如果是webm格式，尝试转换或使用torchaudio
        try:
            import tempfile
            import os
            # 保存为临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                # 尝试用pydub加载（可能需要ffmpeg）
                audio = AudioSegment.from_file(tmp_path)
                return audio
            except Exception:
                # 如果pydub失败，尝试用torchaudio加载webm
                try:
                    import torchaudio
                    waveform, sample_rate = torchaudio.load(tmp_path)
                    # 转换为numpy数组并归一化
                    import numpy as np
                    audio_array = waveform.numpy()[0]  # 取单声道
                    # 转换为pydub可用的格式（16位PCM）
                    audio_array = (audio_array * 32767).astype(np.int16)
                    audio = AudioSegment(
                        audio_array.tobytes(),
                        frame_rate=sample_rate,
                        sample_width=2,
                        channels=1
                    )
                    return audio
                except Exception as e2:
                    print(f"音频加载失败，尝试了多种方法: {e2}")
                    raise ValueError(f"录音文件无法解析: {str(exc)}") from exc
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception as e3:
            raise ValueError(f"录音文件无法解析: {str(exc)}") from exc


def _collect_metrics(audio: AudioSegment) -> dict:
    duration_ms = len(audio)
    duration_sec = duration_ms / 1000.0
    rms = audio.rms or 1
    max_possible = float(1 << (8 * audio.sample_width - 1))
    silence_threshold = max_possible * 0.02

    frame_ms = 200
    silent_frames = 0
    frames = max(1, duration_ms // frame_ms)
    for start in range(0, duration_ms, frame_ms):
        chunk = audio[start:start + frame_ms]
        if chunk.rms < silence_threshold:
            silent_frames += 1

    silence_ratio = min(1.0, silent_frames / frames)

    return {
        "duration_sec": duration_sec,
        "rms": rms,
        "silence_ratio": silence_ratio,
        "sample_width": audio.sample_width
    }


def _compute_final_score(
    pronunciation_result: Optional[dict], 
    metrics: dict, 
    recognized_text: Optional[str],
    reference_text: Optional[str]
) -> tuple[int, list[str]]:
    """
    综合AI评分和音频特征，计算最终分数
    
    Args:
        pronunciation_result: AI发音评分结果
        metrics: 音频特征指标
        recognized_text: ASR识别的文本
        reference_text: 标准文本
    
    Returns:
        (最终分数, 问题列表)
    """
    issues = []
    
    # 优先使用AI评分
    if pronunciation_result and "score" in pronunciation_result:
        ai_score = pronunciation_result["score"]
        # AI评分作为主要依据
        score = ai_score
        
        # 添加AI发现的问题
        if ai_score < 60:
            issues.append("发音需要改进，注意音调和节奏。")
        elif ai_score < 80:
            issues.append("发音不错，但还有提升空间。")
        
        # 添加详细评分信息
        if "accuracy" in pronunciation_result:
            accuracy = pronunciation_result["accuracy"]
            if accuracy < 70:
                issues.append(f"准确度({accuracy}分)需要提高，注意每个字的发音。")
        
        if "fluency" in pronunciation_result:
            fluency = pronunciation_result["fluency"]
            if fluency < 70:
                issues.append(f"流畅度({fluency}分)可以更好，减少停顿。")
    else:
        # 如果没有AI评分，使用规则评分
        score, issues = _score_by_rules(metrics)
    
    # 文本匹配检查
    if recognized_text and reference_text:
        # 简单的文本相似度检查
        ref_clean = reference_text.replace(" ", "").strip()
        rec_clean = recognized_text.replace(" ", "").strip()
        
        if ref_clean and rec_clean:
            # 计算字符匹配率
            ref_chars = set(ref_clean)
            rec_chars = set(rec_clean)
            match_ratio = len(rec_chars & ref_chars) / len(ref_chars) if ref_chars else 0
            
            if match_ratio < 0.7:
                issues.append(f"识别文本与标准文本差异较大，请重新朗读。")
                score = min(score, 60)  # 降低分数
            elif match_ratio < 0.9:
                issues.append("识别文本基本正确，但可以更准确。")
    
    # 音频质量检查（作为补充）
    duration = metrics["duration_sec"]
    rms = metrics["rms"]
    silence_ratio = metrics["silence_ratio"]
    
    if duration < 0.5:
        score = min(score, 50)
        issues.append("录音太短，至少保持 1 秒。")
    elif duration < 0.8:
        score = min(score, score - 10)
        issues.append("录音略短，建议放慢速度。")
    
    quiet_threshold = 200
    if rms < quiet_threshold:
        score = min(score, score - 15)
        issues.append("声音太轻，靠近麦克风再试。")
    
    if silence_ratio > 0.65:
        score = min(score, score - 10)
        issues.append("停顿太多，尽量一口气读完。")
    
    score = max(5, min(100, score))
    
    if score >= 90 and not issues:
        issues.append("节奏自然，继续保持！")
    
    return score, issues

def _score_by_rules(metrics: dict) -> tuple[int, list[str]]:
    """基于规则的评分（备用方案）"""
    duration = metrics["duration_sec"]
    rms = metrics["rms"]
    silence_ratio = metrics["silence_ratio"]
    issues = []
    score = 95

    if duration < 0.8:
        score -= 45
        issues.append("录音太短，至少保持 1 秒。")
    elif duration < 1.5:
        score -= 25
        issues.append("录音略短，建议放慢速度。")
    elif duration > 5:
        score -= 5
        issues.append("语速稍慢，尝试控制在 3 秒内。")

    quiet_threshold = 200
    if rms < quiet_threshold:
        score -= 25
        issues.append("声音太轻，靠近麦克风再试。")
    elif rms < quiet_threshold * 1.5:
        score -= 10
        issues.append("声音有些轻，保持张口和音量。")

    if silence_ratio > 0.65:
        score -= 25
        issues.append("停顿太多，尽量一口气读完。")
    elif silence_ratio > 0.45:
        score -= 10
        issues.append("录音有较多空白，保持节奏。")

    score = max(5, min(100, score))

    if score >= 90 and not issues:
        issues.append("节奏自然，继续保持！")

    return score, issues


def _pick_emotion(score: int, issues: list[str], metrics: dict) -> dict:
    emotions = {
        "neutral": {"type": "neutral", "label": "平静", "tip": "保持专注，继续加油！"},
        "happy": {"type": "happy", "label": "自信", "tip": "太棒了！保持这样的状态。"},
        "confused": {"type": "confused", "label": "困惑", "tip": "我们一起慢一些，再读一遍。"},
        "frustrated": {"type": "frustrated", "label": "挫败", "tip": "别灰心，深呼吸后再试一次。"}
    }

    if score >= 85 and metrics["silence_ratio"] < 0.4:
        return emotions["happy"]
    if score >= 65 and "录音有较多空白，保持节奏。" not in issues:
        return emotions["neutral"]
    if score < 60 and metrics["silence_ratio"] > 0.4:
        return emotions["frustrated"]
    return emotions["confused"]

def build_feedback(
    score: int, 
    issues: list[str], 
    emotion: dict, 
    recognized_text: Optional[str] = None,
    reference_text: Optional[str] = None
) -> str:
    """生成反馈文本"""
    prefix = ""
    if score >= 85:
        prefix = "发音节奏很自然，保持现在的状态。"
    elif score >= 70:
        prefix = "整体不错，再注意以下细节："
    elif emotion["type"] == "frustrated":
        prefix = "没关系，我们一起修正这些小问题："
    else:
        prefix = "试着根据提示调整："

    details = " ".join(issues) if issues else emotion["tip"]
    
    # 如果识别文本与标准文本不一致，添加提示
    if recognized_text and reference_text:
        ref_clean = reference_text.replace(" ", "").strip()
        rec_clean = recognized_text.replace(" ", "").strip()
        if ref_clean != rec_clean:
            details = f"你读的是：{recognized_text}，标准是：{reference_text}。{details}"
    
    return f"{prefix} {details}".strip()

