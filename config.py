import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Папка, де лежить .exe (або цей файл при запуску з Python)
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Chrome з відкритим портом налагодження
CDP_URL = os.getenv("CDP_URL", "http://localhost:9222")
CHROME_PATH = os.getenv("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CHROME_PROFILE_DIR = os.getenv("CHROME_PROFILE_DIR", r"C:\chrome-debug-profile")

# Частина URL, за якою шукаємо вкладку з дашбордом
DASHBOARD_URL_PART = os.getenv("DASHBOARD_URL_PART", "zgraf.ab.loc")
# Повний URL, який відкриється, якщо Chrome довелося запускати самій програмі (необов'язково)
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "")

# true — додавати скріншоти до аналізу; false — тільки текст сторінки
USE_SCREENSHOTS = os.getenv("USE_SCREENSHOTS", "false").lower() in ("1", "true", "yes")
MAX_SCREENSHOTS = int(os.getenv("MAX_SCREENSHOTS", "6"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "120000"))

PROMPT = """
Ти аналізуєш дашборд моніторингу (текст сторінки, а також скріншоти зверху вниз, якщо вони додані).
Знайди аномалії та проблеми:
- сервіси з підвищеним часом відповіді
- помилки, підвищений % ERR
- різкі стрибки або провали на графіках
- панелі без даних (No data) або з підозріло нульовими значеннями

Дай відповідь українською, чітко й структуровано:
1. Загальний стан: нормально / є проблеми / критично
2. Список знайдених аномалій (панель, що не так, наскільки)
3. Короткі рекомендації, що перевірити першим

Говори так, ніби доповідаєш черговому. Не вигадуй те, чого немає на дашборді.
"""
