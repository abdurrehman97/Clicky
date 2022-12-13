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

        delivery_time = response.xpath('//div[@class="delivery-time-img"]/following-sibling::div/div/text()').get()
        delivery_time_case_1 = re.findall(r'(\d+)-\d+\s(Hours|days|Days)', delivery_time)
        delivery_time_case_2 = re.findall(r'same day', delivery_time)

        if 'same day' in delivery_time_case_2:
            delivery_time_case_2 = 'Today'

        elif '0' in delivery_time or 'Order will be dispatched after 25th October' in delivery_time:
            delivery_time_case_2 = None

        else:
            delivery_time_case_2 = ' '.join(delivery_time_case_1[0])

        sizes = response.css('.sizes_main_box  .size_heading + div span::text').getall()
        sizes = ''.join(sizes)
        if 'free size' in sizes.casefold():
            sizes = 'NO SIZE'

        price_new = response.css('span.set::text').get()
        price_new = Price.fromstring(price_new)

        price_old = response.css('.price-hot h2 del::text').get()
        price_old = Price.fromstring(price_old)

        sku = response.url
        sku = re.findall(r'id=(.*)', sku)

        image_urls = re.findall(r'large:"(https:.*?)"', response.text)

        yield {

            'title': response.css('.p_name::text').get('').strip().capitalize(),
            'brand': response.css('.product_style_code:contains("By")::text').get('').replace('By', '').replace(' :', '').strip(),
            'style': response.css('.product_style_code:contains("Style")::text').get('').replace('Style', '').replace(' :', '').strip(),
            'sku': sku[0],
            'price_was': price_old.amount_float,
            'price_now': price_new.amount_float,
            'discount': response.css('span.set + span.percentage-text::text').get('').replace('(-', '').replace(')', '').replace('-', '').strip(),
            'size': sizes.split(),
            'reviews': response.css('.review-box span::text').get(),
            'image_urls': image_urls,
            'delivery_time': delivery_time_case_2,
            'url': response.url

        }
