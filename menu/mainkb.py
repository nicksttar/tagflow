from __future__ import annotations

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


STYLE_MAP = {
    "style:hard": "😎 Дерзкий",
    "style:expert": "🧠 Экспертный",
    "style:fun": "😂 Лёгкий",
    "style:viral": "🔥 Вирусный",
}


def new_kb():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🎬 Идея для видео", callback_data="video:create"),
        InlineKeyboardButton(text="📝 Генерация поста", callback_data="post:create"),
        InlineKeyboardButton(text="🏷 Пулы тегов", callback_data="tags:menu"),
    )
    builder.adjust(1)
    return builder.as_markup()


def style_kb(mode: str):
    builder = InlineKeyboardBuilder()
    for callback_data, title in STYLE_MAP.items():
        builder.add(InlineKeyboardButton(text=title, callback_data=f"{mode}:{callback_data}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back:main"))
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def back_kb():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back:main"))
    return builder.as_markup()


def tags_pull_kb():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Создать пул", callback_data="pool:create"),
        InlineKeyboardButton(text="🤖 Сгенерировать теги", callback_data="pool:generate_tags"),
        InlineKeyboardButton(text="📚 Мои пулы", callback_data="pool:list"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back:main"),
    )
    builder.adjust(1)
    return builder.as_markup()


def your_pull_kb(data):
    builder = InlineKeyboardBuilder()
    for item in data:
        builder.add(
            InlineKeyboardButton(
                text=f"📦 {item['tags_name']}",
                callback_data=f"pool:view:{item['id']}",
            )
        )
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="tags:menu"))
    builder.adjust(1)
    return builder.as_markup()


def one_pull_kb(pool_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🎬 Использовать для идеи", callback_data=f"pool:use_video:{pool_id}"),
        InlineKeyboardButton(text="📝 Использовать для поста", callback_data=f"pool:use_post:{pool_id}"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"pool:edit:{pool_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"pool:delete:{pool_id}"),
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="pool:list"),
    )
    builder.adjust(1)
    return builder.as_markup()


def generated_tags_kb():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💾 Сохранить в новый пул", callback_data="generated_tags:save"),
        InlineKeyboardButton(text="🔙 К пулам тегов", callback_data="tags:menu"),
    )
    builder.adjust(1)
    return builder.as_markup()
