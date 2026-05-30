import logging
import random
import time

from bs4 import BeautifulSoup as soup
from fake_headers import Headers
from requests import exceptions as reqexc

from .proxy import Proxy

logger = logging.getLogger(__name__)


class VacancyScrapper:
    __url_search = "https://hh.ru/search/vacancy"
    __url_vacancy = "https://hh.ru/vacancy"

    @classmethod
    def get_search_url(self):
        return self.__url_search

    @classmethod
    def get_vacancy_url(self):
        return self.__url_vacancy

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:91.0) Firefox/91.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive",
    }

    __fake_header = Headers()

    params = {"salary": None, "st": "searchVacancy", "text": "", "page": 0}

    sleep_time = {"min": 0.1, "max": 1}

    def __init__(self, params=None, sleep_time=None):
        if sleep_time:
            self.sleep_time = sleep_time
        if params:
            self.params = params
        self.proxy = Proxy()

    def __wait(self):
        time.sleep(
            self.sleep_time["min"]
            + (random.random() * (self.sleep_time["max"] - self.sleep_time["min"]))
        )

    def get_page(self, url, use_params=True):
        exceptions = (
            reqexc.Timeout,
            reqexc.TooManyRedirects,
            reqexc.RequestException,
            reqexc.HTTPError,
        )
        unparsed = None
        try:
            self.__wait()
            params = self.params if use_params else None
            logger.debug("GET %s params=%s", url, params)
            current_session = self.proxy.get()
            logger.debug("Using proxy session %s", current_session.proxies)
            response = current_session.get(
                url, headers=self.__fake_header.generate() or self.headers, params=params
            )
            unparsed = soup(response.text, "html.parser")
        except exceptions as err:
            logger.warning("get page error: %s", err)

        return unparsed or self.get_page(url, use_params=use_params)

    def get_vacancy_page(self, url, id=None):
        if id:
            url = self.__url_vacancy + "/" + id
        return self.get_page(url, use_params=False)

    def get_searching_results_page(self, page_number=None):
        self.params["page"] = page_number or 0
        return self.get_page(self.__url_search)

    def get_page_count(self):
        from .template_parser import DumpParser

        response = self.get_searching_results_page()
        return DumpParser.get_search_page_count(response)

    def get_vacancy_links(self):
        from .template_parser import DumpParser

        links = []

        for page_number in range(self.get_page_count()):
            vacancies = []
            while not vacancies:
                response = self.get_searching_results_page(page_number=page_number)
                vacancies = DumpParser.parse_search_page(response)

            for vacancy in vacancies:
                links.append(vacancy["url"])

        return links
