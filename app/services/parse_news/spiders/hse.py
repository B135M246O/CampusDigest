from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import scrapy
from scrapy.exceptions import CloseSpider

from app.services.parse_news.items import ArticleItem

MONTHS = {
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'мая': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
}


class HseSpider(scrapy.Spider):
    name = 'hse_spider'
    allowed_domains = ['www.hse.ru']
    start_urls = ['https://www.hse.ru/news/']

    def parse(self, response):
        cards = response.css('.post')
        links = cards.css('h2 a::attr(href)').getall()
        if not links:
            raise CloseSpider('HSE news links not found; check selectors')
        for href in dict.fromkeys(links):
            # У подразделений ВШЭ отдельные шаблоны без полного года публикации.
            if urlparse(response.urljoin(href)).hostname != 'www.hse.ru':
                continue
            yield response.follow(
                href, callback=self.parse_article,
                cb_kwargs={'student_feed': '/news/students/' in response.url},
            )

    def parse_article(self, response, student_feed=False):
        title = response.css('h1.post-title').xpath('normalize-space(.)').get()
        date = response.css('.post_single .post-meta__date')
        paragraphs = response.css('.post_single .post__text p').xpath('normalize-space(.)').getall()
        paragraphs = [text for text in paragraphs if text]
        day = date.css('.post-meta__day::text').get()
        month = date.css('.post-meta__month::text').get()
        year = date.css('.post-meta__year::text').get()
        if not all((title, day, month, year, paragraphs)):
            raise CloseSpider(f'Incomplete HSE article at {response.url}; check selectors')
        published = datetime(int(year), MONTHS[month.strip().lower()[:3]], int(day),
                             tzinfo=timezone(timedelta(hours=3)))
        tags = ' '.join(response.css('.tag-set a::attr(href)').getall())
        category = 'Кампус'
        if student_feed or 'students' in tags or 'studentlife' in tags:
            category = 'Студентам'
        elif 'resanl' in tags or 'science' in tags:
            category = 'Наука'
        elif 'education' in tags or '/edu/' in response.url:
            category = 'Образование'
        image = response.css('meta[property="og:image"]::attr(content)').get()
        yield ArticleItem(
            date=published, category=category, title=title,
            overview=response.css('meta[name="description"]::attr(content)').get(),
            text='\n'.join(paragraphs), link=response.url,
            picture_link=response.urljoin(image) if image else None,
            video_link=response.css('.post__text iframe::attr(src)').get(),
            video_preview_link=None, infographic_links=[], authors=[], source='НИУ ВШЭ',
        )
