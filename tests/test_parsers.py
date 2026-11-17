from pathlib import Path

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse

from app.filters.articles import CategoryFilter, SourceFilter
from app.services.parse_news.spiders.hse import HseSpider
from app.services.parse_news.spiders.itmo import ItmoSpider

FIXTURES = Path(__file__).parent / 'fixtures'


def response(name, url):
    return HtmlResponse(url, body=(FIXTURES / name).read_bytes(), encoding='utf-8')


@pytest.mark.parametrize('spider,fixture,url', [
    (ItmoSpider, 'itmo_index.html', 'https://news.itmo.ru/ru/'),
    (HseSpider, 'hse_index.html', 'https://www.hse.ru/news/'),
])
def test_index_follows_real_article_links(spider, fixture, url):
    requests = list(spider().parse(response(fixture, url)))
    assert len(requests) == 2
    assert all('/news/' in request.url for request in requests)
    assert all(request.callback.__name__ == 'parse_article' for request in requests)


def test_itmo_extracts_article_date_author_and_science_category():
    item, = ItmoSpider().parse_article(response(
        'itmo_article.html', 'https://news.itmo.ru/ru/it/science/news/15078'))
    assert '500' in item['title']
    assert item['date'].isoformat() == '2026-10-21T16:03:41+03:00'
    assert item['source'] == SourceFilter.ITMO
    assert item['category'] == CategoryFilter.SCIENCE
    assert item['text'] and item['authors']
    assert item['picture_link'].startswith('https://news.itmo.ru/')


def test_itmo_student_section_is_available_to_filter():
    item, = ItmoSpider().parse_article(response(
        'itmo_article.html', 'https://news.itmo.ru/ru/education/students/news/15078'))
    assert item['category'] == CategoryFilter.STUDENTS


def test_hse_extracts_article_and_moscow_date():
    item, = HseSpider().parse_article(response(
        'hse_article.html', 'https://www.hse.ru/news/edu/1218814495.html'))
    assert 'executive' in item['title']
    assert item['date'].isoformat() == '2026-11-16T00:00:00+03:00'
    assert item['category'] == CategoryFilter.EDUCATION
    assert item['source'] == SourceFilter.HSE
    assert item['text'] and item['overview']


def test_student_feed_marks_hse_announcements():
    item, = HseSpider().parse_article(response(
        'hse_article.html', 'https://www.hse.ru/news/edu/1218814495.html'), student_feed=True)
    assert item['category'] == CategoryFilter.STUDENTS


def test_hse_does_not_follow_departments_with_different_templates():
    html = b'<div class="post"><h2><a href="https://geography.hse.ru/news/1.html">Department</a></h2></div>'
    page = HtmlResponse('https://www.hse.ru/news/', body=html)
    assert list(HseSpider().parse(page)) == []


@pytest.mark.parametrize('spider', [ItmoSpider, HseSpider])
def test_changed_html_is_an_error(spider):
    empty = HtmlResponse('https://example.org/', body=b'<html></html>')
    with pytest.raises(CloseSpider):
        list(spider().parse(empty))
    with pytest.raises(CloseSpider):
        list(spider().parse_article(empty))
