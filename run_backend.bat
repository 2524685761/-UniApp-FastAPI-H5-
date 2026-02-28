@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Demo Backend Launcher

echo ========================================
echo Demo backend launcher (one-click)
echo - Chat: DeepSeek (optional)
echo - TTS : V-API (OpenAI-compatible) qwen3-tts-flash (optional)
echo ========================================
echo.

REM --- sanity checks ---
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Please install Python 3.8+
  pause
  exit /b 1
)

if not exist "backend\\requirements.txt" (
  echo [ERROR] Missing backend\\requirements.txt
  pause
  exit /b 1
)

echo [1/3] Installing deps...
pip install -r backend/requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed
  pause
  exit /b 1
)
echo.

REM --- ensure config.local.txt exists ---
if not exist "config.local.txt" goto _maybe_copy_config
goto _optional_setup

:_maybe_copy_config
if exist "config.local.example.txt" (
  echo Creating config.local.txt from config.local.example.txt ...
  copy /Y "config.local.example.txt" "config.local.txt" >nul
) else (
  echo [WARN] config.local.txt not found. Will run offline chat + local TTS.
)

:_optional_setup
REM 跳过交互式配置，直接检测已有密钥

:_detect_keys

REM --- detect keys (only checks presence; backend will load full values) ---
set HAS_DEEPSEEK_KEY=0
if exist "config.local.txt" findstr /R /C:"^DEEPSEEK_API_KEY=" config.local.txt >nul 2>&1 && set HAS_DEEPSEEK_KEY=1
set HAS_OPENAI_KEY=0
if exist "config.local.txt" findstr /R /C:"^OPENAI_API_KEY=" config.local.txt >nul 2>&1 && set HAS_OPENAI_KEY=1

if "!HAS_DEEPSEEK_KEY!"=="1" (
  if "%LLM_PROVIDER%"=="" set LLM_PROVIDER=deepseek
  if "%DEEPSEEK_BASE_URL%"=="" set DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
  if "%DEEPSEEK_MODEL%"=="" set DEEPSEEK_MODEL=deepseek-chat
  echo [LLM] DeepSeek enabled. model=!DEEPSEEK_MODEL!
) else if "!HAS_OPENAI_KEY!"=="1" (
  if "%LLM_PROVIDER%"=="" set LLM_PROVIDER=openai
  if "%OPENAI_MODEL%"=="" set OPENAI_MODEL=gpt-3.5-turbo
  echo [LLM] OpenAI-compatible chat enabled. model=!OPENAI_MODEL!
) else (
  echo [LLM] Offline chat (no API key found)
)

set HAS_VAPI_KEY=0
if exist "config.local.txt" findstr /R /C:"^OPENAI_API_KEY=" config.local.txt >nul 2>&1 && set HAS_VAPI_KEY=1
if "!HAS_VAPI_KEY!"=="1" (
  if "%TTS_PROVIDER%"=="" set TTS_PROVIDER=openai_compat
  if "%OPENAI_BASE_URL%"=="" set OPENAI_BASE_URL=https://api.v36.cm/v1
  if "%OPENAI_TTS_MODEL%"=="" set OPENAI_TTS_MODEL=qwen3-tts-flash
  if "%OPENAI_TTS_VOICE%"=="" set OPENAI_TTS_VOICE=alloy
  echo [TTS] V-API enabled. model=!OPENAI_TTS_MODEL!
) else (
  echo [TTS] Local TTS (no OPENAI_API_KEY found)
)

echo.
set PORT=8000
if not "%PORT_OVERRIDE%"=="" set PORT=%PORT_OVERRIDE%
echo [2/3] Starting backend on http://127.0.0.1:%PORT% ...
echo Docs: http://127.0.0.1:%PORT%/docs
echo.

uvicorn backend.main:app --reload --host 127.0.0.1 --port %PORT%
if errorlevel 1 (
  echo.
  echo [ERROR] Backend failed to start. Most common cause: port %PORT% already in use.
  echo Try closing other backend windows, or set PORT_OVERRIDE=8001 and re-run.
)

pause
