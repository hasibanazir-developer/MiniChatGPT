"""All project settings in one place.

Secret values (like the Gemini API key) are read from the .env file,
so they never appear inside the code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root folder (two levels above this file: src/chatbot -> src -> project)
PROJECT_DIR = Path(__file__).resolve().parents[2]

# Load values from the .env file in the project root
load_dotenv(PROJECT_DIR / ".env")

# ---------- Gemini API (main brain) ----------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_BACKUP_MODEL = os.getenv("GEMINI_BACKUP_MODEL", "").strip()

# If Gemini is busy (error 503), try again this many times before giving up
GEMINI_RETRIES = 1

# How long Gemini may "think" before answering: minimal, low, medium, high.
# Lower = faster answers. Leave empty in .env to use Google's default.
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "minimal").strip().lower()

# If Gemini does not answer within this many seconds, stop waiting and use the backup
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "15"))

# How many earlier messages Gemini should remember (chat memory)
MAX_HISTORY_MESSAGES = 20

# Instructions that give the chatbot its personality
SYSTEM_PROMPT = (
    "You are MiniChatGPT, a friendly and helpful AI assistant. "
    "Give clear, correct, and well-organized answers. "
    "Use simple English unless the user asks for more detail. "
    "Use Markdown (lists, bold text, code blocks) when it makes the answer easier to read."
)

# ---------- Local trained model (backup brain) ----------
LOCAL_MODEL_DIR = Path(
    os.getenv("LOCAL_MODEL_DIR", PROJECT_DIR / "models" / "minichatgpt-model")
)

# Must be the same prefix that was used during training in Colab
LOCAL_PROMPT_PREFIX = "Reply to this message: "
LOCAL_MAX_INPUT_TOKENS = 64
LOCAL_MAX_NEW_TOKENS = 48