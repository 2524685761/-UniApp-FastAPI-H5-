# futuretts（移动端 H5：DeepSeek 聊天 + V-API TTS）

你将得到一个“开箱即用”的移动端 H5：
- **前端**：Vue 3 + Vite + Vant（移动端主流 UI）
- **后端**：FastAPI
- **能力**：
  - **聊天（DeepSeek）**：`/api/chat`
  - **文本转语音（V-API / OpenAI 兼容）**：`/api/tts`（返回 mp3）

> 说明：出于安全原因，**不会把你的 Key 写进仓库**。启动时会弹窗让你粘贴 Key，并写入本机 `futuretts/.env.local`（已忽略，不会提交）。

## 一键启动（Windows）

在 `futuretts` 目录里双击：
- `run.bat`

它会：
1. 让你输入 DeepSeek Key（可跳过）
2. 让你输入 V-API Key（可跳过）
3. 安装后端依赖并启动后端
4. 安装前端依赖并启动前端
5. 自动打开浏览器

默认地址：
- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- 后端文档：`http://127.0.0.1:8000/docs`

## 手动配置（可选）

如果你不想每次弹窗输入，也可以手动创建 `futuretts/.env.local`：

```ini
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

V36_API_KEY=sk-...
V36_BASE_URL=https://api.v36.cm/v1
V36_TTS_MODEL=qwen3-tts-flash
V36_TTS_VOICE=alloy
V36_TTS_SPEED=1.0
```

## 参考
- V-API：[`https://api.v36.cm/`](https://api.v36.cm/)


