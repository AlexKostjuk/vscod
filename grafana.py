import time
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from google import genai
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

# ================== НАЛАШТУВАННЯ ==================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CDP_URL = "http://localhost:9222"
INTERVAL_SECONDS = 60

# Частина URL дашборду (щоб знайти потрібну вкладку)
DASHBOARD_URL_PART = "zgraf.ab.loc"          # або "health" / uid дашборду

PROMPT = """
Ось повний текстовий вміст дашборду Health системи.

Проаналізуй стан системи:
- Які сервіси мають підвищений час відповіді
- Де є помилки або підвищений % ERR
- Загальний стан системи (нормально / є проблеми / критично)
- Короткі рекомендації

Відповідай українською, чітко і структуровано. Говори так, ніби доповідаєш черговому.
"""

client = genai.Client(api_key=GEMINI_API_KEY)

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "link", "meta"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)[:120000]

def scroll_full_page(page):
    """Прокручує сторінку, щоб підвантажити весь контент"""
    page.evaluate("""
        async () => {
            const delay = ms => new Promise(r => setTimeout(r, ms));
            const height = document.body.scrollHeight;
            const step = window.innerHeight * 0.85;
            let pos = 0;
            while (pos < height) {
                window.scrollBy(0, step);
                pos += step;
                await delay(350);
            }
            window.scrollTo(0, 0);
            await delay(400);
        }
    """)

def get_analysis(page_text: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"{PROMPT}\n\nТекст дашборду:\n\n{page_text}"
    )
    return response.text

def speak_in_gemini(analysis: str):
    """Знаходить або відкриває вкладку Gemini і змушує проговорити текст"""
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        
        gemini_page = None
        for context in browser.contexts:
            for page in context.pages:
                if "gemini.google.com" in page.url:
                    gemini_page = page
                    break
            if gemini_page:
                break

        if not gemini_page:
            print("Вкладки Gemini немає — відкриваю нову...")
            context = browser.contexts[0]
            gemini_page = context.new_page()
            gemini_page.goto("https://gemini.google.com/app", wait_until="networkidle")
            time.sleep(3)
        else:
            print("Використовую існуючу вкладку Gemini")
            gemini_page.bring_to_front()

        try:
            # Поле вводу
            input_box = gemini_page.wait_for_selector('div[contenteditable="true"]', timeout=8000)
            input_box.click()
            time.sleep(0.4)
            gemini_page.keyboard.press("Control+A")
            gemini_page.keyboard.press("Backspace")
            
            prompt_text = f"Прочитай вголос цей аналіз дашборду системи:\n\n{analysis}"
            input_box.fill(prompt_text)
            time.sleep(0.6)
            gemini_page.keyboard.press("Enter")
            
            print("Текст відправлено в Gemini. Чекаю відповіді...")
            time.sleep(9)

            # Натискаємо Listen
            listen_buttons = gemini_page.query_selector_all('button[aria-label*="Listen"], button[aria-label*="Прослухати"], button[aria-label*="Read"]')
            if listen_buttons:
                listen_buttons[-1].click()
                print("Натиснув Listen — Gemini говорить")
            else:
                print("Кнопку Listen не знайдено. Натисни вручну.")

        except Exception as e:
            print("Помилка при роботі з Gemini:", e)

def main():
    print("Запуск моніторингу дашборду...")
    print("Інтервал:", INTERVAL_SECONDS, "секунд\n")
    
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(CDP_URL)
                
                # Шукаємо вкладку з дашбордом
                dashboard_page = None
                for context in browser.contexts:
                    for page in context.pages:
                        if DASHBOARD_URL_PART in page.url:
                            dashboard_page = page
                            break
                    if dashboard_page:
                        break

                if not dashboard_page:
                    print("Не знайдено вкладку з дашбордом! Перевір URL.")
                    time.sleep(INTERVAL_SECONDS)
                    continue

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Знайшов дашборд. Збираю дані...")

                # Прокручуємо і збираємо текст
                scroll_full_page(dashboard_page)
                time.sleep(1)
                
                html = dashboard_page.content()
                page_text = clean_html(html)

                print("Робити аналіз...")
                analysis = get_analysis(page_text)
                print("Аналіз готовий.")

                # Зберігаємо на всяк випадок
                with open("last_analysis.txt", "w", encoding="utf-8") as f:
                    f.write(analysis)

                # Голос
                speak_in_gemini(analysis)

        except Exception as e:
            print("Помилка:", e)

        print(f"Чекаю {INTERVAL_SECONDS} секунд...\n")
        time.sleep(INTERVAL_SECONDS)

if name == "main":
    main()
    
    