import codecs
from .scrapper import VacancyScrapper
import unicodedata
import re
import datetime
from price_parser import Price

class Parser:

    def __init__(self, scrapper = None):
        self.scrapper = scrapper

    def __sanitize_string(self, raw_string):
        raw_string = codecs.encode(str(raw_string),'utf8')
        raw_string = codecs.decode(raw_string,'utf8')
        raw_string = unicodedata.normalize("NFKD", raw_string).rstrip()             
        return re.sub(r'\n','',raw_string)       

    def parse_salary(self, raw_salary):        
        salary_value_strings = re.findall(r'((\d+\s*)+)+', raw_salary)
        salary_sequence = []
        for pair in salary_value_strings: salary_sequence.append(int(re.sub(r'\s+', r'', pair[0])))
        salary_sequence.sort()        
        salary = {
            "from": salary_sequence[0] if len(salary_sequence)>0 else False,
            "to": salary_sequence[1] if len(salary_sequence)>1 else False,
            "gross": False if re.search(r'на\s+руки', raw_salary) else True,
            "currancy":  Price.fromstring(raw_salary).currency
        }

        return salary

    def parse_date(self, raw_date):

        date_text = re.search(r'\d+\s+[^\d\s]+\s+\d+', raw_date or "")        

        if date_text:
            date_text = date_text.group()

        date_splited = re.split("\s+", date_text)  
        a_month = ['', 'янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
        month_abbr = re.search(r'^[\w+]{3}', date_splited[-2]).group()
        month_number = a_month.index(month_abbr)

        return datetime.date(int(date_splited[-1]), month_number, int(date_splited[0]))
        
    def parse_vacancy_page(self, url, parse_salary = False, parse_date = False):

        vacancy = {}
        response_parsed = self.scrapper.get_vacancy_page(url)

        vacancy["url"] = url
        vacancy["title"] = response_parsed.find("h1",attrs = {"data-qa": 'vacancy-title'}).get_text()
        vacancy["salary"] = response_parsed.find("div",attrs = {"data-qa": 'vacancy-salary'}).get_text()        
        vacancy["company_name"] = response_parsed.find("a",attrs = {"data-qa": 'vacancy-company-name',"class": 'vacancy-company-name'}).get_text()              
        vacancy["description"] = response_parsed.find("div",attrs = {"class": 'vacancy-section'}).get_text()      
        #vacancy["company_verified"] = response_parsed.find("div", attrs = {"class": 'vacancy-company-badge'}).find("a",{"class": 'bloko-link', "href":'https://feedback.hh.ru/article/details/id/5951'}) and True
        vacancy["company_verified"] = response_parsed.find("div", attrs = {"class": 'vacancy-company-badge'}) and True
      
        full_adress = response_parsed.find("span",attrs = {"data-qa": 'vacancy-view-raw-address'})
        city_or_smth = response_parsed.find("p",attrs = {"data-qa": 'vacancy-view-location'})   
        vacancy["adress"] = (city_or_smth or full_adress).get_text() if city_or_smth or full_adress else ""
        
        vacancy["employment_mode"] = response_parsed.find("p",attrs = {"data-qa": 'vacancy-view-employment-mode'}).get_text()
        vacancy["experience"] = response_parsed.find("span", attrs = {"data-qa": 'vacancy-experience'}).get_text()
        
        part_time = response_parsed.find("p",attrs={"data-qa" : 'vacancy-view-parttime-options'})  
        vacancy["parttime"] = part_time.get_text() if part_time else False

        accept_temporary = response_parsed.find("p",attrs={"data-qa" : 'vacancy-view-accept-temporary'})  
        vacancy["accept_temporary"] = accept_temporary.get_text() if accept_temporary else False
        vacancy["creation-time"] = response_parsed.find("p",attrs={"class" : 'vacancy-creation-time'}).get_text() 
        
        tags = response_parsed.find_all("div",attrs = {"class": 'bloko-tag bloko-tag_inline',"data-qa": 'bloko-tag bloko-tag_inline skills-element'})
        vacancy["tag"] = list(tag.get_text() for tag in tags)
        
        # на скорую руку подчищаем вывод
        for key in vacancy:
            if type(vacancy[key]) == str:
                vacancy[key] = self.__sanitize_string(vacancy[key])
            elif type(vacancy[key]) == list:
                vacancy[key] = list(self.__sanitize_string(string) for string in vacancy[key])

        if parse_salary:
            vacancy["salary"] = self.parse_salary(vacancy["salary"])
        if parse_date:
            vacancy["creation-time"] = self.parse_date(vacancy["creation-time"])

        return vacancy

    def parse_vacancys(self, url_list = None, parse_salary = False, parse_date = False):

        vacancys_data = []
        if not url_list:
            url_list = self.scrapper.get_vacancy_links()

        for url in url_list: vacancys_data.append(self.parse_vacancy_page(url=url, parse_salary = parse_salary, parse_date = parse_date))

        return vacancys_data
    

