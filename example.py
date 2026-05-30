import json
import logging

from hhparser import Api, VacancyScrapper, configure_logging

configure_logging(logging.INFO)

params = {
    "clusters": True,
    "ored_clusters": True,
    "enable_snippets": True,
    "salary": None,
    "text": "golang junior",
    "area": None,
    "page": 0,
}

scrapper = VacancyScrapper(params=params)
hh_ru_api = Api(scrapper)

vac = hh_ru_api.get_vacancies(bless_fields=["description", "key_skills"])

logging.getLogger(__name__).info("Total vacancies: %s", len(vac))
print(json.dumps(vac, indent=4, ensure_ascii=False))
