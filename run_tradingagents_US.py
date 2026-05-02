import os
import sys
import traceback
import importlib.util

# ---------------- PATH SETUP ----------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Go one level UP to reach colab-notebooks
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def _ensure_import_path() -> None:
    # ✅ Add project root, not script dir
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)


def _configure_environment() -> None:
    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key

    telegram_enabled = bool(telegram_bot_token and telegram_chat_id)
    os.environ["TELEGRAM_ENABLED"] = "true" if telegram_enabled else "false"

    if telegram_enabled:
        os.environ["TELEGRAM_BOT_TOKEN"] = telegram_bot_token
        os.environ["TELEGRAM_CHAT_ID"] = telegram_chat_id


def _validate_paths(input_dir: str, output_dir: str) -> None:
    if not os.path.exists(input_dir):
        print("CONFIG ERROR: input path does not exist:", input_dir)
        raise SystemExit(1)

    os.makedirs(output_dir, exist_ok=True)


def _check_required_modules() -> None:
    required_modules = {
        "typer": "typer",
        "rich": "rich",
        "dotenv": "python-dotenv",
        "requests": "requests",
        "questionary": "questionary",
    }

    missing = []
    for module_name, package_name in required_modules.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)

    if missing:
        print("DEPENDENCY ERROR:", ", ".join(set(missing)))
        raise SystemExit(1)


def _build_argv(input_dir: str, output_dir: str) -> list[str]:
    return [
        "run_tradingagents_US.py",
        "--input-mode", "file",
        "--country", "US",
        "--input-path", input_dir,
        "--output-dir", output_dir,
        "--latest-files", "1",
        "--llm-provider", "google",
        "--quick-model", "gemini-2.5-flash",
        "--deep-model", "gemini-3.1-pro-preview",
        "--research-depth", "1",
        "--analysts", "market,news,fundamentals",
        "--output-language", "English",
    ]


def main() -> None:
    _ensure_import_path()

    # ✅ FIXED PATHS (no duplicate colab-notebooks)
    input_dir = os.path.join(BASE_DIR, "colab-notebooks", "Output", "Tradesetups_finder", "US", "csv_data")
    output_dir = os.path.join(BASE_DIR, "colab-notebooks", "Output", "TradingAgents")

    print("SCRIPT_DIR:", SCRIPT_DIR)
    print("BASE_DIR:", BASE_DIR)
    print("INPUT_DIR:", input_dir)
    print("INPUT EXISTS:", os.path.exists(input_dir))
    print("OUTPUT_DIR:", output_dir)

    _configure_environment()
    _validate_paths(input_dir, output_dir)
    _check_required_modules()

    sys.argv = _build_argv(input_dir, output_dir)
    print("ARGV:", sys.argv)

    # ❗ TEMP: since cli doesn't exist, fail clearly
    try:
        from cli import main as trading_main
    except Exception:
        print("\n❌ ERROR: 'cli' module not found in project")
        print("You must replace this import with your actual entry script\n")
        raise SystemExit(1)

    try:
        trading_main.main()
    except Exception as exc:
        print("RUNTIME ERROR:", exc)
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()