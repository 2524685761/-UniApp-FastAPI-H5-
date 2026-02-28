from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import chat, tts


def create_app() -> FastAPI:
    app = FastAPI(title="futuretts API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"ok": True}

    app.include_router(chat.router, prefix="/api")
    app.include_router(tts.router, prefix="/api")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    return app


app = create_app()


