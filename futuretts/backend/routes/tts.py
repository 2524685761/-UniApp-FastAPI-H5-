from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.v36_tts_service import v36_tts_mp3

router = APIRouter()


class TTSIn(BaseModel):
    text: str


@router.post("/tts")
def tts(payload: TTSIn):
    text = (payload.text or "").strip()
    if not text:
        return Response(content=b"", media_type="audio/mpeg")
    audio = v36_tts_mp3(text)
    return Response(content=audio, media_type="audio/mpeg")


