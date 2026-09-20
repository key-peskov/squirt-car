"""Математика калькулятора — построчный порт скрипта из SquirtCar_0.1.2.html.

Имена функций сохранены (computeAnnuity, getHaveOperating, ...), чтобы
расхождения с HTML можно было находить сверкой по названию.
"""

from dataclasses import dataclass
from datetime import date

from .model import State

YEARS_HORIZON = 10
CURVE_YEARS = 15


def current_year() -> int:
    return date.today().year


# ============ БАЗОВЫЕ ФОРМУЛЫ ============


@dataclass
class Annuity:
    monthly: float = 0.0
    overpay: float = 0.0


def compute_annuity(principal: float, rate_pct: float, months: float) -> Annuity:
    if principal <= 0 or months <= 0:
        return Annuity()
    mr = rate_pct / 100 / 12
    if mr <= 0:
        monthly = principal / months
    else:
        monthly = principal * mr * (1 + mr) ** months / ((1 + mr) ** months - 1)
    return Annuity(monthly=monthly, overpay=monthly * months - principal)


def compute_fuel_annual(distance: float, price: float, consumption: float, unit: str) -> float:
    if distance <= 0 or price <= 0 or consumption <= 0:
        return 0.0
    liters = (distance / 100) * consumption if unit == "per100" else distance / consumption
    return liters * price


@dataclass
class TimeSaved:
    hours_per_month: float = 0.0
    hours_per_year: float = 0.0


def compute_time_saved(trips: float, time_now: float, time_new: float) -> TimeSaved:
    if trips <= 0 or time_now <= 0 or time_new <= 0:
        return TimeSaved()
    min_per_week = (time_now - time_new) * trips * 2
    hours_per_week = min_per_week / 60
    return TimeSaved(hours_per_week * 4.33, hours_per_week * 52)


def simulate_savings(
    years: int, monthly_outflow: float, monthly_net: float, start_capital: float, rate_annual: float
) -> list[tuple[int, float]]:
    """Помесячная симуляция с капитализацией, точки — на конец каждого года."""
    monthly_rate = (1 + rate_annual) ** (1 / 12) - 1
    bal = start_capital
    points = [(0, bal)]
    for m in range(1, years * 12 + 1):
        bal = bal * (1 + monthly_rate) + monthly_net - monthly_outflow
        if m % 12 == 0:
            points.append((m // 12, bal))
    return points


@dataclass
class CurvePoint:
    year: int
    calendar_year: int
    per_km: float
    total: float


def build_curve(
    max_years: int,
    *,
    purchase_price: float,
    annual_km: float,
    operating_base: float,
    operating_growth: float,
    credit_monthly: float,
    total_months: float,
    start_age: int,
    start_calendar_year: int,
    include_purchase_in_year0: bool,
    one_time_year0: float,
    credit_start_offset: int = 0,
) -> list[CurvePoint]:
    """Стоимость владения по годам: эксплуатация + амортизация + кредит."""
    pts: list[CurvePoint] = []
    for y in range(max_years + 1):
        age = start_age + y
        operating = operating_base * (1 + operating_growth) ** y
        floor = purchase_price * 0.10
        value = max(floor, purchase_price * 0.85**age)
        value_next = max(floor, purchase_price * 0.85 ** (age + 1))
        dep = value - value_next

        credit = 0.0
        if credit_monthly > 0 and total_months > 0:
            paid_start_year = credit_start_offset + y * 12
            paid_end_year = credit_start_offset + (y + 1) * 12
            rem_start = max(0.0, total_months - paid_start_year)
            rem_end = max(0.0, total_months - paid_end_year)
            credit = credit_monthly * max(0.0, rem_start - rem_end)

        purchase_hit = purchase_price if (y == 0 and include_purchase_in_year0) else 0.0
        one_time = one_time_year0 if y == 0 else 0.0
        total = operating + dep + credit + purchase_hit + one_time
        pts.append(
            CurvePoint(
                year=y,
                calendar_year=start_calendar_year + y,
                per_km=total / max(1.0, annual_km),
                total=total,
            )
        )
    return pts


# ============ СЦЕНАРИЙ «ЕСТЬ МАШИНА» ============


@dataclass
class Loan:
    price: float = 0.0
    trade_in: float = 0.0
    effective_price: float = 0.0
    principal: float = 0.0
    monthly: float = 0.0
    overpay: float = 0.0
    term: float = 0.0


def have_fuel_annual(s: State) -> float:
    if s.toggles["fuelMode"] == "manual":
        return s.num("fuelCost")
    return compute_fuel_annual(
        s.num("distanceValue"),
        s.num("fuelPrice"),
        s.num("consumptionValue"),
        s.toggles["consumptionUnit"],
    )


def have_operating(s: State) -> float:
    return (
        have_fuel_annual(s)
        + s.num("insurance")
        + s.num("maintenance")
        + s.num("taxes")
        + s.num("other")
    )


def have_auto_depreciation(s: State) -> float:
    if s.toggles["depreciationMode"] != "auto":
        return 0.0
    p, py, cp = s.num("purchasePrice"), s.num("purchaseYear"), s.num("currentMarketPrice")
    cy = current_year()
    if py <= 0 or py > cy:
        return 0.0
    return max(0.0, p - cp) / max(1, cy - int(py))


def have_depreciation(s: State) -> float:
    if s.toggles["depreciationMode"] == "manual":
        return s.num("depreciationManual")
    return have_auto_depreciation(s)


def have_credit_yearly(s: State) -> float:
    return s.num("monthlyPayment") * 12 if s.toggles["creditMode"] == "on" else 0.0


def have_credit_overpay(s: State) -> float:
    if s.toggles["creditMode"] == "off":
        return 0.0
    m = s.num("monthlyPayment")
    remaining = max(0.0, s.num("totalMonths") - s.num("monthsAlreadyPaid"))
    r = s.num("interestRate")
    if m <= 0 or remaining <= 0 or r <= 0:
        return 0.0
    mr = r / 100 / 12
    principal = m * (1 - (1 + mr) ** -remaining) / mr
    return max(0.0, m * remaining - principal)


def have_residual(s: State) -> float:
    """Остаточная стоимость текущей машины — подставляется в цену продажи."""
    if s.toggles["depreciationMode"] == "auto":
        return s.num("currentMarketPrice")
    p, py, dep = s.num("purchasePrice"), s.num("purchaseYear"), s.num("depreciationManual")
    if py <= 0:
        return p
    return max(0.0, p - dep * max(0, current_year() - int(py)))


def have_current_monthly(s: State) -> float:
    return (have_operating(s) + have_depreciation(s) + have_credit_yearly(s)) / 12


def have_trade_in(s: State) -> float:
    return 0.0 if s.toggles["tradeInMode"] == "off" else s.num("tradeInValue")


def have_new_car_loan(s: State) -> Loan:
    price = s.num("newCarPrice")
    trade_in = have_trade_in(s)
    effective = max(0.0, price - trade_in)
    loan = Loan(price=price, trade_in=trade_in, effective_price=effective)
    if s.toggles["paymentMode"] == "credit":
        loan.principal = max(0.0, effective - s.num("newCarDownPayment"))
        loan.term = s.num("newCarTerm")
        a = compute_annuity(loan.principal, s.num("newCarRate"), loan.term)
        loan.monthly, loan.overpay = a.monthly, a.overpay
    return loan


def have_new_operating(s: State) -> float:
    growth = (s.num("newCarOpGrowth") or 5) / 100
    return have_operating(s) * (1 + growth)


def have_new_monthly(s: State) -> float:
    dep = s.num("newCarPrice") * 0.15
    loan = have_new_car_loan(s)
    credit = loan.monthly if s.toggles["paymentMode"] == "credit" else 0.0
    return (have_new_operating(s) + dep) / 12 + credit


def have_personal_monthly(s: State) -> float:
    return s.num("expFood") + s.num("expHousing") + s.num("expComms") + s.num("expOther")


# ============ СЦЕНАРИЙ «НЕТ МАШИНЫ» ============


def nc_fuel_annual(s: State) -> float:
    if s.toggles["ncFuelMode"] == "manual":
        return s.num("ncFuel")
    return compute_fuel_annual(
        s.num("ncDistance"),
        s.num("ncFuelPrice"),
        s.num("ncConsumptionValue"),
        s.toggles["ncConsumptionUnit"],
    )


def nc_operating(s: State) -> float:
    return (
        nc_fuel_annual(s)
        + s.num("ncInsurance")
        + s.num("ncMaintenance")
        + s.num("ncTaxes")
        + s.num("ncOther")
    )


def nc_loan(s: State) -> Loan:
    price = s.num("ncPrice")
    loan = Loan(price=price, effective_price=price)
    if s.toggles["ncPaymentMode"] == "credit":
        loan.principal = max(0.0, price - s.num("ncDownPayment"))
        loan.term = s.num("ncTerm")
        a = compute_annuity(loan.principal, s.num("ncRate"), loan.term)
        loan.monthly, loan.overpay = a.monthly, a.overpay
    return loan


def nc_depreciation(s: State) -> float:
    return s.num("ncPrice") * 0.15


def nc_monthly(s: State) -> float:
    loan = nc_loan(s)
    credit = loan.monthly if s.toggles["ncPaymentMode"] == "credit" else 0.0
    return (nc_operating(s) + nc_depreciation(s)) / 12 + credit


def nc_personal_monthly(s: State) -> float:
    return s.num("ncExpFood") + s.num("ncExpHousing") + s.num("ncExpComms") + s.num("ncExpOther")


# ============ НАКОПЛЕНИЯ ============


def _simulate_with_loan(
    years: int,
    start: float,
    monthly_net: float,
    rate: float,
    loan_monthly: float,
    loan_months: float,
    operating_monthly: float,
) -> list[tuple[int, float]]:
    """Платёж по кредиту уходит из потока только пока идёт срок кредита."""
    monthly_rate = (1 + rate) ** (1 / 12) - 1
    bal = start
    points = [(0, bal)]
    for m in range(1, years * 12 + 1):
        outflow = (loan_monthly if m <= loan_months else 0.0) + operating_monthly
        bal = bal * (1 + monthly_rate) + monthly_net - outflow
        if m % 12 == 0:
            points.append((m // 12, bal))
    return points


@dataclass
class HaveSavings:
    keep: list[tuple[int, float]]
    new: list[tuple[int, float]]
    no_car: list[tuple[int, float]]

    @property
    def keep_end(self) -> float:
        return self.keep[-1][1]

    @property
    def new_end(self) -> float:
        return self.new[-1][1]

    @property
    def no_car_end(self) -> float:
        return self.no_car[-1][1]


def have_savings(s: State, years: int = YEARS_HORIZON) -> HaveSavings:
    start_capital = s.num("currentSavings")
    rate = (s.num("savingsRate") or 0) / 100
    monthly_net = max(0.0, s.num("monthlyIncome") - have_personal_monthly(s))
    loan = have_new_car_loan(s)
    curr_monthly = have_current_monthly(s)

    keep = simulate_savings(years, curr_monthly, monthly_net, start_capital, rate)
    no_car = simulate_savings(years, 0, monthly_net, start_capital, rate)

    if s.toggles["paymentMode"] == "cash":
        new_start = start_capital - max(0.0, loan.effective_price)
        loan_months = 0.0
    else:
        new_start = start_capital - s.num("newCarDownPayment")
        loan_months = loan.term
    new = _simulate_with_loan(
        years,
        new_start,
        monthly_net,
        rate,
        loan.monthly,
        loan_months,
        have_new_operating(s) / 12,
    )
    return HaveSavings(keep=keep, new=new, no_car=no_car)


@dataclass
class NoneSavings:
    car: list[tuple[int, float]]
    no_car: list[tuple[int, float]]

    @property
    def car_end(self) -> float:
        return self.car[-1][1]

    @property
    def no_car_end(self) -> float:
        return self.no_car[-1][1]


def none_savings(s: State, years: int = YEARS_HORIZON) -> NoneSavings:
    start_capital = s.num("ncCurrentSavings")
    rate = (s.num("ncSavingsRate") or 0) / 100
    monthly_net = max(0.0, s.num("ncMonthlyIncome") - nc_personal_monthly(s))
    loan = nc_loan(s)

    no_car = simulate_savings(years, 0, monthly_net, start_capital, rate)
    if s.toggles["ncPaymentMode"] == "cash":
        start = start_capital - s.num("ncPrice")
        loan_months = 0.0
    else:
        start = start_capital - s.num("ncDownPayment")
        loan_months = loan.term
    car = _simulate_with_loan(
        years, start, monthly_net, rate, loan.monthly, loan_months, nc_operating(s) / 12
    )
    return NoneSavings(car=car, no_car=no_car)


# ============ СЧАСТЬЕ ============


@dataclass
class Happiness:
    series: list[tuple[int, float]]
    slope: float
    purchase_year: int
    now: int
    at_purchase: int
    at_now: int


def happiness(s: State) -> Happiness:
    cy = current_year()
    py = int(s.num("purchaseYear") or cy)
    h_purchase = s.intval("happyAtPurchase", 1, 10, 5)
    h_now = s.intval("happyNow", 1, 10, 5)
    years_owned = max(1, cy - py)
    slope = (h_now - h_purchase) / years_owned
    series: list[tuple[int, float]] = [(py, float(h_purchase)), (cy, float(h_now))]
    for y in range(1, 11):
        series.append((cy + y, max(1.0, min(10.0, h_now + slope * y))))
    return Happiness(series, slope, py, cy, h_purchase, h_now)


# ============ КРИВЫЕ СТОИМОСТИ ============


def have_curves(s: State) -> tuple[list[CurvePoint], list[CurvePoint]]:
    cy = current_year()
    py = int(s.num("purchaseYear") or cy)
    operating = have_operating(s)
    growth = (s.num("newCarOpGrowth") or 5) / 100
    loan = have_new_car_loan(s)
    credit_on = s.toggles["creditMode"] == "on"

    existing = build_curve(
        CURVE_YEARS,
        purchase_price=s.num("purchasePrice"),
        annual_km=max(1.0, s.num("distanceValue") or 1),
        operating_base=operating,
        operating_growth=growth,
        credit_monthly=s.num("monthlyPayment") if credit_on else 0.0,
        total_months=s.num("totalMonths") if credit_on else 0.0,
        start_age=0,
        start_calendar_year=py,
        include_purchase_in_year0=True,
        one_time_year0=s.num("monthlyPayment") if credit_on else 0.0,
    )

    on_credit = s.toggles["paymentMode"] == "credit"
    cash_year0 = 0.0 if on_credit else max(0.0, s.num("newCarPrice") - loan.trade_in)
    new = build_curve(
        CURVE_YEARS,
        purchase_price=s.num("newCarPrice"),
        annual_km=max(1.0, s.num("newCarDistance") or s.num("distanceValue") or 1),
        operating_base=operating,
        operating_growth=growth,
        credit_monthly=loan.monthly if on_credit else 0.0,
        total_months=loan.term if on_credit else 0.0,
        start_age=0,
        start_calendar_year=cy,
        include_purchase_in_year0=False,
        one_time_year0=(s.num("newCarDownPayment") + loan.monthly) if on_credit else cash_year0,
    )
    return existing, new


def none_curve(s: State) -> list[CurvePoint]:
    loan = nc_loan(s)
    on_credit = s.toggles["ncPaymentMode"] == "credit"
    return build_curve(
        CURVE_YEARS,
        purchase_price=s.num("ncPrice"),
        annual_km=max(1.0, s.num("ncDistance") or 1),
        operating_base=nc_operating(s),
        operating_growth=0.05,
        credit_monthly=loan.monthly if on_credit else 0.0,
        total_months=loan.term if on_credit else 0.0,
        start_age=0,
        start_calendar_year=current_year(),
        include_purchase_in_year0=True,
        one_time_year0=loan.monthly if on_credit else 0.0,
    )
