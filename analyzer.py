from google import genai
from google.genai import types

import config
from browser import Capture


def analyze(cap: Capture) -> str:
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    parts = [types.Part.from_bytes(data=shot, mime_type="image/png") for shot in cap.screenshots]
    parts.append(
        f"{config.PROMPT}\n\n"
        f"Дашборд: {cap.title} ({cap.url})\n\n"
        f"Текст дашборду:\n{cap.text}"
    )

    response = client.models.generate_content(model=config.GEMINI_MODEL, contents=parts)
    return response.text or "(Gemini повернув порожню відповідь)"
