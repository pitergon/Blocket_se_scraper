# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class JobItem(scrapy.Item):
    # define the fields for your item here like:

    url = scrapy.Field()
    title = scrapy.Field()
    company = scrapy.Field()
    published_date = scrapy.Field()
    apply_date = scrapy.Field()
    location = scrapy.Field()
    category = scrapy.Field()
    job_type = scrapy.Field()
    description = scrapy.Field()
    processed_date = scrapy.Field()
    phone = scrapy.Field()
    email = scrapy.Field()
    additional_contacts = scrapy.Field()


    def __bool__(self):
        return bool(self.get('url') and self.get('title'))