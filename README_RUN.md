# ss

这是一个基于 UniApp (前端) 和 FastAPI (后端) 的情感伴学系统原型。系统不仅能进行发音评分，还能通过分析音频特征模拟判断学习者的情绪状态（如困惑、挫败、自信），并动态调整反馈策略。

## 面向人群与核心价值（你这个项目的“亮点”）

- **面向人群**：民族地区、边境/偏远地区、幼儿等国家通用语学习者（更需要“低门槛、低挫败、强鼓励”的练习体验）。
- **核心能力**：
  - **纠音**：录音→评分→问题点提示（如停顿、音量、识别文本差异等）。
  - **情感伴学**：检测到“困惑/挫败”等负面情绪时，自动**放缓节奏、加强示范、鼓励复练或换题**，降低挫败、提升坚持度。
- **政策契合点**：
  - **教育提质**：助力民族地区、边境地区、偏远地区开展国家通用语言文字教学与培训。
  - **社会和谐**：利用语言科技促进青少年身心健康发展（情绪识别与情感激励）。

## 一、系统组成

- **Frontend**: UniApp (Vue 2)，支持 H5、App 和小程序。
- **Backend**: Python FastAPI，提供 RESTful API。
- **Database**: SQLite (轻量级文件数据库，无需安装)。
- **AI Analysis**: 基于音频特征的启发式模拟算法（可替换为真实 AI 模型）。

## 二、主题字库（开箱即用，支持增删改）

系统自带 10 个主题字库（会自动变成“课程”，在首页直接看到并点击进入）：

- 🐾 动物字（25）
- 👤 身体部位（20）
- 👕 衣物字（15）
- 🎨 颜色字（15）
- 🍎 食物字（25）
- 🍊 水果字（20）
- 🪑 家具字（15）
- 👔 职业字（20）
- 🚗 交通工具（18）
- ☀️ 天气字（15）

### 如何修改词库内容（推荐你后续按地区/年龄微调）

编辑文件：`backend/data/vocab_categories.json`

- **增加/删除分类**：新增一个顶层 key（如 `"plant"`），或删掉不要的 key。
- **修改数量/内容**：修改该分类下的 `items` 列表即可。
- **修改后如何生效**：**重启后端**即可（后端启动时会自动把词库 upsert 同步到 `courses` 表）。

## 二、快速开始

### 1. 启动后端 (Python)

确保你已经安装了 Python 3.8+。

**Windows 推荐：直接双击 `run_backend.bat`（一键启动，自动读取 `config.local.txt`）**

```bash
# 1. 确保在项目根目录（demo 目录）
# 如果不在，先执行: cd C:\Users\25246\Desktop\demo

# 2. 安装依赖
pip install -r backend/requirements.txt

# （可选）如果你要启用“真实AI模型”(ASR/情感模型)，再安装：
pip install -r backend/requirements_ai.txt

# 3. 安装 FFmpeg（用于 mp3 解析）
# Windows: https://www.gyan.dev/ffmpeg/builds/ 下载后将 ffmpeg.exe 所在目录加入 PATH
# macOS: `brew install ffmpeg`
# Linux: 通过包管理器安装（如 `apt install ffmpeg`）

# 4. 启动服务（从项目根目录运行）
# Windows PowerShell:
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# Linux/Mac:
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# 或者，如果你想从 backend 目录运行，需要先修改导入方式或使用：
# cd backend
# python -m uvicorn main:app --reload

> 如果已经运行过旧版本并生成了 `sql_app.db`，想要看到新的课程词汇，可以先删除该文件或清空数据库，再重新启动后端以便自动写入最新课程内容。
```

后端启动后，访问 `http://127.0.0.1:8000/docs` 可以查看自动生成的 API 文档。

### 2. 运行前端 (UniApp)

**方法 A：使用 HBuilderX (推荐)**
1. 打开 HBuilderX，导入本项目根目录。
2. 点击菜单栏 "运行" -> "运行到浏览器" -> "Chrome/Edge"。
3. 浏览器会自动打开项目。

**方法 B：使用 CLI**
如果你是 CLI 创建的项目（本项目结构为 HBuilderX 结构），可能需要调整。但在 HBuilderX 中最简单。

### 3. 使用流程

1. **首页**：系统会自动从后端拉取课程列表（如“基础问候”、“校园生活”）。
2. **学习页**：
   - 点击“开始”进入学习。
   - 按住“按住说话”按钮，对着麦克风朗读屏幕上的词语。
   - 松开按钮，音频会自动上传到后端。
3. **反馈**：
   - 后端分析音频文件（保存在 `backend/uploads`），返回评分和情绪。
   - 如果你的语速过快或音量异常，系统可能会识别为“焦虑”或“挫败”。
   - 前端会根据情绪显示相应的鼓励话语，如果情绪消极，会提示“已为您放慢语速”。

## 三、核心代码说明

- **后端分析逻辑 (`backend/services/audio_service.py`)**: 
  目前采用基于规则的算法模拟情感分析。例如：
  - 基础分：随机 + 文件大小校验。
  - 情感：根据分数高低映射（高分->自信，低分->困惑）。
  - *扩展建议*：可以在此处接入 OpenAI Whisper 或 HuggingFace 的情感识别模型。

- **主题字库与课程同步**
  - 词库配置：`backend/data/vocab_categories.json`
  - 同步逻辑：`backend/services/vocab_service.py`（启动时自动 upsert 到 `courses`）
  - 接口：`/vocab/categories` 与 `/vocab/{category_key}`（可用于做“按主题入口/统计面板”）

- **前端交互 (`pages/learn/learn.vue`)**:
  - 使用 `uni.getRecorderManager` 录音。
  - 使用 `uni.uploadFile` 上传文件到 `/analyze` 接口。
  - **情绪自适应**：当检测到困惑/挫败时，提供“再练一次/换一题”，并自动多示范一次，降低挫败感。

## 四、AI聊天功能配置（可选）

系统默认使用**离线模式**（关键词匹配 + 预设故事库）。如果你想接入真实大模型API，可以配置：

### 方式1：使用 DeepSeek API（推荐）

先在环境变量里设置密钥，然后运行 `run_backend_with_deepseek.bat`。

Windows PowerShell 示例：
```powershell
$env:LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="sk-你的密钥"
```

### 方式2：使用OpenAI API

1. 获取API Key：访问 https://platform.openai.com/api-keys
2. 设置环境变量（Windows PowerShell）：
   ```powershell
   $env:LLM_PROVIDER="openai"
   $env:OPENAI_API_KEY="sk-你的API密钥"
   ```
3. 重启后端服务

### 方式3：使用通义千问（阿里云DashScope）

1. 获取API Key：访问 https://dashscope.console.aliyun.com/
2. 设置环境变量：
   ```powershell
   $env:LLM_PROVIDER="dashscope"
   $env:DASHSCOPE_API_KEY="你的API密钥"
   ```
3. 重启后端服务

### 方式4：继续使用离线模式（默认）

不设置任何环境变量，系统会自动使用离线模式（关键词匹配 + 故事库）。

**注意**：如果API配置错误或网络不通，系统会自动回退到离线模式，不影响使用。

## 五、注意事项

- **跨域问题**: 后端已配置 `CORSMiddleware` 允许所有来源 (`*`)，因此 H5 模式下可以直接请求。
- **录音权限**: 浏览器可能会请求麦克风权限，请允许。部分浏览器（如 Safari）对非 HTTPS 环境的录音限制较严，推荐使用 Chrome 或 Edge 调试。
- **API配置**: AI聊天功能默认离线，如需真实AI对话，请按上述方式配置API密钥。
- **手机/真机访问**：不要用 `127.0.0.1`，请到【我的】页填写电脑的局域网 IP（如 `192.168.1.8:8000`），然后点“测试连接”。

