Scrapper for site blocket.se



run 
scrapy crawl blocket

update data from first pages of categories
scrapy crawl blocket -s refresh_mode=True -s refresh_dates=4
or set tis parameters in custom_settings.py
