from datetime import datetime, timedelta, timezone

import scrapy
from scrapy.exceptions import CloseSpider

from app.services.parse_news.items import ArticleItem


class ItmoSpider(scrapy.Spider):
    name = 'itmo_spider'
    allowed_domains = ['news.itmo.ru']
    start_urls = ['https://news.itmo.ru/ru/', 'https://news.itmo.ru/ru/education/students/']

    def parse(self, response):
        links = response.css('h3 a[href*="/news/"]::attr(href), h4 a[href*="/news/"]::attr(href)').getall()
        if not links:
            raise CloseSpider('ITMO news links not found; check selectors')
        for href in dict.fromkeys(links):
            yield response.follow(href, callback=self.parse_article)

    def parse_article(self, response):
        title = response.css('h1').xpath('normalize-space(.)').get()
        date = response.css('time::attr(datetime)').get()
        paragraphs = response.css('.js-mediator-article p').xpath('normalize-space(.)').getall()
        paragraphs = [text for text in paragraphs if text]
        if not title or not date or not paragraphs:
            raise CloseSpider('Incomplete ITMO article; check selectors')
        published = datetime.fromisoformat(date)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone(timedelta(hours=3)))
        path = response.url.lower()
        category = 'Кампус'
        if '/students/' in path:
            category = 'Студентам'
        elif '/science/' in path:
            category = 'Наука'
        elif '/education/' in path:
            category = 'Образование'
        image = response.css('meta[property="og:image"]::attr(content)').get()
        yield ArticleItem(
            date=published, category=category, title=title,
            overview=response.css('meta[name="description"]::attr(content)').get(),
            text='\n'.join(paragraphs), link=response.url,
            picture_link=response.urljoin(image) if image else None,
            video_link=response.css('.js-mediator-article iframe::attr(src)').get(),
            video_preview_link=None, infographic_links=[],
            authors=response.css('meta[property="article:author"]::attr(content)').getall(),
            source='ИТМО',
        )
