import re
import sqlite3
import logging
import scrapy
from scrapy.dupefilters import RFPDupeFilter
from scrapy.utils.request import request_fingerprint, fingerprint


class DuplicateURLFilter(logging.Filter):
    """Hides standard scrape messages about duplicate URLs without changing the log level"""
    def filter(self, record):
        return not re.search(r'Dropped: Duplicate URL found', record.getMessage())


class JobUrlDupeFilter(RFPDupeFilter):
    def __init__(self, path=None, debug=False, *, fingerprinter=None, db_connection=None):
        super().__init__(path=path, debug=debug, fingerprinter=fingerprinter)
        self.connection = db_connection
        self.cursor = self.connection.cursor()
        # Hides standard scrape messages about duplicate URLs without changing the log level
        logging.getLogger('scrapy.core.scraper').addFilter(DuplicateURLFilter())

    @classmethod
    def from_crawler(cls, crawler):
        db_connection = crawler.db_connection # pylint: disable=attribute-defined-outside-init
        path = crawler.settings.get('JOB_URL_DUPEFILTER_PATH', None)
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)
        fingerprinter = crawler.request_fingerprinter
        return cls(path=path, debug=debug, fingerprinter=fingerprinter, db_connection=db_connection)

    def request_seen(self, request: scrapy.Request):
        """
        Checking for URLs in the table visited_urls
        """
        fp = request_fingerprint(request)
        # url = request.url
        self.cursor.execute("SELECT 1 FROM visited_urls WHERE fingerprint = ?", (fp,))
        # if crawler.mode == "update":
        #     processed_date = self.settings.last_update_date
        #     self.cursor.execute('''
        #     SELECT 1
        #     FROM visited_urls
        #     WHERE fingerprint = ?
        #     AND processed_date >
        #     ''',
        #                         (fp,processed_date,))
        # else:
        #     self.cursor.execute("SELECT 1 FROM visited_urls WHERE fingerprint = ?", (fp,))
        # self.cursor.execute("SELECT 1 FROM jobs WHERE url = ?", (url,))
        return bool(self.cursor.fetchone())

