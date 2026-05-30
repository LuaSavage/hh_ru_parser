from .template_parser import DumpParser


class VacancyBlesser:
    """
    Зачастую вакансии, полученные из результатов поиска, содержат неполную информацию.
    Класс реализует дополнение полей вакансии/вакансий путем получения данных с их страниц.
    """

    def __init__(self, scrapper) -> None:
        self.scrapper = scrapper

    def __get_blesser(self, vacancy):
        if "url" in vacancy:
            page = self.scrapper.get_vacancy_page(vacancy["url"])
        elif "id" in vacancy:
            page = self.scrapper.get_vacancy_page(id=str(vacancy["id"]))
        else:
            raise ValueError("Vacancy must contain 'url' or 'id' to bless fields")
        return DumpParser.parse_vacancy_page(page)

    def bless_fields(self, vacancy, fields):
        if isinstance(vacancy, list):
            for vac in vacancy:
                self.bless_fields(vac, fields)
            return vacancy

        vacancy_full_data = self.__get_blesser(vacancy)
        for key in fields:
            if key in vacancy_full_data:
                vacancy[key] = vacancy_full_data[key]
        return vacancy
