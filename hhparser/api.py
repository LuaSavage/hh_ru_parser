from .template_parser import DumpParser
from .bless import VacancyBlesser

class Api:
    
    def __init__(self, scrapper) -> None:
        self.scrapper = scrapper
        self.vacancy_blasser = VacancyBlesser(self.scrapper)

    def get_vacancy(self, id = None, url = None):
        vacancy_page = self.scrapper.get_vacancy_page(url, id = id)
        return DumpParser.parse_vacancy_page(vacancy_page)

    def get_vacancies(self, search_text = None, bless_fields = False):
        if search_text:
            self.scrapper.params["text"] = search_text

        all_vacancies = []
        print("page_count",self.scrapper.get_page_count(),self.scrapper.params["text"])
        for i in range(self.scrapper.get_page_count()):            
            vacancies = []

            while len(vacancies) == 0:    
                vacancies_page = self.scrapper.get_searching_results_page(page_number = i)                
                vacancies = DumpParser.parse_search_page(vacancies_page)
            print(len(vacancies),i)
            all_vacancies += vacancies

        if bless_fields:
            self.vacancy_blasser.bless_fields(all_vacancies, bless_fields)

        return all_vacancies