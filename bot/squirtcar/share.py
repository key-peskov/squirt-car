"""Экспорт расчёта в HTML — порт buildSharedHTML() из SquirtCar_0.1.2.html.

Разметка и CSS перенесены один в один, чтобы файл из бота выглядел так же,
как файл, который отдаёт кнопка «Поделиться» в веб-версии.
"""

from datetime import date
from html import escape

from . import calc
from .model import State
from .report import fmt

CSS = """
      body { font-family: -apple-system, system-ui, 'Segoe UI', Roboto, sans-serif; background:#f5f6f8; color:#1a1d23; margin:0; padding:2rem 1rem; line-height:1.5; }
      .wrap { max-width: 900px; margin:0 auto; }
      h1 { font-size:1.5rem; font-weight:800; margin:0 0 0.3rem; }
      .sub { color:#5c6470; font-size:0.9rem; margin-bottom:1.5rem; }
      .card { background:#fff; border:1px solid #d9dde3; border-radius:12px; padding:1.25rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
      .card h2 { font-size:1rem; font-weight:700; margin:0 0 0.8rem; }
      .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
      @media (max-width:640px) { .grid2 { grid-template-columns:1fr; } }
      .line { display:flex; justify-content:space-between; padding:0.35rem 0; border-bottom:1px solid #f0f2f5; font-size:0.9rem; }
      .line:last-child { border-bottom:none; }
      .line strong { font-weight:700; }
      .total { border-top:2px solid #d9dde3; margin-top:0.4rem; padding-top:0.4rem; font-weight:700; }
      .total strong { color:#2b5fd9; }
      .badge { display:inline-block; background:#e8eefb; color:#2b5fd9; font-weight:700; padding:0.15rem 0.6rem; border-radius:6px; margin-right:0.3rem; font-size:0.85rem; }
      .row2 { display:grid; grid-template-columns:1fr 1fr; gap:0.7rem; }
      @media (max-width:500px) { .row2 { grid-template-columns:1fr; } }
      .metric { background:#f0f2f5; border-radius:8px; padding:0.8rem; text-align:center; }
      .metric .lbl { font-size:0.72rem; color:#5c6470; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.3rem; }
      .metric .val { font-size:1.2rem; font-weight:800; color:#1a1d23; }
      .footer { text-align:center; color:#8a929e; font-size:0.78rem; margin-top:1.5rem; }
"""


def _have_body(s: State, include_personal: bool, include_savings: bool) -> str:
    curr_monthly = calc.have_current_monthly(s)
    new_monthly = calc.have_new_monthly(s)
    loan = calc.have_new_car_loan(s)
    income = s.num("monthlyIncome")
    h = calc.happiness(s)
    hap_per_money = (h.at_now / curr_monthly * 1000) if curr_monthly > 0 else 0.0
    ts = calc.compute_time_saved(
        s.num("tripsPerWeek"), s.num("commuteTimeNow"), s.num("commuteTimeNew")
    )
    sav = calc.have_savings(s)

    time_line = (
        f'<div class="line"><span>Экономия времени</span><strong>'
        f"{ts.hours_per_month:.1f} ч/мес ({ts.hours_per_year:.0f} ч/год)</strong></div>"
        if ts.hours_per_month > 0
        else ""
    )
    personal_card = (
        f"""
          <div class="card">
            <h2>🏠 Личные расходы</h2>
            <div class="line"><span>Еда</span><strong>{fmt(s.num('expFood'))} ₽/мес</strong></div>
            <div class="line"><span>Жильё</span><strong>{fmt(s.num('expHousing'))} ₽/мес</strong></div>
            <div class="line"><span>Связь</span><strong>{fmt(s.num('expComms'))} ₽/мес</strong></div>
            <div class="line"><span>Прочее</span><strong>{fmt(s.num('expOther'))} ₽/мес</strong></div>
            <div class="line total"><span>Доход</span><strong>{fmt(income)} ₽/мес</strong></div>
          </div>
        """
        if include_personal
        else ""
    )
    savings_card = (
        f"""
          <div class="card">
            <h2>🏦 Накопления</h2>
            <div class="line"><span>Текущий баланс</span><strong>{fmt(s.num('currentSavings'))} ₽</strong></div>
            <div class="line"><span>Ставка</span><strong>{s.num('savingsRate'):g}% годовых</strong></div>
          </div>
        """
        if include_savings
        else ""
    )
    no_car_metric = (
        f'<div class="metric" style="margin-top:0.7rem;"><div class="lbl">Без машины вообще</div>'
        f'<div class="val">{fmt(sav.no_car_end)} ₽</div></div>'
        if include_personal
        else ""
    )

    return f"""
        <div class="grid2">
          <div class="card">
            <h2>🚗 Текущая: {escape(s.text('carModel'))}</h2>
            <div class="line"><span>Цена покупки</span><strong>{fmt(s.num('purchasePrice'))} ₽</strong></div>
            <div class="line"><span>Год покупки</span><strong>{int(s.num('purchaseYear')) or '—'}</strong></div>
            <div class="line"><span>Пробег за год</span><strong>{fmt(s.num('distanceValue'))} км</strong></div>
            <div class="line total"><span>Стоимость в месяц</span><strong>{fmt(curr_monthly)} ₽</strong></div>
            <div style="margin-top:0.8rem;">
              <div class="badge">Счастье сейчас: {h.at_now}/10</div>
              <div class="badge">При покупке: {h.at_purchase}/10</div>
            </div>
          </div>
          <div class="card">
            <h2>🆕 Новая: {escape(s.text('newCarModel'))}</h2>
            <div class="line"><span>Цена</span><strong>{fmt(s.num('newCarPrice'))} ₽</strong></div>
            <div class="line"><span>Платёж по кредиту</span><strong>{fmt(loan.monthly)} ₽/мес</strong></div>
            <div class="line"><span>Переплата</span><strong>{fmt(loan.overpay)} ₽</strong></div>
            <div class="line total"><span>Стоимость в месяц</span><strong>{fmt(new_monthly)} ₽</strong></div>
          </div>
        </div>
        <div class="card">
          <h2>📊 Сравнение в месяц</h2>
          <div class="row2">
            <div class="metric"><div class="lbl">Текущая</div><div class="val">{fmt(curr_monthly)} ₽</div></div>
            <div class="metric"><div class="lbl">Новая</div><div class="val">{fmt(new_monthly)} ₽</div></div>
          </div>
          <div class="line total" style="margin-top:0.8rem;"><span>Разница</span><strong>{fmt(new_monthly - curr_monthly)} ₽/мес</strong></div>
          <div class="line"><span>Счастье за деньги</span><strong>{hap_per_money:.1f} очков / 1000 ₽</strong></div>
          {time_line}
        </div>
        {personal_card}
        {savings_card}
        <div class="card">
          <h2>💰 Итог через 10 лет</h2>
          <div class="row2">
            <div class="metric"><div class="lbl">Оставить текущую</div><div class="val">{fmt(sav.keep_end)} ₽</div></div>
            <div class="metric"><div class="lbl">Купить новую</div><div class="val">{fmt(sav.new_end)} ₽</div></div>
          </div>
          {no_car_metric}
        </div>
      """


def _none_body(s: State, include_personal: bool, include_savings: bool) -> str:
    car_monthly = calc.nc_monthly(s)
    loan = calc.nc_loan(s)
    income = s.num("ncMonthlyIncome")
    ts = calc.compute_time_saved(
        s.num("ncTripsPerWeek"), s.num("ncCommuteTimeNow"), s.num("ncCommuteTimeNew")
    )
    sav = calc.none_savings(s)
    share = f"{car_monthly / income * 100:.1f}%" if income > 0 else "—"

    time_line = (
        f'<div class="line"><span>Экономия времени</span><strong>'
        f"{ts.hours_per_month:.1f} ч/мес ({ts.hours_per_year:.0f} ч/год)</strong></div>"
        if ts.hours_per_month > 0
        else ""
    )
    personal_card = (
        f"""
          <div class="card">
            <h2>🏠 Личные расходы</h2>
            <div class="line"><span>Еда</span><strong>{fmt(s.num('ncExpFood'))} ₽/мес</strong></div>
            <div class="line"><span>Жильё</span><strong>{fmt(s.num('ncExpHousing'))} ₽/мес</strong></div>
            <div class="line"><span>Связь</span><strong>{fmt(s.num('ncExpComms'))} ₽/мес</strong></div>
            <div class="line"><span>Прочее</span><strong>{fmt(s.num('ncExpOther'))} ₽/мес</strong></div>
            <div class="line total"><span>Доход</span><strong>{fmt(income)} ₽/мес</strong></div>
          </div>
        """
        if include_personal
        else ""
    )
    savings_card = (
        f"""
          <div class="card">
            <h2>🏦 Накопления</h2>
            <div class="line"><span>Текущий баланс</span><strong>{fmt(s.num('ncCurrentSavings'))} ₽</strong></div>
            <div class="line"><span>Ставка</span><strong>{s.num('ncSavingsRate'):g}% годовых</strong></div>
          </div>
        """
        if include_savings
        else ""
    )

    return f"""
        <div class="card">
          <h2>🚗 Машина: {escape(s.text('ncCarModel'))}</h2>
          <div class="line"><span>Цена</span><strong>{fmt(s.num('ncPrice'))} ₽</strong></div>
          <div class="line"><span>Платёж по кредиту</span><strong>{fmt(loan.monthly)} ₽/мес</strong></div>
          <div class="line"><span>Переплата</span><strong>{fmt(loan.overpay)} ₽</strong></div>
          <div class="line total"><span>Стоимость в месяц</span><strong>{fmt(car_monthly)} ₽</strong></div>
        </div>
        <div class="card">
          <h2>📊 Сравнение с жизнью</h2>
          <div class="row2">
            <div class="metric"><div class="lbl">Машина</div><div class="val">{fmt(car_monthly)} ₽</div></div>
            <div class="metric"><div class="lbl">Доля дохода</div><div class="val">{share}</div></div>
          </div>
          {time_line}
        </div>
        {personal_card}
        {savings_card}
        <div class="card">
          <h2>💰 Итог через 10 лет</h2>
          <div class="row2">
            <div class="metric"><div class="lbl">Купить машину</div><div class="val">{fmt(sav.car_end)} ₽</div></div>
            <div class="metric"><div class="lbl">Без машины</div><div class="val">{fmt(sav.no_car_end)} ₽</div></div>
          </div>
          <div class="line total" style="margin-top:0.8rem;"><span>Машина съест</span><strong>{fmt(sav.no_car_end - sav.car_end)} ₽</strong></div>
        </div>
      """


def build_shared_html(s: State, include_personal: bool = True, include_savings: bool = True) -> str:
    if s.mode == "have":
        body = _have_body(s, include_personal, include_savings)
        title = "Расчёт: есть машина"
    else:
        body = _none_body(s, include_personal, include_savings)
        title = "Расчёт: нет машины"

    notes = ""
    if not include_personal:
        notes += "Личные расходы не включены. "
    if not include_savings:
        notes += "Накопления не включены."

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SquirtCar — {title}</title><style>{CSS}</style></head><body>
<div class="wrap">
  <h1><span style="color:#2b5fd9;">SquirtCar</span> — {title}</h1>
  <div class="sub">Расчёт от {date.today().strftime('%d.%m.%Y')}</div>
  {body}
  <div class="footer">
    SquirtCar · расчёты — оценочные. «Счастье за деньги» — субъективная метрика.
    {notes}
  </div>
</div>
</body></html>"""
