import os
from dotenv import load_dotenv

load_dotenv()

USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Use OpenRouter if no Anthropic key
USE_OPENROUTER = bool(OPENROUTER_API_KEY) and not bool(ANTHROPIC_API_KEY)

MODEL_MAIN = os.getenv("MODEL_MAIN", "Qwen/Qwen2.5-7B-Instruct")
MODEL_LIGHT = os.getenv("MODEL_LIGHT", os.getenv("MODEL_MAIN", "Qwen/Qwen2.5-7B-Instruct"))

# Attached to every captured Agent run. Release packaging can override this
# with the final Git tag without changing code.
AGENT_VERSION = os.getenv("AGENT_VERSION", "ventureai-v2-stage3-2026-09-15")

JWT_SECRET = os.getenv("JWT_SECRET", "venture-ai-secret-key-change-in-production")
