# TagFlow

Telegram-бот для генерации идей для TikTok-видео, постов и пулов хэштегов.

## Что умеет

- `🎬 Идея для видео` по теме и стилю
- `📝 Генерация поста` по теме и стилю
- `🏷 Пулы тегов`: создание, просмотр, редактирование, удаление
- `🤖 Сгенерировать теги` и сохранить их в новый пул
- локальный запуск через polling
- деплой на Render через webhook

## Локальный запуск

1. Заполни `.env` по примеру `.env.example`
2. Установи зависимости:

```bash
pip install -r requirements.txt
```

3. Запусти бота:

```bash
python main.py
```

Если `RENDER_EXTERNAL_URL` пустой, бот работает в polling-режиме.

## Render

Проект подготовлен под бесплатный `Render Web Service`.

### Что важно

- На бесплатном Render удобнее запускать Telegram-бота как `Web Service` через webhook, а не как background worker.
- Файловая система Render эфемерная, поэтому `SQLite` в `tagflow.db` не подходит для постоянного хранения между деплоями и рестартами. Для постоянных данных лучше вынести БД наружу.

### Быстрый деплой

1. Загрузи проект в GitHub.
2. В Render выбери `New +` -> `Blueprint`.
3. Подключи репозиторий с этим проектом.
4. Render подхватит `render.yaml`.
5. В переменных окружения Render обязательно задай:

```env
TOKEN_API=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

6. После первого деплоя Render сам выставит публичный URL сервиса. Его значение попадёт в `RENDER_EXTERNAL_URL`, и бот начнёт работать через webhook.

### Режимы запуска

- локально: polling
- на Render с `RENDER_EXTERNAL_URL`: webhook + HTTP health check на `/healthz`

## AI-режим

- `REAL_GENERATION_ENABLED=true` включает реальный Gemini-вызов
- при ошибке провайдера бот мягко откатывается на локальный fallback, чтобы не падать
