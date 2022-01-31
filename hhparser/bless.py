from .template_parser import DumpParser

# Вакансии, получаемые на странице результатов поиска, не содержат полного описания
# ключевых навыков, и возможно, чего-то еще.
# Нижеследующее решение догружает информацию с персональной страницы вакансии

class VacancyBlesser:    

    def __init__(self, scrapper) -> None:
        self.scrapper = scrapper

    def __get_blesser(self,vacancy):
        page = self.scrapper.get_vacancy_page(vacancy["url"])
        return DumpParser.parse_vacancy_page(page)

    def bless_fields(self,vacancy,fields):
        if type(vacancy) == list:
            for vac in vacancy: self.bless_fields(vac,fields)
            return vacancy
        vacancy_full_data = self.__get_blesser(vacancy)
        for key in fields:
            if key in vacancy: vacancy[key] = vacancy_full_data[key]
        return vacancy