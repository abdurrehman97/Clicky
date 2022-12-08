import scrapy
import math
import re
from price_parser import Price


class ClickySpider(scrapy.Spider):

    name = 'clicky'
    start_urls = ['https://www.clicky.pk/']
    api_url_template = 'https://www.clicky.pk/api/promotions/search/null?page=1&categories={}&sort=-createdAt'

    def extract_slug(self, api_url_template):
        url = api_url_template.split('?')[0]
        return url.replace('/', '')

    def parse(self, response, **kwargs):

        categories_list = response.css('nav.cat div a::attr(href)').getall()
        for url_path in categories_list:
            url = self.api_url_template.format(self.extract_slug(url_path))
            yield scrapy.Request(
             url=url,
             callback=self.parse_products_shelf
            )

    def parse_products_shelf(self, response):
        shelve_data = response.json()
        for product in shelve_data['data']:
            product = product['url']
            yield scrapy.Request(
                url=product,
                callback=self.parse_products_items
            )

        products_count = shelve_data['count']
        page_size = shelve_data['pageSize']
        exact_page_size = math.ceil(products_count / page_size)

        for num in range(2, exact_page_size + 1):
            if num <= exact_page_size:
                next_page_url = response.url
                next_page_url = re.sub(r'page=(\d+)', f'page={num}', next_page_url)
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_products_shelf
                )

    def parse_products_items(self, response):

        delivery_time = response.xpath('//div[@class="delivery-time-img"]/following-sibling::div/div/text()').getall()
        delivery_time = re.findall(r':\s(\d+-\d+\s[A-z]+)', delivery_time[0])
        delivery_time = ''.join(delivery_time)

        if not delivery_time:
            delivery_time = None

        delivery_cities = response.xpath('//div[@class="delivery-time-img"]/following-sibling::div/div/text()').getall()
        delivery_cities = re.findall(r'(.*?):', delivery_cities[0])
        delivery_cities = ''.join(delivery_cities)

        sizes = response.css('.sizes_main_box  .size_heading + div span::text').getall()
        sizes = ''.join(sizes)

        price_new = response.css('span.set::text').get()
        price_new = Price.fromstring(price_new)

        price_old = response.css('.price-hot h2 del::text').get()
        price_old = Price.fromstring(price_old)

        categories = response.css('.breadcrumb span a::text').getall()
        categories = ' > '.join(categories)

        yield {

            'name': response.css('.p_name::text').get('').strip(),
            'brand': response.css('.product_style_code:contains("By")::text').get('').replace('By', '').replace(' :', '').strip(),
            'style': response.css('.product_style_code:contains("Style")::text').get('').replace('Style', '').replace(' :', '').strip(),
            'old_price': price_old.amount,
            'new_price': price_new.amount,
            'discount': response.css('span.set + span.percentage-text::text').get('').replace('(-', '').replace(')', '').replace('-', '').strip(),
            'sizes': sizes.split(),
            'categories': categories,
            'reviews': response.css('.review-box span::text').get(),
            'image_url': response.css('.links-categories .sub-category-link .sub-cat-img img::attr(src)').getall(),
            'delivery_time': delivery_time,
            'delivery_cities': delivery_cities.split(),
            'url': response.url

        }
