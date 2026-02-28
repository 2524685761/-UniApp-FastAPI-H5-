"""
AI聊天服务 - 增强版
支持对话和讲故事功能，适合幼儿使用，语言简单友好

支持多种模式：
1. 离线模式：增强的关键词匹配 + 丰富故事库 + 情境对话
2. 在线模式：DeepSeek/OpenAI/通义千问等API

新增功能：
- 分类故事库（动物、冒险、寓言等）
- 情境感知对话
- 学习鼓励回复
- 多轮对话上下文
"""
import random
import os
import requests
import json
import re
from typing import Dict, Optional, List, Tuple
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """读取 .env 文件"""
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


# 加载本地配置
_ROOT = Path(__file__).resolve().parents[2]
_load_env_file(_ROOT / ".env.local")
_load_env_file(_ROOT / "backend" / ".env.local")
_load_env_file(_ROOT / "config.local.txt")
_load_env_file(_ROOT / "backend" / "config.local.txt")

# 导入配置
try:
    from ..config import config
except ImportError:
    try:
        from backend.config import config
    except ImportError:
        class SimpleConfig:
            def __init__(self):
                self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "offline")
                self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
                self.OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
                self.DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
                self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
                self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
                self.BAIDU_API_KEY = os.getenv("BAIDU_API_KEY", "")
                self.BAIDU_SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")
            
            def is_llm_configured(self):
                if self.LLM_PROVIDER == "offline":
                    return False
                elif self.LLM_PROVIDER == "openai":
                    return bool(self.OPENAI_API_KEY)
                elif self.LLM_PROVIDER == "deepseek":
                    return bool(self.DEEPSEEK_API_KEY)
                elif self.LLM_PROVIDER == "dashscope":
                    return bool(self.DASHSCOPE_API_KEY)
                elif self.LLM_PROVIDER == "baidu":
                    return bool(self.BAIDU_API_KEY and self.BAIDU_SECRET_KEY)
                return False
        config = SimpleConfig()


# ======================== 故事库 ========================

STORIES = {
    # 动物故事
    "animal": [
        {
            "title": "小兔子的胡萝卜",
            "content": "从前有一只小兔子，它最喜欢吃胡萝卜。有一天，小兔子在花园里发现了一根又大又红的胡萝卜。它高兴地跳了起来，说：'哇，这根胡萝卜真大呀！'小兔子把胡萝卜带回家，和妈妈一起分享。妈妈夸小兔子是个好孩子。小兔子开心地笑了。",
            "moral": "分享让快乐加倍"
        },
        {
            "title": "小鸟学飞",
            "content": "小鸟宝宝想要学会飞翔。它站在树枝上，看着妈妈在空中自由地飞。小鸟宝宝鼓起勇气，张开小翅膀，用力一跳！第一次，它掉了下来。第二次，它飞了一点点。第三次，它终于飞起来了！小鸟宝宝高兴地叫着：'我会飞了！我会飞了！'",
            "moral": "失败是成功之母"
        },
        {
            "title": "小熊的蜂蜜",
            "content": "小熊最喜欢吃蜂蜜了。有一天，它看到树上有一个大大的蜂巢。小熊想：'我要爬上去拿蜂蜜！'它慢慢地往上爬，终于够到了蜂巢。小熊尝了一口，真甜呀！但是，蜜蜂们飞回来了，小熊赶紧跑。虽然被追着跑，但小熊还是很开心，因为它吃到了甜甜的蜂蜜。",
            "moral": "收获需要付出努力"
        },
        {
            "title": "小猫钓鱼",
            "content": "小猫拿着小渔竿来到河边。它把鱼饵放进水里，静静地等着。等了好久，终于有一条小鱼上钩了！小猫高兴地拉起来，但是小鱼太滑了，又掉回水里。小猫不灰心，又试了一次。这次，它小心地抓住小鱼，终于成功了！小猫把小鱼带回家，和朋友们一起分享。",
            "moral": "耐心和坚持能带来成功"
        },
        {
            "title": "小鸭子的朋友",
            "content": "小鸭子一个人在池塘里游泳，觉得很孤单。它看到岸上有一只小青蛙，就游过去说：'你好，我们可以做朋友吗？'小青蛙高兴地答应了。它们一起游泳，一起玩耍，成了最好的朋友。小鸭子再也不孤单了，因为它有了好朋友。",
            "moral": "友谊让生活更美好"
        },
        {
            "title": "小蜗牛爬山",
            "content": "小蜗牛想要爬上高高的山顶，看看那里的风景。其他动物都说：'你爬得太慢了，不可能成功的！'但是小蜗牛没有放弃，它每天都努力往上爬一点点。过了好多天，小蜗牛终于爬到了山顶！它看到了最美丽的风景，也证明了自己可以做到！",
            "moral": "坚持就是胜利"
        }
    ],
    
    # 寓言故事
    "fable": [
        {
            "title": "乌鸦喝水",
            "content": "一只乌鸦很渴，它找到一个瓶子，里面有一点点水。但是瓶口太小，乌鸦喝不到。乌鸦想了想，它开始把小石子一颗一颗放进瓶子里。慢慢地，水升高了！乌鸦终于喝到了水。它高兴地说：'遇到困难不要怕，动动脑筋就能解决！'",
            "moral": "善于思考能解决问题"
        },
        {
            "title": "小马过河",
            "content": "小马要过河去送粮食。它问老牛：'河水深吗？'老牛说：'不深，才到我的膝盖。'小松鼠听了，着急地说：'不行不行，水很深，我的朋友都被冲走了！'小马不知道该听谁的，就自己试着走过去。它发现：水不像老牛说的那么浅，也不像松鼠说的那么深。原来，做事情要自己去尝试！",
            "moral": "实践出真知"
        },
        {
            "title": "龟兔赛跑",
            "content": "骄傲的兔子和乌龟比赛跑步。兔子跑得很快，跑到一半就睡着了。慢吞吞的乌龟一直往前爬，从不停下来。当兔子醒来时，乌龟已经到达终点了！兔子后悔地说：'我不应该骄傲大意！'乌龟笑着说：'只要坚持，就能成功！'",
            "moral": "骄傲使人落后，坚持就能成功"
        }
    ],
    
    # 日常生活故事
    "daily": [
        {
            "title": "小明的早晨",
            "content": "每天早上，小明听到闹钟响，就自己起床。他先刷牙、洗脸，然后穿好衣服。妈妈夸小明：'你真是个好孩子，自己的事情自己做！'小明高兴地说：'我长大了，我可以照顾自己了！'吃完早饭，小明背上书包，开开心心地去上学。",
            "moral": "自己的事情自己做"
        },
        {
            "title": "帮妈妈做家务",
            "content": "周末，小红看到妈妈在忙着打扫房间。她想：'我可以帮妈妈做点什么呢？'小红拿起扫帚帮妈妈扫地，又把桌子擦得干干净净。妈妈看到了，开心地抱着小红说：'我的宝贝长大了，会帮妈妈做事了！'小红心里暖暖的，觉得帮助别人真开心！",
            "moral": "帮助家人是美德"
        },
        {
            "title": "新朋友",
            "content": "幼儿园来了一个新同学，他一个人坐在角落里，看起来很害羞。小华主动走过去说：'你好，我叫小华，我们一起玩吧！'新同学高兴地笑了，说：'谢谢你！我叫小明。'从那天起，他们成了好朋友，一起学习，一起游戏。",
            "moral": "友好待人，收获友谊"
        }
    ],
    
    # 冒险故事
    "adventure": [
        {
            "title": "勇敢的小老鼠",
            "content": "小老鼠听说山的那边有美味的奶酪。虽然路很远，可能会遇到危险，但小老鼠决定出发。路上，它遇到了大河，就找来树枝搭桥；遇到了大猫，就藏在草丛里等它走开。经过很多困难，小老鼠终于找到了奶酪！它开心地说：'勇敢向前走，一定能成功！'",
            "moral": "勇敢面对困难"
        },
        {
            "title": "小鱼的梦想",
            "content": "小鱼住在小池塘里，它梦想着去看看大海。其他鱼都说：'大海太远了，你去不了的。'但小鱼没有放弃，它顺着小河往前游。游啊游，有一天，它终于看到了蓝蓝的大海！'哇！原来世界这么大！'小鱼实现了自己的梦想。",
            "moral": "有梦想就要勇敢追"
        }
    ],
    
    # 教育故事
    "educational": [
        {
            "title": "爱护眼睛",
            "content": "小明喜欢看电视，一看就是好几个小时。有一天，他发现自己看东西有点模糊了。医生说：'看电视太久会伤害眼睛的。'从那以后，小明每看半小时就休息一下，还经常做眼保健操。慢慢地，他的眼睛又变得明亮了。",
            "moral": "保护眼睛很重要"
        },
        {
            "title": "诚实的小华",
            "content": "小华不小心打破了花瓶。他很害怕，想把碎片藏起来。但是，他想起老师说过：'诚实的孩子最可爱。'于是，小华主动告诉妈妈自己打破了花瓶。妈妈不但没有骂他，还夸他：'你能承认错误，妈妈很高兴！'小华学会了做一个诚实的孩子。",
            "moral": "诚实是美德"
        }
    ]
}


# ======================== 对话模板 ========================

DIALOGUE_RESPONSES = {
    # 问候类
    "greetings": {
        "keywords": ["你好", "早上好", "下午好", "晚上好", "嗨", "哈喽"],
        "responses": [
            "你好呀！我是你的AI小伙伴，很高兴认识你！",
            "你好！今天想听故事还是问我问题呢？",
            "你好！我们一起玩吧！",
            "嗨！见到你真开心！"
        ]
    },
    
    # 告别类
    "goodbye": {
        "keywords": ["再见", "拜拜", "明天见", "我要走了"],
        "responses": [
            "再见！记得多练习普通话哦！",
            "再见！明天见！",
            "拜拜！要好好学习哦！",
            "下次再来玩哦！"
        ]
    },
    
    # 感谢类
    "thanks": {
        "keywords": ["谢谢", "感谢", "多谢"],
        "responses": [
            "不客气！能帮助你我很快乐！",
            "不用谢！继续加油！",
            "不客气！你真棒！",
            "不用谢，这是我应该做的！"
        ]
    },
    
    # 故事请求类
    "story_request": {
        "keywords": ["故事", "讲故事", "讲个故事", "听故事"],
        "responses": [
            "好的，我来给你讲一个有趣的故事！",
            "你想听什么故事呢？我来给你讲一个吧！",
            "太好了！我最喜欢讲故事了！"
        ],
        "action": "tell_story"
    },
    
    # 问题类
    "questions": {
        "keywords": ["问题", "问你", "想知道", "为什么"],
        "responses": [
            "有什么问题尽管问我吧！",
            "你想知道什么呢？",
            "问吧问吧，我会认真回答的！"
        ]
    },
    
    # 动物类话题
    "animals": {
        "keywords": ["动物", "小猫", "小狗", "兔子", "熊猫", "老虎"],
        "responses": [
            "动物们都很可爱呢！你最喜欢什么动物？",
            "我知道很多动物，你想听哪个动物的故事？",
            "动物是我们的好朋友！",
            "你喜欢动物吗？我可以给你讲动物的故事！"
        ]
    },
    
    # 学习鼓励类
    "learning": {
        "keywords": ["学习", "学普通话", "读书", "认字"],
        "responses": [
            "学习普通话很有趣的！我们一起加油！",
            "多练习就能说得越来越好！",
            "你真棒，继续努力！",
            "每天进步一点点，你会越来越厉害的！"
        ]
    },
    
    # 自我介绍类
    "introduction": {
        "keywords": ["名字", "你是谁", "你叫什么"],
        "responses": [
            "我是你的AI学习伙伴，你可以叫我小助手！",
            "我是来帮助你学习的AI朋友！",
            "我是你的学习小助手，很高兴认识你！"
        ]
    },
    
    # 情绪安慰类
    "comfort": {
        "keywords": ["不开心", "难过", "伤心", "害怕", "不想"],
        "responses": [
            "别担心，我陪着你呢！",
            "没关系，休息一下再继续好吗？",
            "每个人都会有不开心的时候，想听个故事吗？",
            "你很棒的！相信自己！"
        ]
    },
    
    # 表扬回应类
    "praise_response": {
        "keywords": ["我很棒", "我做到了", "我会了", "成功"],
        "responses": [
            "太棒了！你真的很厉害！",
            "恭喜你！继续保持！",
            "你做到了！我就知道你可以的！",
            "真是太棒了！给你一个大大的赞！"
        ]
    },
    
    # 天气类话题
    "weather": {
        "keywords": ["天气", "下雨", "太阳", "晴天"],
        "responses": [
            "无论什么天气，学习的热情都不能减少哦！",
            "今天是学习的好日子呢！",
            "天气很好，我们一起学习吧！"
        ]
    }
}


# ======================== API调用 ========================

def _call_openai_api(prompt: str, system_prompt: str = None) -> Optional[str]:
    """调用OpenAI API"""
    api_key = config.OPENAI_API_KEY
    base_url = config.OPENAI_BASE_URL
    model = config.OPENAI_MODEL
    
    if not api_key:
        return None
    if "REPLACE_ME" in str(api_key):
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            print(f"OpenAI API错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"OpenAI API调用失败: {e}")
        return None


def _call_deepseek_api(prompt: str, system_prompt: str = None) -> Optional[str]:
    """调用DeepSeek API"""
    api_key = config.DEEPSEEK_API_KEY
    if not api_key:
        # 尝试从环境变量获取
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    if not api_key:
        return None
    
    try:
        base_url = config.DEEPSEEK_BASE_URL or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = config.DEEPSEEK_MODEL or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            print(f"DeepSeek API错误: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"DeepSeek API调用失败: {e}")
        return None


def _call_dashscope_api(prompt: str, system_prompt: str = None) -> Optional[str]:
    """调用通义千问API"""
    api_key = config.DASHSCOPE_API_KEY
    if not api_key:
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    if not api_key:
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": "qwen-turbo",
            "input": {"messages": messages},
            "parameters": {"temperature": 0.7, "max_tokens": 500}
        }
        
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "output" in result and "choices" in result["output"]:
                return result["output"]["choices"][0]["message"]["content"].strip()
            # 新版本API格式
            if "output" in result and "text" in result["output"]:
                return result["output"]["text"].strip()
        else:
            print(f"DashScope API错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"DashScope API调用失败: {e}")
        return None


def _call_llm_api(prompt: str, system_prompt: str = None) -> Optional[str]:
    """统一调用大模型API"""
    provider = os.getenv("LLM_PROVIDER", "offline").lower()
    
    if provider == "offline":
        return None
    
    if provider == "openai":
        return _call_openai_api(prompt, system_prompt)
    elif provider == "deepseek":
        return _call_deepseek_api(prompt, system_prompt)
    elif provider == "dashscope":
        return _call_dashscope_api(prompt, system_prompt)
    
    return None


# ======================== 离线对话引擎 ========================

class OfflineDialogueEngine:
    """离线对话引擎"""
    
    def __init__(self):
        self.context = []  # 对话上下文
        self.last_topic = None
    
    def match_intent(self, user_input: str) -> Tuple[str, Dict]:
        """匹配用户意图"""
        user_input_clean = user_input.strip().lower()
        
        # 遍历所有对话模板
        for intent, data in DIALOGUE_RESPONSES.items():
            keywords = data.get("keywords", [])
            for keyword in keywords:
                if keyword in user_input_clean:
                    return intent, data
        
        return "unknown", {}
    
    def get_response(self, user_input: str) -> Dict[str, str]:
        """获取回复"""
        intent, data = self.match_intent(user_input)
        
        if intent == "unknown":
            # 默认回复
            return {
                "text": random.choice([
                    "我在听呢，你可以问我问题，或者让我给你讲故事！",
                    "你说得真好！想听故事还是问我问题呢？",
                    "我明白了！你想听故事吗？还是有什么问题要问我？",
                    "好的！我可以给你讲故事，也可以回答你的问题哦！"
                ]),
                "title": None,
                "intent": intent
            }
        
        # 检查是否有特殊动作
        action = data.get("action")
        if action == "tell_story":
            return self.tell_story()
        
        # 返回匹配的回复
        responses = data.get("responses", ["好的！"])
        return {
            "text": random.choice(responses),
            "title": None,
            "intent": intent
        }
    
    def tell_story(self, category: str = None) -> Dict[str, str]:
        """讲故事"""
        # 如果没有指定类别，随机选择
        if not category:
            category = random.choice(list(STORIES.keys()))
        
        stories = STORIES.get(category, [])
        if not stories:
            # 如果类别不存在，从所有故事中随机选择
            all_stories = []
            for cat_stories in STORIES.values():
                all_stories.extend(cat_stories)
            stories = all_stories
        
        story = random.choice(stories)
        story_text = f"今天我给你讲一个故事，叫《{story['title']}》。\n\n{story['content']}"
        
        if story.get("moral"):
            story_text += f"\n\n这个故事告诉我们：{story['moral']}"
        
        return {
            "text": story_text,
            "title": story['title'],
            "category": category
        }


# 全局对话引擎
_dialogue_engine = OfflineDialogueEngine()


# ======================== 主要API ========================

def chat_with_ai(user_input: str, mode: str = "chat") -> Dict[str, str]:
    """AI聊天主函数"""
    provider = os.getenv("LLM_PROVIDER", "offline").lower()
    
    # 调试信息（不打印任何密钥片段）
    print(f"[chat] provider={provider}")
    
    # 如果配置了API，优先使用API
    if provider != "offline":
        if mode == "story":
            system_prompt = """你是一个专门给3-6岁幼儿讲故事的AI助手。请用简单、温暖、有趣的语言讲一个短故事（150-250字）。
故事要求：
1. 内容积极向上，有教育意义
2. 语言简单，适合幼儿理解
3. 有明确的开始、过程和结尾
4. 可以是关于动物、友谊、勇气、善良等主题"""
            prompt = "请给我讲一个适合幼儿的短故事，故事要简单有趣，有教育意义。"
        else:
            system_prompt = """你是一个专门陪伴3-6岁幼儿学习国家通用语的AI助手。
要求：
1. 语言简单、温暖、鼓励
2. 回答简短（50字以内）
3. 适合幼儿理解
4. 多用表情符号增加亲切感"""
            prompt = user_input
        
        api_response = _call_llm_api(prompt, system_prompt)
        if api_response:
            return {
                "text": api_response,
                "title": None if mode != "story" else "AI故事"
            }
        print("API调用失败，使用离线模式")
    
    # 离线模式
    if mode == "story":
        return _dialogue_engine.tell_story()
    
    return _dialogue_engine.get_response(user_input)


def get_random_story(category: str = None) -> Dict[str, str]:
    """获取随机故事"""
    provider = os.getenv("LLM_PROVIDER", "offline").lower()
    
    # 如果配置了API，使用API生成故事
    if provider != "offline":
        system_prompt = """你是一个专门给3-6岁幼儿讲故事的AI助手。请用简单、温暖、有趣的语言讲一个短故事（150-250字）。
故事要求：
1. 内容积极向上，有教育意义
2. 语言简单，适合幼儿理解
3. 有明确的开始、过程和结尾"""
        
        prompt = "请给我讲一个适合幼儿的短故事。"
        if category:
            category_prompts = {
                "animal": "请讲一个关于小动物的故事",
                "fable": "请讲一个寓言故事",
                "adventure": "请讲一个冒险故事",
                "educational": "请讲一个有教育意义的故事"
            }
            prompt = category_prompts.get(category, prompt)
        
        api_response = _call_llm_api(prompt, system_prompt)
        if api_response:
            return {
                "text": api_response,
                "title": "AI故事"
            }
        print("API调用失败，使用离线故事库")
    
    # 离线模式
    return _dialogue_engine.tell_story(category)


def get_story_categories() -> List[Dict]:
    """获取故事分类列表"""
    categories = []
    category_info = {
        "animal": {"name": "动物故事", "emoji": "🐾", "description": "可爱的小动物们的故事"},
        "fable": {"name": "寓言故事", "emoji": "📚", "description": "有道理的经典故事"},
        "daily": {"name": "日常生活", "emoji": "🏠", "description": "身边发生的小故事"},
        "adventure": {"name": "冒险故事", "emoji": "🌟", "description": "勇敢的冒险故事"},
        "educational": {"name": "教育故事", "emoji": "📖", "description": "学习好习惯的故事"}
    }
    
    for key, stories in STORIES.items():
        info = category_info.get(key, {"name": key, "emoji": "📗", "description": ""})
        categories.append({
            "key": key,
            "name": info["name"],
            "emoji": info["emoji"],
            "description": info["description"],
            "count": len(stories)
        })
    
    return categories


def get_learning_encouragement(emotion_type: str = "neutral") -> str:
    """获取学习鼓励语"""
    encouragements = {
        "happy": [
            "太棒了！继续保持！",
            "你学得真好！",
            "真是学习小明星！"
        ],
        "neutral": [
            "加油！你可以的！",
            "继续努力！",
            "你做得很好！"
        ],
        "confused": [
            "没关系，慢慢来！",
            "再试一次，你一定行！",
            "别着急，我们一起练习！"
        ],
        "frustrated": [
            "别灰心，学习需要时间！",
            "休息一下再继续吧！",
            "你已经很努力了！"
        ]
    }
    
    messages = encouragements.get(emotion_type, encouragements["neutral"])
    return random.choice(messages)
