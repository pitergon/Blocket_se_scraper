import asyncio
from asyncio import events
from twisted.internet import asyncioreactor
from blocket.spiders.blocket import BlocketSpider


# if isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
#
# asyncioreactor.install('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

# try:
#     asyncioreactor.install()
# except RuntimeError as e:
#     print(f"Reactor already installed: {e}")

# from scrapy.cmdline import execute
#
# if __name__ == "__main__":
#     execute(['scrapy', 'crawl', 'blocket'])
#
#

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

process = CrawlerProcess(settings=get_project_settings())
process.crawl("blocket")
process.start()

