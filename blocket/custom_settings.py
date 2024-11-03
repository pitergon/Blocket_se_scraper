# custom_settings.py
from scrapy.settings.default_settings import LOG_LEVEL

SQLITE_FILE = "scrapy_data.db"
JOBDIR = "spider_data"


JOB_PAGE_PARSING_ENABLED = True
SAVE_JOB_DESCRIPTION = False
MAX_CATEGORY_PAGE_NUMBER = 0

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

ITEM_PIPELINES = {
   "blocket.pipelines.JobPipeline": 300,
   "blocket.pipelines.DatabasePipeline": 400,
   "blocket.pipelines.ExcelSavePipeline": 500,
   "blocket.pipelines.ExcelFinalExportPipeline": 600,
}

EXTENSIONS = {
    'blocket.extensions.DbExtension': 500,
}

DOWNLOADER_MIDDLEWARES = {
    'blocket.middlewares.BlocketSpiderMiddleware': 543,
}


DUPEFILTER_CLASS = 'blocket.dupefilters.JobUrlDupeFilter'


HTTPERROR_ALLOW_ALL = False


CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.25
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 8.0
REACTOR_THREADPOOL_MAXSIZE = 20


REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
DOWNLOAD_FAIL_ON_DATALOSS = False
LOG_LEVEL = 'WARNING'

