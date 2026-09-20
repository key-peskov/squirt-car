"""Математика: формулы сверяются независимым способом, а не повтором реализации."""

import pytest
from squirtcar import calc


def pv_of_payments(monthly: float, months: float, rate_pct: float) -> float:
    """Текущая стоимость потока платежей — независимая проверка аннуитета."""
    mr = rate_pct / 100 / 12
    return sum(monthly / (1 + mr) ** m for m in range(1, int(months) + 1))


# ============ АННУИТЕТ ============


def test_annuity_payments_discount_back_to_principal():
    a = calc.compute_annuity(1_000_000, 19.2, 60)
    assert pv_of_payments(a.monthly, 60, 19.2) == pytest.approx(1_000_000, rel=1e-9)
    assert a.overpay == pytest.approx(a.monthly * 60 - 1_000_000)


def test_annuity_without_rate_is_simple_division():
    a = calc.compute_annuity(600_000, 0, 60)
    assert a.monthly == pytest.approx(10_000)
    assert a.overpay == pytest.approx(0)


@pytest.mark.parametrize("principal,months", [(0, 60), (-100, 60), (1_000_000, 0)])
def test_annuity_degenerate_input_is_zero(principal, months):
    a = calc.compute_annuity(principal, 19.2, months)
    assert (a.monthly, a.overpay) == (0.0, 0.0)


# ============ ТОПЛИВО ============


def test_fuel_per_100km():
    # 15 000 км при 8.5 л/100 км = 1275 л по 60 ₽
    assert calc.compute_fuel_annual(15_000, 60, 8.5, "per100") == pytest.approx(76_500)


def test_fuel_km_per_liter_is_the_other_direction():
    assert calc.compute_fuel_annual(15_000, 60, 8.5, "kmPer") == pytest.approx(15_000 / 8.5 * 60)


@pytest.mark.parametrize(
    "distance,price,consumption", [(0, 60, 8.5), (15_000, 0, 8.5), (15_000, 60, 0)]
)
def test_fuel_zero_when_any_component_missing(distance, price, consumption):
    assert calc.compute_fuel_annual(distance, price, consumption, "per100") == 0.0


# ============ ВРЕМЯ ============


def test_time_saved_counts_both_directions():
    ts = calc.compute_time_saved(5, 45, 25)
    # (45-25) мин × 5 поездок × 2 конца = 200 мин/нед
    assert ts.hours_per_month == pytest.approx(200 / 60 * 4.33)
    assert ts.hours_per_year == pytest.approx(200 / 60 * 52)


def test_time_saved_is_negative_when_new_car_is_slower():
    assert calc.compute_time_saved(5, 25, 45).hours_per_month < 0


def test_time_saved_zero_on_empty_input():
    assert calc.compute_time_saved(0, 45, 25).hours_per_month == 0.0


# ============ НАКОПЛЕНИЯ ============


def test_savings_without_rate_are_linear():
    pts = calc.simulate_savings(3, monthly_outflow=10_000, monthly_net=30_000,
                                start_capital=500_000, rate_annual=0)
    assert [p[0] for p in pts] == [0, 1, 2, 3]
    assert pts[0][1] == 500_000
    assert pts[3][1] == pytest.approx(500_000 + 20_000 * 36)


def test_monthly_rate_compounds_exactly_to_annual():
    pts = calc.simulate_savings(1, 0, 0, 100_000, 0.08)
    assert pts[-1][1] == pytest.approx(108_000)


def test_outflow_can_drive_balance_negative():
    pts = calc.simulate_savings(5, monthly_outflow=50_000, monthly_net=0,
                                start_capital=100_000, rate_annual=0)
    assert pts[-1][1] < 0


# ============ КРИВАЯ ВЛАДЕНИЯ ============


CURVE_KW = dict(
    purchase_price=1_000_000,
    annual_km=10_000,
    operating_base=100_000,
    operating_growth=0.05,
    credit_monthly=0.0,
    total_months=0.0,
    start_age=0,
    start_calendar_year=2026,
    include_purchase_in_year0=False,
    one_time_year0=0.0,
)


def test_curve_year_zero_is_operating_plus_depreciation():
    pts = calc.build_curve(3, **CURVE_KW)
    # амортизация первого года: 1 000 000 → 850 000
    assert pts[0].total == pytest.approx(100_000 + 150_000)
    assert pts[0].calendar_year == 2026
    assert pts[0].per_km == pytest.approx(250_000 / 10_000)


def test_curve_operating_grows_by_the_given_rate():
    pts = calc.build_curve(3, **CURVE_KW)
    dep_second_year = 1_000_000 * (0.85 - 0.85**2)
    assert pts[1].total - dep_second_year == pytest.approx(100_000 * 1.05)


def test_curve_depreciation_stops_at_the_ten_percent_floor():
    pts = calc.build_curve(40, **CURVE_KW)
    # 0.85^40 давно ниже 10%, обе оценки упёрлись в пол — амортизации больше нет
    assert pts[40].total == pytest.approx(100_000 * 1.05**40)


def test_curve_purchase_lands_only_in_year_zero():
    with_purchase = calc.build_curve(2, **{**CURVE_KW, "include_purchase_in_year0": True})
    without = calc.build_curve(2, **CURVE_KW)
    assert with_purchase[0].total - without[0].total == pytest.approx(1_000_000)
    assert with_purchase[1].total == pytest.approx(without[1].total)


def test_curve_spreads_credit_over_its_term_only():
    kw = {**CURVE_KW, "credit_monthly": 10_000, "total_months": 18}
    pts = calc.build_curve(3, **kw)
    base = calc.build_curve(3, **CURVE_KW)
    assert pts[0].total - base[0].total == pytest.approx(120_000)  # 12 платежей
    assert pts[1].total - base[1].total == pytest.approx(60_000)  # оставшиеся 6
    assert pts[2].total == pytest.approx(base[2].total)


def test_curve_credit_offset_shifts_remaining_payments():
    kw = {**CURVE_KW, "credit_monthly": 10_000, "total_months": 18, "credit_start_offset": 12}
    pts = calc.build_curve(3, **kw)
    base = calc.build_curve(3, **CURVE_KW)
    assert pts[0].total - base[0].total == pytest.approx(60_000)  # 6 платежей остатка
    assert pts[1].total == pytest.approx(base[1].total)


def test_curve_older_car_depreciates_slower():
    young = calc.build_curve(1, **CURVE_KW)[0].total
    old = calc.build_curve(1, **{**CURVE_KW, "start_age": 8})[0].total
    assert old < young
