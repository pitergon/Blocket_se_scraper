import re
import sqlite3
import logging
import scrapy
from scrapy.dupefilters import RFPDupeFilter
from scrapy.utils.request import fingerprint


class JobUrlDupeFilter(RFPDupeFilter):
    def __init__(self, path=None, debug=False, *, fingerprinter=None, db_connection=None):
        super().__init__(path=path, debug=debug, fingerprinter=fingerprinter)
        self.connection = db_connection
        self.cursor = self.connection.cursor()

    @classmethod
    def from_crawler(cls, crawler):
        db_connection = crawler.db_connection # pylint: disable=attribute-defined-outside-init
        path = crawler.settings.get('JOB_URL_DUPEFILTER_PATH', None)
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)
        fingerprinter = crawler.request_fingerprinter
        return cls(path=path, debug=debug, fingerprinter=fingerprinter, db_connection=db_connection)

    def request_seen(self, request: scrapy.Request):
        """
        Checking for URLs in the table visited_urls.
        For  request to main page and some category pages in update mode
        this filter will be disabled with dont_filter = true
        """
        fp = fingerprint(request)
        self.cursor.execute("SELECT 1 FROM visited_urls WHERE fingerprint = ?", (fp,))
        return bool(self.cursor.fetchone())

    def close_spider(self, spider):
        self.cursor.close()