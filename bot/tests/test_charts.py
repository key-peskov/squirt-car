"""Графики: проверяем, что каждая тема рисуется и отдаёт валидный PNG."""

import pytest
from squirtcar import calc, charts

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
THEMES = ["light", "dark", "cyber"]


def is_png(data: bytes) -> bool:
    return data.startswith(PNG_MAGIC) and data.endswith(b"IEND\xaeB`\x82")


@pytest.mark.parametrize("theme", THEMES)
def test_cost_chart_renders_in_every_theme(theme, have, frozen_year):
    existing, new = calc.have_curves(have)
    png = charts.cost_chart(theme, existing, new, frozen_year, "текущая", "новая")
    assert is_png(png) and len(png) > 1000


@pytest.mark.parametrize("theme", THEMES)
def test_happiness_chart_renders_in_every_theme(theme, have, frozen_year):
    assert is_png(charts.happiness_chart(theme, calc.happiness(have)))


@pytest.mark.parametrize("theme", THEMES)
def test_have_savings_chart_renders_in_every_theme(theme, have):
    assert is_png(charts.have_savings_chart(theme, calc.have_savings(have)))


@pytest.mark.parametrize("theme", THEMES)
def test_none_savings_chart_renders_in_every_theme(theme, none):
    assert is_png(charts.none_savings_chart(theme, calc.none_savings(none)))


def test_charts_handle_negative_savings(have):
    have.values["newCarPrice"] = 20_000_000
    have.toggles["tradeInMode"] = "off"
    assert is_png(charts.have_savings_chart("light", calc.have_savings(have)))


def test_cost_chart_returns_none_when_there_is_nothing_to_draw(have, frozen_year):
    """Пустой расчёт — ₽/км везде нули, график не рисуется, а не падает."""
    for key in list(have.values):
        have.values[key] = 0
    existing, new = calc.have_curves(have)
    assert charts.cost_chart("light", existing, new, frozen_year, "текущая", "новая") is None


def test_savings_chart_handles_an_empty_state(have):
    for key in list(have.values):
        have.values[key] = 0
    assert is_png(charts.have_savings_chart("light", calc.have_savings(have)))


def test_unknown_theme_falls_back_instead_of_crashing(have, frozen_year):
    assert is_png(charts.happiness_chart("нет такой темы", calc.happiness(have)))
