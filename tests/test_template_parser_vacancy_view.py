"""Unit tests for vacancyView layout changes on hh.ru."""

from hhparser.template_parser import DumpParser
from hhparser.vacancy_decorator import ViewVacancyDecorator


def test_vacancy_from_view_nested_vacancy_full():
    vacancy_view = {
        "vacancyFull": {
            "vacancy": {
                "vacancyId": 42,
                "name": "Go dev",
                "keySkills": ["Golang"],
                "publicationTimeIso": "2026-01-01T00:00:00+03:00",
            }
        },
        "mapDisabled": True,
    }
    vacancy = DumpParser._DumpParser__vacancy_from_view(vacancy_view)
    ViewVacancyDecorator(vacancy)
    assert vacancy["id"] == 42
    assert vacancy["name"] == "Go dev"
    assert vacancy["key_skills"] == ["Golang"]


def test_vacancy_from_view_legacy_flat():
    vacancy_view = {
        "vacancyId": 7,
        "name": "Legacy",
        "keySkills": ["Go"],
        "publicationTimeIso": "2026-01-01T00:00:00+03:00",
    }
    vacancy = DumpParser._DumpParser__vacancy_from_view(vacancy_view)
    ViewVacancyDecorator(vacancy)
    assert vacancy["id"] == 7


def test_vacancy_description_keeps_html():
    """description от HH идёт как есть: без html2text и без сноса переносов."""
    vacancy = {
        "id": 7,
        "description": "<p><strong>Мы — MyHeat.</strong></p>\n<ul><li>знание C/C++</li><li>STM32</li></ul>",
        "is_branding_preview": True,
    }
    ViewVacancyDecorator(vacancy)
    assert vacancy["description"] == (
        "<p><strong>Мы — MyHeat.</strong></p>\n<ul><li>знание C/C++</li><li>STM32</li></ul>"
    )
    assert vacancy["branded_description"] == vacancy["description"]
