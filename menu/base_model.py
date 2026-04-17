from __future__ import annotations

from aiogram import F, Router
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.core import generate_post_text, generate_tags, generate_video_idea
from data.database import Database
from data.texts import (
    GENERATED_PULL_NAME_TEXT,
    POST_STYLE_TEXT,
    POST_TOPIC_TEXT,
    PULL_EDIT_TEXT,
    PULL_NAME_TEXT,
    PULL_TAGS_TEXT,
    PULLS_MENU_TEXT,
    TAG_GENERATION_TOPIC_TEXT,
    VIDEO_STYLE_TEXT,
    VIDEO_TOPIC_TEXT,
    WELCOME_TEXT,
)
from menu.mainkb import (
    STYLE_MAP,
    back_kb,
    generated_tags_kb,
    new_kb,
    one_pull_kb,
    style_kb,
    tags_pull_kb,
    your_pull_kb,
)
from utils.states import Form


router = Router()
db = Database()


def _normalize_tags(raw_tags: str) -> str:
    parts = [part.strip() for part in raw_tags.replace(",", " ").split() if part.strip()]
    normalized = []
    for part in parts:
        normalized.append(part if part.startswith("#") else f"#{part}")
    return " ".join(dict.fromkeys(normalized))


async def _delete_message_safe(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def _cleanup_temp_messages(state: FSMContext, chat_id: int, bot) -> None:
    data = await state.get_data()
    message_ids = data.get("temp_bot_message_ids", [])
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            continue
    await state.update_data(temp_bot_message_ids=[], screen_message_id=None)


async def _send_temp_message(state: FSMContext, source: Message | CallbackQuery, text: str, **kwargs) -> Message:
    if isinstance(source, Message):
        sent_message = await source.answer(text, **kwargs)
    else:
        sent_message = await source.message.answer(text, **kwargs)

    data = await state.get_data()
    temp_ids = data.get("temp_bot_message_ids", [])
    temp_ids.append(sent_message.message_id)
    await state.update_data(temp_bot_message_ids=temp_ids)
    return sent_message


async def _render_screen(state: FSMContext, source: Message | CallbackQuery, text: str, **kwargs) -> None:
    if isinstance(source, Message):
        chat_id = source.chat.id
        bot = source.bot
    else:
        chat_id = source.message.chat.id
        bot = source.bot

    data = await state.get_data()
    screen_message_id = data.get("screen_message_id")

    if screen_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=screen_message_id,
                text=text,
                **kwargs,
            )
            return
        except Exception:
            pass

    sent_message = await _send_temp_message(state, source, text, **kwargs)
    await state.update_data(screen_message_id=sent_message.message_id)


async def _show_main_menu(target: Message | CallbackQuery, state: FSMContext) -> None:
    if isinstance(target, Message):
        await _cleanup_temp_messages(state, target.chat.id, target.bot)
        await state.clear()
        await _render_screen(state, target, WELCOME_TEXT, reply_markup=new_kb())
    else:
        await _cleanup_temp_messages(state, target.message.chat.id, target.bot)
        await state.clear()
        await _render_screen(state, target, WELCOME_TEXT, reply_markup=new_kb())
        await target.answer()


async def _send_video_result(callback: CallbackQuery, state: FSMContext, style_key: str) -> None:
    data = await state.get_data()
    topic = data.get("video_topic")
    style = STYLE_MAP[style_key]
    tags_name = data.get("selected_pool_name")
    tags_content = data.get("selected_pool_tags")

    result = generate_video_idea(topic, style, tags_name=tags_name, tags_content=tags_content)
    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await _delete_message_safe(callback.message)
    await db.save_post(
        user_id=callback.from_user.id,
        topic=topic,
        style=f"video:{style}",
        content=result,
        tags_name=tags_name,
        tags_content=tags_content,
    )
    await callback.message.answer(result, parse_mode="HTML", reply_markup=back_kb())
    await state.clear()
    await callback.answer("Идея готова ✨")


async def _send_post_result(callback: CallbackQuery, state: FSMContext, style_key: str) -> None:
    data = await state.get_data()
    topic = data.get("post_topic")
    style = STYLE_MAP[style_key]
    tags_name = data.get("selected_pool_name")
    tags_content = data.get("selected_pool_tags")

    result = generate_post_text(topic, style, tags_name=tags_name, tags_content=tags_content)
    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await _delete_message_safe(callback.message)
    await db.save_post(
        user_id=callback.from_user.id,
        topic=topic,
        style=f"post:{style}",
        content=result,
        tags_name=tags_name,
        tags_content=tags_content,
    )
    await callback.message.answer(result, parse_mode="HTML", reply_markup=back_kb())
    await state.clear()
    await callback.answer("Пост готов 📝")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await _show_main_menu(message, state)


@router.callback_query(F.data == "back:main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await _show_main_menu(callback, state)


@router.callback_query(F.data == "video:create")
async def video_create(callback: CallbackQuery, state: FSMContext):
    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await state.clear()
    await state.set_state(Form.video_topic)
    await _render_screen(state, callback, VIDEO_TOPIC_TEXT)
    await callback.answer()


@router.message(Form.video_topic)
async def video_topic(message: Message, state: FSMContext):
    topic = (message.text or "").strip()
    if not topic:
        await message.answer("⚠️ Тема не должна быть пустой. Напиши, о чём будет видео.")
        return

    await _cleanup_temp_messages(state, message.chat.id, message.bot)
    await state.update_data(video_topic=topic)
    await state.set_state(Form.video_style)
    await _render_screen(state, message, VIDEO_STYLE_TEXT, reply_markup=style_kb("video"))


@router.callback_query(Form.video_style, F.data.startswith("video:style:"))
async def video_style(callback: CallbackQuery, state: FSMContext):
    style_key = callback.data.replace("video:", "", 1)
    if style_key not in STYLE_MAP:
        await callback.answer()
        return
    await _send_video_result(callback, state, style_key)


@router.callback_query(F.data == "post:create")
async def post_create(callback: CallbackQuery, state: FSMContext):
    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await state.clear()
    await state.set_state(Form.post_topic)
    await _render_screen(state, callback, POST_TOPIC_TEXT)
    await callback.answer()


@router.message(Form.post_topic)
async def post_topic(message: Message, state: FSMContext):
    topic = (message.text or "").strip()
    if not topic:
        await message.answer("⚠️ Тема не должна быть пустой. Напиши, какой пост нужен.")
        return

    await _cleanup_temp_messages(state, message.chat.id, message.bot)
    await state.update_data(post_topic=topic)
    await state.set_state(Form.post_style)
    await _render_screen(state, message, POST_STYLE_TEXT, reply_markup=style_kb("post"))


@router.callback_query(Form.post_style, F.data.startswith("post:style:"))
async def post_style(callback: CallbackQuery, state: FSMContext):
    style_key = callback.data.replace("post:", "", 1)
    if style_key not in STYLE_MAP:
        await callback.answer()
        return
    await _send_post_result(callback, state, style_key)


@router.callback_query(F.data == "tags:menu")
async def tags_menu(callback: CallbackQuery):
    await callback.message.edit_text(PULLS_MENU_TEXT, reply_markup=tags_pull_kb())
    await callback.answer()


@router.callback_query(F.data == "pool:generate_tags")
async def pool_generate_tags(callback: CallbackQuery, state: FSMContext):
    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await state.clear()
    await state.set_state(Form.tag_topic)
    await _render_screen(state, callback, TAG_GENERATION_TOPIC_TEXT)
    await callback.answer()


@router.message(Form.tag_topic)
async def tag_topic(message: Message, state: FSMContext):
    topic = (message.text or "").strip()
    if not topic:
        await message.answer("⚠️ Напиши тему, для которой нужно подобрать теги.")
        return

    await _cleanup_temp_messages(state, message.chat.id, message.bot)
    tags = _normalize_tags(generate_tags(topic))
    await state.update_data(generated_tags_topic=topic, generated_tags_value=tags)
    await _render_screen(
        state,
        message,
        f"<b>🏷 Теги для темы:</b> {topic}\n\n{tags}\n\n"
        f"Если хочешь, я могу сразу сохранить их как новый пул 👇",
        parse_mode="HTML",
        reply_markup=generated_tags_kb(),
    )


@router.callback_query(F.data == "generated_tags:save")
async def generated_tags_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("generated_tags_value"):
        await callback.message.answer("⚠️ Сначала нужно сгенерировать теги.")
        await callback.answer()
        return

    await state.set_state(Form.generated_pull_name)
    await _render_screen(state, callback, GENERATED_PULL_NAME_TEXT)
    await callback.answer()


@router.message(Form.generated_pull_name)
async def generated_pull_name(message: Message, state: FSMContext):
    pool_name = (message.text or "").strip()
    if not pool_name:
        await message.answer("⚠️ Название пула не должно быть пустым.")
        return

    data = await state.get_data()
    tags = data.get("generated_tags_value")
    topic = data.get("generated_tags_topic")

    if not tags:
        await message.answer("⚠️ Не нашёл сгенерированные теги. Сгенерируй их ещё раз.")
        await state.clear()
        return

    await db.add_tag_pool(message.from_user.id, pool_name, tags)
    await message.answer(
        f'✅ Пул "<b>{pool_name}</b>" сохранён.\n\n<b>Тема:</b> {topic}\n<b>Теги:</b>\n{tags}',
        parse_mode="HTML",
        reply_markup=back_kb(),
    )
    await state.clear()


@router.callback_query(F.data == "pool:create")
async def create_pull(callback: CallbackQuery, state: FSMContext):
    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await state.clear()
    await state.set_state(Form.pull_name)
    await _render_screen(state, callback, PULL_NAME_TEXT)
    await callback.answer()


@router.message(Form.pull_name)
async def pull_name(message: Message, state: FSMContext):
    pool_name = (message.text or "").strip()
    if not pool_name:
        await message.answer("⚠️ Название пула не должно быть пустым.")
        return

    await _cleanup_temp_messages(state, message.chat.id, message.bot)
    await state.update_data(pull_name=pool_name)
    await state.set_state(Form.pull_tags)
    await _render_screen(state, message, PULL_TAGS_TEXT)


@router.message(Form.pull_tags)
async def pull_tags(message: Message, state: FSMContext):
    raw_tags = (message.text or "").strip()
    normalized_tags = _normalize_tags(raw_tags)
    if not normalized_tags:
        await message.answer("⚠️ Не вижу тегов. Отправь хотя бы один хэштег.")
        return

    await _cleanup_temp_messages(state, message.chat.id, message.bot)
    data = await state.get_data()
    pool_name = data.get("pull_name")
    await db.add_tag_pool(message.from_user.id, pool_name, normalized_tags)

    await message.answer(
        f'✅ Пул "<b>{pool_name}</b>" сохранён.\n\n{normalized_tags}',
        parse_mode="HTML",
        reply_markup=back_kb(),
    )
    await state.clear()


@router.callback_query(F.data == "pool:list")
async def my_pulls(callback: CallbackQuery):
    data = await db.show_user_data(callback.from_user.id)
    if not data:
        await callback.message.edit_text("📭 У тебя пока нет сохранённых пулов.", reply_markup=tags_pull_kb())
        await callback.answer()
        return

    await callback.message.edit_text("📚 Твои пулы тегов:", reply_markup=your_pull_kb(data))
    await callback.answer()


@router.callback_query(F.data.startswith("pool:view:"))
async def one_pull(callback: CallbackQuery):
    pool_id = int(callback.data.split(":")[2])
    pool = await db.get_user_pool(pool_id, callback.from_user.id)

    if not pool:
        await callback.message.answer("⚠️ Пул не найден или недоступен.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"<b>📦 {pool['tags_name']}</b>\n\n{pool['tags_content']}",
        parse_mode="HTML",
        reply_markup=one_pull_kb(pool_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pool:use_video:"))
async def use_pull_for_video(callback: CallbackQuery, state: FSMContext):
    pool_id = int(callback.data.split(":")[2])
    pool = await db.get_user_pool(pool_id, callback.from_user.id)

    if not pool:
        await callback.message.answer("⚠️ Не удалось применить пул.")
        await callback.answer()
        return

    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await state.clear()
    await state.update_data(
        selected_pool_id=pool["id"],
        selected_pool_name=pool["tags_name"],
        selected_pool_tags=pool["tags_content"],
    )
    await state.set_state(Form.video_topic)
    await _render_screen(
        state,
        callback,
        f'🎬 Пул "<b>{pool["tags_name"]}</b>" подключён.\nТеперь напиши тему для идеи видео.',
        parse_mode="HTML",
    )
    await callback.answer("Пул подключён")


@router.callback_query(F.data.startswith("pool:use_post:"))
async def use_pull_for_post(callback: CallbackQuery, state: FSMContext):
    pool_id = int(callback.data.split(":")[2])
    pool = await db.get_user_pool(pool_id, callback.from_user.id)

    if not pool:
        await callback.message.answer("⚠️ Не удалось применить пул.")
        await callback.answer()
        return

    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await state.clear()
    await state.update_data(
        selected_pool_id=pool["id"],
        selected_pool_name=pool["tags_name"],
        selected_pool_tags=pool["tags_content"],
    )
    await state.set_state(Form.post_topic)
    await _render_screen(
        state,
        callback,
        f'📝 Пул "<b>{pool["tags_name"]}</b>" подключён.\nТеперь напиши тему для поста.',
        parse_mode="HTML",
    )
    await callback.answer("Пул подключён")


@router.callback_query(F.data.startswith("pool:edit:"))
async def edit_pull(callback: CallbackQuery, state: FSMContext):
    pool_id = int(callback.data.split(":")[2])
    pool = await db.get_user_pool(pool_id, callback.from_user.id)

    if not pool:
        await callback.message.answer("⚠️ Не удалось открыть пул для редактирования.")
        await callback.answer()
        return

    await _cleanup_temp_messages(state, callback.message.chat.id, callback.bot)
    await state.clear()
    await state.update_data(edit_pool_id=pool["id"])
    await state.set_state(Form.pull_edit_name)
    await _render_screen(
        state,
        callback,
        f"<b>📦 {pool['tags_name']}</b>\n\nТекущие теги:\n{pool['tags_content']}\n\n{PULL_EDIT_TEXT}",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Form.pull_edit_name)
async def pull_edit_name(message: Message, state: FSMContext):
    data = await state.get_data()
    pool_id = data.get("edit_pool_id")
    normalized_tags = _normalize_tags((message.text or "").strip())

    if not normalized_tags:
        await message.answer("⚠️ Не вижу тегов. Отправь обновлённый список ещё раз.")
        return

    updated = await db.replace_pack(pool_id, message.from_user.id, normalized_tags)
    if not updated:
        await message.answer("⚠️ Не удалось обновить пул.")
        await state.clear()
        return

    await message.answer(f"✅ Пул обновлён.\n\n{normalized_tags}", reply_markup=back_kb())
    await state.clear()


@router.callback_query(F.data.startswith("pool:delete:"))
async def delete_pull(callback: CallbackQuery):
    pool_id = int(callback.data.split(":")[2])
    deleted = await db.delete_pack_by_id(pool_id, callback.from_user.id)

    if not deleted:
        await callback.message.answer("⚠️ Пул не найден или уже удалён.")
        await callback.answer()
        return

    await callback.message.answer("🗑 Пул удалён.", reply_markup=back_kb())
    await callback.answer()
