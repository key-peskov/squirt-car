"""Сценарии «есть машина» / «нет машины»: как переключатели меняют расчёт."""

import pytest
from squirtcar import calc

from .test_calc import pv_of_payments

# ============ ЭКСПЛУАТАЦИЯ ============


def test_operating_sums_all_cost_lines(have):
    # дефолты: топливо 96 000 + страховка 24 000 + ТО 30 000 + налоги 12 000 + прочее 18 000
    assert calc.have_operating(have) == pytest.approx(180_000)


def test_fuel_mode_switches_from_manual_sum_to_price_times_consumption(have):
    have.toggles["fuelMode"] = "price"
    assert calc.have_fuel_annual(have) == pytest.approx(76_500)
    assert calc.have_operating(have) == pytest.approx(76_500 + 84_000)


# ============ АМОРТИЗАЦИЯ ============


def test_manual_depreciation_is_taken_as_is(have):
    assert calc.have_depreciation(have) == pytest.approx(120_000)


def test_auto_depreciation_spreads_the_loss_over_years_owned(have, frozen_year):
    have.toggles["depreciationMode"] = "auto"
    # (2 000 000 − 1 400 000) за 2026 − 2021 = 5 лет
    assert calc.have_depreciation(have) == pytest.approx(120_000)


def test_auto_depreciation_ignores_future_purchase_year(have, frozen_year):
    have.toggles["depreciationMode"] = "auto"
    have.values["purchaseYear"] = frozen_year + 1
    assert calc.have_depreciation(have) == 0.0


def test_residual_is_market_price_in_auto_mode(have):
    have.toggles["depreciationMode"] = "auto"
    assert calc.have_residual(have) == pytest.approx(1_400_000)


def test_residual_in_manual_mode_subtracts_yearly_loss(have, frozen_year):
    assert calc.have_residual(have) == pytest.approx(2_000_000 - 120_000 * 5)


def test_residual_never_goes_below_zero(have, frozen_year):
    have.values["depreciationManual"] = 900_000
    assert calc.have_residual(have) == 0.0


# ============ ТЕКУЩИЙ КРЕДИТ ============


def test_credit_is_ignored_while_the_toggle_is_off(have):
    assert calc.have_credit_yearly(have) == 0.0
    assert calc.have_credit_overpay(have) == 0.0


def test_credit_overpay_counts_only_remaining_payments(have):
    have.toggles["creditMode"] = "on"
    # 60 мес всего, 24 выплачено → остаток 36 платежей по 25 000 под 19.2%
    principal = pv_of_payments(25_000, 36, 19.2)
    assert calc.have_credit_overpay(have) == pytest.approx(25_000 * 36 - principal, rel=1e-9)
    assert calc.have_credit_yearly(have) == pytest.approx(300_000)


def test_fully_paid_credit_has_no_overpay(have):
    have.toggles["creditMode"] = "on"
    have.values["monthsAlreadyPaid"] = 60
    assert calc.have_credit_overpay(have) == 0.0


# ============ НОВАЯ МАШИНА ============


def test_trade_in_reduces_the_effective_price(have):
    loan = calc.have_new_car_loan(have)
    assert loan.trade_in == pytest.approx(1_400_000)
    assert loan.effective_price == pytest.approx(3_000_000 - 1_400_000)
    assert loan.principal == pytest.approx(1_600_000 - 600_000)
    assert pv_of_payments(loan.monthly, 60, 19.2) == pytest.approx(loan.principal, rel=1e-9)


def test_trade_in_off_keeps_the_full_price(have):
    have.toggles["tradeInMode"] = "off"
    loan = calc.have_new_car_loan(have)
    assert loan.trade_in == 0.0
    assert loan.effective_price == pytest.approx(3_000_000)


def test_trade_in_above_price_does_not_make_the_car_free_money(have):
    have.values["tradeInValue"] = 5_000_000
    assert calc.have_new_car_loan(have).effective_price == 0.0


def test_cash_purchase_has_no_loan(have):
    have.toggles["paymentMode"] = "cash"
    loan = calc.have_new_car_loan(have)
    assert (loan.monthly, loan.overpay, loan.principal) == (0.0, 0.0, 0.0)


def test_new_car_operating_grows_by_the_configured_percent(have):
    assert calc.have_new_operating(have) == pytest.approx(180_000 * 1.05)


# ============ НАКОПЛЕНИЯ ============


def test_keeping_a_car_costs_less_than_buying_a_new_one(have):
    sav = calc.have_savings(have)
    assert sav.no_car_end > sav.keep_end > sav.new_end


def test_cash_purchase_takes_the_whole_price_out_of_savings_upfront(have):
    have.toggles["paymentMode"] = "cash"
    sav = calc.have_savings(have)
    assert sav.new[0][1] == pytest.approx(500_000 - 1_600_000)


def test_credit_purchase_takes_only_the_down_payment_upfront(have):
    sav = calc.have_savings(have)
    assert sav.new[0][1] == pytest.approx(500_000 - 600_000)


def test_loan_payment_stops_after_the_term(have):
    """После 60-го месяца платёж уходит из расходов — поток становится легче."""
    sav = calc.have_savings(have)
    fifth_year = sav.new[5][1] - sav.new[4][1]
    seventh_year = sav.new[7][1] - sav.new[6][1]
    assert seventh_year > fifth_year


def test_savings_horizon_is_ten_years(have):
    sav = calc.have_savings(have)
    assert [p[0] for p in sav.keep] == list(range(11))


def test_spending_more_than_income_leaves_net_flow_at_zero(have):
    have.values["monthlyIncome"] = 1_000
    a = calc.have_savings(have).no_car_end
    have.values["monthlyIncome"] = 0
    assert calc.have_savings(have).no_car_end == pytest.approx(a)


# ============ СЦЕНАРИЙ «НЕТ МАШИНЫ» ============


def test_none_operating_and_depreciation(none):
    assert calc.nc_operating(none) == pytest.approx(180_000)
    assert calc.nc_depreciation(none) == pytest.approx(2_000_000 * 0.15)


def test_none_loan_has_no_trade_in(none):
    loan = calc.nc_loan(none)
    assert loan.trade_in == 0.0
    assert loan.principal == pytest.approx(2_000_000 - 400_000)


def test_buying_a_car_always_eats_savings(none):
    sav = calc.none_savings(none)
    assert sav.no_car_end > sav.car_end


def test_none_cash_purchase_hits_savings_immediately(none):
    none.toggles["ncPaymentMode"] = "cash"
    assert calc.none_savings(none).car[0][1] == pytest.approx(500_000 - 2_000_000)


# ============ СЧАСТЬЕ ============


def test_happiness_slope_and_forecast(have, frozen_year):
    h = calc.happiness(have)
    assert (h.at_purchase, h.at_now) == (9, 6)
    assert h.slope == pytest.approx((6 - 9) / 5)
    assert h.series[0] == (2021, 9.0)
    assert h.series[1] == (2026, 6.0)
    assert h.series[-1][0] == 2036


def test_happiness_forecast_is_clamped_to_one_ten(have, frozen_year):
    have.values["happyAtPurchase"] = 10
    have.values["happyNow"] = 1
    assert min(v for _, v in calc.happiness(have).series) >= 1.0
    have.values["happyAtPurchase"] = 1
    have.values["happyNow"] = 10
    assert max(v for _, v in calc.happiness(have).series) <= 10.0


def test_happiness_survives_a_car_bought_this_year(have, frozen_year):
    have.values["purchaseYear"] = frozen_year
    assert calc.happiness(have).slope == pytest.approx(6 - 9)  # делим на 1 год, не на 0


# ============ КРИВЫЕ ============


def test_have_curves_start_from_purchase_year_and_today(have, frozen_year):
    existing, new = calc.have_curves(have)
    assert existing[0].calendar_year == 2021
    assert new[0].calendar_year == 2026
    assert len(existing) == len(new) == calc.CURVE_YEARS + 1


def test_none_curve_includes_the_purchase_in_year_zero(none, frozen_year):
    pts = calc.none_curve(none)
    assert pts[0].total > pts[1].total + 1_000_000
    assert pts[0].calendar_year == 2026
