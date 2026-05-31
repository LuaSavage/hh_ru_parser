import json

from bs4 import NavigableString, Tag

from .vacancy_decorator import SearchedVacancyDecorator, ViewVacancyDecorator


class DumpParser:
    @classmethod
    def __extract_raw_json(cls, page):
        candidates: list[str] = []

        noindex = page.find("noindex")
        if noindex is not None:
            for template in noindex.find_all("template", id="HH-Lux-InitialState"):
                candidates.append(template.string or template.get_text())
            for script in noindex.find_all("script"):
                candidates.append(script.string or script.get_text())
            for child in noindex.children:
                if isinstance(child, NavigableString):
                    candidates.append(str(child))
                elif isinstance(child, Tag) and child.get("id") == "HH-Lux-InitialState":
                    candidates.append(child.string or child.get_text())

        template = page.find("template", id="HH-Lux-InitialState")
        if template is not None:
            candidates.append(template.string or template.get_text())

        for raw in candidates:
            if not raw:
                continue
            text = raw.strip()
            if text.startswith("{"):
                return text

        raise ValueError("Page state JSON not found")

    @classmethod
    def __parse_template(cls, page):
        raw_json = cls.__extract_raw_json(page)
        return json.loads(json.dumps(json.loads(raw_json), indent=4, ensure_ascii=False))

    @classmethod
    def page_has_expected_state(cls, page, kind: str) -> bool:
        if page is None:
            return False
        try:
            json_obj = cls.__parse_template(page)
        except (ValueError, json.JSONDecodeError, TypeError):
            return False

        if kind == "search":
            return "vacancySearchResult" in json_obj
        if kind == "vacancy":
            return "vacancyView" in json_obj
        return False

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
        if "vacancyView" not in json_obj:
            raise ValueError("vacancyView not found in page state (blocked or incomplete page)")
        vacancy = json_obj["vacancyView"]
        ViewVacancyDecorator(vacancy)
        return vacancy

    @classmethod
    def parse_search_page(cls, searching_page):
        json_obj = cls.__parse_template(searching_page)
        vacancies = json_obj["vacancySearchResult"]["vacancies"]
        SearchedVacancyDecorator(vacancies)
        return vacancies
