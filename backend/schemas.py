from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re


# ============ 输入验证辅助函数 ============

def sanitize_text(text: str, max_length: int = 500) -> str:
    """清理文本输入，移除危险字符"""
    if not text:
        return ""
    # 移除控制字符，保留换行符
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # 截断长度
    return cleaned[:max_length].strip()


# ============ 课程相关 ============

class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="课程标题")
    desc: Optional[str] = Field(default="", max_length=500, description="课程描述")
    level: Optional[str] = Field(default="Level 1", description="课程等级")
    duration: Optional[int] = Field(default=5, ge=1, le=120, description="课程时长(分钟)")
    content_json: Optional[str] = Field(default="[]", description="课程内容JSON")

class CourseCreate(CourseBase):
    pass

class Course(CourseBase):
    id: int
    class Config:
        from_attributes = True

class AnalysisResult(BaseModel):
    score: float = Field(..., ge=0, le=100, description="得分")
    emotion: dict
    feedback: str
    strategy_adjusted: bool
    feedback_audio: Optional[str] = None
    issues: List[str] = []


# ============ 请求模型 ============

class ChatTextRequest(BaseModel):
    """AI文本聊天请求"""
    text: str = Field(..., min_length=1, max_length=500, description="用户输入文本")
    mode: str = Field(default="chat", pattern=r'^(chat|story)$', description="聊天模式")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        return sanitize_text(v, 500)


class TTSRequest(BaseModel):
    """TTS请求"""
    text: str = Field(..., min_length=1, max_length=260, description="要合成的文本")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        return sanitize_text(v, 260)


class LearningRecordOut(BaseModel):
    id: int
    user_id: int
    course_id: int
    word_text: str
    score: float = Field(..., ge=0, le=100)
    emotion_type: str
    emotion_label: str
    feedback_text: str
    created_at: str


class StatsOut(BaseModel):
    learning_days: int
    total_records: int
    avg_score: float
    total_stars: int
    badges: int


class MoodDayOut(BaseModel):
    day: str
    value: int
    color: str
    emotion: str


class WeakWordOut(BaseModel):
    """薄弱词汇响应"""
    word_text: str
    pinyin: str
    times: int = Field(..., ge=0)
    avg_score: float = Field(..., ge=0, le=100)
    last_score: float = Field(..., ge=0, le=100)
    last_time: str


# ============ 参数验证工具 ============

def validate_course_id(course_id: int) -> int:
    """验证课程ID"""
    if course_id < 1:
        raise ValueError("课程ID必须大于0")
    return course_id


def validate_user_id(user_id: int) -> int:
    """验证用户ID"""
    if user_id < 1:
        raise ValueError("用户ID必须大于0")
    return user_id


def validate_limit(limit: int, max_limit: int = 500) -> int:
    """验证分页限制"""
    return max(1, min(max_limit, limit))
