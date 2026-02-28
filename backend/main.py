from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import json
import os
import time

try:
    # 灏濊瘯鐩稿瀵煎叆锛堜粠 backend 鐩綍杩愯鏃讹級
    # 鍏堝姞杞芥湰鍦伴厤缃紙config.local.txt / .env.local锛夛紝纭繚鍚?service 璇诲彇鍒版纭殑鐜鍙橀噺
    from . import config as _config  # noqa: F401
    from . import models, schemas, database
    from .services import audio_service, tts_service, vocab_service, chat_service, asr_service, emotion_service, cleanup_service
    from .logger import log_info, log_error, log_warning, log_request, log_response
    from .exceptions import register_exception_handlers, ValidationError, AudioProcessingError
except ImportError:
    # 濡傛灉鐩稿瀵煎叆澶辫触锛屼娇鐢ㄧ粷瀵瑰鍏ワ紙浠庨」鐩牴鐩綍杩愯鏃讹級
    from backend import config as _config  # noqa: F401
    from backend import models, schemas, database
    from backend.services import audio_service, tts_service, vocab_service, chat_service, asr_service, emotion_service, cleanup_service
    from backend.logger import log_info, log_error, log_warning, log_request, log_response
    from backend.exceptions import register_exception_handlers, ValidationError, AudioProcessingError

# 鍒涘缓鏁版嵁搴撹〃
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="鎯呮劅浼村绯荤粺 API",
    description="语音学习平台后端 API",
    version="1.0.0"
)

def _default_user_id() -> int:
    raw = (os.getenv("DEFAULT_USER_ID") or "1").strip()
    try:
        uid = int(raw)
    except Exception:
        uid = 1
    return uid if uid > 0 else 1


DEFAULT_USER_ID = _default_user_id()

register_exception_handlers(app)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    
    # 璺宠繃闈欐€佽祫婧愯姹傜殑鏃ュ織
    if not request.url.path.startswith('/uploads'):
        log_response(request.url.path, response.status_code, duration_ms)
    
    return response

def _parse_cors_origins(raw: str) -> list[str]:
    s = (raw or "").strip()
    if not s:
        return ["*"]
    # 鏀寔閫楀彿鍒嗛殧鎴栧崟涓?*
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(os.getenv("CORS_ALLOW_ORIGINS", "*")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# uploads锛氱敓浜?涓婃灦鏇村畨鍏ㄧ殑榛樿鍊硷細鍙叕寮€ TTS 浜х墿锛屼笉鍏紑鐢ㄦ埛褰曢煶
os.makedirs(os.path.join("uploads", "tts"), exist_ok=True)
app.mount("/uploads/tts", StaticFiles(directory=os.path.join("uploads", "tts")), name="tts")

# 濡傞渶鏈湴璋冭瘯鍙樉寮忓紑鍚紙鈿?浼氬叕寮€ uploads 涓嬫墍鏈夋枃浠讹級
if os.getenv("EXPOSE_UPLOADS_ALL", "false").strip().lower() in ("1", "true", "yes", "y"):
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_user_exists(db: Session, user_id: int = DEFAULT_USER_ID) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        return user
    user = models.User(id=user_id, username=f"user_{user_id}", level="L1")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.on_event("startup")
async def startup_event():
    log_info("Startup", "Emotion learning service starting")

    # 预热模型，降低首次语音请求延迟
    try:
        asr_service.preload_model_async()
    except Exception as e:
        log_warning("Startup", f"ASR preload failed: {e}")
    try:
        emotion_service.preload_model_async()
    except Exception as e:
        log_warning("Startup", f"Emotion preload failed: {e}")

    # 启动清理
    try:
        stats = cleanup_service.cleanup_uploads_from_env()
        log_info("Cleanup", f"Uploads cleanup done: {stats}")
    except Exception as e:
        log_warning("Cleanup", f"Cleanup failed: {e}")

    db = database.SessionLocal()
    try:
        ensure_user_exists(db, DEFAULT_USER_ID)

        # 空库时写入基础课程
        if db.query(models.Course).count() == 0:
            courses = [
                models.Course(
                    title="基础问候",
                    desc="学习常见问候语",
                    level="Level 1",
                    duration=5,
                    content_json=json.dumps([
                        {"text": "你好", "pinyin": "ni hao", "tip": "语速自然"},
                        {"text": "老师好", "pinyin": "lao shi hao", "tip": "注意声调"},
                        {"text": "谢谢", "pinyin": "xie xie", "tip": "发音清晰"}
                    ], ensure_ascii=False),
                ),
                models.Course(
                    title="校园生活",
                    desc="校园常用表达",
                    level="Level 2",
                    duration=8,
                    content_json=json.dumps([
                        {"text": "请问", "pinyin": "qing wen", "tip": "礼貌表达"},
                        {"text": "我知道了", "pinyin": "wo zhi dao le", "tip": "连读自然"},
                        {"text": "我们一起", "pinyin": "wo men yi qi", "tip": "节奏均匀"}
                    ], ensure_ascii=False),
                ),
            ]
            db.add_all(courses)
            db.commit()

        # 主题词库同步
        try:
            created, updated = vocab_service.upsert_vocab_courses(db, models)
            if created or updated:
                print(f"[vocab] courses upserted: created={created}, updated={updated}")
        except Exception as e:
            print(f"[vocab] upsert failed: {e}")

        # 生词本课程兜底
        try:
            title = " 生词本"
            existing = db.query(models.Course).filter(models.Course.title == title).first()
            if not existing:
                db.add(
                    models.Course(
                        title=title,
                        desc="从学习记录里自动生成的薄弱词练习",
                        level="Level 1",
                        duration=5,
                        content_json="[]",
                    )
                )
                db.commit()
        except Exception as e:
            print(f"[vocabbook] ensure course failed: {e}")
    finally:
        db.close()
@app.get("/courses", response_model=List[schemas.Course])
def get_courses(db: Session = Depends(get_db)):
    return db.query(models.Course).all()


@app.get("/vocab/categories")
def get_vocab_categories():
    """词库分类列表"""
    return vocab_service.list_categories()


@app.get("/vocab/{category_key}")
def get_vocab_items(category_key: str):
    """获取指定分类词表"""
    cats = vocab_service.load_vocab_categories()
    cat = cats.get(category_key)
    if not cat:
        raise HTTPException(status_code=404, detail="category not found")
    return vocab_service.build_course_content(category_key, cat)


@app.get("/vocabbook/course")
def get_vocabbook_course(db: Session = Depends(get_db)):
    c = db.query(models.Course).filter(models.Course.title == "📒 生词本").first()
    if not c:
        raise HTTPException(status_code=500, detail="vocabbook course missing")
    return {"id": c.id, "title": c.title}


@app.get("/records", response_model=List[schemas.LearningRecordOut])
def get_records(user_id: int = DEFAULT_USER_ID, limit: int = 50, db: Session = Depends(get_db)):
    ensure_user_exists(db, user_id)
    rows = (
        db.query(models.LearningRecord)
        .filter(models.LearningRecord.user_id == user_id)
        .order_by(models.LearningRecord.created_at.desc())
        .limit(min(500, max(1, limit)))
        .all()
    )
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "course_id": r.course_id,
            "word_text": r.word_text,
            "score": float(r.score or 0),
            "emotion_type": r.emotion_type or "neutral",
            "emotion_label": r.emotion_label or "平静",
            "feedback_text": r.feedback_text or "",
            "created_at": (r.created_at or datetime.now()).isoformat(),
        }
        for r in rows
    ]


@app.get("/stats", response_model=schemas.StatsOut)
def get_stats(user_id: int = DEFAULT_USER_ID, db: Session = Depends(get_db)):
    ensure_user_exists(db, user_id)
    rows = db.query(models.LearningRecord).filter(models.LearningRecord.user_id == user_id).all()
    if not rows:
        return {"learning_days": 0, "total_records": 0, "avg_score": 0.0, "total_stars": 0, "badges": 0}
    days = set()
    total = 0
    stars = 0
    badges = 0
    for r in rows:
        dt = r.created_at or datetime.now()
        days.add(dt.date().isoformat())
        s = float(r.score or 0)
        total += s
        if s >= 80:
            stars += 3
        elif s >= 60:
            stars += 2
        else:
            stars += 1
        if s >= 90:
            badges += 1

    avg = total / max(1, len(rows))
    return {
        "learning_days": len(days),
        "total_records": len(rows),
        "avg_score": round(avg, 1),
        "total_stars": stars,
        "badges": badges,
    }


@app.get("/mood/weekly", response_model=List[schemas.MoodDayOut])
def get_mood_weekly(user_id: int = DEFAULT_USER_ID, db: Session = Depends(get_db)):
    ensure_user_exists(db, user_id)
    # 最近 7 天（包含今天）
    today = datetime.now().date()
    start = today - timedelta(days=6)
    rows = (
        db.query(models.LearningRecord)
        .filter(models.LearningRecord.user_id == user_id)
        .filter(models.LearningRecord.created_at >= datetime.combine(start, datetime.min.time()))
        .all()
    )

    def weekday_cn(d: datetime.date) -> str:
        mapping = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return mapping[d.weekday()]

    # 按天聚合
    by_day = {}
    for r in rows:
        d = (r.created_at or datetime.now()).date().isoformat()
        by_day.setdefault(d, []).append(r)

    out = []
    for i in range(7):
        day = start + timedelta(days=i)
        key = day.isoformat()
        rs = by_day.get(key, [])
        if not rs:
            out.append({"day": weekday_cn(day), "value": 0, "color": "#d9d9d9", "emotion": "无数据"})
            continue

        # 统计情绪分布
        cnt = {"happy": 0, "neutral": 0, "confused": 0, "frustrated": 0}
        for r in rs:
            t = (r.emotion_type or "neutral").lower()
            if t in cnt:
                cnt[t] += 1
            else:
                cnt["neutral"] += 1

        total = sum(cnt.values()) or 1
        positive = cnt["happy"] + cnt["neutral"]
        value = int(round(positive * 100 / total))

        # 主导情绪（用于配色）
        dominant = max(cnt.items(), key=lambda x: x[1])[0]
        if dominant in ["happy"]:
            color = "#409EFF"
            emo = "积极"
        elif dominant in ["neutral"]:
            color = "#52c41a"
            emo = "平静"
        elif dominant in ["confused"]:
            color = "#fa8c16"
            emo = "困惑"
        else:
            color = "#ff4d4f"
            emo = "挫败"

        out.append({"day": weekday_cn(day), "value": value, "color": color, "emotion": emo})
    return out


@app.get("/weak_words", response_model=List[schemas.WeakWordOut])
def get_weak_words(user_id: int = DEFAULT_USER_ID, limit: int = 50, db: Session = Depends(get_db)):
    ensure_user_exists(db, user_id)
    # 鍙栨渶杩?00鏉¤褰曪紝閬垮厤鍏ㄨ〃鎵弿澶參
    rows = (
        db.query(models.LearningRecord)
        .filter(models.LearningRecord.user_id == user_id)
        .order_by(models.LearningRecord.created_at.desc())
        .limit(500)
        .all()
    )
    agg = {}
    for r in rows:
        w = (r.word_text or "").strip()
        if not w:
            continue
        dt = r.created_at or datetime.now()
        s = float(r.score or 0)
        item = agg.get(w)
        if not item:
            agg[w] = {"times": 1, "sum": s, "last_score": s, "last_time": dt}
        else:
            item["times"] += 1
            item["sum"] += s
            # rows 宸叉寜 desc锛岀涓€鏉″氨鏄?last
    # 璁＄畻 avg锛屽苟鎸?avg 鍗囧簭锛堣杽寮变紭鍏堬級
    result = []
    for w, v in agg.items():
        avg = v["sum"] / max(1, v["times"])
        result.append(
            {
                "word_text": w,
                "pinyin": getattr(vocab_service, "_to_pinyin")(w) if hasattr(vocab_service, "_to_pinyin") else "",
                "times": v["times"],
                "avg_score": round(avg, 1),
                "last_score": float(v["last_score"]),
                "last_time": (v["last_time"] or datetime.now()).isoformat(),
            }
        )
    result.sort(key=lambda x: (x["avg_score"], -x["times"]))
    return result[: min(200, max(1, limit))]

@app.post("/analyze", response_model=schemas.AnalysisResult)
async def analyze_audio(
    file: UploadFile = File(...),
    course_id: int = Form(1),
    user_id: int = Form(DEFAULT_USER_ID),
    word_text: str = Form(""),
    attempt_count: int = Form(1),  # 鏂板: 灏濊瘯娆℃暟
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        print(f"鏀跺埌闊抽鏂囦欢: {file.filename}, 澶у皬: {len(content)} bytes, 鏍煎紡: {file.content_type}")
        
        # 浼犲叆鏍囧噯鏂囨湰鍜屽皾璇曟鏁扮敤浜庡彂闊宠瘎鍒嗗姣斿拰鑷€傚簲鍙嶉
        result = audio_service.analyze_audio_file(
            content, 
            file.filename, 
            reference_text=word_text,
            attempt_count=attempt_count
        )
        print(f"鍒嗘瀽瀹屾垚锛屽垎鏁? {result.get('score')}")
    except ValueError as exc:
        print(f"鍒嗘瀽閿欒: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"鏈煡閿欒: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"鍒嗘瀽澶辫触: {str(exc)}") from exc
    
    # 濡傛灉鏈夊弽棣堝缓璁紝鐢熸垚璇煶
    feedback_audio = ""
    if result.get("feedback"):
        try:
            # 鐢熸垚鍙嶉璇煶
            path = tts_service.generate_tts_audio(result["feedback"])
            # 杞崲涓?URL 璺緞 (windows path separator fix)
            feedback_audio = path.replace("\\", "/")
        except Exception as e:
            print(f"TTS Error: {e}")

    # 灏嗙敓鎴愮殑璇煶璺緞鍔犲叆杩斿洖缁撴灉锛堢◢寰瓟鏀逛竴涓?Schema 鎴栫洿鎺ョ敤 dict 杩斿洖锛?    # 涓轰簡鏂逛究锛岃繖閲岀洿鎺ユ妸 feedback 瀛楁鏀瑰啓鎴愬寘鍚?audio 鐨?dict
    # 浣嗕负浜嗕笉鏀?Schema 瀹氫箟澶鏉傦紝鎴戜滑閫氳繃 header 鎴栭澶栧瓧娈佃繑鍥烇紝杩欓噷绠€鍗曡捣瑙佺洿鎺ユ嫾鍦?feedback 鏂囨湰鍚?    # 鎴栬€呮垜浠复鏃朵慨鏀?AnalysisResult schema锛屽鍔?feedback_audio 瀛楁
    
    # 杩欓噷鎴戜滑 hack 涓€涓嬶紝鍓嶇瑙ｆ瀽鏃舵敞鎰忥細濡傛灉涓嶆敼 schema锛屽氨鎶?audio path 鏀惧湪 feedback 鏂囨湰閲?    # 鏇村ソ鐨勫仛娉曟槸淇敼 Schema锛岃涓嬫柟 todo
    
    ensure_user_exists(db, user_id)
    db_record = models.LearningRecord(
        user_id=user_id,
        course_id=course_id,
        word_text=word_text,
        audio_path=result["audio_path"],
        score=result["score"],
        emotion_type=result["emotion"]["type"],
        emotion_label=result["emotion"]["label"],
        feedback_text=result["feedback"]
    )
    db.add(db_record)
    db.commit()
    
    # 鏋勯€犺繑鍥炴暟鎹紝甯︿笂闊抽 URL
    return {
        "score": result["score"],
        "emotion": result["emotion"],
        "feedback": result["feedback"],
        "strategy_adjusted": result["strategy_adjusted"],
        "feedback_audio": feedback_audio,
        "issues": result.get("issues", [])
    }

@app.get("/tts")
def get_tts(text: str):
    """ 鑾峰彇绀鸿寖闊?"""
    try:
        if not text:
            raise HTTPException(status_code=400, detail="text parameter is required")
        print(f"TTS 璇锋眰: text={text}")
        path = tts_service.generate_tts_audio(text)
        print(f"TTS 鐢熸垚鎴愬姛: {path}")
        return FileResponse(path)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"TTS 閿欒: {e}")
        raise HTTPException(status_code=500, detail=f"TTS鐢熸垚澶辫触: {str(e)}")


# ========== AI鑱婂ぉ鎺ュ彛 ==========

@app.post("/chat/voice")
async def chat_with_voice(
    file: UploadFile = File(...),
    mode: str = Form("chat"),
    text: str = Form("")
):
    """
    璇煶鑱婂ぉ鎺ュ彛
    鎺ユ敹璇煶鏂囦欢锛岃瘑鍒悗杩斿洖AI鍥炲锛堟枃瀛?闊抽锛?    """
    try:
        content = await file.read()
        print(f"鏀跺埌璇煶鑱婂ぉ鏂囦欢: {file.filename}, 澶у皬: {len(content)} bytes")
        
        # 1) 优先使用后端 ASR，前端文本仅作兜底，避免前端识别晚收尾导致最后一字丢失
        recognized_text = ""
        used_asr = True
        try:
            recognized_text = asr_service.recognize_speech(
                content,
                file.filename.split('.')[-1] if '.' in file.filename else "webm"
            ) or ""
            recognized_text = recognized_text.strip()
            if recognized_text:
                print(f"ASR璇嗗埆缁撴灉: {recognized_text}")
        except Exception as e:
            print(f"ASR璇嗗埆澶辫触: {e}")

        if not recognized_text:
            recognized_text = (text or "").strip()
            used_asr = False

        if not recognized_text:
            return {
                "text": "我没有听到声音，请再说一遍吧。",
                "audio_url": None,
                "recognized_text": None,
                "used_asr": used_asr
            }
        
        # 2. AI鐢熸垚鍥炲
        chat_result = chat_service.chat_with_ai(recognized_text, mode=mode)
        reply_text = chat_result["text"]
        
        # 3. 鐢熸垚TTS闊抽
        audio_url = None
        try:
            path = tts_service.generate_tts_audio(reply_text)
            audio_url = path.replace("\\", "/")
        except Exception as e:
            print(f"TTS鐢熸垚澶辫触: {e}")
        
        return {
            "text": reply_text,
            "audio_url": audio_url,
            "recognized_text": recognized_text,
            "title": chat_result.get("title"),
            "used_asr": used_asr
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"璇煶鑱婂ぉ閿欒: {e}")
        raise HTTPException(status_code=500, detail=f"澶勭悊澶辫触: {str(e)}")


@app.post("/chat/text")
def chat_with_text(text: str, mode: str = "chat"):
    """
    鏂囨湰鑱婂ぉ鎺ュ彛锛堝鐢紝骞煎効涓昏鐢ㄨ闊筹級
    """
    try:
        if not text:
            raise HTTPException(status_code=400, detail="text parameter is required")
        
        chat_result = chat_service.chat_with_ai(text, mode=mode)
        reply_text = chat_result["text"]
        
        # 鐢熸垚TTS闊抽
        audio_url = None
        try:
            path = tts_service.generate_tts_audio(reply_text)
            audio_url = path.replace("\\", "/")
        except Exception as e:
            print(f"TTS鐢熸垚澶辫触: {e}")
        
        return {
            "text": reply_text,
            "audio_url": audio_url,
            "title": chat_result.get("title")
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"澶勭悊澶辫触: {str(e)}")


@app.get("/chat/story")
def get_story(category: str = None):
    """
    鑾峰彇闅忔満鏁呬簨锛堢洿鎺ヨ繑鍥炴晠浜嬪唴瀹?闊抽锛?    鍙€夊弬鏁?category: animal, fable, daily, adventure, educational
    """
    try:
        story_result = chat_service.get_random_story(category)
        reply_text = story_result["text"]
        
        # 鐢熸垚TTS闊抽
        audio_url = None
        try:
            path = tts_service.generate_tts_audio(reply_text)
            audio_url = path.replace("\\", "/")
        except Exception as e:
            print(f"TTS鐢熸垚澶辫触: {e}")
        
        return {
            "text": reply_text,
            "audio_url": audio_url,
            "title": story_result.get("title"),
            "category": story_result.get("category")
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"澶勭悊澶辫触: {str(e)}")


@app.get("/chat/categories")
def get_story_categories():
    """鑾峰彇鏁呬簨鍒嗙被鍒楄〃"""
    return chat_service.get_story_categories()


