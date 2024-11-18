# custom_settings.py

SQLITE_FILE = "blocket.db"
JOBDIR = "spider_data"
EXCEL_FILE_INCREMENTAL = "job_data.xlsx"
EXCEL_FILE_FROM_DB = "job_data_from_db.xlsx"

SAVE_JOB_DESCRIPTION = True


# REFRESH_MODE - duplicate filter bypass mode:
# True — pages meeting the refresh_days condition are processed even if they were previously handled.
# False — all pages are checked for duplicates.
REFRESH_MODE = True
# REFRESH_DAYS - maximum number of days between today’s date and the latest job posting on the page for the next page in this category
# to bypass duplicate filtering
REFRESH_DAYS = 14
MAX_CATEGORY_PAGE_NUMBER = 1

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

EXTENSIONS = {
    'blocket.extensions.LoggingExtension': 400,
    'blocket.extensions.DbExtension': 500,
}
ITEM_PIPELINES = {
   "blocket.pipelines.JobPipeline": 300,
   "blocket.pipelines.DatabasePipeline": 400,
   "blocket.pipelines.ExcelSavePipeline": 500,
   "blocket.pipelines.ExcelFinalExportPipeline": 600,
}


SPIDER_MIDDLEWARES = {
    'blocket.middlewares.BlocketSpiderMiddleware': 543,
}


DUPEFILTER_CLASS = 'blocket.dupefilters.JobUrlDupeFilter'
DEPTH_LIMIT = 502

HTTPERROR_ALLOW_ALL = False


CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 10
DOWNLOAD_DELAY = 0.2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 8.0
REACTOR_THREADPOOL_MAXSIZE = 20


REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
DOWNLOAD_FAIL_ON_DATALOSS = False
#LOG_LEVEL = 'DEBUG'
LOG_LEVEL = 'WARNING'
CUSTOM_LOG_LEVEL = "INFO"
#DUPEFILTER_DEBUG = True