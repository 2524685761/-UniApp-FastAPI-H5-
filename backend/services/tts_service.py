import pyttsx3
import os
import uuid
import threading
import hashlib
import re
import requests
import json
from typing import Any
from pathlib import Path
from datetime import datetime, timedelta

# 日志支持（可选）
try:
    from ..logger import log_info, log_warning, log_error
except ImportError:
    def log_info(ctx, msg, extra=None): print(f"[INFO] {ctx}: {msg}")
    def log_warning(ctx, msg, extra=None): print(f"[WARN] {ctx}: {msg}")
    def log_error(ctx, err, extra=None): print(f"[ERROR] {ctx}: {err}")


def _load_env_file(path: Path) -> None:
    """
    读取一个简单的 .env 文件（KEY=VALUE），写入 os.environ。
    - 忽略空行与 # 注释
    - 不覆盖已存在的环境变量（优先环境变量 > 文件）

    说明：TTS 服务可能在应用启动早期被导入；为确保能读取 config.local.txt，
    这里做一次轻量的 env 文件加载（与 backend/config.py 保持一致）。
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
        return


# 确保本地配置被加载（避免没 import backend.config 时，TTS 退回 local）
_ROOT = Path(__file__).resolve().parents[2]
_load_env_file(_ROOT / ".env.local")
_load_env_file(_ROOT / "backend" / ".env.local")
_load_env_file(_ROOT / "config.local.txt")
_load_env_file(_ROOT / "backend" / "config.local.txt")

# pyttsx3 在 Windows + 多线程场景下容易出现句柄占用问题
# 通过锁保证同一时间只有一个线程在生成语音，同时在函数内临时初始化引擎
OUTPUT_DIR = "uploads/tts"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

_engine_lock = threading.Lock()
_tts_lock = threading.Lock()

def _build_engine():
    engine = pyttsx3.init()
    for voice in engine.getProperty("voices"):
        if "Chinese" in voice.name or "ZH" in voice.id:
            engine.setProperty("voice", voice.id)
            break
    engine.setProperty("rate", 180)
    return engine


def _detect_audio_ext_from_bytes(content: bytes, fallback: str = "mp3") -> str:
    """根据音频字节头识别扩展名，识别失败时使用 fallback。"""
    if not content:
        return fallback
    head = content[:16]
    if head.startswith(b"RIFF"):
        return "wav"
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "mp3"
    if head.startswith(b"OggS"):
        return "ogg"
    if head.startswith(b"fLaC"):
        return "flac"
    return fallback


def _replace_ext(path: str, ext: str) -> str:
    base, _ = os.path.splitext(path)
    return f"{base}.{ext.lstrip('.')}"


def _write_audio_with_detected_ext(preferred_out_path: str, content: bytes, fallback_ext: str = "mp3") -> str:
    """
    按真实音频格式落盘，返回实际路径。
    例如 URL 实际是 wav 时，避免写成 .mp3 导致缓存失效和前端解码问题。
    """
    ext = _detect_audio_ext_from_bytes(content, fallback=fallback_ext)
    actual_out_path = _replace_ext(preferred_out_path, ext)
    with open(actual_out_path, "wb") as f:
        f.write(content)
    return actual_out_path


def _openai_compat_tts_to_mp3(text: str, out_path: str) -> str:
    """
    使用 OpenAI 兼容接口生成 TTS（可对接 V-API / OpenAI / 任何兼容中转）。

    依赖环境变量：
    - TTS_PROVIDER=openai_compat
    - OPENAI_API_KEY=...
    - OPENAI_BASE_URL=https://api.v36.cm/v1  (或 https://api.openai.com/v1)
    - OPENAI_TTS_MODEL=tts-1 (可选)
    - OPENAI_TTS_VOICE=alloy (可选)
    """
    # 强制重新读取关键配置，确保配置生效
    # 这里为了稳定性，牺牲微小的性能读取本地配置文件
    from pathlib import Path
    _local_conf = Path(__file__).resolve().parents[2] / "config.local.txt"
    if _local_conf.exists():
        try:
            for line in _local_conf.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
        except:
            pass

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    model = os.getenv("OPENAI_TTS_MODEL", "tts-1").strip()
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy").strip()
    speed_raw = os.getenv("OPENAI_TTS_SPEED", "").strip()
    instructions = os.getenv("OPENAI_TTS_INSTRUCTIONS", "").strip()
    speed: float | None = None
    if speed_raw:
        try:
            speed = float(speed_raw)
        except Exception:
            speed = None

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty")
    if "REPLACE_ME" in api_key:
        raise RuntimeError("OPENAI_API_KEY is placeholder")

    url = f"{base_url}/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    def _model_supports_instructions(m: str) -> bool:
        # 兼容性考虑：tts-1/tts-1-hd 往往不支持 instructions
        ml = (m or "").lower()
        if ml in ("tts-1", "tts-1-hd"):
            return False
        # 经验：带 -tts 的新模型更可能支持
        return "tts" in ml and ml not in ("tts-1", "tts-1-hd")

    def _post(payload: dict) -> requests.Response:
        return requests.post(url, headers=headers, json=payload, timeout=60)

    def _build_payload(m: str, v: str, spd: float | None, instr: str) -> dict:
        payload = {
            "model": m,
            "input": text,
            "voice": v,
            "response_format": "mp3",  # 使用标准的 OpenAI 参数名
        }
        if spd is not None:
            payload["speed"] = spd
        if instr and _model_supports_instructions(m):
            payload["instructions"] = instr
        return payload

    def _should_fallback_to_tts1(status: int, body: str) -> bool:
        # V-API 常见：403 + “不支持模型”
        s = (body or "")
        return status in (400, 401, 403) and ("不支持模型" in s or "model" in s.lower())

    # 尝试顺序：当前配置 -> (如不支持模型) tts-1 -> (如参数不兼容) 去掉speed -> 换voice兜底
    attempts: list[dict] = []
    attempts.append(_build_payload(model, voice, speed, instructions))

    if model.lower() != "tts-1":
        attempts.append(_build_payload("tts-1", voice, speed, ""))  # tts-1 不发 instructions

    # 如果 speed 造成不兼容，再尝试不带 speed
    if speed is not None:
        attempts.append(_build_payload("tts-1", voice, None, ""))

    # voice 兜底（更偏女声/可爱）
    for v in ("shimmer", "nova", "fable", "alloy"):
        attempts.append(_build_payload("tts-1", v, None, ""))

    last_err = None
    for i, payload in enumerate(attempts):
        print(f"[tts] Attempt {i+1}: model={payload.get('model')} voice={payload.get('voice')}")
        resp = _post(payload)
        
        # 调试：打印详细响应
        try:
            print(f"[tts] Response {resp.status_code}: {resp.text[:200]}")
        except:
            pass
            
        if resp.status_code == 200:
            # 兼容处理：标准 OpenAI 接口直接返回 binary，
            # 但部分中转商（如 api.gpt.ge / api.v36.cm）调用阿里云 Qwen 时可能返回 JSON + URL
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "application/json" in ctype:
                try:
                    data = resp.json()
                    # 尝试从 JSON 中提取 audio url
                    # 常见结构 1 (DashScope 风格): output.audio.url / output.audio.audio_url
                    # 常见结构 2: audio_url / url
                    audio_url = (
                        (((data.get("output") or {}).get("audio") or {}).get("url")) or
                        (((data.get("output") or {}).get("audio") or {}).get("audio_url")) or
                        data.get("audio_url") or
                        data.get("url")
                    )
                    
                    if audio_url and isinstance(audio_url, str):
                        # 下载音频
                        log_info("TTS", f"OpenAI compat received JSON with URL, downloading: {audio_url}")
                        r2 = requests.get(audio_url, timeout=60)
                        if r2.status_code == 200:
                            return _write_audio_with_detected_ext(out_path, r2.content, fallback_ext="mp3")
                        else:
                            last_err = RuntimeError(f"Failed to download audio from URL: {r2.status_code}")
                            continue
                    else:
                        # 也许是报错信息
                        log_warning("TTS", f"OpenAI compat received JSON but no URL found: {json.dumps(data)[:200]}")
                        last_err = RuntimeError(f"TTS API response JSON invalid: {json.dumps(data)}")
                        # 如果不是“不支持模型”错误，就不继续尝试了
                        if not _should_fallback_to_tts1(200, json.dumps(data)):
                            continue
                except Exception as e:
                    last_err = e
                    log_warning("TTS", f"Failed to parse JSON response: {e}")
                    continue
            else:
                # 标准情况：直接是音频数据
                return _write_audio_with_detected_ext(out_path, resp.content, fallback_ext="mp3")

        body = ""
        try:
            body = resp.text
        except Exception:
            body = ""

        # 无效 token 直接失败，避免无意义多次重试
        if resp.status_code == 401 and ("无效的令牌" in body or "invalid" in body.lower() or "token" in body.lower()):
            raise RuntimeError(f"TTS HTTP 401: {body}")

        # 如果是“模型不支持”，继续尝试 tts-1；否则继续下一种参数组合
        last_err = RuntimeError(f"TTS HTTP {resp.status_code}: {body}")
        if not _should_fallback_to_tts1(resp.status_code, body):
            continue

    raise last_err or RuntimeError("TTS failed with unknown error")



def _dashscope_tts_to_mp3(text: str, out_path: str) -> None:
    """
    使用阿里云 DashScope（通义千问）TTS 生成语音。

    依赖环境变量：
    - TTS_PROVIDER=dashscope
    - DASHSCOPE_API_KEY=...
    - DASHSCOPE_TTS_MODEL=qwen3-tts-flash (可选)
    - DASHSCOPE_TTS_VOICE=Cherry (可选)
    - DASHSCOPE_TTS_FORMAT=mp3 (可选)

    文档参考：
    - https://help.aliyun.com/zh/model-studio/qwen-tts
    - https://help.aliyun.com/zh/model-studio/qwen-tts-api
    """
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is empty")

    model = os.getenv("DASHSCOPE_TTS_MODEL", "qwen3-tts-flash").strip()
    voice = os.getenv("DASHSCOPE_TTS_VOICE", "Cherry").strip()
    fmt = os.getenv("DASHSCOPE_TTS_FORMAT", "mp3").strip().lower() or "mp3"

    # 兼容不同文档/版本的 endpoint：优先使用环境变量覆盖
    endpoint = os.getenv(
        "DASHSCOPE_TTS_ENDPOINT",
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/speech/synthesis",
    ).strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "model": model,
        "input": {"text": text},
        "parameters": {
            "voice": voice,
            "format": fmt,
        },
    }

    resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)

    # 有些实现会直接返回音频 bytes
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if resp.status_code == 200 and ("audio/" in ctype or "application/octet-stream" in ctype):
        with open(out_path, "wb") as f:
            f.write(resp.content)
        return

    # 也可能返回 JSON（包含 url / base64 等）
    body_text = ""
    try:
        body_text = resp.text
    except Exception:
        body_text = ""

    if resp.status_code != 200:
        raise RuntimeError(f"DashScope TTS HTTP {resp.status_code}: {body_text}")

    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"DashScope TTS unexpected response: {body_text[:400]}")

    # 尝试多种可能字段
    audio_url = (
        (((data.get("output") or {}).get("audio") or {}).get("url"))
        or (((data.get("output") or {}).get("audio") or {}).get("audio_url"))
        or (((data.get("output") or {}).get("audio") or {}).get("href"))
    )
    if audio_url and isinstance(audio_url, str):
        r2 = requests.get(audio_url, timeout=60)
        r2.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r2.content)
        return

    # base64 / bytes 字段兜底（不同实现命名可能不同）
    audio_b64 = (
        (((data.get("output") or {}).get("audio") or {}).get("content"))
        or (((data.get("output") or {}).get("audio") or {}).get("data"))
    )
    if isinstance(audio_b64, str) and audio_b64:
        import base64

        raw = base64.b64decode(audio_b64)
        with open(out_path, "wb") as f:
            f.write(raw)
        return

    raise RuntimeError(f"DashScope TTS response missing audio payload: {json.dumps(data)[:800]}")


def generate_tts_audio(text: str) -> str:
    """
    生成 TTS 音频文件，返回文件相对路径
    """
    if not text:
        text = "你好"

    # 幼儿友好：长文本会导致生成慢/播放慢，限制长度并按句截断
    text = str(text).strip()
    if len(text) > 260:
        # 尝试按句号/问号/感叹号截断到前 260 字
        shortened = text[:260]
        cut = re.split(r"[。！？!?]", shortened)
        text = cut[0] + "。" if cut and cut[0] else shortened

    # 选择 TTS 提供方：默认 local（pyttsx3）
    # - local：本地系统TTS，离线但音色偏机械（输出 wav）
    # - openai_compat：OpenAI兼容TTS（可走 V-API），音色更自然但需要联网/计费（输出 mp3）
    # - dashscope：阿里云 DashScope（通义千问）TTS，直连不依赖中转（输出 mp3）
    requested = os.getenv("TTS_PROVIDER", "local").strip().lower()
    if requested not in ("local", "openai_compat", "dashscope"):
        requested = "local"

    def _cache_key_for(p: str) -> str:
        # 缓存：相同(提供方+参数+文本)复用同一个音频文件，避免反复生成
        if p == "openai_compat":
            model = os.getenv("OPENAI_TTS_MODEL", "tts-1").strip()
            voice = os.getenv("OPENAI_TTS_VOICE", "alloy").strip()
            speed = os.getenv("OPENAI_TTS_SPEED", "").strip()
            instructions = os.getenv("OPENAI_TTS_INSTRUCTIONS", "").strip()
            extra = os.getenv("OPENAI_BASE_URL", "").strip().rstrip("/")
        elif p == "dashscope":
            model = os.getenv("DASHSCOPE_TTS_MODEL", "qwen3-tts-flash").strip()
            voice = os.getenv("DASHSCOPE_TTS_VOICE", "Cherry").strip()
            speed = os.getenv("DASHSCOPE_TTS_SPEED", "").strip()
            instructions = os.getenv("DASHSCOPE_TTS_STYLE", "").strip()
            extra = os.getenv("DASHSCOPE_TTS_ENDPOINT", "").strip()
        else:
            model = "local"
            voice = "local"
            speed = "local"
            instructions = "local"
            extra = ""

        cache_seed = f"{p}|{model}|{voice}|{speed}|{instructions}|{text}"
        if extra:
            cache_seed += f"|{extra}"
        return hashlib.md5(cache_seed.encode("utf-8")).hexdigest()

    def _cache_path_for(p: str, ext: str | None = None) -> str:
        key = _cache_key_for(p)
        if not ext:
            ext = "wav" if p == "local" else "mp3"
        return os.path.join(OUTPUT_DIR, f"{key}.{ext}")

    def _cache_candidates_for(p: str) -> list[str]:
        key = _cache_key_for(p)
        if p == "openai_compat":
            exts = ("mp3", "wav", "ogg", "flac")
        elif p == "dashscope":
            exts = ("mp3", "wav")
        else:
            exts = ("wav",)
        return [os.path.join(OUTPUT_DIR, f"{key}.{e}") for e in exts]

    def _looks_like_wav_file(path: str) -> bool:
        try:
            with open(path, "rb") as f:
                head = f.read(4)
            return head == b"RIFF"
        except Exception:
            return False

    # 依次尝试：配置的 provider -> local 兜底
    candidates = [requested] if requested == "local" else [requested, "local"]

    last_err: Exception | None = None
    for provider in candidates:
        filepath = _cache_path_for(provider)
        for cached in _cache_candidates_for(provider):
            if not os.path.exists(cached):
                continue
            # 兼容历史遗留：曾经把 wav 写成 mp3 扩展名会导致前端解码失败
            if cached.lower().endswith(".mp3") and _looks_like_wav_file(cached):
                try:
                    fixed = _replace_ext(cached, "wav")
                    os.replace(cached, fixed)
                    print(f"[tts] fixed cache ext .mp3 -> .wav: {fixed}")
                    return fixed
                except Exception:
                    try:
                        os.remove(cached)
                        print(f"[tts] invalid mp3 cache (actually wav), removed: {cached}")
                    except Exception:
                        print(f"[tts] invalid mp3 cache (actually wav), but failed to remove: {cached}")
            else:
                print(f"[tts] cache hit provider={provider} path={cached}")
                return cached

        try:
            with _tts_lock:
                # 双重检查（避免并发重复生成）
                for cached in _cache_candidates_for(provider):
                    if not os.path.exists(cached):
                        continue
                    if cached.lower().endswith(".mp3") and _looks_like_wav_file(cached):
                        try:
                            fixed = _replace_ext(cached, "wav")
                            os.replace(cached, fixed)
                            print(f"[tts] fixed cache ext .mp3 -> .wav: {fixed}")
                            return fixed
                        except Exception:
                            try:
                                os.remove(cached)
                                print(f"[tts] invalid mp3 cache (actually wav), removed: {cached}")
                            except Exception:
                                print(f"[tts] invalid mp3 cache (actually wav), but failed to remove: {cached}")
                    else:
                        print(f"[tts] cache hit provider={provider} path={cached}")
                        return cached

                if provider == "openai_compat":
                    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
                    model_dbg = os.getenv("OPENAI_TTS_MODEL", "").strip()
                    print(f"[tts] provider=openai_compat base_url={base_url} model={model_dbg}")
                    filepath = _openai_compat_tts_to_mp3(text, filepath)
                elif provider == "dashscope":
                    model_dbg = os.getenv("DASHSCOPE_TTS_MODEL", "").strip()
                    print(f"[tts] provider=dashscope model={model_dbg}")
                    _dashscope_tts_to_mp3(text, filepath)
                else:
                    print("[tts] provider=local")
                    with _engine_lock:
                        engine = _build_engine()
                        engine.save_to_file(text, filepath)
                        engine.runAndWait()
                        engine.stop()

            if not os.path.exists(filepath):
                raise RuntimeError(f"TTS 文件生成失败: {filepath}")

            print(f"TTS 生成成功(provider={provider}): {filepath}")
            return filepath
        except Exception as e:
            last_err = e
            print(f"[tts] provider={provider} failed: {e}")
            continue

    raise Exception(f"TTS 生成失败: {str(last_err) if last_err else 'unknown error'}")


# ============ 缓存管理 ============

def get_cache_stats() -> dict:
    """
    获取TTS缓存统计信息
    
    Returns:
        缓存统计字典
    """
    if not os.path.exists(OUTPUT_DIR):
        return {"total_files": 0, "total_size_mb": 0, "oldest_file": None}
    
    files = []
    total_size = 0
    oldest_time = None
    
    for f in os.listdir(OUTPUT_DIR):
        filepath = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            total_size += stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            files.append((filepath, mtime))
            if oldest_time is None or mtime < oldest_time:
                oldest_time = mtime
    
    return {
        "total_files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "oldest_file": oldest_time.isoformat() if oldest_time else None
    }


def cleanup_old_cache(max_age_days: int = 7, max_size_mb: int = 500) -> dict:
    """
    清理过期的TTS缓存文件
    
    Args:
        max_age_days: 最大保留天数
        max_size_mb: 最大缓存大小(MB)
    
    Returns:
        清理统计字典
    """
    if not os.path.exists(OUTPUT_DIR):
        return {"deleted_files": 0, "freed_size_mb": 0}
    
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted_files = 0
    freed_size = 0
    
    # 收集所有文件信息
    files = []
    for f in os.listdir(OUTPUT_DIR):
        filepath = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            files.append((filepath, mtime, stat.st_size))
    
    # 按修改时间排序（最旧的在前面）
    files.sort(key=lambda x: x[1])
    
    # 计算当前总大小
    current_size = sum(f[2] for f in files)
    max_size_bytes = max_size_mb * 1024 * 1024
    
    for filepath, mtime, size in files:
        # 删除过期文件
        if mtime < cutoff_time:
            try:
                os.remove(filepath)
                deleted_files += 1
                freed_size += size
                current_size -= size
                log_info("TTS", f"删除过期缓存: {os.path.basename(filepath)}")
            except Exception as e:
                log_warning("TTS", f"删除失败: {filepath}, {e}")
        # 如果超出大小限制，也删除
        elif current_size > max_size_bytes:
            try:
                os.remove(filepath)
                deleted_files += 1
                freed_size += size
                current_size -= size
                log_info("TTS", f"删除超出大小限制的缓存: {os.path.basename(filepath)}")
            except Exception as e:
                log_warning("TTS", f"删除失败: {filepath}, {e}")
    
    result = {
        "deleted_files": deleted_files,
        "freed_size_mb": round(freed_size / (1024 * 1024), 2)
    }
    
    if deleted_files > 0:
        log_info("TTS", f"缓存清理完成: {result}")
    
    return result
