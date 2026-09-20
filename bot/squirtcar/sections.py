"""Разделы формы: какие поля и переключатели показывать при текущем состоянии.

Повторяет show/hide-логику HTML: поля расхода топлива, амортизации, кредита
и trade-in появляются и прячутся ровно по тем же условиям.
"""

from typing import Literal

from .model import State

Item = tuple[Literal["head", "field", "toggle", "action"], str]

SECTION_TITLES = {
    "cur": "🚗 Текущая машина",
    "new": "🆕 Новая машина",
    "life": "🏠 Ваша жизнь и накопления",
    "car": "🚗 Машина, которую рассматриваете",
    "nclife": "🏠 Ваша жизнь и накопления",
}


def _fuel_block(s: State, mode_key: str, manual_key: str, price_key: str, unit_key: str,
                value_key: str) -> list[Item]:
    items: list[Item] = [("head", "Расходы в год"), ("toggle", mode_key)]
    if s.toggles[mode_key] == "manual":
        items.append(("field", manual_key))
    else:
        items += [("field", price_key), ("toggle", unit_key), ("field", value_key)]
    return items


def have_current(s: State) -> list[Item]:
    items: list[Item] = [
        ("field", "carModel"),
        ("field", "purchasePrice"),
        ("field", "purchaseYear"),
        ("field", "distanceValue"),
    ]
    items += _fuel_block(s, "fuelMode", "fuelCost", "fuelPrice", "consumptionUnit",
                         "consumptionValue")
    items += [
        ("field", "insurance"),
        ("field", "maintenance"),
        ("field", "taxes"),
        ("field", "other"),
        ("head", "Амортизация"),
        ("toggle", "depreciationMode"),
    ]
    items.append(
        ("field", "depreciationManual")
        if s.toggles["depreciationMode"] == "manual"
        else ("field", "currentMarketPrice")
    )
    items += [("head", "Кредит на текущую"), ("toggle", "creditMode")]
    if s.toggles["creditMode"] == "on":
        items += [
            ("field", "monthlyPayment"),
            ("field", "interestRate"),
            ("field", "totalMonths"),
            ("field", "monthsAlreadyPaid"),
        ]
    items += [
        ("head", "😊 Счастье от машины"),
        ("field", "happyAtPurchase"),
        ("field", "happyNow"),
    ]
    return items


def have_new(s: State) -> list[Item]:
    items: list[Item] = [
        ("field", "newCarModel"),
        ("field", "newCarPrice"),
        ("field", "newCarDistance"),
        ("head", "🕒 Поездки и время"),
        ("field", "tripsPerWeek"),
        ("field", "commuteDistance"),
        ("field", "commuteTimeNow"),
        ("field", "commuteTimeNew"),
        ("head", "Как платим"),
        ("toggle", "paymentMode"),
        ("toggle", "tradeInMode"),
    ]
    if s.toggles["tradeInMode"] == "on":
        items += [("field", "tradeInValue"), ("action", "residual")]
    if s.toggles["paymentMode"] == "credit":
        items += [
            ("field", "newCarDownPayment"),
            ("field", "newCarRate"),
            ("field", "newCarTerm"),
        ]
    items.append(("field", "newCarOpGrowth"))
    return items


def have_life(_s: State) -> list[Item]:
    return [
        ("field", "expFood"),
        ("field", "expHousing"),
        ("field", "expComms"),
        ("field", "expOther"),
        ("field", "monthlyIncome"),
        ("field", "currentSavings"),
        ("field", "savingsRate"),
    ]


def none_car(s: State) -> list[Item]:
    items: list[Item] = [
        ("field", "ncCarModel"),
        ("field", "ncPrice"),
        ("field", "ncDistance"),
        ("head", "🕒 Поездки и время"),
        ("field", "ncTripsPerWeek"),
        ("field", "ncCommuteDistance"),
        ("field", "ncCommuteTimeNow"),
        ("field", "ncCommuteTimeNew"),
        ("head", "Как платим"),
        ("toggle", "ncPaymentMode"),
    ]
    if s.toggles["ncPaymentMode"] == "credit":
        items += [("field", "ncDownPayment"), ("field", "ncRate"), ("field", "ncTerm")]
    items += _fuel_block(s, "ncFuelMode", "ncFuel", "ncFuelPrice", "ncConsumptionUnit",
                         "ncConsumptionValue")
    items += [
        ("field", "ncInsurance"),
        ("field", "ncMaintenance"),
        ("field", "ncTaxes"),
        ("field", "ncOther"),
    ]
    return items


def none_life(_s: State) -> list[Item]:
    return [
        ("field", "ncExpFood"),
        ("field", "ncExpHousing"),
        ("field", "ncExpComms"),
        ("field", "ncExpOther"),
        ("field", "ncMonthlyIncome"),
        ("field", "ncCurrentSavings"),
        ("field", "ncSavingsRate"),
    ]


BUILDERS = {
    "cur": have_current,
    "new": have_new,
    "life": have_life,
    "car": none_car,
    "nclife": none_life,
}

MENU = {
    "have": [("cur", "🚗 Текущая машина"), ("new", "🆕 Новая машина"),
             ("life", "🏠 Жизнь и накопления")],
    "none": [("car", "🚗 Машина"), ("nclife", "🏠 Жизнь и накопления")],
}


def items(section: str, s: State) -> list[Item]:
    return BUILDERS[section](s)
