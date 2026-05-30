import json

from .vacancy_decorator import SearchedVacancyDecorator, ViewVacancyDecorator


class DumpParser:
    @classmethod
    def __extract_raw_json(cls, page):
        noindex = page.find("noindex")
        if noindex:
            for child in noindex.children:
                if child.contents:
                    return child.contents[0]

        template = page.find("template", id="HH-Lux-InitialState")
        if template is not None:
            return template.string or template.get_text()

        raise ValueError("Page state JSON not found")

    @classmethod
    def __parse_template(cls, page):
        raw_json = cls.__extract_raw_json(page)
        return json.loads(json.dumps(json.loads(raw_json), indent=4, ensure_ascii=False))

    @classmethod
    def get_search_page_count(cls, searching_page):
        json_obj = cls.__parse_template(searching_page)
        paging = json_obj["vacancySearchResult"]["paging"]
        last_page = paging.get("lastPage")
        if last_page and "page" in last_page:
            return last_page["page"] + 1
        return 1

    @classmethod
    def parse_vacancy_page(cls, page):
        json_obj = cls.__parse_template(page)
        vacancy = json_obj["vacancyView"]
        ViewVacancyDecorator(vacancy)
        return vacancy

    @classmethod
    def parse_search_page(cls, searching_page):
        json_obj = cls.__parse_template(searching_page)
        vacancies = json_obj["vacancySearchResult"]["vacancies"]
        SearchedVacancyDecorator(vacancies)
        return vacancies
