"""Разделы формы: какие поля показываются при каких переключателях."""

import pytest
from squirtcar import sections
from squirtcar.model import ALL_FIELDS, TOGGLES


def keys(section, s, kind="field"):
    return [key for k, key in sections.items(section, s) if k == kind]


@pytest.mark.parametrize("section", list(sections.BUILDERS))
def test_every_section_references_only_known_keys(section, have):
    for kind, key in sections.items(section, have):
        if kind == "field":
            assert key in ALL_FIELDS, key
        elif kind == "toggle":
            assert key in TOGGLES, key


@pytest.mark.parametrize("section", list(sections.BUILDERS))
def test_no_field_is_shown_twice_in_one_section(section, have):
    shown = keys(section, have)
    assert len(shown) == len(set(shown))


def test_menu_sections_all_have_builders():
    for mode, entries in sections.MENU.items():
        for key, _title in entries:
            assert key in sections.BUILDERS, (mode, key)
            assert key in sections.SECTION_TITLES, (mode, key)


# ============ ПЕРЕКЛЮЧАТЕЛИ ПРЯЧУТ ПОЛЯ ============


def test_manual_fuel_hides_price_and_consumption(have):
    shown = keys("cur", have)
    assert "fuelCost" in shown
    assert "fuelPrice" not in shown and "consumptionValue" not in shown


def test_price_fuel_shows_price_and_consumption(have):
    have.toggles["fuelMode"] = "price"
    shown = keys("cur", have)
    assert "fuelCost" not in shown
    assert "fuelPrice" in shown and "consumptionValue" in shown
    assert "consumptionUnit" in keys("cur", have, "toggle")


def test_credit_fields_appear_only_when_there_is_a_credit(have):
    assert "monthlyPayment" not in keys("cur", have)
    have.toggles["creditMode"] = "on"
    shown = keys("cur", have)
    for key in ("monthlyPayment", "interestRate", "totalMonths", "monthsAlreadyPaid"):
        assert key in shown


def test_manual_depreciation_hides_market_price(have):
    assert "depreciationManual" in keys("cur", have)
    have.toggles["depreciationMode"] = "auto"
    shown = keys("cur", have)
    assert "depreciationManual" not in shown
    assert "currentMarketPrice" in shown


def test_cash_payment_hides_loan_fields(have):
    assert "newCarRate" in keys("new", have)
    have.toggles["paymentMode"] = "cash"
    shown = keys("new", have)
    for key in ("newCarDownPayment", "newCarRate", "newCarTerm"):
        assert key not in shown


def test_trade_in_value_follows_its_toggle(have):
    assert "tradeInValue" in keys("new", have)
    have.toggles["tradeInMode"] = "off"
    assert "tradeInValue" not in keys("new", have)


def test_none_car_credit_fields_follow_the_payment_toggle(none):
    assert "ncDownPayment" in keys("car", none)
    none.toggles["ncPaymentMode"] = "cash"
    shown = keys("car", none)
    for key in ("ncDownPayment", "ncRate", "ncTerm"):
        assert key not in shown
