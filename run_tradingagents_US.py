import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cli import main as trading_main


INPUT_DIR = os.path.join(BASE_DIR, "Output", "Tradesetups_finder", "US", "csv_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "Output", "TradingAgents")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")


if TELEGRAM_BOT_TOKEN:
    os.environ["TELEGRAM_BOT_TOKEN"] = TELEGRAM_BOT_TOKEN
if TELEGRAM_CHAT_ID:
    os.environ["TELEGRAM_CHAT_ID"] = TELEGRAM_CHAT_ID
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

os.environ["TELEGRAM_ENABLED"] = "true"


sys.argv = [
    "run_tradingagents_US.py",
    "analyze",
    "--input-mode",
    "file",
    "--country",
    "US",
    "--input-path",
    INPUT_DIR,
    "--output-dir",
    OUTPUT_DIR,
    "--latest-files",
    "1",
    "--llm-provider",
    "google",
    "--quick-model",
    "gemini-2.5-flash",
    "--deep-model",
    "gemini-3.1-pro-preview",
    "--research-depth",
    "1",
    "--analysts",
    "market,social,news,fundamentals",
    "--output-language",
    "English",
]


trading_main.main()