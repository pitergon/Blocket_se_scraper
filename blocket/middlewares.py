# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import logging
from datetime import datetime
from typing import Optional
import sqlite3
import scrapy
from pandas.io.sas.sas_constants import page_type_mask
from scrapy.utils.request import fingerprint
from scrapy import signals
from twisted.internet.defer import DeferredLock


class BlocketSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.
    def __init__(self, crawler):
        bot_name = crawler.settings.get('BOT_NAME', 'scrapy_project')
        self.logger = logging.getLogger(bot_name)
        self.lock = DeferredLock()
        self.children_request_counts = {}  # dict
        self.connection: Optional[sqlite3.Connection] = crawler.db_connection

    @classmethod
    def from_crawler(cls, crawler):
        """
        Connect handler to signal request_dropped when child request dropped for decrement child request counter
        This method is used by Scrapy to create your spiders.
        """
        s = cls(crawler)
        crawler.signals.connect(s.request_dropped_handler, signal=signals.request_dropped)
        return s

    def process_spider_input(self, response, spider):
        """
        Marks the request as "in progress" when entering the spider
        Called for each response that goes through the spider middleware and into the spider.
        Should return None or raise an exception.
        """
        url = response.url
        fp = fingerprint(response.request)
        parent_url = response.meta.get('parent_url')
        page_type = response.meta.get('page_type')
        self._mark_url_in_progress(fp, url, parent_url, page_type)
        return None

    def process_spider_output(self, response, result, spider):
        """
        Adds parent request metadata to each child request and manages a count of active child requests.
        Uses a lock to safely increment the child request counter on creation and decrement it upon completion.

        Called with the results returned from the Spider, after it has processed the response.
        Must return an iterable of Request, or item objects.
        """

        # Getting parent URL and parent fingerprint from metadata
        parent_fp = response.meta.get('parent_fp')
        parent_url = response.meta.get('parent_url')
        fp = fingerprint(response.request)
        url = response.url
        # Init counter for child requests
        pending_requests = []
        item_count = 0
        for item in result:
            if isinstance(item, scrapy.Request):
                # Set Metadata parent_url и fingerprint for all child request
                # Preventing looping by visiting parent page
                if item.url != parent_url:
                    item.meta["parent_fp"] = fp
                    item.meta["parent_url"] = url
                    # Append request to pending list for delayed yield
                    pending_requests.append(item)
            else:
                item_count += 1
                yield item

        if pending_requests:
            self._update_counter_with_lock(fp, url, len(pending_requests))
        elif item_count:
            self._mark_url_processed(fp, url)
        else:
            self.logger.warning(f"~~~Page {url} did not generate any queries or items. May be you are blocked")
        # Yield all pending requests after iterating over result
        for request in pending_requests:
            yield request

        # Decrement children count with a locker
        if parent_fp:
            self._update_counter_with_lock(parent_fp, parent_url, -1)

    def _update_counter_with_lock(self, fp, url, delta):
        """
        Update counter of children requests with deferred lock
        """
        d = self.lock.acquire()
        d.addCallback(self._update_count, fp, url, delta)
        d.addErrback(self._handle_error)

    def _handle_error(self, failure):
        self.logger.error(f"Error accessing variable children_request_counts {failure}")

    def _update_count(self, result, fp, url, delta):
        """
        Should be called only with external lock for self.children_request_counts.
        Updates counter and set parent request processed if counter equals 0
        """
        processed = False
        try:
            self.children_request_counts[fp] = self.children_request_counts.get(fp, 0) + delta
            if self.children_request_counts[fp] == 0:
                del self.children_request_counts[fp]
                processed = True
        except Exception as e:
            self.logger.error(f"Error accessing variable children_request_counts {e}")
        finally:
            self.lock.release()
        if processed:
            self._mark_url_processed(fp, url)

    # def _decrement_count(self, parent_fp: bytes, parent_url: str):
    #     """Decrement the child request counter for specified parent_url"""
    #     processed = False
    #     if parent_fp in self.children_request_counts:
    #         with self.lock:
    #             self.children_request_counts[parent_fp] -= 1
    #             if self.children_request_counts[parent_fp] == 0:
    #                 del self.children_request_counts[parent_fp]
    #                 processed = True
    #         if processed:
    #             self._mark_url_processed(parent_fp, parent_url)

    def _mark_url_in_progress(self, fp: bytes, url: str, parent_url: str = None, page_type: str = None):
        """Marks the request with fingerprint as "in progress" in DB"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
            INSERT INTO visited_urls (fingerprint, url, parent_url, page_type, status) 
            VALUES (?, ?, ?, ?, "in_progress") 
            ON CONFLICT(fingerprint) DO UPDATE SET status="in_progress"
            ''',
                           (fp, url, parent_url, page_type))
            self.connection.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error marking URL as in progress: {e}")
        finally:
            cursor.close()

    def _mark_url_processed(self, fp: bytes, url: str):
        """Marks the request with fingerprint as "progressed" in DB"""

        last_processed_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    def request_dropped_handler(self, request: scrapy.Request, spider):
        """Decrement the counter if the request was rejected as a duplicate."""
        parent_fp = request.meta.get('parent_fp')
        parent_url = request.meta.get('parent_url')
        if parent_fp in self.children_request_counts:
            self._update_counter_with_lock(parent_fp, parent_url, -1)
            # with self.lock:
            #     self.children_request_counts[parent_fp] -= 1
            #     if self.children_request_counts[parent_fp] == 0:
            #         self._mark_url_processed(parent_fp, parent_url)


