"""
配置文件
用于管理API密钥等配置
"""
import os
from pathlib import Path
from typing import Optional


def _load_env_file(path: Path) -> None:
    """
    读取一个简单的 .env 文件（KEY=VALUE），写入 os.environ。
    - 忽略空行与 # 注释
    - 不覆盖已存在的环境变量（优先环境变量 > 文件）
    """
    try:
        if not path.exists() or not path.is_file():
            return

        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        # 配置加载失败不应阻塞应用启动
        return


# 自动加载本地配置（避免把密钥写进代码）
_ROOT = Path(__file__).resolve().parents[1]
_load_env_file(_ROOT / ".env.local")
_load_env_file(_ROOT / "backend" / ".env.local")
_load_env_file(_ROOT / "config.local.txt")
_load_env_file(_ROOT / "backend" / "config.local.txt")


class Config:
    """应用配置"""
    
    # 讯飞API配置（可选，用于发音评分）
    # 获取方式：https://www.xfyun.cn/ 注册并创建应用
    XUNFEI_APPID: Optional[str] = os.getenv("XUNFEI_APPID", "")
    XUNFEI_API_KEY: Optional[str] = os.getenv("XUNFEI_API_KEY", "")
    XUNFEI_API_SECRET: Optional[str] = os.getenv("XUNFEI_API_SECRET", "")
    
    # AI模型配置
    USE_GPU: bool = os.getenv("USE_GPU", "false").lower() == "true"  # 是否使用GPU
    
    # 大模型API配置（可选，用于AI聊天）
    # 选项1: OpenAI API
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # 选项2: DeepSeek API（国内，兼容OpenAI格式）
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: Optional[str] = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # 选项3: 国内大模型（通义千问/文心一言等）
    # 通义千问
    DASHSCOPE_API_KEY: Optional[str] = os.getenv("DASHSCOPE_API_KEY", "")
    # 文心一言
    BAIDU_API_KEY: Optional[str] = os.getenv("BAIDU_API_KEY", "")
    BAIDU_SECRET_KEY: Optional[str] = os.getenv("BAIDU_SECRET_KEY", "")
    
    # 使用哪个API（openai/deepseek/dashscope/baidu/offline）
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "offline").lower()
    
    # 音频处理配置
    AUDIO_UPLOAD_DIR: str = os.getenv("AUDIO_UPLOAD_DIR", "uploads")
    TTS_OUTPUT_DIR: str = os.getenv("TTS_OUTPUT_DIR", "uploads/tts")
    
    @classmethod
    def is_xunfei_configured(cls) -> bool:
        """检查讯飞API是否已配置"""
        return all([cls.XUNFEI_APPID, cls.XUNFEI_API_KEY, cls.XUNFEI_API_SECRET])
    
    @classmethod
    def is_llm_configured(cls) -> bool:
        """检查大模型API是否已配置"""
        if cls.LLM_PROVIDER == "offline":
            return False
        elif cls.LLM_PROVIDER == "openai":
            return bool(cls.OPENAI_API_KEY)
        elif cls.LLM_PROVIDER == "deepseek":
            return bool(cls.DEEPSEEK_API_KEY)
        elif cls.LLM_PROVIDER == "dashscope":
            return bool(cls.DASHSCOPE_API_KEY)
        elif cls.LLM_PROVIDER == "baidu":
            return bool(cls.BAIDU_API_KEY and cls.BAIDU_SECRET_KEY)
        return False

# 导出配置实例
config = Config()

