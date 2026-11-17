from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.filters.articles import CategoryFilter, SourceFilter

MAIN_MENU_NUM, SOURCE_MENU_NUM, CATEGORY_MENU_NUM, SETTINGS_MENU_NUM = range(4)
MAIN_MENU_TXT = 'CampusDigest — новости вузов и объявления для студентов. Выберите действие:'
SOURCE_MENU_TXT = 'Выберите университет:'
CATEGORY_MENU_TXT = 'Выберите тему университетских новостей:'
SETTINGS_MENU_TXT = 'Выбрано статей для получения: <b>{}</b>'.format
ALL_BTN = 'ВСЕ'


def keyboard_constructor(
    buttons: dict[str, str],
    all_button: bool = False,
    back_button: str = None,
    n_cols: int = 5,
    url: str = None
):
    """Конструктор клавиатур для различных меню."""
    keyboard = []
    for i in range(0, len(buttons), n_cols):
        keyboard.append(
            [
                InlineKeyboardButton(btn, callback_data=clb, url=url)
                for btn, clb in list(buttons.items())[i: i + n_cols]
            ]
        )
    if all_button:
        all_button = [
            InlineKeyboardButton(ALL_BTN, callback_data=ALL_BTN, url=url)
        ]
        keyboard.append(all_button)
    if back_button:
        back_button = [
            InlineKeyboardButton('⬅ Назад', callback_data=back_button)
        ]
        keyboard.append(back_button)
    return InlineKeyboardMarkup(keyboard)


def get_article_url(article_id: int, domain: bool = settings.DOMAIN):
    """Получение ссылки на страницу статьи."""
    url = f'http://{settings.IP}:{settings.PORT}/articles/html/{article_id}'
    if domain:
        url = f'{settings.DOMAIN_NAME}/articles/html/{article_id}'
    return url


def article_keyboard(article_id: int):
    """Клавиатура для сообщения с новостной статьей."""
    url = get_article_url(article_id)
    keyboard = keyboard_constructor({'Читать далее': None}, url=url)
    return keyboard


def pattern(menu):
    return '^' + str(menu) + '$'


main_keyboard = keyboard_constructor(
    {'📰 Новости кампуса': str(SOURCE_MENU_NUM), '⚒️ Настройки': str(SETTINGS_MENU_NUM)}
)
source_keyboard = keyboard_constructor(
    {s.value: s.value for s in SourceFilter if s != 'ВСЕ'},
    all_button=True,
    back_button=str(MAIN_MENU_NUM)
)
category_keyboard = keyboard_constructor(
    {c.value: c.value for c in CategoryFilter if c != 'ВСЕ'},
    all_button=True,
    back_button=str(SOURCE_MENU_NUM),
    n_cols=4
)
settings_keyboard = keyboard_constructor(
    {str(s): str(s) for s in range(1, 11)},
    back_button=str(MAIN_MENU_NUM)
)
