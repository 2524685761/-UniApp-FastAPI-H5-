"""
情感自适应反馈机制服务
当检测到负面情绪时，智能调整学习节奏和难度

功能：
1. 学习节奏调整策略
2. 题目难度动态调整
3. 个性化鼓励策略
4. 练习内容智能切换
5. 学习状态追踪与分析
"""
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# 日志支持
try:
    from ..logger import log_info, log_warning
except ImportError:
    def log_info(ctx, msg, extra=None): print(f"[INFO] {ctx}: {msg}")
    def log_warning(ctx, msg, extra=None): print(f"[WARN] {ctx}: {msg}")


# ======================== 学习状态定义 ========================

class LearningState:
    """学习状态类型"""
    EXCELLENT = "excellent"      # 表现优秀
    GOOD = "good"                # 表现良好
    NORMAL = "normal"            # 正常状态
    STRUGGLING = "struggling"    # 有些困难
    FRUSTRATED = "frustrated"    # 感到挫败
    NEEDS_BREAK = "needs_break"  # 需要休息


class DifficultyLevel:
    """难度等级"""
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    
    @classmethod
    def get_order(cls, level: str) -> int:
        order = {cls.EASY: 1, cls.NORMAL: 2, cls.HARD: 3}
        return order.get(level, 2)


# ======================== 自适应策略定义 ========================

ADAPTIVE_STRATEGIES = {
    # 当检测到优秀表现时
    "excellent": {
        "demo_count": 1,          # 示范次数
        "demo_speed": 1.0,        # 示范语速
        "wait_before_record": 1,  # 录音前等待（秒）
        "auto_next": True,        # 自动进入下一题
        "next_delay": 2.0,        # 下一题延迟（秒）
        "difficulty_adjust": 1,   # 难度调整（+1升难度）
        "praise_level": "high",   # 表扬程度
        "show_progress": True,    # 显示进度
        "messages": [
            "太棒了！你学得真快！",
            "完美！继续挑战下一个！",
            "你真是学习小天才！",
            "老师都要为你鼓掌了！"
        ]
    },
    
    # 当检测到良好表现时
    "good": {
        "demo_count": 1,
        "demo_speed": 1.0,
        "wait_before_record": 1.5,
        "auto_next": True,
        "next_delay": 2.5,
        "difficulty_adjust": 0,
        "praise_level": "medium",
        "show_progress": True,
        "messages": [
            "不错哦！继续加油！",
            "读得很好，再来下一个！",
            "你进步很大！",
            "保持这个状态！"
        ]
    },
    
    # 正常状态
    "normal": {
        "demo_count": 1,
        "demo_speed": 1.0,
        "wait_before_record": 2,
        "auto_next": False,
        "next_delay": 3.0,
        "difficulty_adjust": 0,
        "praise_level": "low",
        "show_progress": True,
        "messages": [
            "继续加油！",
            "保持专注！",
            "再来一次会更好！"
        ]
    },
    
    # 当检测到困难时
    "struggling": {
        "demo_count": 2,          # 多示范一次
        "demo_speed": 0.85,       # 放慢语速
        "wait_before_record": 3,  # 给更多准备时间
        "auto_next": False,
        "next_delay": 4.0,
        "difficulty_adjust": 0,
        "praise_level": "encouraging",
        "show_progress": False,   # 暂时隐藏进度，减少压力
        "offer_retry": True,      # 提供重试选项
        "offer_demo": True,       # 提供再听一次
        "messages": [
            "没关系，我们再来一次！",
            "慢慢来，不着急～",
            "先听我读，然后跟着读！",
            "这个词有点难，我们多练几次！"
        ]
    },
    
    # 当检测到挫败时
    "frustrated": {
        "demo_count": 2,
        "demo_speed": 0.75,       # 明显放慢
        "wait_before_record": 4,
        "auto_next": False,
        "next_delay": 5.0,
        "difficulty_adjust": -1,  # 降低难度
        "praise_level": "comforting",
        "show_progress": False,
        "offer_retry": True,
        "offer_skip": True,       # 提供跳过选项
        "offer_break": True,      # 提供休息选项
        "offer_easier": True,     # 提供更简单的题目
        "messages": [
            "别着急，学习本来就需要时间！",
            "你已经很努力了！休息一下？",
            "我们换一个试试？",
            "没关系没关系，慢慢来～",
            "深呼吸，我们再试一次！"
        ]
    },
    
    # 需要休息
    "needs_break": {
        "demo_count": 0,
        "demo_speed": 0.8,
        "wait_before_record": 5,
        "auto_next": False,
        "next_delay": 0,
        "difficulty_adjust": -1,
        "praise_level": "caring",
        "show_progress": False,
        "suggest_break": True,
        "break_duration": 5,      # 建议休息时长（分钟）
        "messages": [
            "你学了好久了，休息一下吧！",
            "喝点水，活动活动再继续！",
            "今天的学习很棒，可以先休息一下！",
            "学习也要劳逸结合哦～"
        ]
    }
}


# ======================== 自适应引擎 ========================

class AdaptiveEngine:
    """自适应学习引擎"""
    
    def __init__(self):
        self.session_stats = {
            "start_time": datetime.now(),
            "total_attempts": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "consecutive_correct": 0,
            "consecutive_incorrect": 0,
            "emotion_history": [],
            "score_history": [],
            "difficulty_level": DifficultyLevel.NORMAL
        }
    
    def analyze_learning_state(
        self, 
        score: int, 
        emotion_type: str,
        attempt_count: int = 1
    ) -> str:
        """
        分析当前学习状态
        
        Args:
            score: 本次评分
            emotion_type: 检测到的情感类型
            attempt_count: 当前词的尝试次数
        
        Returns:
            学习状态类型
        """
        # 更新统计
        self.session_stats["total_attempts"] += 1
        self.session_stats["score_history"].append(score)
        self.session_stats["emotion_history"].append(emotion_type)
        
        if score >= 70:
            self.session_stats["correct_count"] += 1
            self.session_stats["consecutive_correct"] += 1
            self.session_stats["consecutive_incorrect"] = 0
        else:
            self.session_stats["incorrect_count"] += 1
            self.session_stats["consecutive_incorrect"] += 1
            self.session_stats["consecutive_correct"] = 0
        
        # 检查是否需要休息
        if self._needs_break():
            return LearningState.NEEDS_BREAK
        
        # 基于多个因素判断状态
        
        # 1. 连续失败多次
        if self.session_stats["consecutive_incorrect"] >= 3:
            return LearningState.FRUSTRATED
        
        # 2. 当前尝试多次仍未成功
        if attempt_count >= 3 and score < 60:
            return LearningState.FRUSTRATED
        
        # 3. 检测到负面情绪
        if emotion_type in ["frustrated"]:
            return LearningState.FRUSTRATED
        
        if emotion_type in ["confused"]:
            if score < 60:
                return LearningState.STRUGGLING
            return LearningState.NORMAL
        
        # 4. 高分且积极情绪
        if score >= 90 and emotion_type in ["happy", "neutral"]:
            if self.session_stats["consecutive_correct"] >= 3:
                return LearningState.EXCELLENT
            return LearningState.GOOD
        
        # 5. 一般情况
        if score >= 80:
            return LearningState.GOOD
        elif score >= 60:
            return LearningState.NORMAL
        else:
            return LearningState.STRUGGLING
    
    def _needs_break(self) -> bool:
        """判断是否需要休息"""
        # 学习超过15分钟
        elapsed = datetime.now() - self.session_stats["start_time"]
        if elapsed > timedelta(minutes=15):
            return True
        
        # 连续尝试超过20次
        if self.session_stats["total_attempts"] > 20:
            return True
        
        # 最近5次都是负面情绪
        recent_emotions = self.session_stats["emotion_history"][-5:]
        if len(recent_emotions) >= 5:
            negative_count = sum(1 for e in recent_emotions if e in ["confused", "frustrated"])
            if negative_count >= 4:
                return True
        
        return False
    
    def get_strategy(self, learning_state: str) -> Dict:
        """获取对应的自适应策略"""
        return ADAPTIVE_STRATEGIES.get(learning_state, ADAPTIVE_STRATEGIES["normal"])
    
    def get_random_message(self, learning_state: str) -> str:
        """获取随机的鼓励消息"""
        strategy = self.get_strategy(learning_state)
        messages = strategy.get("messages", ["加油！"])
        return random.choice(messages)
    
    def adjust_difficulty(self, current_words: List[Dict], learning_state: str) -> Tuple[List[Dict], str]:
        """
        根据学习状态调整题目难度
        
        Args:
            current_words: 当前词汇列表
            learning_state: 学习状态
        
        Returns:
            (调整后的词汇列表, 调整说明)
        """
        strategy = self.get_strategy(learning_state)
        adjust = strategy.get("difficulty_adjust", 0)
        
        if adjust == 0:
            return current_words, "保持当前难度"
        
        # 这里可以根据词汇的复杂度重新排序
        # 简单实现：根据词汇长度排序
        if adjust < 0:
            # 降低难度：优先显示短词
            sorted_words = sorted(current_words, key=lambda x: len(x.get("text", "")))
            return sorted_words, "已调整为更简单的词汇"
        else:
            # 提高难度：优先显示长词
            sorted_words = sorted(current_words, key=lambda x: -len(x.get("text", "")))
            return sorted_words, "已调整为更有挑战的词汇"
    
    def suggest_alternative_word(
        self, 
        current_word: Dict, 
        all_words: List[Dict]
    ) -> Optional[Dict]:
        """
        推荐替代词汇（当学习者多次失败时）
        
        Args:
            current_word: 当前词汇
            all_words: 所有可用词汇
        
        Returns:
            推荐的替代词汇
        """
        current_text = current_word.get("text", "")
        current_len = len(current_text)
        
        # 找到比当前词更简单的词
        easier_words = [
            w for w in all_words 
            if len(w.get("text", "")) < current_len 
            and w.get("text") != current_text
        ]
        
        if easier_words:
            return random.choice(easier_words)
        
        # 如果没有更简单的，随机选一个不同的
        different_words = [
            w for w in all_words 
            if w.get("text") != current_text
        ]
        
        return random.choice(different_words) if different_words else None
    
    def get_session_summary(self) -> Dict:
        """获取学习会话总结"""
        total = self.session_stats["total_attempts"]
        correct = self.session_stats["correct_count"]
        
        if total == 0:
            accuracy = 0
        else:
            accuracy = (correct / total) * 100
        
        avg_score = 0
        if self.session_stats["score_history"]:
            avg_score = sum(self.session_stats["score_history"]) / len(self.session_stats["score_history"])
        
        # 判断整体表现
        if accuracy >= 80 and avg_score >= 85:
            overall = "excellent"
            summary_message = "太棒了！今天学得非常好！"
        elif accuracy >= 60 and avg_score >= 70:
            overall = "good"
            summary_message = "不错！继续努力会更好！"
        else:
            overall = "needs_practice"
            summary_message = "多练习就会进步的！加油！"
        
        return {
            "total_attempts": total,
            "correct_count": correct,
            "accuracy": round(accuracy, 1),
            "average_score": round(avg_score, 1),
            "duration_minutes": (datetime.now() - self.session_stats["start_time"]).seconds // 60,
            "overall_performance": overall,
            "summary_message": summary_message
        }


# ======================== 反馈生成器 ========================

class FeedbackGenerator:
    """反馈内容生成器"""
    
    # 表扬语库
    PRAISE_TEMPLATES = {
        "high": [
            "🌟 太棒了！发音非常标准！",
            "🎉 完美！你是学习小明星！",
            "✨ 哇！读得太好了！",
            "🏆 超级棒！老师都要表扬你！"
        ],
        "medium": [
            "👍 不错！继续加油！",
            "😊 读得很好哦！",
            "🌈 进步很大！",
            "💪 你做到了！"
        ],
        "low": [
            "继续保持！",
            "可以的！",
            "再接再厉！"
        ],
        "encouraging": [
            "💝 没关系，慢慢来！",
            "🌻 你已经很努力了！",
            "🌸 再试一次，你可以的！",
            "💫 相信自己！"
        ],
        "comforting": [
            "🤗 别着急，学习需要时间",
            "💖 休息一下再试试？",
            "🌺 换一个词也没关系哦",
            "🍀 你做得比你想象的好！"
        ],
        "caring": [
            "☕ 休息一下吧！",
            "🌙 今天学得够多了！",
            "🎈 明天继续加油！",
            "💕 你今天很棒！"
        ]
    }
    
    # 建议语库
    SUGGESTION_TEMPLATES = {
        "retry": "再试一次，你一定可以！",
        "listen_again": "先听我读一遍，然后跟着读！",
        "slow_down": "慢一点，每个字都读清楚！",
        "louder": "大声一点，让老师听清楚！",
        "skip": "我们先跳过，一会儿再回来！",
        "break": "休息一下，喝点水吧！"
    }
    
    @classmethod
    def generate_praise(cls, level: str) -> str:
        """生成表扬语"""
        templates = cls.PRAISE_TEMPLATES.get(level, cls.PRAISE_TEMPLATES["low"])
        return random.choice(templates)
    
    @classmethod
    def generate_feedback(
        cls,
        score: int,
        learning_state: str,
        issues: List[Dict] = None
    ) -> Dict:
        """
        生成完整的反馈内容
        
        Args:
            score: 评分
            learning_state: 学习状态
            issues: 问题列表
        
        Returns:
            反馈内容字典
        """
        strategy = ADAPTIVE_STRATEGIES.get(learning_state, ADAPTIVE_STRATEGIES["normal"])
        
        # 生成主要反馈
        praise_level = strategy.get("praise_level", "low")
        main_feedback = cls.generate_praise(praise_level)
        
        # 生成建议
        suggestions = []
        normalized_issues = issues
        if isinstance(normalized_issues, (str, dict)):
            normalized_issues = [normalized_issues]
        elif normalized_issues is None:
            normalized_issues = []
        elif not isinstance(normalized_issues, list):
            try:
                normalized_issues = list(normalized_issues)
            except Exception:
                normalized_issues = []

        if normalized_issues:
            for issue in normalized_issues[:2]:  # 最多显示2个问题的建议
                if isinstance(issue, dict):
                    suggestion = issue.get("suggestion", "") or issue.get("message", "")
                else:
                    suggestion = str(issue).strip()
                if suggestion:
                    suggestions.append(suggestion)
        
        # 根据状态添加额外建议
        if strategy.get("offer_retry"):
            suggestions.append(cls.SUGGESTION_TEMPLATES["retry"])
        if strategy.get("offer_demo"):
            suggestions.append(cls.SUGGESTION_TEMPLATES["listen_again"])
        
        # 生成策略消息
        strategy_message = random.choice(strategy.get("messages", ["加油！"]))
        
        return {
            "main_feedback": main_feedback,
            "strategy_message": strategy_message,
            "suggestions": suggestions,
            "show_retry_button": strategy.get("offer_retry", False),
            "show_skip_button": strategy.get("offer_skip", False),
            "show_break_button": strategy.get("offer_break", False),
            "auto_demo": strategy.get("demo_count", 1) > 1,
            "demo_speed": strategy.get("demo_speed", 1.0)
        }


# ======================== 主要API ========================

# 全局自适应引擎实例
_adaptive_engine = None


def get_adaptive_engine() -> AdaptiveEngine:
    """获取自适应引擎实例"""
    global _adaptive_engine
    if _adaptive_engine is None:
        _adaptive_engine = AdaptiveEngine()
    return _adaptive_engine


def reset_session():
    """重置学习会话"""
    global _adaptive_engine
    _adaptive_engine = AdaptiveEngine()


def get_adaptive_feedback(
    score: int,
    emotion_type: str,
    attempt_count: int = 1,
    issues: List[Dict] = None
) -> Dict:
    """
    获取自适应反馈
    
    Args:
        score: 评分
        emotion_type: 情感类型
        attempt_count: 尝试次数
        issues: 问题列表
    
    Returns:
        自适应反馈字典
    """
    engine = get_adaptive_engine()
    
    # 分析学习状态
    learning_state = engine.analyze_learning_state(score, emotion_type, attempt_count)
    
    # 获取策略
    strategy = engine.get_strategy(learning_state)
    
    # 生成反馈
    feedback = FeedbackGenerator.generate_feedback(score, learning_state, issues)
    
    # 合并结果
    result = {
        "learning_state": learning_state,
        "strategy": strategy,
        **feedback,
        "session_stats": {
            "total_attempts": engine.session_stats["total_attempts"],
            "consecutive_correct": engine.session_stats["consecutive_correct"],
            "consecutive_incorrect": engine.session_stats["consecutive_incorrect"]
        }
    }
    
    log_info("Adaptive", f"状态={learning_state}, 分数={score}, 情感={emotion_type}")
    
    return result


def should_adjust_difficulty(score: int, emotion_type: str, attempt_count: int) -> Tuple[bool, str]:
    """
    判断是否需要调整难度
    
    Returns:
        (是否调整, 调整方向 "easier"/"harder"/"none")
    """
    engine = get_adaptive_engine()
    learning_state = engine.analyze_learning_state(score, emotion_type, attempt_count)
    strategy = engine.get_strategy(learning_state)
    
    adjust = strategy.get("difficulty_adjust", 0)
    if adjust < 0:
        return True, "easier"
    elif adjust > 0:
        return True, "harder"
    return False, "none"


def get_encouragement_for_emotion(emotion_type: str, score: int = None) -> str:
    """
    根据情感类型获取鼓励语
    
    Args:
        emotion_type: 情感类型
        score: 评分（可选）
    
    Returns:
        鼓励语文本
    """
    # 确定状态
    if emotion_type == "frustrated":
        state = "frustrated"
    elif emotion_type == "confused":
        state = "struggling"
    elif emotion_type == "happy" and score and score >= 85:
        state = "excellent"
    elif score and score >= 70:
        state = "good"
    else:
        state = "normal"
    
    strategy = ADAPTIVE_STRATEGIES.get(state, ADAPTIVE_STRATEGIES["normal"])
    messages = strategy.get("messages", ["加油！"])
    return random.choice(messages)


def get_session_summary() -> Dict:
    """获取当前学习会话总结"""
    engine = get_adaptive_engine()
    return engine.get_session_summary()
