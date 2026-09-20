"""Текстовый отчёт: форматирование, ветки инсайтов, безопасность разметки."""

import re

import pytest
from squirtcar import calc, report
from squirtcar.report import NBSP

TAG = re.compile(r"</?([a-z]+)>")
ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "a"}  # то, что понимает Telegram HTML


def test_fmt_groups_thousands_with_nbsp():
    assert report.fmt(1_234_567) == f"1{NBSP}234{NBSP}567"
    assert report.fmt(999) == "999"


def test_fmt_rounds_like_js_math_round():
    assert report.fmt(0.5) == "1"
    assert report.fmt(1.5) == "2"
    assert report.fmt(2.5) == "3"
    assert report.fmt(-0.4) == "0"


def test_fmt_keeps_the_minus_for_negative_sums():
    assert report.fmt(-1_234_567) == f"-1{NBSP}234{NBSP}567"


@pytest.mark.parametrize("v", [float("nan"), float("inf"), float("-inf"), "абв", None])
def test_fmt_swallows_broken_numbers(v):
    assert report.fmt(v) == "0"


# ============ ИНСАЙТЫ ============


def test_loan_comparison_cash_without_trade_in(have):
    have.toggles["paymentMode"] = "cash"
    have.toggles["tradeInMode"] = "off"
    text = report.loan_comparison(have, calc.have_new_car_loan(have))
    assert "Доплата наличными" in text
    assert report.fmt(3_000_000) in text


def test_loan_comparison_cash_fully_covered_by_trade_in(have):
    have.toggles["paymentMode"] = "cash"
    have.values["tradeInValue"] = 3_500_000
    assert "Доплата не нужна" in report.loan_comparison(have, calc.have_new_car_loan(have))


def test_loan_comparison_credit_not_needed(have):
    have.values["newCarDownPayment"] = 2_000_000
    assert "Кредит не нужен" in report.loan_comparison(have, calc.have_new_car_loan(have))


def test_loan_comparison_warns_when_overpay_exceeds_third_of_price(have):
    have.toggles["tradeInMode"] = "off"
    have.values["newCarDownPayment"] = 0
    have.values["newCarTerm"] = 84
    text = report.loan_comparison(have, calc.have_new_car_loan(have))
    assert "Переплата по кредиту" in text
    assert "⚠️" in text


def test_happiness_insight_reads_the_slope(have, frozen_year):
    falling = report.happiness_insight(calc.happiness(have))
    assert "теряет радость" in falling

    have.values["happyAtPurchase"] = 3
    have.values["happyNow"] = 9
    assert "радует всё больше" in report.happiness_insight(calc.happiness(have))

    have.values["happyAtPurchase"] = 6
    have.values["happyNow"] = 6
    assert "стабильна" in report.happiness_insight(calc.happiness(have))


def test_happiness_insight_warns_about_a_grim_forecast(have, frozen_year):
    have.values["happyAtPurchase"] = 10
    have.values["happyNow"] = 2
    assert "перестанет радовать" in report.happiness_insight(calc.happiness(have))


def test_have_savings_insight_names_all_three_paths(have):
    text = report.have_savings_insight(calc.have_savings(have))
    assert "с текущей" in text and "с новой" in text and "без машины" in text
    assert "Оставить текущую выгоднее" in text


def test_have_savings_insight_flags_going_negative(have):
    have.values["newCarPrice"] = 30_000_000
    have.toggles["tradeInMode"] = "off"
    assert "уйдёте в минус" in report.have_savings_insight(calc.have_savings(have))


def test_none_savings_insight_warns_when_the_car_eats_half_the_savings(none):
    none.values["ncPrice"] = 800_000
    none.values["ncDownPayment"] = 200_000
    text = report.none_savings_insight(calc.none_savings(none))
    assert "больше половины" in text
    assert "уйдёте в минус" not in text


def test_none_savings_insight_flags_going_negative(none):
    none.values["ncPrice"] = 20_000_000
    assert "уйдёте в минус" in report.none_savings_insight(calc.none_savings(none))


# ============ ОТЧЁТ ЦЕЛИКОМ ============


def test_have_report_contains_every_block(have):
    text = report.report(have)
    for block in ("Текущая машина", "Новая машина", "Жизнь без машины",
                  "Кредит на новую", "Накопления через 10 лет", "Счастье"):
        assert block in text


def test_none_report_contains_every_block(none):
    text = report.report(none)
    for block in ("Машина, ₽/мес", "Жизнь, ₽/мес", "Кредит", "Накопления через 10 лет"):
        assert block in text


def test_report_uses_only_tags_telegram_understands(have, none):
    for text in (report.report(have), report.report(none)):
        assert set(TAG.findall(text)) <= ALLOWED_TAGS


def test_car_model_is_escaped_and_cannot_inject_markup(have):
    have.values["carModel"] = "<b>bold</b> & <script>alert(1)</script>"
    text = report.report(have)
    assert "<script>" not in text
    assert "&lt;script&gt;" in text and "&amp;" in text


def test_report_survives_a_completely_empty_state(have, none):
    for s in (have, none):
        for key in list(s.values):
            s.values[key] = 0
        assert report.report(s)  # без ZeroDivisionError


def test_credit_block_appears_only_with_the_toggle_on(have):
    assert "Кредит на текущую" not in report.report(have)
    have.toggles["creditMode"] = "on"
    assert "Кредит на текущую" in report.report(have)


def test_depreciation_line_appears_only_in_auto_mode(have):
    assert "Потери от амортизации" not in report.report(have)
    have.toggles["depreciationMode"] = "auto"
    assert "Потери от амортизации" in report.report(have)
