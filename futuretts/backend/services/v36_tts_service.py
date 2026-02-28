import os
import requests
from .. import env  # noqa: F401  (ensure .env.local loaded)


def v36_tts_mp3(text: str) -> bytes:
    api_key = os.getenv("V36_API_KEY", "").strip()
    base_url = os.getenv("V36_BASE_URL", "https://api.v36.cm/v1").strip().rstrip("/")
    model = os.getenv("V36_TTS_MODEL", "qwen3-tts-flash").strip()
    voice = os.getenv("V36_TTS_VOICE", "alloy").strip()
    speed_raw = os.getenv("V36_TTS_SPEED", "").strip()

    if not api_key:
        raise RuntimeError("V36_API_KEY is empty")

    speed = None
    if speed_raw:
        try:
            speed = float(speed_raw)
        except Exception:
            speed = None

    url = f"{base_url}/audio/speech"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": text, "voice": voice, "format": "mp3"}
    if speed is not None:
        payload["speed"] = speed

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"V36 TTS error {resp.status_code}: {resp.text}")
    return resp.content


