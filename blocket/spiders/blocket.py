import json
import logging
import signal
import sqlite3
from datetime import datetime, timedelta
from typing import Any
import scrapy
from urllib.parse import urlparse, parse_qs
import dateparser
from scrapy import Spider, signals
from enum import Enum
from scrapy.crawler import Crawler
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import TCPTimedOutError

from blocket.items import JobItem


class PageType(Enum):
    MAIN_PAGE = "main_page"
    CATEGORY_PAGE = "category_page"
    JOB_PAGE = "job_page"


class BlocketSpider(scrapy.Spider):
    name = 'blocket'

    def __init__(self,crawler: Crawler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super()._set_crawler(crawler)
        bot_name = self.settings.get('BOT_NAME', 'scrapy_project')
        self._logger = logging.getLogger(bot_name)
        self.refresh_mode = crawler.settings.getbool("REFRESH_MODE", False)
        self.logger.info("Start spider")

    @property
    def logger(self):
        return self._logger

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(crawler, *args, **kwargs)
        return spider

    def start_requests(self):
        main_page_url = 'https://jobb.blocket.se/'
        unprocessed_pages = self._get_unprocessed_pages()
        yield scrapy.Request(url=main_page_url,
                             callback=self.parse_main_page,
                             dont_filter=True,
                             meta={"page_type": PageType.MAIN_PAGE.value})

        for page in unprocessed_pages:
            if page[1] == PageType.CATEGORY_PAGE.value:
                yield scrapy.Request(url=page[0], callback=self.parse_category_page, dont_filter=True)
            elif page[1] == PageType.JOB_PAGE.value:
                yield scrapy.Request(url=page[0], callback=self.parse_job_page, dont_filter=True)


    def _get_unprocessed_pages(self):
        connection: sqlite3.Connection = self.crawler.db_connection
        cursor: sqlite3.Cursor = connection.cursor()
        query = '''
        SELECT url, page_type             
        FROM visited_urls
        WHERE status = "in_progress"
        ORDER BY last_processed_date
        '''
        cursor.execute(query)
        records = cursor.fetchall()
        cursor.close()
        return records



    def parse_main_page(self, response, **kwargs: Any) -> Any:
        """
        The function retrieves categories urls from the main page
        """

        category_urls = response.css("li.sc-d56e3ac2-5.sc-2a550f1a-2.brdyEP.jsNiHv a::attr(href)").getall()
        for url in category_urls:
            url = f"{url}&sort=PUBLISHED"
            yield response.follow(
                url,
                callback=self.parse_category_page,
                errback=self.handle_error,
                priority=0,
                dont_filter=True,  # The first page of every category is not checked by the duplicate filter
                meta={"page_type": PageType.CATEGORY_PAGE.value}
            )

    def parse_category_page(self, response, **kwargs: Any) -> Any:
        """
        The function retrieves job links and link to the next category page from the category page
        """

        # Current page number
        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)
        current_page = int(query_params.get("page", ['1'])[0])
        category = query_params.get("filters", ["-"])[0]

        self.logger.info(f"Start parsing category {category} page {current_page} {response.url}")

        job_urls = response.css("div.sc-b071b343-0.eujsyo a")
        for idx, job_url in enumerate(job_urls):
            yield response.follow(
                job_url,
                callback=self.parse_job_page,
                errback=self.handle_error,
                meta={"page_type": PageType.JOB_PAGE.value,
                      "category": category,
                      "page_number": current_page,
                      "link_number": idx + 1, },
                priority=30
            )

        max_page_number = self.settings.getint("MAX_CATEGORY_PAGE_NUMBER")

        if max_page_number and current_page >= max_page_number:
            self.logger.info(f"Max category page number has been reached: {current_page}")
            return

        # Find pages count:
        page_count = response.css('div.sc-9aebc51e-3.eMQydw a:last-of-type::text').get()
        page_count = int(page_count) if page_count else None

        next_page_url = response.css(
            "a.sc-c1be1115-0.heGCdS.sc-539f7386-0.gWJszl.sc-9aebc51e-2.jHuKGp:last-of-type::attr(href)").get()

        request_kwargs = {
            "callback": self.parse_category_page,
            "errback": self.handle_error,
            "priority": 20,
            "meta": {"page_type": PageType.CATEGORY_PAGE.value},
        }

        # In refresh mode, the maximum age of the last job on the page (in days) is compared with
        # REFRESH_DAYS to skip the duplicate filter for the next category page

        if self.refresh_mode:
            days = self.settings.getint("REFRESH_DAYS", 0)
            target_date = datetime.now() - timedelta(days=days)
            published_dates = response.css("p.sc-f047e250-1.gRACBc::text").getall()
            last_date_sw = published_dates[-1] if published_dates else None
            last_date = dateparser.parse(f"{last_date_sw} {datetime.now().year}", languages=['sv'])
            if last_date and last_date >= target_date:
                request_kwargs['dont_filter'] = True  # disable duplicate filter for this request and parse next page again

        self.logger.info(f"Category {category} page {current_page} / {page_count} processed")

        if next_page_url is not None:
            self.logger.info(f"Found new category page {next_page_url}")
            #add next page url to queue
            yield response.follow(next_page_url, **request_kwargs)
        else:
            self.logger.info(f"Next category page not found. Category {category} processed")


    def parse_job_page(self, response) -> Any:
        """
        The function retrieves job data from the job page
        """
        meta = response.meta
        self.logger.info(f"Parsing job {meta.get('link_number')} from {meta.get('category')} page {meta.get('page_number')} {response.url}")

        item = JobItem()
        json_str = response.css('#__NEXT_DATA__::text').get()
        try:
            json_data = json.loads(json_str)
            if json_data:
                job_data = {}
                for k, v in json_data["props"]["pageProps"]["initialApolloState"]["ROOT_QUERY"].items():
                    if isinstance(v, dict) and (ref := v.get("__ref")):
                        job_data = json_data["props"]["pageProps"]["initialApolloState"][ref]
                        break
                if job_data:
                    item['url'] = response.url
                    item['title'] = job_data.get("subject")
                    item['company'] = job_data.get("corpName")
                    item['published_date'] = job_data.get("publishedDate")
                    item['apply_date'] = job_data.get("applyDate")
                    item['location'] = job_data.get("areaName")
                    item['category'] = job_data.get("categoryName")
                    item['job_type'] = job_data.get("employmentName")
                    item['phone'] = job_data.get("phone")
                    item['email'] = job_data.get("email")
                    if self.settings.get('SAVE_JOB_DESCRIPTION'):
                        # item['description'] = job_data.get("bodyHtml") # get with HTML tags from JSON
                        item['description'] = response.css("div.sc-d56e3ac2-5.sc-5fe98a8b-10.brdyEP *::text").getall()

        except json.JSONDecodeError as e:
            self.logger.error(f"Error during loading JSON: {e}, url: {response.url}")
        except KeyError as e:
            self.logger.error(f"Error during parsing JSON with job data: {e}, url: {response.url}")
        if item:
            yield item
        # else:
        # Getting job data from HTML. Some fields can be mixed up in this case
        # item['url'] = response.url
        # item['title'] = response.css("h1::text").get()
        # item['company'] = response.css("a.sc-5fe98a8b-2.iapiPt::text").get()
        # item['published_date'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(4) span::text").get()
        # item['apply_date'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(2) span::text").get()
        # item['location'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(6) a::text").get()
        # item['category'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(8) a::text").getall()
        # item['job_type'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(10) a::text").getall()
        # if self.settings.get('SAVE_JOB_DESCRIPTION'):
        #     item['description'] = response.css("div.sc-d56e3ac2-5.sc-5fe98a8b-10.brdyEP *::text").getall()
        # if item:
        #     yield item

    def handle_error(self, failure):

        if failure.check(TimeoutError, TCPTimedOutError):
            self.logger.warning("Request timed out")
        elif failure.check(HttpError):
            response = failure.value.response
            if response.status == 404:
                self.logger.warning(f"Page not found: {response.url}")
            if response.status == 403 or response.status == 429:
                self.logger.warning(f"!!! May be you are blocked! HTTP Status {response.status} {response.url}")
            else:
                self.logger.warning(f"HTTP error occurred. HTTP Status {response.status} {response.url} ")
        else:
            self.logger.warning("Unknown error occurred")

    def close_spider(self, reason):
        stats = self.crawler.stats
        processed_pages = stats.get_value('response_received_count', 0)
        items_scraped = stats.get_value('item_scraped_count', 0)

        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Processed pages: {processed_pages}")
        self.logger.info(f"Scraped items: {items_scraped}")



