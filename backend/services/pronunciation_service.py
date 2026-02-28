"""
发音评分服务 - 增强版
支持多维度发音评估:
1. 讯飞API（专业评分，需配置）
2. 本地增强算法（停顿检测、语速、音调、能量分析）
3. 文本相似度匹配
4. 详细问题点反馈
"""
import os
import json
import base64
import hmac
import hashlib
import time
import requests
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlencode
from io import BytesIO

# 可选依赖
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# 讯飞API配置
try:
    import sys
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import config
    XUNFEI_APPID = config.XUNFEI_APPID or os.getenv("XUNFEI_APPID", "")
    XUNFEI_API_KEY = config.XUNFEI_API_KEY or os.getenv("XUNFEI_API_KEY", "")
    XUNFEI_API_SECRET = config.XUNFEI_API_SECRET or os.getenv("XUNFEI_API_SECRET", "")
except ImportError:
    XUNFEI_APPID = os.getenv("XUNFEI_APPID", "")
    XUNFEI_API_KEY = os.getenv("XUNFEI_API_KEY", "")
    XUNFEI_API_SECRET = os.getenv("XUNFEI_API_SECRET", "")

XUNFEI_PRONUNCIATION_URL = "https://ise-api.xfyun.cn/v2/ise"


# ======================== 问题类型定义 ========================

class PronunciationIssue:
    """发音问题类型"""
    
    ISSUES = {
        # 时长问题
        "too_short": {
            "code": "DURATION_SHORT",
            "message": "录音太短，至少保持1秒",
            "suggestion": "慢慢读，不要着急",
            "severity": "high"
        },
        "slightly_short": {
            "code": "DURATION_SLIGHTLY_SHORT",
            "message": "录音略短，建议放慢速度",
            "suggestion": "可以再放慢一点节奏",
            "severity": "medium"
        },
        "too_long": {
            "code": "DURATION_LONG",
            "message": "语速稍慢，尝试更流畅地朗读",
            "suggestion": "试着连贯一些",
            "severity": "low"
        },
        
        # 音量问题
        "too_quiet": {
            "code": "VOLUME_LOW",
            "message": "声音太轻，靠近麦克风再试",
            "suggestion": "大声一点，让老师听清楚",
            "severity": "high"
        },
        "slightly_quiet": {
            "code": "VOLUME_SLIGHTLY_LOW",
            "message": "声音有些轻，保持张口和音量",
            "suggestion": "再大声一点点就更好了",
            "severity": "medium"
        },
        
        # 停顿问题
        "too_many_pauses": {
            "code": "PAUSES_MANY",
            "message": "停顿太多，尽量一口气读完",
            "suggestion": "深呼吸后，一口气读完",
            "severity": "high"
        },
        "some_pauses": {
            "code": "PAUSES_SOME",
            "message": "录音有较多空白，保持节奏",
            "suggestion": "减少中间的停顿",
            "severity": "medium"
        },
        "long_pause": {
            "code": "PAUSE_LONG",
            "message": "中间有较长停顿",
            "suggestion": "尝试保持连贯",
            "severity": "medium"
        },
        
        # 语速问题
        "speaking_too_fast": {
            "code": "SPEED_FAST",
            "message": "语速过快，放慢一些更清晰",
            "suggestion": "慢一点，每个字都读清楚",
            "severity": "medium"
        },
        "speaking_too_slow": {
            "code": "SPEED_SLOW",
            "message": "语速偏慢，可以稍微快一点",
            "suggestion": "节奏可以再快一点",
            "severity": "low"
        },
        
        # 能量变化问题
        "energy_decreasing": {
            "code": "ENERGY_FADE",
            "message": "声音越说越小，保持音量稳定",
            "suggestion": "从头到尾保持一样大声",
            "severity": "medium"
        },
        "energy_unstable": {
            "code": "ENERGY_UNSTABLE",
            "message": "音量不稳定，尝试保持均匀",
            "suggestion": "用稳定的力度读出来",
            "severity": "low"
        },
        
        # 文本匹配问题
        "text_mismatch_high": {
            "code": "TEXT_MISMATCH",
            "message": "识别文本与标准文本差异较大",
            "suggestion": "请重新朗读，注意每个字",
            "severity": "high"
        },
        "text_mismatch_low": {
            "code": "TEXT_SLIGHTLY_OFF",
            "message": "识别文本基本正确，但可以更准确",
            "suggestion": "再仔细读一遍",
            "severity": "low"
        },
        
        # 发音问题
        "accuracy_low": {
            "code": "ACCURACY_LOW",
            "message": "发音准确度需要提高",
            "suggestion": "注意每个字的发音",
            "severity": "high"
        },
        "fluency_low": {
            "code": "FLUENCY_LOW",
            "message": "流畅度可以更好",
            "suggestion": "减少停顿，更连贯地读",
            "severity": "medium"
        },
        
        # 正面反馈
        "good_rhythm": {
            "code": "RHYTHM_GOOD",
            "message": "节奏自然，继续保持！",
            "suggestion": "",
            "severity": "positive"
        },
        "excellent": {
            "code": "EXCELLENT",
            "message": "发音非常标准，太棒了！",
            "suggestion": "",
            "severity": "positive"
        }
    }
    
    @classmethod
    def get(cls, issue_type: str) -> Dict:
        """获取问题详情"""
        return cls.ISSUES.get(issue_type, {
            "code": "UNKNOWN",
            "message": issue_type,
            "suggestion": "",
            "severity": "low"
        })


# ======================== 讯飞API评分 ========================

def _generate_xunfei_auth_url():
    """生成讯飞API的认证URL"""
    if not all([XUNFEI_APPID, XUNFEI_API_KEY, XUNFEI_API_SECRET]):
        return None
    
    date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
    signature_origin = f"host: ise-api.xfyun.cn\ndate: {date}\nGET /v2/ise HTTP/1.1"
    
    signature_sha = hmac.new(
        XUNFEI_API_SECRET.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')
    
    authorization_origin = f'api_key="{XUNFEI_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
    
    return {
        "authorization": authorization,
        "date": date,
        "host": "ise-api.xfyun.cn"
    }


def score_pronunciation_xunfei(audio_content: bytes, reference_text: str) -> Optional[Dict]:
    """使用讯飞API进行发音评分"""
    if not all([XUNFEI_APPID, XUNFEI_API_KEY, XUNFEI_API_SECRET]):
        print("警告: 讯飞API配置不完整")
        return None
    
    try:
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        data = {
            "common": {"app_id": XUNFEI_APPID},
            "business": {
                "category": "read_sentence",
                "rstcd": "utf8",
                "group": "chinese_mandarin",
                "sub": "ise",
                "ent": "cn_vip",
                "cmd": "ssb",
                "auf": "audio/L16;rate=16000",
                "aue": "raw",
                "text": reference_text,
                "ttp_skip": True,
                "aus": 1
            },
            "data": {
                "status": 2,
                "data": audio_base64
            }
        }
        
        auth_params = _generate_xunfei_auth_url()
        if not auth_params:
            return None
        
        response = requests.post(
            XUNFEI_PRONUNCIATION_URL,
            json=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_params.get("authorization"),
                "Date": auth_params.get("date")
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                data_str = result.get("data", "")
                if data_str:
                    decoded_data = base64.b64decode(data_str).decode('utf-8')
                    parsed_data = json.loads(decoded_data)
                    
                    read_chapter = parsed_data.get("read_chapter", {})
                    return {
                        "score": int(read_chapter.get("total_score", 0)),
                        "accuracy": int(read_chapter.get("accuracy_score", 0)),
                        "fluency": int(read_chapter.get("fluency_score", 0)),
                        "completeness": int(read_chapter.get("completeness_score", 0)),
                        "details": parsed_data.get("read_sentence", {}).get("sentences", []),
                        "source": "xunfei"
                    }
        
        print(f"讯飞API调用失败: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"讯飞发音评分错误: {e}")
        return None


# ======================== 本地增强评分 ========================

class LocalPronunciationScorer:
    """本地增强发音评分器"""
    
    def __init__(self, audio_content: bytes, reference_text: str, recognized_text: Optional[str] = None):
        self.audio_content = audio_content
        self.reference_text = reference_text
        self.recognized_text = recognized_text
        self.audio = None
        self.issues: List[Dict] = []
        self.positive_feedback: List[Dict] = []
        self.metrics = {}
    
    def analyze(self) -> Dict:
        """执行完整分析并返回评分结果"""
        # 加载音频
        if not self._load_audio():
            return self._default_result()
        
        # 提取指标
        self._extract_metrics()
        
        # 计算评分
        score = self._calculate_score()
        
        # 生成问题列表
        issues = [issue for issue in self.issues if issue.get("severity") != "positive"]
        positive = [issue for issue in self.positive_feedback]
        
        # 计算子项评分
        accuracy = self._calculate_accuracy_score()
        fluency = self._calculate_fluency_score()
        completeness = self._calculate_completeness_score()
        
        return {
            "score": score,
            "accuracy": accuracy,
            "fluency": fluency,
            "completeness": completeness,
            "issues": issues,
            "positive_feedback": positive,
            "metrics": self.metrics,
            "source": "local_enhanced"
        }
    
    def _load_audio(self) -> bool:
        """加载音频文件"""
        if not PYDUB_AVAILABLE:
            return False
        try:
            self.audio = AudioSegment.from_file(BytesIO(self.audio_content))
            return True
        except Exception as e:
            print(f"音频加载失败: {e}")
            return False
    
    def _extract_metrics(self):
        """提取音频指标"""
        if self.audio is None:
            return
        
        audio = self.audio
        duration_ms = len(audio)
        duration_sec = duration_ms / 1000.0
        rms = audio.rms or 1
        
        # 基本指标
        self.metrics = {
            "duration_sec": duration_sec,
            "rms_energy": rms,
            "max_amplitude": audio.max,
        }
        
        # 静音分析
        self._analyze_silence()
        
        # 能量分析
        self._analyze_energy()
        
        # 语速估算
        self._analyze_speaking_rate()
        
        # 文本匹配分析
        if self.recognized_text and self.reference_text:
            self._analyze_text_match()
    
    def _analyze_silence(self):
        """静音/停顿分析"""
        audio = self.audio
        frame_ms = 100
        max_possible = float(1 << (8 * audio.sample_width - 1))
        silence_threshold = max_possible * 0.02

        frames = list(range(0, len(audio), frame_ms))
        total_frames = max(1, len(frames))
        silent_flags = []
        for start in frames:
            chunk = audio[start:start + frame_ms]
            silent_flags.append(chunk.rms < silence_threshold)

        # 忽略首尾静音，避免“按下录音和松开录音”的空白被过度惩罚
        non_silent_idx = [i for i, is_silent in enumerate(silent_flags) if not is_silent]
        if non_silent_idx:
            active_start = non_silent_idx[0]
            active_end = non_silent_idx[-1]
        else:
            active_start = 0
            active_end = total_frames - 1

        active_total = max(1, active_end - active_start + 1)
        active_flags = silent_flags[active_start:active_end + 1]
        silent_frames = sum(1 for v in active_flags if v)

        silence_segments = []
        current_silence_start = None
        for i, is_silent in enumerate(active_flags):
            if is_silent:
                if current_silence_start is None:
                    current_silence_start = i
            else:
                if current_silence_start is not None:
                    segment_length = i - current_silence_start
                    if segment_length > 2:  # 只计算超过200ms的停顿
                        silence_segments.append(segment_length)
                    current_silence_start = None

        if current_silence_start is not None:
            segment_length = len(active_flags) - current_silence_start
            if segment_length > 2:
                silence_segments.append(segment_length)

        self.metrics["silence_ratio"] = min(1.0, silent_frames / active_total)
        self.metrics["pause_count"] = len(silence_segments)
        self.metrics["max_pause_duration"] = max(silence_segments) * frame_ms / 1000.0 if silence_segments else 0

        if NUMPY_AVAILABLE and silence_segments:
            self.metrics["avg_pause_duration"] = float(np.mean(silence_segments)) * frame_ms / 1000.0
        else:
            self.metrics["avg_pause_duration"] = 0
    
    def _analyze_energy(self):
        """能量变化分析"""
        audio = self.audio
        segment_count = 10
        segment_length = len(audio) // segment_count
        
        if segment_length < 50:
            self.metrics["energy_trend"] = "stable"
            self.metrics["energy_consistency"] = 1.0
            return
        
        energies = []
        for i in range(segment_count):
            start = i * segment_length
            chunk = audio[start:start + segment_length]
            if len(chunk) > 0:
                energies.append(chunk.rms)
        
        if len(energies) >= 3 and NUMPY_AVAILABLE:
            start_energy = float(np.mean(energies[:len(energies)//3]))
            end_energy = float(np.mean(energies[-len(energies)//3:]))
            
            if end_energy < start_energy * 0.6:
                self.metrics["energy_trend"] = "decreasing"
            elif end_energy > start_energy * 1.4:
                self.metrics["energy_trend"] = "increasing"
            else:
                self.metrics["energy_trend"] = "stable"
            
            mean_energy = np.mean(energies)
            if mean_energy > 0:
                self.metrics["energy_consistency"] = float(1.0 - min(1.0, np.std(energies) / mean_energy))
            else:
                self.metrics["energy_consistency"] = 0.5
        else:
            self.metrics["energy_trend"] = "stable"
            self.metrics["energy_consistency"] = 0.5
    
    def _analyze_speaking_rate(self):
        """语速分析"""
        audio = self.audio
        duration_sec = len(audio) / 1000.0
        
        # 基于参考文本长度估算预期时长
        text_len = len(self.reference_text.replace(" ", ""))
        # 假设正常语速：每个汉字约0.3-0.5秒
        expected_min = text_len * 0.25
        expected_max = text_len * 0.8
        
        self.metrics["expected_duration_min"] = expected_min
        self.metrics["expected_duration_max"] = expected_max
        self.metrics["chars_per_second"] = text_len / duration_sec if duration_sec > 0 else 0
        
        # 判断语速
        if duration_sec < expected_min:
            self.metrics["speaking_rate_status"] = "fast"
        elif duration_sec > expected_max:
            self.metrics["speaking_rate_status"] = "slow"
        else:
            self.metrics["speaking_rate_status"] = "normal"
    
    def _analyze_text_match(self):
        """文本匹配分析"""
        ref_clean = self.reference_text.replace(" ", "").strip()
        rec_clean = self.recognized_text.replace(" ", "").strip()
        
        if not ref_clean or not rec_clean:
            self.metrics["text_match_ratio"] = 0
            return
        
        # 计算字符匹配率
        ref_chars = set(ref_clean)
        rec_chars = set(rec_clean)
        match_ratio = len(rec_chars & ref_chars) / len(ref_chars) if ref_chars else 0
        
        # 计算顺序匹配（编辑距离）
        def edit_distance(s1, s2):
            if len(s1) < len(s2):
                return edit_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]
        
        distance = edit_distance(ref_clean, rec_clean)
        max_len = max(len(ref_clean), len(rec_clean))
        sequence_match = 1 - (distance / max_len) if max_len > 0 else 0
        
        self.metrics["text_match_ratio"] = match_ratio
        self.metrics["text_sequence_match"] = sequence_match
        self.metrics["text_combined_match"] = (match_ratio + sequence_match) / 2
    
    def _calculate_score(self) -> int:
        """计算综合评分"""
        score = 85  # 基础分
        
        duration = self.metrics.get("duration_sec", 0)
        rms = self.metrics.get("rms_energy", 0)
        silence_ratio = self.metrics.get("silence_ratio", 0)
        
        # 1. 时长评分
        if duration < 0.5:
            score -= 35
            self.issues.append(PronunciationIssue.get("too_short"))
        elif duration < 0.8:
            score -= 15
            self.issues.append(PronunciationIssue.get("slightly_short"))
        elif duration > 5:
            score -= 5
            self.issues.append(PronunciationIssue.get("too_long"))
        
        # 2. 音量评分
        if rms < 150:
            score -= 20
            self.issues.append(PronunciationIssue.get("too_quiet"))
        elif rms < 250:
            score -= 8
            self.issues.append(PronunciationIssue.get("slightly_quiet"))
        
        # 3. 停顿评分
        if silence_ratio > 0.6:
            score -= 12
            self.issues.append(PronunciationIssue.get("too_many_pauses"))
        elif silence_ratio > 0.4:
            score -= 6
            self.issues.append(PronunciationIssue.get("some_pauses"))
        
        max_pause = self.metrics.get("max_pause_duration", 0)
        if max_pause > 1.5:
            score -= 5
            self.issues.append(PronunciationIssue.get("long_pause"))
        
        # 4. 语速评分
        rate_status = self.metrics.get("speaking_rate_status", "normal")
        if rate_status == "fast":
            score -= 10
            self.issues.append(PronunciationIssue.get("speaking_too_fast"))
        elif rate_status == "slow":
            score -= 5
            self.issues.append(PronunciationIssue.get("speaking_too_slow"))
        
        # 5. 能量变化评分
        energy_trend = self.metrics.get("energy_trend", "stable")
        if energy_trend == "decreasing":
            score -= 8
            self.issues.append(PronunciationIssue.get("energy_decreasing"))
        
        energy_consistency = self.metrics.get("energy_consistency", 0.5)
        if energy_consistency < 0.25:
            score -= 3
            self.issues.append(PronunciationIssue.get("energy_unstable"))
        
        # 6. 文本匹配评分
        text_match = self.metrics.get("text_combined_match", 1.0)
        if text_match < 0.5:
            score -= 25
            self.issues.append(PronunciationIssue.get("text_mismatch_high"))
        elif text_match < 0.8:
            score -= 10
            self.issues.append(PronunciationIssue.get("text_mismatch_low"))
        elif text_match >= 0.95:
            score += 5  # 奖励分

        # 朗读文本匹配很高且时长合理时，给轻微保底加分
        if text_match >= 0.98:
            expected_min = self.metrics.get("expected_duration_min", 0.5)
            expected_max = self.metrics.get("expected_duration_max", 1.6)
            if expected_min <= duration <= expected_max:
                score += 3
        
        # 7. 正面反馈
        if score >= 90 and len(self.issues) == 0:
            self.positive_feedback.append(PronunciationIssue.get("excellent"))
        elif score >= 80 and len(self.issues) <= 1:
            self.positive_feedback.append(PronunciationIssue.get("good_rhythm"))
        
        return max(5, min(100, score))
    
    def _calculate_accuracy_score(self) -> int:
        """计算准确度评分"""
        text_match = self.metrics.get("text_combined_match", 0.7)
        base = int(70 + text_match * 30)
        
        # 根据音量稳定性调整
        energy_consistency = self.metrics.get("energy_consistency", 0.5)
        base = int(base * (0.9 + energy_consistency * 0.1))
        
        return max(30, min(100, base))
    
    def _calculate_fluency_score(self) -> int:
        """计算流畅度评分"""
        silence_ratio = self.metrics.get("silence_ratio", 0.3)
        pause_count = self.metrics.get("pause_count", 0)
        
        base = 85
        base -= int(silence_ratio * 18)
        base -= min(10, pause_count * 2)
        
        # 语速正常加分
        if self.metrics.get("speaking_rate_status") == "normal":
            base += 5
        
        return max(30, min(100, base))
    
    def _calculate_completeness_score(self) -> int:
        """计算完整度评分"""
        duration = self.metrics.get("duration_sec", 0)
        expected_min = self.metrics.get("expected_duration_min", 0.5)
        
        if duration < expected_min * 0.5:
            return 50
        elif duration < expected_min:
            return 70
        else:
            return 90
    
    def _default_result(self) -> Dict:
        """返回默认结果"""
        return {
            "score": 60,
            "accuracy": 55,
            "fluency": 60,
            "completeness": 58,
            "issues": [],
            "positive_feedback": [],
            "metrics": {},
            "source": "default"
        }


# ======================== 主要API ========================

def score_pronunciation_local(
    audio_content: bytes, 
    reference_text: str, 
    recognized_text: Optional[str] = None
) -> Dict:
    """
    本地发音评分算法（增强版）
    
    Args:
        audio_content: 音频文件字节内容
        reference_text: 标准文本
        recognized_text: ASR识别的文本（如果已识别）
    
    Returns:
        评分结果字典
    """
    scorer = LocalPronunciationScorer(audio_content, reference_text, recognized_text)
    return scorer.analyze()


def score_pronunciation(
    audio_content: bytes, 
    reference_text: str, 
    recognized_text: Optional[str] = None
) -> Dict:
    """
    发音评分主函数
    优先使用讯飞API，失败则使用本地增强算法
    
    Args:
        audio_content: 音频文件字节内容
        reference_text: 标准文本
        recognized_text: ASR识别的文本（可选）
    
    Returns:
        评分结果字典
    """
    # 尝试使用讯飞API
    if all([XUNFEI_APPID, XUNFEI_API_KEY, XUNFEI_API_SECRET]):
        result = score_pronunciation_xunfei(audio_content, reference_text)
        if result:
            # 如果有识别文本，添加本地分析作为补充
            if recognized_text:
                local_result = score_pronunciation_local(audio_content, reference_text, recognized_text)
                result["issues"] = local_result.get("issues", [])
                result["positive_feedback"] = local_result.get("positive_feedback", [])
                result["local_metrics"] = local_result.get("metrics", {})
            return result
    
    # 使用本地增强算法
    print("使用本地发音评分算法")
    return score_pronunciation_local(audio_content, reference_text, recognized_text)


def get_improvement_suggestions(issues: List[Dict]) -> List[str]:
    """
    根据问题列表生成改进建议
    
    Args:
        issues: 问题列表
    
    Returns:
        建议列表
    """
    suggestions = []
    
    # 按严重程度排序
    severity_order = {"high": 0, "medium": 1, "low": 2, "positive": 3}
    sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.get("severity", "low"), 2))
    
    for issue in sorted_issues[:3]:  # 最多显示3个主要问题
        suggestion = issue.get("suggestion", "")
        if suggestion:
            suggestions.append(suggestion)
    
    if not suggestions:
        suggestions.append("继续保持练习！")
    
    return suggestions
