# CampusDigest

Агрегатор публичных новостей университетов и объявлений для студентов.
Scrapy-пауки собирают публикации ИТМО и НИУ ВШЭ в PostgreSQL; FastAPI выдаёт
подборки, а Telegram-бот позволяет выбрать вуз, тему и количество новостей.
Полученные записи помечаются прочитанными и не повторяются в следующей подборке.

Автор адаптации и доработок — Рябуха Олег.

## Возможности

- Регистрация, JWT-аутентификация, управление своим профилем и лимитом подборки.
- Фильтры «ИТМО», «НИУ ВШЭ», «ВСЕ» и темы «Наука», «Образование», «Студентам», «Кампус».
- Сбор новостей вручную или по расписанию, исключение дублей по ссылке.
- Очистка публикаций старше заданного числа дней, управление доступно суперпользователю.
- HTML-страница публикации с указанием источника; опциональный Telegram Instant View.
- Telegram `/start`, выбор вуза и темы, настройки количества записей, polling и webhook.

Python 3.11, FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, Scrapy и python-telegram-bot 20.
Внутренние имена `Article`, `/articles/`, `/db_interact/` сохранены: новости остаются статьями.
Поле `date` в API содержит ISO 8601 с часовым поясом вместо ручного сдвига даты.

## Локальный запуск

PowerShell из каталога проекта:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

В `.env` задайте свой пароль PostgreSQL (`POSTGRES_PASSWORD`) и случайный `SECRET`.
Для создания администратора раскомментируйте и заполните
`FIRST_SUPERUSER_EMAIL` и `FIRST_SUPERUSER_PASSWORD`.
База PostgreSQL должна быть доступна на `DB_HOST:DB_PORT`; можно запустить её через Docker:

```powershell
docker compose --env-file .env -f infra/docker-compose.local.yml up -d campus_db
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe run.py
```

API: http://127.0.0.1:8006/docs (Swagger), http://127.0.0.1:8006/redoc.
В Linux/macOS используйте `python3.11`, `.venv/bin/python`.

Для запуска API вместе с БД в контейнерах:

```powershell
docker compose --env-file .env -f infra/docker-compose.local.yml --profile app up --build
```

Все образы приложения собираются локально; автоматической публикации и SSH-деплоя нет.

## Источники и управление

Источники: [ИТМО](https://news.itmo.ru/ru/),
[раздел ИТМО для студентов](https://news.itmo.ru/ru/education/students/),
[НИУ ВШЭ](https://www.hse.ru/news/).
Используются только публичные страницы; robots.txt соблюдается, запросы ограничены.
Для ВШЭ обрабатываются статьи основного портала `www.hse.ru`: отдельные сайты
факультетов используют другой шаблон и не входят в обход.

В Swagger зарегистрируйтесь через `POST /auth/register`, войдите через
`POST /auth/jwt/login` (`username` — email, `password`), нажмите Authorize.
Обычный пользователь получает непрочитанные новости:

```http
GET /articles/?source=ИТМО&category_filter=Наука
Authorization: Bearer <access_token>
```

Администратор запускает парсеры через `POST /db_interact/`, очищает старые записи
через `DELETE /db_interact/?days=30`, проверяет количество через `GET /articles/count`.
HTML-страница: `GET /articles/html/{id}`.
Документация схем и всех маршрутов формируется самим FastAPI в `/docs`.

Сбор по расписанию включается через `ENABLE_SCHEDULER=true`, частота —
`PARSER_FREQUENCY` минут; ежедневная очистка выполняется в полночь серверного времени.
По умолчанию расписание выключено, чтобы первый запуск не обращался к внешним сайтам.

## Telegram

В `.env` задайте полученный у BotFather `BOT_TOKEN` и `BOT_ENABLED=true`.
Для локального запуска используйте `WEBHOOK=false` (polling).
Ссылка «Читать далее» должна быть доступна устройству с Telegram:
укажите внешний адрес сервера в `IP` или `DOMAIN=true` и `DOMAIN_NAME=https://ваш-домен/`.
Для webhook нужен публичный HTTPS-адрес, для Instant View — собственный `RHASH`
и `INSTANT_VIEW=true`. При пустом токене API запускается с `BOT_ENABLED=false`.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

`tests/fixtures/` содержит небольшие реальные HTML-фрагменты ИТМО и НИУ ВШЭ,
сохранённые 17 ноября 2026 года; parser-тесты работают без сети.
API и бизнес-логика проверяются в изолированной SQLite без изменения основной PostgreSQL.
Исторические миграции используют PostgreSQL; SQLite для их применения не подходит.
Результаты live-проверок и ограничения перечислены в `REVIEW.md`.

## Лицензия

MIT License. Условия использования приведены в файле `LICENSE`.
