import scrapy
from scrapy import Request, FormRequest
from mountain_project_scraper.items import AreaItem, RouteItem, HTMLItem
from bs4 import BeautifulSoup
import unicodedata
import os
from dotenv import load_dotenv, find_dotenv


class AreasSpider(scrapy.Spider):
    name = 'areas_routes'
    allowed_domains = ['mountainproject.com']

    def start_requests(self):
        main_page_url = 'https://www.mountainproject.com/auth/login'
        yield Request(main_page_url, callback=self.login)

    def login(self, response):
        dotenv_file = find_dotenv()
        load_dotenv(dotenv_file)
        username = os.environ.get('USERNAME')
        password = os.environ.get('PASSWORD')
        formdata = {'email': username, 'pass': password}
        return FormRequest.from_response(response, callback=self.after_login,
                                         formdata=formdata,
                                         formxpath='//form[@action="/auth/login/email"]')

    def after_login(self, response):
        self.logger.info('logged in, start crawling')
        yield Request('https://www.mountainproject.com/area/105731932/red-rocks', callback=self.parse_area,
                      cb_kwargs={'parent_name': 'ROOT', 'parent_url': 'area/-1/root'})

    def parse_area(self, response, parent_name, parent_url):
        parent_id = parent_url.rsplit('/', 2)[-2]
        area_url_name = response.request.url.rsplit('/', 1)[-1]
        area_id = response.request.url.rsplit('/', 2)[-2]

        info_message = 'scraping area: {0} with id {1} from parent area: {2} with id {3}'.format(
            area_url_name, area_id, parent_name, parent_id)
        self.logger.info(info_message)

        # parse area data
        area_name = response.css('h1::text').get().strip()
        area_description = self.extract_description(response)
        long, lat = (response.xpath('//table[@class="description-details"]//tr[td="GPS:"]/td[2]/text()')
                     .get().strip().split(', '))
        child_type = ''
        child_ids = []
        child_area_urls = response.css('div.lef-nav-row a::attr(href)').extract()
        child_route_urls = response.css('table#left-nav-route-table tr a::attr(href)').extract()
        if child_area_urls:
            child_type = 'area'
            child_ids += [url.rsplit('/', 2)[-2] for url in child_area_urls]
        if child_route_urls:
            child_type = 'route'
            child_ids += [url.rsplit('/', 2)[-2] for url in child_route_urls]

        area_item = AreaItem(id=area_id,
                             name=area_name,
                             description=area_description,
                             long=long,
                             lat=lat,
                             url=response.request.url,
                             child_type=child_type,
                             child_ids=child_ids,
                             parent_name=parent_name,
                             parent_id=parent_id
                             )
        yield Request(
            f"https://www.mountainproject.com/comments/forObject/Climb-Lib-Models-Route/{area_id}?sortOrder=oldest&showAll=true",
            callback=self.parse_comment, meta={'item': area_item})

        # save raw html
        # html_item = HTMLItem(html=response.css('div.row.pt-main-content').get())
        # yield html_item

        # scrape sub areas if exist
        sub_areas_links = response.css('div.lef-nav-row a')
        if sub_areas_links is not None:
            yield from response.follow_all(sub_areas_links, callback=self.parse_area,
                                           cb_kwargs={'parent_name': area_name, 'parent_url': response.url})

        # scrape routes if no sub areas
        routes_links = response.css('table#left-nav-route-table tr a')
        if routes_links is not None:
            yield from response.follow_all(routes_links, callback=self.parse_route,
                                           cb_kwargs={'parent_name': area_name, 'parent_url': response.url})

    def parse_route(self, response, parent_name, parent_url):
        parent_id = parent_url.rsplit('/', 2)[-2]
        route_url_name = response.request.url.rsplit('/', 1)[-1]
        route_id = response.request.url.rsplit('/', 2)[-2]

        info_message = 'scraping route: {0} with id {1} from area: {2} with id {3}'.format(
            route_url_name, route_id, parent_name, parent_id)
        self.logger.info(info_message)

        # parse route data
        route_name = response.css('h1::text').get().strip()
        grade = self.scrape_grade(response)
        climb_type, length, pitch, commitment_grade = self.scrape_type_length_pitch(response)
        protection = self.scrape_protection(response)
        user_rating = response.css(f'span#starsWithAvgText-{route_id}::text').getall()[1].strip()
        route_description = self.extract_description(response)
        route_comment = self.extract_comment(response)

        route_item = RouteItem(id=route_id,
                               name=route_name,
                               grade=grade,
                               type=climb_type,
                               length=length,
                               pitch=pitch,
                               commitment_grade=commitment_grade,
                               protection=protection,
                               user_rating=user_rating,
                               description=route_description,
                               comment=route_comment,
                               url=response.request.url,
                               parent_name=parent_name,
                               parent_id=parent_id
                               )
        yield Request(
            f"https://www.mountainproject.com/comments/forObject/Climb-Lib-Models-Route/{route_id}?sortOrder=oldest&showAll=true",
            callback=self.parse_comment, meta={'item': route_item})
        # save raw html
        # html_item = HTMLItem(html=response.css('div.row.pt-main-content').get())
        # yield html_item

    def parse_comment(self, response):
        comment = self.extract_comment(response)
        item = response.meta['item']
        item['comment'] = comment
        yield item

    def innertext(self, selector):
        texts = []
        htmls = selector.getall()
        for html in htmls:
            soup = BeautifulSoup(html, 'html.parser')
            text = ''
            for words in soup.strings:
                words = unicodedata.normalize("NFKD", words)
                if not text:
                    text += words
                else:
                    text += '\n' + words
            texts.append(text)
        return texts

    def extract_description(self, response):
        description = ''
        titles = self.innertext(response.xpath("//div[@class='fr-view']/preceding-sibling::h2"))
        contents = self.innertext(response.css('div.fr-view'))
        for title, content in zip(titles, contents):
            description += title.strip() + '\n' + content.strip() + '\n'
        return description

    def extract_comment(self, response):
        comment = ''
        contents = self.innertext(response.xpath('//div[@class="comment-body"]/span[contains(@id, "-full")]'))
        times = self.innertext(response.xpath("//span[@class='comment-time']/a"))
        likes = self.innertext(response.xpath("//span[@class='num-likes']"))
        for content, time, like in zip(contents, times, likes):
            comment += (content.strip() + '\n'
                        + 'comment time: ' + time.strip() + '\n'
                        + 'up votes: ' + like.strip() + '\n\n')
        return comment


    def scrape_grade(self, response):
        grade_dict = {}
        grade_types = {
            'YDS': '.rateYDS',
            'French': '.rateFrench',
            'Ewbanks': '.rateEwbanks',
            'UIAA': '.rateUIAA',
            'ZA': '.rateZA',
            'British': '.rateBritish',
            'FontFrench': '.rateFont',
        }

        # Extract grades for each grading system, if available
        for grade_name, grade_class in grade_types.items():
            grade = response.css(f'h2.inline-block.mr-2 {grade_class}::text').get()
            if grade:
                grade_dict[grade_name] = grade.strip()
            else:
                grade_dict[grade_name] = None

        return grade_dict

    def scrape_protection(self, response):
        protection_types = ["G", "PG", "PG13", "R", "X"]
        raw_data = response.css('h2.inline-block.mr-2::text').getall()[-1].strip()
        if raw_data in protection_types:
            return raw_data
        return ''

    def scrape_type_length_pitch(self, response):
        raw_data = (response.xpath('//table[@class="description-details"]//tr[td="Type:"]/td[2]/text()')
                    .get().strip().split(', '))

        # assume climb is 1 pitch if pitch info is not available
        climb_types = {'TR', 'Sport', 'Trad', 'Boulder', 'Aid', 'Ice', 'Snow', 'Alpine'}
        climb_type = ''
        length = ''
        pitch = 1
        commitment_grade = ''
        for element in raw_data:
            if element in climb_types:
                if not climb_type:
                    climb_type = element
                else:
                    climb_type += f', {element}'
            elif 'm' in element or 'ft' in element:
                length = element
            elif 'pitch' in element:
                pitch = int(element.split(' ')[0])
            elif 'Grade' in element:
                commitment_grade = element
        return climb_type, length, pitch, commitment_grade

