import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, ttk

import analyzer
import browser
import config


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Аналіз дашборду")
        self.geometry("820x620")
        self.events = queue.Queue()

        self.button = ttk.Button(self, text="Аналізувати дашборд", command=self.start)
        self.button.pack(fill="x", padx=12, pady=(12, 6), ipady=10)

        self.status = tk.StringVar(value="Готово до роботи")
        ttk.Label(self, textvariable=self.status).pack(anchor="w", padx=12)

        self.output = scrolledtext.ScrolledText(self, wrap="word", font=("Segoe UI", 11))
        self.output.pack(fill="both", expand=True, padx=12, pady=12)

        self.after(100, self.poll)

    def start(self):
        self.button.state(["disabled"])
        self.output.delete("1.0", "end")
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        """Виконується у фоновому потоці, щоб вікно не зависало."""
        try:
            if not config.GEMINI_API_KEY:
                raise RuntimeError("Не задано GEMINI_API_KEY у файлі .env")

            cap = browser.capture(lambda m: self.events.put(("status", m)))
            self.events.put(("status", "Gemini аналізує..."))
            result = analyzer.analyze(cap)

            (config.BASE_DIR / "last_analysis.txt").write_text(result, encoding="utf-8")
            self.events.put(("result", result))
        except Exception as e:
            self.events.put(("error", str(e)))

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status.set(payload)
                elif kind == "result":
                    self.output.insert("end", payload)
                    self.status.set(f"Готово ({datetime.now():%H:%M:%S})")
                    self.button.state(["!disabled"])
                elif kind == "error":
                    self.output.insert("end", f"Помилка: {payload}")
                    self.status.set("Помилка")
                    self.button.state(["!disabled"])
        except queue.Empty:
            pass
        self.after(100, self.poll)


if __name__ == "__main__":
    App().mainloop()
