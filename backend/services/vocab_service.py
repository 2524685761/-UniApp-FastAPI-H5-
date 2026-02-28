"""
词库服务 - 增强版
主题字库管理与课程同步

功能：
1. 从JSON配置加载词库
2. 自动同步到数据库courses表
3. 支持增删改操作
4. 拼音自动生成
5. 变更检测与增量同步
"""
import json
import os
import hashlib
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime


def _data_file_path() -> str:
    """获取词库配置文件路径"""
    base = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base, "data", "vocab_categories.json")


def _backup_file_path() -> str:
    """获取备份文件路径"""
    base = os.path.dirname(os.path.dirname(__file__))
    backup_dir = os.path.join(base, "data", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(backup_dir, f"vocab_categories_{timestamp}.json")


def load_vocab_categories() -> Dict[str, dict]:
    """
    从配置文件加载词库分类
    如果文件缺失或无效，返回空字典
    """
    path = _data_file_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        print(f"[vocab] 加载词库失败: {e}")
        return {}


def save_vocab_categories(categories: Dict[str, dict], backup: bool = True) -> bool:
    """
    保存词库配置到文件
    
    Args:
        categories: 词库分类数据
        backup: 是否先备份现有文件
    
    Returns:
        是否保存成功
    """
    path = _data_file_path()
    
    try:
        # 备份现有文件
        if backup and os.path.exists(path):
            import shutil
            backup_path = _backup_file_path()
            shutil.copy2(path, backup_path)
            print(f"[vocab] 已备份到: {backup_path}")
        
        # 保存新数据
        with open(path, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
        
        print(f"[vocab] 词库已保存")
        return True
    except Exception as e:
        print(f"[vocab] 保存词库失败: {e}")
        return False


def _to_pinyin(text: str) -> str:
    """
    将中文文本转换为带声调的拼音
    """
    try:
        from pypinyin import pinyin, Style
        parts = pinyin(text, style=Style.TONE3, heteronym=False, errors="default")
        flat = [x[0] for x in parts if x and x[0]]
        return " ".join(flat)
    except ImportError:
        return ""
    except Exception:
        return ""


def _default_tip_for_category(key: str) -> str:
    """获取分类的默认发音提示"""
    tips = {
        "animal": "读慢一点，注意声调变化。",
        "body": "张大嘴巴，发音更清楚。",
        "clothes": "把每个字读清楚，不要吞音。",
        "color": "注意声调，红/黄/蓝读得更准。",
        "food": "语速放慢，尽量一口气读完。",
        "fruit": "双字连读要顺：先慢后快。",
        "furniture": "注意卷舌音（zh/ch/sh）和鼻音（n/ng）。",
        "job": "多字词先分开读，再连起来读。",
        "traffic": "注意送气音（p/t/k）和声调。",
        "weather": "用轻松的语气读出来，像在聊天。",
    }
    return tips.get(key, "保持专注，继续加油！")


def build_course_title(cat: dict) -> str:
    """构建课程标题"""
    emoji = (cat or {}).get("emoji", "").strip()
    title = (cat or {}).get("title", "").strip()
    if emoji and title:
        return f"{emoji} {title}"
    return title or emoji or "主题字库"


def build_course_content(category_key: str, cat: dict) -> List[dict]:
    """
    构建课程内容列表
    
    Args:
        category_key: 分类键
        cat: 分类数据
    
    Returns:
        包含text, pinyin, tip的词汇列表
    """
    items = cat.get("items", []) if isinstance(cat, dict) else []
    out = []
    default_tip = cat.get("tip") or _default_tip_for_category(category_key)
    
    for item in items:
        # 支持简单字符串或对象格式
        if isinstance(item, str):
            text = item.strip()
            tip = default_tip
            pinyin = _to_pinyin(text)
        elif isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            tip = item.get("tip", default_tip)
            pinyin = item.get("pinyin", "") or _to_pinyin(text)
        else:
            continue
        
        if not text:
            continue
        
        out.append({
            "text": text,
            "pinyin": pinyin,
            "tip": tip,
        })
    
    return out


def list_categories() -> List[dict]:
    """
    获取词库分类列表
    
    Returns:
        分类信息列表
    """
    cats = load_vocab_categories()
    result = []
    for key, cat in cats.items():
        if not isinstance(cat, dict):
            continue
        title = build_course_title(cat)
        items = cat.get("items", []) if isinstance(cat.get("items", []), list) else []
        result.append({
            "key": key,
            "emoji": cat.get("emoji", ""),
            "title": title,
            "desc": cat.get("desc", ""),
            "count": len(items),
            "level": cat.get("level", "Level 1"),
            "duration": int(cat.get("duration", 5) or 5),
        })
    return result


def get_category(key: str) -> Optional[dict]:
    """获取单个分类数据"""
    cats = load_vocab_categories()
    return cats.get(key)


def add_category(key: str, data: dict) -> Tuple[bool, str]:
    """
    添加新分类
    
    Args:
        key: 分类键
        data: 分类数据
    
    Returns:
        (是否成功, 消息)
    """
    cats = load_vocab_categories()
    
    if key in cats:
        return False, f"分类 '{key}' 已存在"
    
    # 验证数据
    if not data.get("title"):
        return False, "标题不能为空"
    
    cats[key] = {
        "emoji": data.get("emoji", "📚"),
        "title": data.get("title", ""),
        "desc": data.get("desc", ""),
        "level": data.get("level", "Level 1"),
        "duration": data.get("duration", 5),
        "tip": data.get("tip", ""),
        "items": data.get("items", [])
    }
    
    if save_vocab_categories(cats):
        return True, f"分类 '{key}' 添加成功"
    return False, "保存失败"


def update_category(key: str, data: dict) -> Tuple[bool, str]:
    """
    更新分类
    
    Args:
        key: 分类键
        data: 更新数据
    
    Returns:
        (是否成功, 消息)
    """
    cats = load_vocab_categories()
    
    if key not in cats:
        return False, f"分类 '{key}' 不存在"
    
    # 合并更新
    for field in ["emoji", "title", "desc", "level", "duration", "tip", "items"]:
        if field in data:
            cats[key][field] = data[field]
    
    if save_vocab_categories(cats):
        return True, f"分类 '{key}' 更新成功"
    return False, "保存失败"


def delete_category(key: str) -> Tuple[bool, str]:
    """
    删除分类
    
    Args:
        key: 分类键
    
    Returns:
        (是否成功, 消息)
    """
    cats = load_vocab_categories()
    
    if key not in cats:
        return False, f"分类 '{key}' 不存在"
    
    del cats[key]
    
    if save_vocab_categories(cats):
        return True, f"分类 '{key}' 删除成功"
    return False, "保存失败"


def add_words_to_category(key: str, words: List[str]) -> Tuple[bool, str]:
    """
    向分类添加词汇
    
    Args:
        key: 分类键
        words: 词汇列表
    
    Returns:
        (是否成功, 消息)
    """
    cats = load_vocab_categories()
    
    if key not in cats:
        return False, f"分类 '{key}' 不存在"
    
    existing_items = cats[key].get("items", [])
    existing_texts = set(str(item) if isinstance(item, str) else item.get("text", "") for item in existing_items)
    
    added = 0
    for word in words:
        word = word.strip()
        if word and word not in existing_texts:
            existing_items.append(word)
            existing_texts.add(word)
            added += 1
    
    cats[key]["items"] = existing_items
    
    if save_vocab_categories(cats):
        return True, f"添加了 {added} 个词汇"
    return False, "保存失败"


def remove_words_from_category(key: str, words: List[str]) -> Tuple[bool, str]:
    """
    从分类删除词汇
    
    Args:
        key: 分类键
        words: 词汇列表
    
    Returns:
        (是否成功, 消息)
    """
    cats = load_vocab_categories()
    
    if key not in cats:
        return False, f"分类 '{key}' 不存在"
    
    words_to_remove = set(w.strip() for w in words)
    existing_items = cats[key].get("items", [])
    
    new_items = []
    removed = 0
    for item in existing_items:
        text = str(item) if isinstance(item, str) else item.get("text", "")
        if text in words_to_remove:
            removed += 1
        else:
            new_items.append(item)
    
    cats[key]["items"] = new_items
    
    if save_vocab_categories(cats):
        return True, f"删除了 {removed} 个词汇"
    return False, "保存失败"


def _compute_content_hash(content_json: str) -> str:
    """计算内容哈希用于变更检测"""
    return hashlib.md5(content_json.encode()).hexdigest()[:16]


def upsert_vocab_courses(db, models) -> Tuple[int, int]:
    """
    同步词库分类到数据库courses表
    
    Args:
        db: 数据库会话
        models: 数据模型模块
    
    Returns:
        (创建数量, 更新数量)
    """
    cats = load_vocab_categories()
    created = 0
    updated = 0
    
    for key, cat in cats.items():
        if not isinstance(cat, dict):
            continue
        
        title = build_course_title(cat)
        if not title:
            continue
        
        content = build_course_content(key, cat)
        desc = cat.get("desc", "主题字库练习")
        level = cat.get("level", "Level 1")
        duration = int(cat.get("duration", 5) or 5)
        content_json = json.dumps(content, ensure_ascii=False)
        
        # 查找现有课程
        existing = db.query(models.Course).filter(models.Course.title == title).first()
        
        if existing:
            # 检查是否需要更新（比较内容）
            if existing.content_json != content_json or existing.desc != desc:
                existing.desc = desc
                existing.level = level
                existing.duration = duration
                existing.content_json = content_json
                updated += 1
                print(f"[vocab] 更新课程: {title}")
        else:
            db.add(
                models.Course(
                    title=title,
                    desc=desc,
                    level=level,
                    duration=duration,
                    content_json=content_json,
                )
            )
            created += 1
            print(f"[vocab] 创建课程: {title}")
    
    if created or updated:
        db.commit()
    
    return created, updated


def sync_deleted_courses(db, models) -> int:
    """
    同步删除：移除数据库中已不存在于配置的课程
    
    注意：此函数不会删除非词库课程（如手动创建的课程）
    
    Args:
        db: 数据库会话
        models: 数据模型模块
    
    Returns:
        删除数量
    """
    cats = load_vocab_categories()
    valid_titles = set()
    
    for key, cat in cats.items():
        if isinstance(cat, dict):
            title = build_course_title(cat)
            if title:
                valid_titles.add(title)
    
    # 查找带有emoji的课程标题（词库课程的标识）
    # 词库课程标题格式通常是 "emoji 标题"
    deleted = 0
    all_courses = db.query(models.Course).all()
    
    for course in all_courses:
        # 只处理词库课程（标题包含emoji的）
        if course.title and any(ord(c) > 0x1F000 for c in course.title):
            if course.title not in valid_titles:
                # 检查是否有关联的学习记录
                records = db.query(models.LearningRecord).filter(
                    models.LearningRecord.course_id == course.id
                ).first()
                
                if records:
                    # 有关联记录，只标记为不活跃（保留数据）
                    course.desc = f"[已删除] {course.desc}"
                    print(f"[vocab] 标记课程为已删除: {course.title}")
                else:
                    # 无关联记录，可以安全删除
                    db.delete(course)
                    deleted += 1
                    print(f"[vocab] 删除课程: {course.title}")
    
    if deleted:
        db.commit()
    
    return deleted


def get_sync_status(db, models) -> Dict:
    """
    获取同步状态
    
    Returns:
        同步状态信息
    """
    cats = load_vocab_categories()
    
    # 统计配置文件中的分类
    config_categories = set()
    config_word_count = 0
    
    for key, cat in cats.items():
        if isinstance(cat, dict):
            title = build_course_title(cat)
            if title:
                config_categories.add(title)
                items = cat.get("items", [])
                if isinstance(items, list):
                    config_word_count += len(items)
    
    # 统计数据库中的课程
    db_courses = db.query(models.Course).all()
    db_vocab_courses = set()
    db_word_count = 0
    
    for course in db_courses:
        if course.title and any(ord(c) > 0x1F000 for c in course.title):
            db_vocab_courses.add(course.title)
            try:
                content = json.loads(course.content_json or "[]")
                db_word_count += len(content)
            except:
                pass
    
    # 计算差异
    to_create = config_categories - db_vocab_courses
    to_delete = db_vocab_courses - config_categories
    synced = config_categories & db_vocab_courses
    
    return {
        "config_categories": len(config_categories),
        "config_words": config_word_count,
        "db_vocab_courses": len(db_vocab_courses),
        "db_words": db_word_count,
        "synced": len(synced),
        "to_create": list(to_create),
        "to_delete": list(to_delete),
        "is_synced": len(to_create) == 0 and len(to_delete) == 0
    }

