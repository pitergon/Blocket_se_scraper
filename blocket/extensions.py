import sqlite3
from scrapy.crawler import Crawler

class DbExtension:
    def __init__(self, crawler: Crawler):
        self.connection = sqlite3.connect(crawler.settings.get("SQLITE_FILE"), check_same_thread=False)
        crawler.db_connection = self.connection
        cursor = self.connection.cursor()
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
                    additional_contacts TEXT, 
                    company_job_count INTEGER
                );
                CREATE TABLE IF NOT EXISTS visited_urls (
                    fingerprint TEXT PRIMARY KEY,
                    url TEXT UNIQUE,
                    status TEXT,
                    last_processed_date TEXT                   
                );
            ''')
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error creating database {e}")
        finally:
            cursor.close()


    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def close_spider(self, spider):
        self.connection.close()
