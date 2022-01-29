from bs4 import BeautifulSoup as soup
import requests, re, time, random 

class VacancyScrapper:

    __url = "https://hh.ru/search/vacancy"
    
    @classmethod
    def get_base_url (self): return self.__url
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:91.0) Firefox/91.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive"
    }

    params = {
        "salary": None,
        "st": "searchVacancy",
        "text": "",
        "page": 0
    }

    sleep_time = {
        'min': 0.1,
        'max': 0.5
    }

    def __init__(self, params = None, headers = None, sleep_time = None):
        if headers: self.headers = headers
        if sleep_time: self.sleep_time = sleep_time
        if params: self.params = params       

    def __wait (self):
        time.sleep(self.sleep_time["min"]+(random.random()*(self.sleep_time["max"]-self.sleep_time["min"])))

    def get_page(self, url, use_params=True):
        try:
            self.__wait()
            params = self.params if use_params else None
            response = requests.get(url, headers = self.headers, params = params)
            return soup(response.text, 'html.parser')          
        except requests.exceptions.Timeout:
            print("get page error: requests.exceptions.Timeout")
            # Maybe set up for a retry, or continue in a retry loop
        except requests.exceptions.TooManyRedirects:
            print("get page error: requests.exceptions.TooManyRedirects")
            # Tell the user their URL was bad and try a different one
        except requests.exceptions.RequestException as err:
            print("get page error: ",err)
        except requests.exceptions.HTTPError as err:
            print("get page error: ",err)


    def get_vacancy_page(self, url):
        return self.get_page(url, use_params=False)

    def get_searching_results_page(self, page_number = None):
        self.params['page'] = page_number or 0
        return self.get_page(self.__url)

    def get_page_count(self):            
        response = self.get_searching_results_page()
        pager_buttons = response.select("div[data-qa='pager-block'] a[class='bloko-button'][data-qa='pager-page']")  
        page_numbers = [0]            
        for pager_button in (pager_buttons or []):              
            page_numbers.append(int(pager_button.get_text()))
        return max(page_numbers)

    def get_vacancy_links(self):
        page_count = self.get_page_count()
        links = []

        ccount = 0      

        for i in range(page_count):
            vacancys_on_page = False       
            while not vacancys_on_page:                
                response = self.get_searching_results_page(page_number = i)
                # ищем блоки с вакансиями
                vacancys_on_page = response.find_all("div",attrs = {"class": 'vacancy-serp-item'})  
                vacancys_on_page = (vacancys_on_page if len(vacancys_on_page or [])>0 else False)

            #if i == 0:
            #    pool_of_vac = response.find('div',attrs = {'class': "vacancy-serp"})
            #    with open("output1.html", "w", encoding='utf-8') as file:
            #        file.write(str(pool_of_vac.prettify()))
            #    with open("all1.html", "w", encoding='utf-8') as file:
            #        file.write(str(response.prettify()))                

            
            # выдергиваем url
            for vacancy_block in (vacancys_on_page or []):
                link_container = vacancy_block.find("a",attrs={"class" : 'bloko-link'})
                links.append(re.sub(r'\?.+',r'', str(link_container['href'])))

        return links
