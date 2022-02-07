from bs4 import BeautifulSoup as soup
import requests, re, time, random
from requests import exceptions as reqexc
from fake_headers import Headers 
from .proxy import Proxy

class VacancyScrapper:

    __url_search = "https://hh.ru/search/vacancy"
    __url_vacancy = "https://hh.ru/vacancy"
    
    @classmethod
    def get_search_url (self): return self.__url_search

    @classmethod
    def get_vacancy_url (self): return self.__url_vacancy

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:91.0) Firefox/91.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive"
    }

    __fake_header = Headers()

    params = {
        "salary": None,
        "st": "searchVacancy",
        "text": "",
        "page": 0
    }

    sleep_time = {
        'min': 0.1,
        'max': 1
    }

    def __init__(self, params = None, sleep_time = None):
        if sleep_time: self.sleep_time = sleep_time
        if params: self.params = params
        self.proxy = Proxy()       

    def __wait (self):
        time.sleep(self.sleep_time["min"]+(random.random()*(self.sleep_time["max"]-self.sleep_time["min"])))

    def get_page(self, url, use_params=True):
        exceptions = (reqexc.Timeout, reqexc.TooManyRedirects, reqexc.RequestException, reqexc.HTTPError)
        unparsed = None
        try:
            self.__wait()
            params = self.params if use_params else None
            print(url)
            #response = requests.get(url, headers = self.__fake_header.generate() or self.headers, params = params)
            current_session = self.proxy.get()
            print(current_session)
            response = current_session.get(url, 
                                    headers = self.__fake_header.generate() or self.headers, 
                                    params = params)                    
            unparsed = soup(response.text, 'html.parser')
        except exceptions as err: 
            print("get page error: "+str(err))
            pass

        return unparsed or self.get_page(url, use_params=use_params)    

    def get_vacancy_page(self, url, id = None):
        if id: 
            url = self.__url_vacancy+"/"+id
        return self.get_page(url, use_params=False)

    def get_searching_results_page(self, page_number = None):
        self.params['page'] = page_number or 0
        return self.get_page(self.__url_search)

    def get_page_count(self):            
        response = self.get_searching_results_page()
        pager_buttons = response.select("div[data-qa='pager-block'] a[class='bloko-button'][data-qa='pager-page']")  
        page_numbers = [] 

        for pager_button in (pager_buttons or []):              
            page_numbers.append(int(pager_button.get_text()))

        if len(page_numbers) == 0:
            page_numbers.append(1)
            
        return max(page_numbers)

    def get_vacancy_links(self):
        page_count = self.get_page_count()
        links = []

        for i in range(page_count):
            vacancys_on_page = False       
            while not vacancys_on_page:                
                response = self.get_searching_results_page(page_number = i)
                # ищем блоки с вакансиями
                vacancys_on_page = response.find_all("div",attrs = {"class": 'vacancy-serp-item'})  
                vacancys_on_page = (vacancys_on_page if len(vacancys_on_page or [])>0 else False)
            
            # выдергиваем url
            for vacancy_block in (vacancys_on_page or []):
                link_container = vacancy_block.find("a",attrs={"class" : 'bloko-link'})
                links.append(re.sub(r'\?.+',r'', str(link_container['href'])))

        return links
