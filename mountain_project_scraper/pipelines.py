# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import csv
import os
from mountain_project_scraper.items import AreaItem, RouteItem


class MountainProjectScraperPipeline:
    def open_spider(self, spider):
        self.file_handles = {}
        self.folder_name = 'out'

        # Create the folder if it doesn't exist
        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)

    def close_spider(self, spider):
        for file in self.file_handles.values():
            file.close()

    def process_item(self, item, spider):
        # Determine the type of item
        if isinstance(item, AreaItem):
            file_name = os.path.join(self.folder_name, 'areas.csv')
        elif isinstance(item, RouteItem):
            file_name = os.path.join(self.folder_name, 'route.csv')
        else:
            return item  # Unknown item

        # If file doesn't exist, open and add headers
        if file_name not in self.file_handles:
            file_handle = open(file_name, 'a', newline='', encoding='utf-8')
            writer = csv.DictWriter(file_handle, fieldnames=item.fields)
            writer.writeheader()
            self.file_handles[file_name] = (file_handle, writer)

        # Write item to its respective file
        self.file_handles[file_name][1].writerow(item)

        return item
