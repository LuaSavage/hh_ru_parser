from hhparser.scrapper import VacancyScrapper
from hhparser.parser import Parser
from hhparser.template_parser import DumpParser
from hhparser.api import Api

params = {
    "clusters": True,
    "ored_clusters": True,
    "enable_snippets": True,
    "salary": None,
    "text": "golang junior",
    "area": None,
    "page": 0
}

scrapper = VacancyScrapper(params = params)

hh_ru_api = Api(scrapper)

vac = hh_ru_api.get_vacancies(bless_fields=["description","key_skills"])
print(len(vac))
import json
print(json.dumps(vac, indent=4, ensure_ascii=False))
#DumpParser.parse_vacancy_page (scrapper.get_vacancy_page(url = "https://hh.ru/vacancy/50329861"))
