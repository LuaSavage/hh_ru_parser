import json
from .vacancy_decorator import SearchedVacancyDecorator, ViewVacancyDecorator

class DumpParser:

    @classmethod
    def __parse_template(self, page):
        raw_json = None
        for ch in page.find('noindex').children: raw_json=ch.contents[0] 
        return json.loads(json.dumps(
            json.loads(raw_json), 
            indent=4, 
            ensure_ascii=False))

    @classmethod
    def parse_vacancy_page(self, page):
        json_obj =  self.__parse_template(page)  
        vacancy = json_obj["vacancyView"]
        ViewVacancyDecorator(vacancy)
        return vacancy

    @classmethod
    def parse_search_page(self, searching_page):    
        json_obj =  self.__parse_template(searching_page)
        vacancies = json_obj["vacancySearchResult"]["vacancies"]
        SearchedVacancyDecorator(vacancies)         
        return vacancies