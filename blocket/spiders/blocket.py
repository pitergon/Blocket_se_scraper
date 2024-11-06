import logging
import signal
from datetime import datetime, timedelta
from typing import Any
import scrapy
from urllib.parse import urlparse, parse_qs
import dateparser
from scrapy import Spider
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.defer import Deferred
from twisted.internet.error import TCPTimedOutError

from blocket.items import JobItem
from blocket.pipelines import JobPipeline


class BlocketSpider(scrapy.Spider):
    name = 'blocket'
    start_urls = ["https://jobb.blocket.se/"]

    #start_urls = ["https://jobb.blocket.se/lediga-jobb?filters=juridik&sort=PUBLISHED"]
    #start_urls = ["https://jobb.blocket.se/lediga-jobb?filters=offentlig-foervaltning&sort=PUBLISHED"]
    #start_urls = ["https://jobb.blocket.se/lediga-jobb?filters=bank-finans-och-foersaekring&sort=PUBLISHED"]
    #https://jobb.blocket.se/lediga-jobb?filters=bank-finans-och-foersaekring&sort=PUBLISHED&page=2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # signal.signal(signal.SIGINT, self.handle_exit)
        # self.company_data_cache = {}

        logging.getLogger('scrapy.dupefilters').setLevel(logging.ERROR)
        self.mode = "continue"  # continue or update
        self.logger.info("Start spider")

    # def start_requests(self):
    #     if self.mode == "continue":
    #         self.logger.info("Running in 'continue' mode.")
    #         # check db for unprocessed url end start from it
    #     elif self.mode == "update":
    #         self.logger.info("Running in 'update' mode.")
    #         # check main page and category pages for update.
    #         # Check max_category_page_numer pages or published_date of jobs
    #     else:
    #         self.logger.info("Running in default mode.")

    def parse(self, response, **kwargs: Any) -> Any:
        """
        The function retrieves categories urls from the main page
        """
        category_urls = response.css("li.sc-d56e3ac2-5.sc-2a550f1a-2.brdyEP.jsNiHv a::attr(href)").getall()

        for url in category_urls:
            url = f"{url}&sort=PUBLISHED"
            yield response.follow(
                url,
                # meta={"parent_url": response.url},
                callback=self.parse_category_page,
                errback=self.handle_error,
                priority=0,
                dont_filter=self.mode == "update"
            )

    def parse_category_page(self, response, **kwargs: Any) -> Any:
        """
        The function retrieves the job data if necessary, job link and link to the next category page from the category page
        """
        # Current page number
        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)
        current_page = int(query_params.get("page", ['1'])[0])
        category = query_params.get("filters", ["-"])[0]

        # self.logger.info(f"Start parsing category {category} page {current_page} {response.url}")

        job_urls = response.css("div.sc-b071b343-0.eujsyo a")
        for idx, job_url in enumerate(job_urls):
            yield response.follow(
                job_url,
                callback=self.parse_job_page,
                errback=self.handle_error,
                meta={"category": category, "page_number": current_page,
                      #"parent_url": response.url,
                      "link_number": idx + 1,},
                priority=30
            )

        max_page_number = self.settings.getint("MAX_CATEGORY_PAGE_NUMBER", 0)

        if max_page_number and current_page >= max_page_number:
            self.logger.info(f"Max category page number has been reached: {current_page}")
            return

        # Find pages count:
        # page_count = response.css('div.sc-9aebc51e-3.eMQydw a:last-of-type::text').get()
        # page_count = int(page_count) if page_count else None

        next_page_url = response.css(
            "a.sc-c1be1115-0.heGCdS.sc-539f7386-0.gWJszl.sc-9aebc51e-2.jHuKGp::attr(href)").get()

        request_kwargs = {
            'callback': self.parse_category_page,
            'errback': self.handle_error,
            'priority': 20,
        }

        if self.mode == 'update':
            days = self.settings.getint("REFRESH_DAYS", 0)
            target_date = datetime.now() - timedelta(days=days)
            published_dates = response.css("p.sc-f047e250-1.gRACBc::text").getall()
            last_date_sw = published_dates[-1] if published_dates else None
            last_date = dateparser.parse(f"{last_date_sw} {datetime.now().year}", languages=['sv'])
            if last_date and last_date >= target_date:
                request_kwargs['dont_filter'] = True # disable dupe filter for this request and parse this page again

        if next_page_url is not None:
            # self.logger.info(f"Found new category page {next_page_url}")
            # add next page url to queue
            yield response.follow(next_page_url, **request_kwargs)
        # else:
        # self.logger.info(f"New category page not found")
        # self.logger.info(f"Finish parsing category page {current_page} / {page_count} ")

    def parse_job_page(self, response) -> Any:
        """
        The function retrieves job data from the job page
        """
        # meta = response.meta
        # self.logger.info(f"Parsing job {meta.get('link_number')} from {meta.get('category')} page {meta.get('page_number')} {response.url}")

        item = JobItem()

        item['url'] = response.url
        item['title'] = response.css("h1::text").get()
        item['company'] = response.css("a.sc-5fe98a8b-2.iapiPt::text").get()
        item['published_date'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(4) span::text").get()
        item['apply_date'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(2) span::text").get()
        item['location'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(6) a::text").get()
        item['category'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(8) a::text").getall()
        item['job_type'] = response.css("div.sc-dd9f06d6-2.dVNNPW:nth-of-type(10) a::text").getall()
        if self.settings.get('SAVE_JOB_DESCRIPTION'):
            item['description'] = response.css("div.sc-d56e3ac2-5.sc-5fe98a8b-10.brdyEP *::text").getall()
        # item["company_job_count"] = None # Can't retrieve without js from company page
        yield item


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

    # def handle_exit(self, signum, frame):
    #     self.crawler.engine.close_spider(self, reason="Interrupted by user")
