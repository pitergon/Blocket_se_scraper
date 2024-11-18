import logging
import logging.config
import sqlite3
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured


class LoggingExtension:
    def __init__(self, crawler):

        self.settings = crawler.settings
        self.bot_name = self.settings.get('BOT_NAME', "blocket")
        self.log_level = self.settings.get('CUSTOM_LOG_LEVEL', 'INFO').upper()
        self.logger = self.create_logger()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        if not crawler.settings.getbool('LOG_ENABLED', True):
            raise NotConfigured
        return cls(crawler)

    def create_logger(self):
        logger = logging.getLogger(self.bot_name)
        logger.propagate = False
        if logger.handlers:
            logger.handlers = []
        handler = logging.StreamHandler()
        handler.setLevel(self.log_level)
        formatter = logging.Formatter(
            fmt=self.settings.get("LOG_FORMAT"), datefmt=self.settings.get("LOG_DATEFORMAT")
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger


class DbExtension:
    def __init__(self, crawler: Crawler):
        bot_name = crawler.settings.get('BOT_NAME', 'scrapy_project')
        self.logger = logging.getLogger(bot_name)
        self.connection: sqlite3.Connection = sqlite3.connect(crawler.settings.get("SQLITE_FILE"),
                                                              check_same_thread=False)
        crawler.db_connection = self.connection
        cursor: sqlite3.Cursor = self.connection.cursor()
        try:
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY,
                    url TEXT UNIQUE,
                    title TEXT,
                    company TEXT,
                    published_date TEXT, 
                    apply_date TEXT, 
                    location TEXT, 
                    category TEXT, 
                    job_type TEXT, 
                    description TEXT,
                    processed_date TEXT, 
                    phone TEXT, 
                    email TEXT, 
                    additional_contacts TEXT
                );
                CREATE TABLE IF NOT EXISTS visited_urls (
                    fingerprint BLOB PRIMARY KEY,
                    url TEXT,
                    parent_url TEXT,
                    page_type TEXT,
                    status TEXT,
                    last_processed_date TEXT                   
                );
            ''')

            self.connection.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"Error creating database {e}")
        finally:
            cursor.close()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def close_spider(self, spider):
        self.connection.close()
