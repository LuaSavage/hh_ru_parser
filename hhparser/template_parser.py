import json
from .vacancy_decorator import SearchedVacancyDecorator, ViewVacancyDecorator

class DumpParser:

    def __init__(self, scrapper = None):
        self.scrapper = scrapper

    def parse_template(self,page):
        raw_json = None
        for ch in page.find('noindex').children: raw_json=ch.contents[0] 
        raw_json = json.dumps(json.loads(raw_json), indent=4, ensure_ascii=False)
        return json.loads(raw_json) 

    def parse_vacancy_page(self, page):
        json_obj =  self.parse_template(page)  

        with open("vacancy.json", "w", encoding='utf-8') as file:
            file.write(json.dumps(json_obj, indent=4, ensure_ascii=False))      



        vacancy = json_obj["vacancyView"]
        decorated_vacancy = ViewVacancyDecorator(vacancy)
        vacancy_json = json.dumps(vacancy, indent=4, ensure_ascii=False)

        with open("vacancy_json.json", "w", encoding='utf-8') as file:
            file.write(vacancy_json)      

    def parse_search_page(self, searching_page):    
        json_obj =  self.parse_template(searching_page)
        vacancies = json_obj["vacancySearchResult"]["vacancies"]
        decorated_vacancies = SearchedVacancyDecorator(vacancies) 

        vacancies_json = json.dumps(vacancies, indent=4, ensure_ascii=False) 

        with open("vacancies_json.json", "w", encoding='utf-8') as file:
            file.write(vacancies_json)      
    








                


            


    def parse(self):
        tmp_page = self.scrapper.get_searching_results_page()
        self.parse_search_page(tmp_page)




    

