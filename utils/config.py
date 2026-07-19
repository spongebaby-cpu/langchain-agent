"""配置加载模块 — 支持本地 Ollama 和云端 DeepSeek 两种模式"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 从 config.py 所在目录向上找到项目根目录的 .env
_PROJECT_ROOT = Path(__file__).parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_FILE)

# 本地 Ollama 默认值
LOCAL_BASE_URL = "http://localhost:11434/v1"
LOCAL_MODEL = "qwen2.5:3b"

# 云端 DeepSeek 默认值
CLOUD_BASE_URL = "https://api.deepseek.com"
CLOUD_MODEL = "deepseek-chat"


def get_config() -> dict:
    """获取所有配置，支持 local / cloud 两种模式"""
    mode = os.getenv("LLM_MODE", "local").strip().lower()

    if mode == "local":
        # 本地 Ollama 模式 — 不需要 API Key
        config = {
            "LLM_MODE": "local",
            "DEEPSEEK_API_KEY": "ollama",  # Ollama 不需要 key，但 ChatOpenAI 要求填一个
            "DEEPSEEK_BASE_URL": os.getenv("DEEPSEEK_BASE_URL", LOCAL_BASE_URL).strip(),
            "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL", LOCAL_MODEL).strip(),
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "").strip() or "",
        }
        print(f"[Local] Ollama | Model: {config['DEEPSEEK_MODEL']} | {config['DEEPSEEK_BASE_URL']}")

    elif mode == "cloud":
        # 云端模式 — 需要 API Key
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "云端模式需要 DEEPSEEK_API_KEY\n"
                "请从 https://platform.deepseek.com/ 获取并填入 .env 文件\n"
                "或者改为本地模式: LLM_MODE=local"
            )
        config = {
            "LLM_MODE": "cloud",
            "DEEPSEEK_API_KEY": api_key,
            "DEEPSEEK_BASE_URL": os.getenv("DEEPSEEK_BASE_URL", CLOUD_BASE_URL).strip(),
            "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL", CLOUD_MODEL).strip(),
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "").strip() or "",
        }
        print(f"[Cloud] DeepSeek | Model: {config['DEEPSEEK_MODEL']}")

    else:
        raise ValueError(f"未知的 LLM_MODE: {mode}，请设置为 local 或 cloud")

    return config
