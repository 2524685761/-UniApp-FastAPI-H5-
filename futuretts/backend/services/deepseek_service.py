import os
import requests

from .. import env  # noqa: F401  (ensure .env.local loaded)


def deepseek_chat(message: str) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip().rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is empty")

    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个温柔、简短、适合手机阅读的中文助手。回答尽量在80字以内。"},
            {"role": "user", "content": message},
        ],
        "temperature": 0.7,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek error {resp.status_code}: {resp.text}")
    data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


