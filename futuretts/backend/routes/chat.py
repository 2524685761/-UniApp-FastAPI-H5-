from fastapi import APIRouter
from pydantic import BaseModel

from ..services.deepseek_service import deepseek_chat

router = APIRouter()


class ChatIn(BaseModel):
    text: str


@router.post("/chat")
def chat(payload: ChatIn):
    text = (payload.text or "").strip()
    if not text:
        return {"text": ""}
    out = deepseek_chat(text)
    return {"text": out}


