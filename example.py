from hhparser.scrapper import VacancyScrapper
from hhparser.parser import Parser

params = {
    "clusters": False,
    "ored_clusters": False,
    "enable_snippets": False,
    "salary": None,
    "st": "searchVacancy",
    "text": "golang junior",
    "page": 0
}

scrapper = VacancyScrapper(params = params)
#links = scrapper.get_vacancy_links()
#print(links)
parser = Parser(scrapper = scrapper)
print(parser.parse_vacancy_page("https://hh.ru/vacancy/49363564", parse_salary=True, parse_date=True))
#print(parser.parse_vacancys(url_list=links))