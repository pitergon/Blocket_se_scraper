import asyncio
from asyncio import events
from twisted.internet import asyncioreactor

# Устанавливаем SelectorEventLoop для совместимости
if isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

asyncioreactor.install()

from scrapy.cmdline import execute

if __name__ == "__main__":
    execute(['scrapy', 'crawl', 'blocket'])