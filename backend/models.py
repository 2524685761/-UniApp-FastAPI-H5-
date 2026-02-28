from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    level = Column(String, default="L1")
    created_at = Column(DateTime, default=datetime.now)

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    desc = Column(String)
    level = Column(String)
    duration = Column(Integer) # 分钟
    content_json = Column(String) # 存储 JSON 字符串的课程内容

class LearningRecord(Base):
    __tablename__ = "learning_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    word_text = Column(String)
    audio_path = Column(String) # 录音文件路径
    score = Column(Float)
    emotion_type = Column(String) # happy, neutral, confused, frustrated
    emotion_label = Column(String)
    feedback_text = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    course = relationship("Course")

