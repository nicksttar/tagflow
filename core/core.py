from __future__ import annotations

from config import GEMINI_API_KEY, REAL_GENERATION_ENABLED
from core.prompts import build_post_prompt, build_tags_prompt, build_video_idea_prompt


def _cyrillic_score(text: str) -> int:
    return sum(1 for char in text if "А" <= char <= "я" or char in "Ёё")


def _repair_mojibake(text: str) -> str:
    candidates = [text]

    for source_encoding, target_encoding in (("latin1", "cp1251"), ("latin1", "utf-8"), ("cp1252", "utf-8")):
        try:
            repaired = text.encode(source_encoding).decode(target_encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        candidates.append(repaired)

    return max(candidates, key=_cyrillic_score)


def _normalize_ai_text(text: str | None) -> str | None:
    if not text:
        return text

    normalized = _repair_mojibake(text).replace("\r\n", "\n").strip()
    normalized = _sanitize_for_telegram_html(normalized)
    return normalized


def _sanitize_for_telegram_html(text: str) -> str:
    replacements = {
        "```html": "",
        "```": "",
        "<p>": "",
        "</p>": "\n\n",
        "<h3>": "<b>",
        "</h3>": "</b>\n\n",
        "<strong>": "<b>",
        "</strong>": "</b>",
        "<br>": "\n",
        "<br/>": "\n",
        "<br />": "\n",
        "<ul>": "",
        "</ul>": "\n",
        "<ol>": "",
        "</ol>": "\n",
        "<li>": "• ",
        "</li>": "\n",
        "<code>": "",
        "</code>": "",
        "<u>": "",
        "</u>": "",
    }

    sanitized = text
    for old, new in replacements.items():
        sanitized = sanitized.replace(old, new)

    while "\n\n\n" in sanitized:
        sanitized = sanitized.replace("\n\n\n", "\n\n")

    return sanitized.strip()


def _run_real_generation(prompt: str) -> str | None:
    if not (REAL_GENERATION_ENABLED and GEMINI_API_KEY):
        return None

    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return _normalize_ai_text(response.text)
    except Exception:
        return None


def generate_video_idea(topic: str, style: str, tags_name: str | None = None, tags_content: str | None = None) -> str:
    tags_block = f"{tags_name}: {tags_content}" if tags_name and tags_content else "не использовать"
    prompt = build_video_idea_prompt(topic, style, tags_block)
    result = _run_real_generation(prompt)
    if result:
        return result
    return _mock_video_idea(topic, style, tags_name, tags_content)


def generate_post_text(topic: str, style: str, tags_name: str | None = None, tags_content: str | None = None) -> str:
    tags_block = f"{tags_name}: {tags_content}" if tags_name and tags_content else "не использовать"
    prompt = build_post_prompt(topic, style, tags_block)
    result = _run_real_generation(prompt)
    if result:
        return result
    return _mock_post_text(topic, style, tags_name, tags_content)


def generate_tags(topic: str) -> str:
    prompt = build_tags_prompt(topic)
    result = _run_real_generation(prompt)
    if result:
        return result
    return _mock_tags(topic)


def _mock_video_idea(topic: str, style: str, tags_name: str | None, tags_content: str | None) -> str:
    tags_line = (
        f"\n<b>🏷 Пул тегов:</b> {tags_name}\n<i>{tags_content}</i>"
        if tags_name and tags_content
        else "\n<b>🏷 Пул тегов:</b> не выбран"
    )
    hashtags = tags_content if tags_content else _mock_tags(topic)

    return (
        f"<b>🎬 Идея для видео</b>\n\n"
        f"<b>Тема:</b> {topic}\n"
        f"<b>Стиль:</b> {style}"
        f"{tags_line}\n\n"
        f"<b>⚡ Hook:</b>\n"
        f"1. Ты тоже делаешь это неправильно?\n"
        f"2. Вот что реально работает в теме «{topic}».\n"
        f"3. Сохрани, чтобы не потерять эту идею.\n\n"
        f"<b>🎥 Сценарий:</b>\n"
        f"<i>Начало:</i> задай цепляющий вопрос.\n"
        f"<i>Середина:</i> покажи 2-3 быстрых наблюдения или шага.\n"
        f"<i>Финал:</i> закончи коротким призывом подписаться или написать в комменты.\n\n"
        f"<b>✨ Визуал:</b>\n"
        f"Крупные планы, быстрые склейки, субтитры на экране и живой темп в стиле «{style}».\n\n"
        f"<b>🏷 Хэштеги:</b>\n{hashtags}"
    )


def _mock_post_text(topic: str, style: str, tags_name: str | None, tags_content: str | None) -> str:
    hashtags = tags_content if tags_content else _mock_tags(topic)
    pool_note = f"С опорой на пул «{tags_name}»." if tags_name and tags_content else "Без подключенного пула тегов."

    return (
        f"<b>📝 Готовый пост</b>\n\n"
        f"<b>{topic}</b>\n"
        f"<i>Стиль: {style}</i>\n\n"
        f"Если хочется подать тему свежо и без воды, начни с одного сильного инсайта, "
        f"потом коротко раскрой пользу для аудитории и заверши понятным действием. "
        f"{pool_note}\n\n"
        f"<b>💡 Идея подачи:</b> короткие абзацы, живой тон, один сильный тезис в начале.\n"
        f"<b>👉 CTA:</b> предложи читателю сохранить пост или поделиться своим опытом.\n\n"
        f"<b>🏷 Хэштеги:</b>\n{hashtags}"
    )


def _mock_tags(topic: str) -> str:
    cleaned = "".join(symbol for symbol in topic.lower() if symbol.isalnum() or symbol.isspace()).strip()
    words = [word for word in cleaned.split() if len(word) > 2]
    base = words[:3] if words else ["trend", "viral", "content"]
    generated = [f"#{word}" for word in base]

    fallback = ["#tiktoktips", "#viralvideo", "#contentidea", "#trend2026", "#fyp"]
    for tag in fallback:
        if len(generated) >= 5:
            break
        if tag not in generated:
            generated.append(tag)

    return " ".join(generated[:5])
