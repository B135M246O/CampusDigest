from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.jobs import send_article_message
from app.bot.menu import MAIN_MENU_TXT, category_keyboard, source_keyboard


@pytest.mark.asyncio
@pytest.mark.parametrize('image', [None, 'https://university.example.com/photo.jpg'])
async def test_bot_sends_text_without_picture_and_photo_with_short_caption(image):
    context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock(), send_message=AsyncMock()))
    article = SimpleNamespace(id=1, title='A < B', category='Наука', overview='Новый & полезный курс',
                              source='ИТМО', picture_link=image, infographic_links=[], video_preview_link=None)
    await send_article_message(article, 42, context)
    if image:
        context.bot.send_photo.assert_awaited_once()
        message = context.bot.send_photo.call_args.kwargs['caption']
    else:
        context.bot.send_message.assert_awaited_once()
        message = context.bot.send_message.call_args.kwargs['text']
    assert 'A &lt; B' in message
    assert 'Новый &amp; полезный курс' in message


def test_bot_menus_match_university_filters():
    assert 'CampusDigest' in MAIN_MENU_TXT
    assert {'ИТМО', 'НИУ ВШЭ'} <= {b.text for row in source_keyboard.inline_keyboard for b in row}
    assert {'Наука', 'Студентам'} <= {b.text for row in category_keyboard.inline_keyboard for b in row}
