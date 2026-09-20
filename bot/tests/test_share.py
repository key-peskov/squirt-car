"""HTML-экспорт: та же структура, что у кнопки «Поделиться» в вебе."""

import pytest
from squirtcar import share
from squirtcar.calc import have_current_monthly
from squirtcar.report import fmt


def test_have_export_is_a_whole_document(have):
    html = share.build_shared_html(have)
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert 'lang="ru"' in html and 'charset="UTF-8"' in html
    assert "SquirtCar — Расчёт: есть машина" in html


def test_none_export_has_its_own_title(none):
    assert "SquirtCar — Расчёт: нет машины" in share.build_shared_html(none)


def test_export_carries_the_numbers_from_the_calculation(have):
    html = share.build_shared_html(have)
    assert fmt(have_current_monthly(have)) in html


@pytest.mark.parametrize("mode", ["have", "none"])
def test_personal_and_savings_blocks_can_be_dropped(mode, have, none):
    s = have if mode == "have" else none
    full = share.build_shared_html(s)
    stripped = share.build_shared_html(s, include_personal=False, include_savings=False)
    assert "<h2>🏠 Личные расходы</h2>" in full
    assert "<h2>🏠 Личные расходы</h2>" not in stripped
    assert "Личные расходы не включены" in stripped
    assert "Накопления не включены" in stripped
    assert len(stripped) < len(full)


def test_model_name_is_escaped_in_the_export(have):
    have.values["carModel"] = '<script>alert("x")</script>'
    html = share.build_shared_html(have)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_tags_are_balanced_enough_to_render(have):
    html = share.build_shared_html(have)
    assert html.count("<div") == html.count("</div>")
    assert html.count("<span") == html.count("</span>")
    assert html.count("<strong") == html.count("</strong>")


def test_export_survives_an_empty_state(have):
    for key in list(have.values):
        have.values[key] = 0
    assert share.build_shared_html(have).startswith("<!DOCTYPE html>")
