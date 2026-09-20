"""Текстовый отчёт — карточки результатов, сравнения и инсайты из HTML.

Тексты инсайтов (renderLoanComparison, renderHappinessInsight,
renderHaveSavings, renderNoneSavings) перенесены дословно.
"""

from html import escape

from . import calc
from .model import State

NBSP = " "


def fmt(v: float) -> str:
    """Аналог fmt(): округление + русский разделитель разрядов."""
    try:
        if v != v or v in (float("inf"), float("-inf")):
            return "0"
    except TypeError:
        return "0"
    return f"{round(v):,}".replace(",", NBSP)


def _pct(part: float, whole: float) -> str:
    return f"{part / whole * 100:.1f}%" if whole > 0 else "—"


def _bar(value: float, maximum: float, width: int = 12) -> str:
    filled = 0 if maximum <= 0 else max(0, min(width, round(value / maximum * width)))
    return "█" * filled + "·" * (width - filled)


# ============ ИНСАЙТЫ ============


def loan_comparison(s: State, loan: calc.Loan) -> str:
    if s.toggles["paymentMode"] == "cash":
        if loan.trade_in >= loan.price:
            return "🎉 Продажа старой полностью покрывает цену новой. Доплата не нужна."
        msg = f"💵 Доплата наличными: <b>{fmt(loan.effective_price)} ₽</b>. Без процентов."
        if loan.trade_in > 0:
            msg += f" Продажа старой снизила цену на <b>{fmt(loan.trade_in)} ₽</b>."
        return msg
    if loan.principal <= 0 and loan.price > 0:
        return "🎉 Продажа + первый взнос покрывают цену полностью. Кредит не нужен."
    if loan.overpay > 0:
        pct = loan.overpay / loan.price * 100
        msg = (
            f"Переплата по кредиту: <b>{fmt(loan.overpay)} ₽</b> ({pct:.1f}% от цены). "
            f"Реальная стоимость: <b>{fmt(loan.price + loan.overpay)} ₽</b>. "
        )
        if pct > 30:
            msg += f"⚠️ Это почти ещё {pct / 100:.2f} такой же машины."
        return msg
    return "Заполните параметры."


def happiness_insight(h: calc.Happiness) -> str:
    if h.slope < -0.15:
        msg = f"Текущая машина теряет радость со временем (наклон {h.slope:.2f}/год). "
    elif h.slope > 0.15:
        msg = "Текущая машина наоборот радует всё больше. "
    else:
        msg = "Текущая машина стабильна по радости. "
    end = h.series[-1][1]
    msg += f"Через 10 лет ожидаемо: <b>{end:.1f}/10</b>."
    if end < 4:
        msg += "\n⚠️ Прогноз говорит, что машина перестанет радовать."
    return msg


def have_savings_insight(sav: calc.HaveSavings) -> str:
    keep, new, no_car = sav.keep_end, sav.new_end, sav.no_car_end
    msg = (
        f"Через 10 лет: с текущей — <b>{fmt(keep)} ₽</b>, "
        f"с новой — <b>{fmt(new)} ₽</b>, без машины — <b>{fmt(no_car)} ₽</b>. "
    )
    diff_keep_vs_new = keep - new
    if diff_keep_vs_new > 0:
        msg += f"Оставить текущую выгоднее новой на <b>{fmt(diff_keep_vs_new)} ₽</b>. "
    elif diff_keep_vs_new < 0:
        msg += (
            f"⚠️ Новая почему-то дешевле на <b>{fmt(abs(diff_keep_vs_new))} ₽</b> — проверьте. "
        )
    if no_car - keep > 0:
        msg += f"Текущая машина съедает <b>{fmt(no_car - keep)} ₽</b> накоплений. "
    if new < 0:
        msg += "\n💸 С новой машиной уйдёте в минус."
    return msg


def none_savings_insight(sav: calc.NoneSavings) -> str:
    car, no_car = sav.car_end, sav.no_car_end
    diff = no_car - car
    msg = f"Через 10 лет: с машиной — <b>{fmt(car)} ₽</b>, без машины — <b>{fmt(no_car)} ₽</b>. "
    msg += f"Машина съест <b>{fmt(diff)} ₽</b> накоплений за 10 лет. "
    if car < 0:
        msg += "\n💸 С машиной уйдёте в минус — накоплений не хватит."
    elif diff > no_car * 0.5:
        msg += "\n⚠️ Это больше половины того, что вы бы накопили без машины."
    return msg


# ============ ОТЧЁТЫ ============


def have_report(s: State) -> str:
    operating = calc.have_operating(s)
    dep = calc.have_depreciation(s)
    credit_annual = calc.have_credit_yearly(s)
    curr_monthly = (operating + dep + credit_annual) / 12

    new_operating = calc.have_new_operating(s)
    new_dep = s.num("newCarPrice") * 0.15
    loan = calc.have_new_car_loan(s)
    new_credit_monthly = loan.monthly if s.toggles["paymentMode"] == "credit" else 0.0
    new_monthly = (new_operating + new_dep) / 12 + new_credit_monthly

    personal = calc.have_personal_monthly(s)
    income = s.num("monthlyIncome")
    h = calc.happiness(s)
    hap_per_money = (h.at_now / curr_monthly * 1000) if curr_monthly > 0 else 0.0
    ts = calc.compute_time_saved(
        s.num("tripsPerWeek"), s.num("commuteTimeNow"), s.num("commuteTimeNew")
    )
    diff = new_monthly - curr_monthly
    max_bar = max(curr_monthly, new_monthly, personal, 1)

    lines = [
        f"📊 <b>{escape(s.text('carModel'))}</b> → <b>{escape(s.text('newCarModel'))}</b>",
        "",
        f"🚗 Текущая: <b>{fmt(curr_monthly)} ₽/мес</b>",
        f"🆕 Новая: <b>{fmt(new_monthly)} ₽/мес</b>",
        f"↔️ Разница: <b>{'+' if diff >= 0 else '−'}{fmt(abs(diff))} ₽/мес</b>",
        f"😊 Счастье за деньги: <b>{hap_per_money:.1f}</b> очков на 1000 ₽",
    ]
    if ts.hours_per_month > 0:
        lines.append(
            f"🕒 Время сэкономлено: <b>{ts.hours_per_month:.1f} ч/мес</b> "
            f"({ts.hours_per_year:.0f} ч/год)"
        )
    else:
        lines.append("🕒 Время сэкономлено: — (укажите время поездок)")

    lines += [
        "",
        "<b>🚗 Текущая машина, ₽/мес</b>",
        f"<code>Эксплуатация  {fmt(operating / 12):>9}</code>",
        f"<code>Амортизация   {fmt(dep / 12):>9}</code>",
        f"<code>Кредит        {fmt(credit_annual / 12):>9}</code>",
        f"<code>Итого         {fmt(curr_monthly):>9}</code>",
        f"<code>{_bar(curr_monthly, max_bar)}</code> доля дохода: {_pct(curr_monthly, income)}",
        "",
        "<b>🆕 Новая машина, ₽/мес</b>",
        f"<code>Эксплуатация  {fmt(new_operating / 12):>9}</code>",
        f"<code>Амортизация   {fmt(new_dep / 12):>9}</code>",
        f"<code>Кредит        {fmt(new_credit_monthly):>9}</code>",
        f"<code>Итого         {fmt(new_monthly):>9}</code>",
        f"<code>{_bar(new_monthly, max_bar)}</code> доля дохода: {_pct(new_monthly, income)}",
        "",
        "<b>🏠 Жизнь без машины, ₽/мес</b>",
        f"<code>Еда           {fmt(s.num('expFood')):>9}</code>",
        f"<code>Жильё         {fmt(s.num('expHousing')):>9}</code>",
        f"<code>Связь/прочее  {fmt(s.num('expComms') + s.num('expOther')):>9}</code>",
        f"<code>Итого         {fmt(personal):>9}</code>",
        f"<code>{_bar(personal, max_bar)}</code> доля дохода: {_pct(personal, income)}",
        "",
        "<b>💳 Кредит на новую</b>",
        f"<code>Сумма         {fmt(loan.principal):>9} ₽</code>",
        f"<code>Платёж/мес    {fmt(loan.monthly):>9} ₽</code>",
        f"<code>Проценты      {fmt(loan.overpay):>9} ₽</code>",
        f"<code>Реальная цена {fmt(loan.price + loan.overpay):>9} ₽</code>",
        loan_comparison(s, loan),
    ]

    if s.toggles["creditMode"] == "on":
        lines += [
            "",
            f"<b>💳 Кредит на текущую</b>: {fmt(credit_annual)} ₽/год · "
            f"переплата {fmt(calc.have_credit_overpay(s))} ₽",
        ]
    if s.toggles["depreciationMode"] == "auto":
        lines += ["", f"📉 Потери от амортизации: <b>{fmt(calc.have_auto_depreciation(s))} ₽/год</b>"]

    sav = calc.have_savings(s)
    lines += [
        "",
        "<b>💰 Накопления через 10 лет</b>",
        f"<code>Оставить текущую  {fmt(sav.keep_end):>12} ₽</code>",
        f"<code>Купить новую      {fmt(sav.new_end):>12} ₽</code>",
        f"<code>Без машины вообще {fmt(sav.no_car_end):>12} ₽</code>",
        "",
        have_savings_insight(sav),
        "",
        "<b>😊 Счастье</b>",
        happiness_insight(h),
    ]
    return "\n".join(lines)


def none_report(s: State) -> str:
    operating = calc.nc_operating(s)
    dep = calc.nc_depreciation(s)
    loan = calc.nc_loan(s)
    credit_monthly = loan.monthly if s.toggles["ncPaymentMode"] == "credit" else 0.0
    car_monthly = (operating + dep) / 12 + credit_monthly
    personal = calc.nc_personal_monthly(s)
    income = s.num("ncMonthlyIncome")
    ts = calc.compute_time_saved(
        s.num("ncTripsPerWeek"), s.num("ncCommuteTimeNow"), s.num("ncCommuteTimeNew")
    )
    max_bar = max(car_monthly, personal, 1)

    lines = [
        f"📊 <b>{escape(s.text('ncCarModel'))}</b>",
        "",
        f"🚗 Машина: <b>{fmt(car_monthly)} ₽/мес</b>",
        f"📈 Доля дохода: <b>{_pct(car_monthly, income)}</b>",
    ]
    if ts.hours_per_month > 0:
        lines.append(
            f"🕒 Время сэкономлено: <b>{ts.hours_per_month:.1f} ч/мес</b> "
            f"({ts.hours_per_year:.0f} ч/год)"
        )
    else:
        lines.append("🕒 Время сэкономлено: — (укажите время поездок)")

    lines += [
        "",
        "<b>🚗 Машина, ₽/мес</b>",
        f"<code>Эксплуатация  {fmt(operating / 12):>9}</code>",
        f"<code>Амортизация   {fmt(dep / 12):>9}</code>",
        f"<code>Кредит        {fmt(credit_monthly):>9}</code>",
        f"<code>Итого         {fmt(car_monthly):>9}</code>",
        f"<code>{_bar(car_monthly, max_bar)}</code>",
        "",
        "<b>🏠 Жизнь, ₽/мес</b>",
        f"<code>Еда           {fmt(s.num('ncExpFood')):>9}</code>",
        f"<code>Жильё         {fmt(s.num('ncExpHousing')):>9}</code>",
        f"<code>Связь/прочее  {fmt(s.num('ncExpComms') + s.num('ncExpOther')):>9}</code>",
        f"<code>Итого         {fmt(personal):>9}</code>",
        f"<code>{_bar(personal, max_bar)}</code> доля дохода: {_pct(personal, income)}",
        "",
        "<b>💳 Кредит</b>",
        f"<code>Сумма         {fmt(loan.principal):>9} ₽</code>",
        f"<code>Платёж/мес    {fmt(loan.monthly):>9} ₽</code>",
        f"<code>Проценты      {fmt(loan.overpay):>9} ₽</code>",
        f"<code>Реальная цена {fmt(loan.price + loan.overpay):>9} ₽</code>",
    ]

    sav = calc.none_savings(s)
    lines += [
        "",
        "<b>💰 Накопления через 10 лет</b>",
        f"<code>Купить машину {fmt(sav.car_end):>12} ₽</code>",
        f"<code>Без машины    {fmt(sav.no_car_end):>12} ₽</code>",
        "",
        none_savings_insight(sav),
    ]
    return "\n".join(lines)


def report(s: State) -> str:
    return have_report(s) if s.mode == "have" else none_report(s)
