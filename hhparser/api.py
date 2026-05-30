import logging

from .bless import VacancyBlesser
from .template_parser import DumpParser

logger = logging.getLogger(__name__)


class Api:
    def __init__(self, scrapper) -> None:
        self.scrapper = scrapper
        self.vacancy_blesser = VacancyBlesser(self.scrapper)

    def get_vacancy(self, id=None, url=None):
        vacancy_page = self.scrapper.get_vacancy_page(url, id=id)
        return DumpParser.parse_vacancy_page(vacancy_page)

    def get_vacancies(self, search_text=None, bless_fields=False):
        if search_text:
            self.scrapper.params["text"] = search_text

        all_vacancies = []
        page_count = self.scrapper.get_page_count()
        logger.info("page_count=%s text=%s", page_count, self.scrapper.params["text"])
        for page_number in range(page_count):
            vacancies = []

            while len(vacancies) == 0:
                vacancies_page = self.scrapper.get_searching_results_page(page_number=page_number)
                vacancies = DumpParser.parse_search_page(vacancies_page)
            logger.debug("page=%s vacancies=%s", page_number, len(vacancies))
            all_vacancies += vacancies

        if bless_fields:
            self.vacancy_blesser.bless_fields(all_vacancies, bless_fields)

        return all_vacancies
