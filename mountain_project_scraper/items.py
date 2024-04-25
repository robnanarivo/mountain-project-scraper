# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class AreaItem(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    description = scrapy.Field()
    comment = scrapy.Field()
    long = scrapy.Field()
    lat = scrapy.Field()
    url = scrapy.Field()
    child_type = scrapy.Field()
    child_ids = scrapy.Field()
    parent_name = scrapy.Field()
    parent_id = scrapy.Field()


class RouteItem(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    grade = scrapy.Field()
    type = scrapy.Field()
    length = scrapy.Field()
    pitch = scrapy.Field()
    commitment_grade = scrapy.Field()
    protection = scrapy.Field()
    user_rating = scrapy.Field()
    description = scrapy.Field()
    comment = scrapy.Field()
    url = scrapy.Field()
    parent_name = scrapy.Field()
    parent_id = scrapy.Field()


class HTMLItem(scrapy.Item):
    html = scrapy.Field()
