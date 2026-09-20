"""Состояние калькулятора: поля, значения по умолчанию, переключатели.

Порт полей формы из SquirtCar_0.1.2.html — id полей сохранены один в один,
чтобы логику расчёта можно было сверять со скриптом в HTML построчно.
"""

from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["have", "none"]


@dataclass
class Field:
    key: str
    label: str
    default: float | str
    kind: Literal["number", "int", "text"] = "number"
    unit: str = ""
    minimum: float | None = 0
    maximum: float | None = None
    hint: str = ""


# ============ HAVE: текущая машина ============
HAVE_CURRENT: list[Field] = [
    Field("carModel", "Марка и модель", "Моя текущая машина", "text"),
    Field("purchasePrice", "Цена покупки", 2_000_000, unit="₽"),
    Field("purchaseYear", "Год покупки", 2021, "int", minimum=1950, maximum=2030),
    Field("distanceValue", "Пробег за год", 15_000, unit="км", minimum=1),
    Field("fuelCost", "⛽ Топливо / электричество", 96_000, unit="₽/год"),
    Field("fuelPrice", "Цена за литр / кВт·ч", 60, unit="₽"),
    Field("consumptionValue", "Расход (значение)", 8.5),
    Field("insurance", "🛡️ Страховка", 24_000, unit="₽/год"),
    Field("maintenance", "🔧 ТО и ремонт", 30_000, unit="₽/год"),
    Field("taxes", "📄 Налоги и сборы", 12_000, unit="₽/год"),
    Field("other", "🅿️ Парковка / прочее", 18_000, unit="₽/год"),
    Field("depreciationManual", "Потеря стоимости в год", 120_000, unit="₽"),
    Field("currentMarketPrice", "Текущая рыночная цена", 1_400_000, unit="₽"),
    Field("monthlyPayment", "Платёж в месяц", 25_000, unit="₽"),
    Field("interestRate", "Ставка", 19.2, unit="%"),
    Field("totalMonths", "Срок кредита", 60, "int", unit="мес", minimum=1),
    Field("monthsAlreadyPaid", "Уже выплачено", 24, "int", unit="мес"),
    Field("happyAtPurchase", "😊 Счастье когда купили", 9, "int", minimum=1, maximum=10),
    Field("happyNow", "😊 Счастье сейчас", 6, "int", minimum=1, maximum=10),
]

# ============ HAVE: новая машина ============
HAVE_NEW: list[Field] = [
    Field("newCarModel", "Марка и модель", "Новая машина", "text"),
    Field("newCarPrice", "Цена новой машины", 3_000_000, unit="₽"),
    Field("newCarDistance", "Пробег за год", 15_000, unit="км", minimum=1),
    Field("tripsPerWeek", "Поездок в неделю", 5, "int"),
    Field("commuteDistance", "Длина в одну сторону", 15, unit="км"),
    Field("commuteTimeNow", "Время сейчас", 45, unit="мин"),
    Field("commuteTimeNew", "Время на новой", 25, unit="мин"),
    Field("tradeInValue", "Цена продажи текущей", 1_400_000, unit="₽"),
    Field("newCarDownPayment", "Первый взнос", 600_000, unit="₽"),
    Field("newCarRate", "Ставка", 19.2, unit="%"),
    Field("newCarTerm", "Срок кредита", 60, "int", unit="мес", minimum=1),
    Field("newCarOpGrowth", "Рост расходов в год", 5, unit="%", maximum=20),
]

# ============ HAVE: жизнь и накопления ============
HAVE_LIFE: list[Field] = [
    Field("expFood", "🥗 Еда и продукты", 25_000, unit="₽/мес"),
    Field("expHousing", "🏠 Жильё и коммуналка", 35_000, unit="₽/мес"),
    Field("expComms", "📱 Связь и подписки", 3_000, unit="₽/мес"),
    Field("expOther", "💊 Здоровье и прочее", 15_000, unit="₽/мес"),
    Field("monthlyIncome", "💰 Доход в месяц", 120_000, unit="₽"),
    Field("currentSavings", "🏦 Текущие накопления", 500_000, unit="₽"),
    Field("savingsRate", "📈 Годовой % на накопления", 8, unit="%", maximum=30),
]

# ============ NONE: машина, которую рассматриваете ============
NONE_CAR: list[Field] = [
    Field("ncCarModel", "Марка и модель", "Машина, которую хочу", "text"),
    Field("ncPrice", "Цена машины", 2_000_000, unit="₽"),
    Field("ncDistance", "Пробег за год", 15_000, unit="км", minimum=1),
    Field("ncTripsPerWeek", "Поездок в неделю", 5, "int"),
    Field("ncCommuteDistance", "Длина в одну сторону", 15, unit="км"),
    Field("ncCommuteTimeNow", "Время сейчас", 50, unit="мин"),
    Field("ncCommuteTimeNew", "Время на машине", 25, unit="мин"),
    Field("ncDownPayment", "Первый взнос", 400_000, unit="₽"),
    Field("ncRate", "Ставка", 19.2, unit="%"),
    Field("ncTerm", "Срок кредита", 60, "int", unit="мес", minimum=1),
    Field("ncFuel", "⛽ Топливо / электричество", 96_000, unit="₽/год"),
    Field("ncFuelPrice", "Цена за литр / кВт·ч", 60, unit="₽"),
    Field("ncConsumptionValue", "Расход (значение)", 8.5),
    Field("ncInsurance", "🛡️ Страховка", 24_000, unit="₽/год"),
    Field("ncMaintenance", "🔧 ТО и ремонт", 30_000, unit="₽/год"),
    Field("ncTaxes", "📄 Налоги и сборы", 12_000, unit="₽/год"),
    Field("ncOther", "🅿️ Парковка / прочее", 18_000, unit="₽/год"),
]

# ============ NONE: жизнь и накопления ============
NONE_LIFE: list[Field] = [
    Field("ncExpFood", "🥗 Еда и продукты", 25_000, unit="₽/мес"),
    Field("ncExpHousing", "🏠 Жильё и коммуналка", 35_000, unit="₽/мес"),
    Field("ncExpComms", "📱 Связь и подписки", 3_000, unit="₽/мес"),
    Field("ncExpOther", "💊 Здоровье и прочее", 15_000, unit="₽/мес"),
    Field("ncMonthlyIncome", "💰 Доход в месяц", 120_000, unit="₽"),
    Field("ncCurrentSavings", "🏦 Текущие накопления", 500_000, unit="₽"),
    Field("ncSavingsRate", "📈 Годовой % на накопления", 8, unit="%", maximum=30),
]

ALL_FIELDS: dict[str, Field] = {
    f.key: f for group in (HAVE_CURRENT, HAVE_NEW, HAVE_LIFE, NONE_CAR, NONE_LIFE) for f in group
}

DEFAULTS: dict[str, float | str] = {f.key: f.default for f in ALL_FIELDS.values()}

# Переключатели: ключ -> (значение по умолчанию, [(значение, подпись), ...])
TOGGLES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "fuelMode": ("manual", [("manual", "Вручную (₽/год)"), ("price", "От цены топлива")]),
    "consumptionUnit": ("per100", [("per100", "л/100 км"), ("kmPer", "км/л")]),
    "depreciationMode": ("manual", [("manual", "Вручную"), ("auto", "От рыночной цены")]),
    "creditMode": ("off", [("off", "Без кредита"), ("on", "Есть кредит")]),
    "paymentMode": ("credit", [("credit", "В кредит"), ("cash", "За наличные")]),
    "tradeInMode": ("on", [("on", "Учесть продажу старой"), ("off", "Без продажи")]),
    "ncFuelMode": ("manual", [("manual", "Вручную (₽/год)"), ("price", "От цены топлива")]),
    "ncConsumptionUnit": ("per100", [("per100", "л/100 км"), ("kmPer", "км/л")]),
    "ncPaymentMode": ("credit", [("credit", "В кредит"), ("cash", "За наличные")]),
}

THEMES = [("light", "☀️ Светлая"), ("dark", "🌙 Тёмная"), ("cyber", "⚡ Киберпанк")]


@dataclass
class State:
    """Один расчёт пользователя. Повторяет объект `state` + значения полей формы."""

    mode: Mode | None = None
    theme: str = "light"
    values: dict[str, float | str] = field(default_factory=lambda: dict(DEFAULTS))
    toggles: dict[str, str] = field(default_factory=lambda: {k: v[0] for k, v in TOGGLES.items()})

    def num(self, key: str) -> float:
        """Аналог num() из HTML: непозитивные и нечисловые значения обнуляются."""
        raw = self.values.get(key, 0)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return 0.0
        return v if v > 0 else 0.0

    def text(self, key: str) -> str:
        return str(self.values.get(key, ""))

    def intval(self, key: str, minimum: int, maximum: int, fallback: int) -> int:
        """Аналог intInRange() из HTML."""
        try:
            v = int(float(self.values.get(key, fallback)))
        except (TypeError, ValueError):
            v = fallback
        return max(minimum, min(maximum, v))

    def reset(self) -> None:
        self.values = dict(DEFAULTS)
        self.toggles = {k: v[0] for k, v in TOGGLES.items()}


DISCLAIMER = """⚠️ <b>Что входит в стоимость владения (о чём часто забывают)</b>

Реальная стоимость машины — это не только цена и бензин:

• <b>Сезонные шины.</b> Летний + зимний комплект = 40–120 тыс. ₽, плюс переобувка дважды в год.
• <b>Замена масла и ТО.</b> 8–25 тыс. ₽ каждые 10–15 тыс. км пробега.
• <b>Поломки и внеплановый ремонт.</b> Даже на новой машине что-то случается после гарантии.
• <b>Страховка.</b> ОСАГО обязательно, КАСКО для новой часто обязательно по условиям кредита.
• <b>Парковка.</b> Платные парковки, резидентные разрешения, гараж или место у дома.
• <b>Транспортный налог.</b> Зависит от мощности двигателя и региона.
• <b>Техосмотр.</b> Раз в год или два, плюс возможные доработки.
• <b>Мойка, химия, мелкие аксессуары.</b> Копейки по отдельности, но набегает.
• <b>Амортизация.</b> Самая большая и незаметная статья — машина теряет в цене каждый день.
• <b>Проценты по кредиту.</b> Если берёте в кредит — реальная цена вырастает на 30–60%.

💡 Не поленитесь заглянуть на Auto.ru, Avito и Дром, чтобы оценить реальные цены на запчасти и обслуживание конкретно вашей модели."""
