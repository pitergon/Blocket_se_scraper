# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import sqlite3
from datetime import datetime
from logging import Logger
from typing import Optional

from scrapy.http import Response
from scrapy.utils.request import request_fingerprint
from twisted.internet import defer
import scrapy
from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class BlocketSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.
    def __init__(self, crawler):
        self.lock = defer.DeferredLock()
        self.children_request_counts = {}  # dict
        self.connection: Optional[sqlite3.Connection] = crawler.db_connection
        self.logger: Optional[Logger] = None

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls(crawler)
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        """Отмечает URL как находящийся в обработке."""
        url = response.url
        fp = request_fingerprint(response.request)
        self._mark_url_in_progress(fp, url)  # Отметка о начале обработки
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Получаем URL родительского запроса
        # Мета parent_url и fingerprint для всех запросов нужно менять здесь
        parent_fp = response.meta.get('parent_fp')
        parent_url = response.meta.get('parent_url')
        # Инициализация или увеличение счетчика дочерних запросов
        yield self.lock.run(self._initialize_or_increment, response.url, result)

        # # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

        # Decrement children count
        if parent_fp:
            yield self.lock.run(self._decrement_count,parent_fp, parent_url)

    def _initialize_or_increment(self, parent_fp, result):
        """Инициализация или увеличение счетчика дочерних запросов для parent_url."""
        if parent_fp not in self.children_request_counts:
            # Инициализация счетчика на основе количества запросов в результате
            self.children_request_counts[parent_fp] = sum(1 for item in result if isinstance(item, scrapy.Request))
            print(f"Инициализирован счетчик для fp {parent_fp}: {self.children_request_counts[parent_fp]}")
        else:
            self.children_request_counts[parent_fp] += sum(1 for item in result if isinstance(item, scrapy.Request))

    def _decrement_count(self, parent_fp, parent_url):
        """Уменьшает счетчик дочерних запросов для указанного parent_url."""
        if parent_fp in self.children_request_counts:
            self.children_request_counts[parent_fp] -= 1
            if self.children_request_counts[parent_fp] == 0:
                # Помечаем URL как обработанный и удаляем из словаря
                self._mark_url_processed(parent_fp, parent_url)
                del self.children_request_counts[parent_fp]

    def _mark_url_in_progress(self, fp, url):
        """Записывает статус URL по отпечатку fp "в процессе" в базе данных."""
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
            INSERT INTO visited_urls (fingerprint, url, status) 
            VALUES (?, ?, "in_progress") 
            ON CONFLICT(fingerprint) DO UPDATE SET status="in_progress"
            ''',
            (fp, url,))
            self.connection.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error marking URL as in progress: {e}")
        finally:
            cursor.close()

    def _mark_url_processed(self, fp, url):
        """Отмечает URL по отпечатку как обработанный в базе данных."""
        last_processed_date = datetime.now().strftime("%Y-%m-%d")
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
            UPDATE visited_urls 
            SET status = "processed", last_processed_date = ?          
            WHERE fingerprint = ?
            ''',
            (last_processed_date, fp,))
            self.connection.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error marking URL {url} as processed: {e}")
        finally:
            cursor.close()

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
        if self.logger is None:
            self.logger = spider.logger

    # def close_spider(self, spider):
    #     self.cursor.close()


class BlocketDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
