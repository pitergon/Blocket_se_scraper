Scrapper for site blocket.se
Use python > 3.10


run 
scrapy crawl blocket

update data from first pages of categories
scrapy crawl blocket -s refresh_mode=True -s refresh_dates=4
or set tis parameters in custom_settings.py
