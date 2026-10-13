import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

import config


class CaptureError(Exception):
    pass


@dataclass
class Capture:
    url: str
    title: str
    text: str
    screenshots: list = field(default_factory=list)


# Знаходить елемент, що реально прокручується (у Grafana це зазвичай внутрішній блок, а не вікно)
PREPARE_JS = """
() => {
  let target = document.scrollingElement || document.documentElement;
  let best = target.scrollHeight - target.clientHeight;
  for (const el of document.querySelectorAll('*')) {
    const s = getComputedStyle(el).overflowY;
    if ((s === 'auto' || s === 'scroll') && el.scrollHeight - el.clientHeight > best) {
      target = el;
      best = el.scrollHeight - el.clientHeight;
    }
  }
  window.__st = target;
  return [target.scrollHeight, target.clientHeight];
}
"""


def cdp_alive() -> bool:
    try:
        urllib.request.urlopen(config.CDP_URL + "/json/version", timeout=2)
        return True
    except Exception:
        return False


def ensure_chrome(progress=lambda m: None):
    """Якщо Chrome з портом налагодження ще не запущений — запускає його."""
    if cdp_alive():
        return
    if not os.path.exists(config.CHROME_PATH):
        raise CaptureError(f"Не знайдено Chrome: {config.CHROME_PATH}. Вкажіть CHROME_PATH у .env")

    progress("Запускаю Chrome...")
    port = urlparse(config.CDP_URL).port or 9222
    args = [
        config.CHROME_PATH,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={config.CHROME_PROFILE_DIR}",
    ]
    if config.DASHBOARD_URL:
        args.append(config.DASHBOARD_URL)
    subprocess.Popen(args)

    for _ in range(20):
        time.sleep(1)
        if cdp_alive():
            return
    raise CaptureError("Chrome запущено, але порт налагодження не відповідає")


def _find_dashboard_page(browser):
    for context in browser.contexts:
        for page in context.pages:
            if config.DASHBOARD_URL_PART in page.url:
                return page
    raise CaptureError(
        f"Не знайдено вкладку з дашбордом (шукаю '{config.DASHBOARD_URL_PART}' в URL). "
        "Відкрийте дашборд у Chrome, який запускає ця програма."
    )


def capture(progress=lambda m: None) -> Capture:
    ensure_chrome(progress)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(config.CDP_URL)
        page = _find_dashboard_page(browser)
        page.bring_to_front()

        progress("Прокручую дашборд...")
        height, client = page.evaluate(PREPARE_JS)
        step = max(int(client * 0.9), 300)
        positions = list(range(0, max(height, 1), step))
        if config.USE_SCREENSHOTS:
            positions = positions[: config.MAX_SCREENSHOTS]

        shots = []
        for pos in positions:
            page.evaluate("y => window.__st.scrollTo(0, y)", pos)
            page.wait_for_timeout(800)  # час на підвантаження панелей
            if config.USE_SCREENSHOTS:
                shots.append(page.screenshot(type="png"))
        page.evaluate("window.__st.scrollTo(0, 0)")

        text = page.inner_text("body")[: config.MAX_TEXT_CHARS]
        return Capture(url=page.url, title=page.title(), text=text, screenshots=shots)
