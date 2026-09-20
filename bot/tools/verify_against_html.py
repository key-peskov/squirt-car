"""Сверка Python-порта с оригинальным JS из SquirtCar_0.1.2.html.

Скрипт из HTML выполняется в JavaScriptCore поверх DOM-стаба (dom_stub.js),
затем значения, которые страница пишет в DOM, сравниваются с тем, что даёт
squirtcar.calc на тех же входных данных.

Запуск:  python tools/verify_against_html.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from squirtcar import calc, report  # noqa: E402
from squirtcar.model import DEFAULTS, State  # noqa: E402

HTML = Path(__file__).resolve().parent.parent.parent / "SquirtCar_0.1.2.html"
HERE = Path(__file__).parent
JSC = "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc"

EXPORTS = """
globalThis.__api = {
  state: state,
  updateResults: updateResults,
  setMode: setMode,
  el: safe,
  residual: getHaveResidual,
  setDraw: function (n, f) {
    if (n === 'cost') drawCostChart = f;
    else if (n === 'sav') drawSavingsChart = f;
    else if (n === 'hap') drawHappinessChart = f;
  }
};
"""

HAVE_OUT = [
    "resultCurrentMonthly", "resultNewMonthly", "resultDiff", "resultHappinessPerMoney",
    "resultTimeSaved", "cmpCurrentOperating", "cmpCurrentDep", "cmpCurrentCredit",
    "cmpCurrentTotal", "cmpNewOperating", "cmpNewDep", "cmpNewCredit", "cmpNewTotal",
    "cmpFood", "cmpHousing", "cmpComms", "cmpLifeTotal", "cmpCurrentShare", "cmpNewShare",
    "cmpLifeShare", "loanAmount", "loanMonthly", "loanOverpay", "loanRealPrice",
    "creditYearlyDisplay", "creditOverpayDisplay", "savKeepVal", "savNewVal", "savNoCarVal",
]
NONE_OUT = [
    "ncResultMonthly", "ncResultShare", "ncResultTimeSaved", "ncCmpOperating", "ncCmpDep",
    "ncCmpCredit", "ncCmpTotal", "ncCmpFood", "ncCmpHousing", "ncCmpComms", "ncCmpLifeTotal",
    "savNewVal", "savNoCarVal",
]
INSIGHTS = ["loanComparison", "happinessInsight", "savingsInsight"]

# Поля формы, которые в HTML живут как <input>; счастье в HTML — два range-инпута.
INPUT_KEYS = [k for k in DEFAULTS if k not in ("happyAtPurchase", "happyNow")]


def build_js(case: dict) -> str:
    script = HTML.read_text(encoding="utf-8")
    body = script.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    idx = body.rstrip().rfind("})();")
    body = body[:idx] + EXPORTS + body[idx:]

    values = dict(DEFAULTS)
    values.update(case.get("values", {}))
    toggles = case.get("toggles", {})

    setters = [
        f"__api.el({json.dumps(k)}).value = {json.dumps(str(v))};"
        for k, v in values.items()
        if k in INPUT_KEYS
    ]
    setters.append(
        f"__api.el('happyAtPurchaseRange').value = "
        f"{json.dumps(str(values['happyAtPurchase']))};"
    )
    setters.append(f"__api.el('happyNowRange').value = {json.dumps(str(values['happyNow']))};")
    for k, v in toggles.items():
        if k in ("consumptionUnit", "ncConsumptionUnit"):
            setters.append(f"__api.el({json.dumps(k)}).value = {json.dumps(v)};")
        else:
            setters.append(f"__api.state.{k} = {json.dumps(v)};")
    # Единицы расхода всегда задаём явно — стаб-элемент стартует с пустым value.
    for k in ("consumptionUnit", "ncConsumptionUnit"):
        if k not in toggles:
            setters.append(f"__api.el({json.dumps(k)}).value = 'per100';")

    out_ids = HAVE_OUT if case["mode"] == "have" else NONE_OUT
    return f"""
{(HERE / 'dom_stub.js').read_text(encoding='utf-8')}
{body}

var __cap = {{}};
__api.setDraw('cost', function (a, b, today) {{ __cap.cost = {{ a: a, b: b, today: today }}; }});
__api.setDraw('sav', function (arr, years) {{ __cap.sav = arr.map(function (s) {{ return s.points; }}); }});
__api.setDraw('hap', function (arr) {{ __cap.hap = arr[0].points; }});

{chr(10).join(setters)}
__api.setMode({json.dumps(case['mode'])});

var __out = {{ text: {{}}, insight: {{}}, cap: __cap }};
{json.dumps(out_ids)}.forEach(function (id) {{ __out.text[id] = __api.el(id).textContent; }});
{json.dumps(INSIGHTS)}.forEach(function (id) {{ __out.insight[id] = __api.el(id).innerHTML; }});
__out.residual = __api.residual();
print(JSON.stringify(__out));
"""


def run_js(case: dict) -> dict:
    path = HERE / "_case.js"
    path.write_text(build_js(case), encoding="utf-8")
    proc = subprocess.run([JSC, str(path)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)
    return json.loads(proc.stdout.strip().splitlines()[-1])


def as_number(text: str) -> float | None:
    cleaned = re.sub(r"[^\d.\-−]", "", (text or "").replace("−", "-").replace(" ", ""))
    if cleaned in ("", "-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def strip_tags(html: str) -> str:
    no_br = re.sub(r"<br\s*/?>", " ", html or "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", no_br)).strip()


def py_state(case: dict) -> State:
    s = State()
    s.mode = case["mode"]
    s.values.update(case.get("values", {}))
    s.toggles.update(case.get("toggles", {}))
    return s


def py_values(s: State) -> dict[str, float]:
    """Те же метрики, что HTML пишет в DOM."""
    if s.mode == "have":
        operating = calc.have_operating(s)
        dep = calc.have_depreciation(s)
        credit_annual = calc.have_credit_yearly(s)
        curr = (operating + dep + credit_annual) / 12
        new_op = calc.have_new_operating(s)
        new_dep = s.num("newCarPrice") * 0.15
        loan = calc.have_new_car_loan(s)
        new_credit = loan.monthly if s.toggles["paymentMode"] == "credit" else 0.0
        new_total = (new_op + new_dep) / 12 + new_credit
        personal = calc.have_personal_monthly(s)
        income = s.num("monthlyIncome")
        h = calc.happiness(s)
        ts = calc.compute_time_saved(
            s.num("tripsPerWeek"), s.num("commuteTimeNow"), s.num("commuteTimeNew")
        )
        sav = calc.have_savings(s)
        return {
            "resultCurrentMonthly": round(curr),
            "resultNewMonthly": round(new_total),
            "resultDiff": abs(round(new_total - curr)),
            "resultHappinessPerMoney": round(h.at_now / curr * 1000, 1) if curr > 0 else 0.0,
            "resultTimeSaved": round(ts.hours_per_month, 1) if ts.hours_per_month > 0 else None,
            "cmpCurrentOperating": round(operating / 12),
            "cmpCurrentDep": round(dep / 12),
            "cmpCurrentCredit": round(credit_annual / 12),
            "cmpCurrentTotal": round(curr),
            "cmpNewOperating": round(new_op / 12),
            "cmpNewDep": round(new_dep / 12),
            "cmpNewCredit": round(new_credit),
            "cmpNewTotal": round(new_total),
            "cmpFood": round(s.num("expFood")),
            "cmpHousing": round(s.num("expHousing")),
            "cmpComms": round(s.num("expComms") + s.num("expOther")),
            "cmpLifeTotal": round(personal),
            "cmpCurrentShare": round(curr / income * 100, 1) if income > 0 else None,
            "cmpNewShare": round(new_total / income * 100, 1) if income > 0 else None,
            "cmpLifeShare": round(personal / income * 100, 1) if income > 0 else None,
            "loanAmount": round(loan.principal),
            "loanMonthly": round(loan.monthly),
            "loanOverpay": round(loan.overpay),
            "loanRealPrice": round(loan.price + loan.overpay),
            "creditYearlyDisplay": round(calc.have_credit_yearly(s)),
            "creditOverpayDisplay": round(calc.have_credit_overpay(s)),
            "savKeepVal": round(sav.keep_end),
            "savNewVal": round(sav.new_end),
            "savNoCarVal": round(sav.no_car_end),
        }

    operating = calc.nc_operating(s)
    dep = calc.nc_depreciation(s)
    loan = calc.nc_loan(s)
    credit = loan.monthly if s.toggles["ncPaymentMode"] == "credit" else 0.0
    car_monthly = (operating + dep) / 12 + credit
    personal = calc.nc_personal_monthly(s)
    income = s.num("ncMonthlyIncome")
    ts = calc.compute_time_saved(
        s.num("ncTripsPerWeek"), s.num("ncCommuteTimeNow"), s.num("ncCommuteTimeNew")
    )
    sav = calc.none_savings(s)
    return {
        "ncResultMonthly": round(car_monthly),
        "ncResultShare": round(car_monthly / income * 100, 1) if income > 0 else None,
        "ncResultTimeSaved": round(ts.hours_per_month, 1) if ts.hours_per_month > 0 else None,
        "ncCmpOperating": round(operating / 12),
        "ncCmpDep": round(dep / 12),
        "ncCmpCredit": round(credit),
        "ncCmpTotal": round(car_monthly),
        "ncCmpFood": round(s.num("ncExpFood")),
        "ncCmpHousing": round(s.num("ncExpHousing")),
        "ncCmpComms": round(s.num("ncExpComms") + s.num("ncExpOther")),
        "ncCmpLifeTotal": round(personal),
        "savNewVal": round(sav.car_end),
        "savNoCarVal": round(sav.no_car_end),
    }


def py_curves(s: State) -> dict:
    if s.mode == "have":
        existing, new = calc.have_curves(s)
        sav = calc.have_savings(s)
        return {
            "cost_a": [p.per_km for p in existing],
            "cost_b": [p.per_km for p in new],
            "sav": [
                [v for _, v in sav.keep],
                [v for _, v in sav.new],
                [v for _, v in sav.no_car],
            ],
            "hap": [v for _, v in calc.happiness(s).series],
        }
    sav = calc.none_savings(s)
    return {
        "cost_a": [],
        "cost_b": [p.per_km for p in calc.none_curve(s)],
        "sav": [[v for _, v in sav.car], [v for _, v in sav.no_car]],
    }


CASES = [
    {"name": "have / дефолты", "mode": "have"},
    {
        "name": "have / топливо от цены, амортизация авто, кредит есть, наличные, без продажи",
        "mode": "have",
        "toggles": {
            "fuelMode": "price", "depreciationMode": "auto", "creditMode": "on",
            "paymentMode": "cash", "tradeInMode": "off", "consumptionUnit": "kmPer",
        },
        "values": {"consumptionValue": 12, "happyAtPurchase": 3, "happyNow": 9,
                   "purchaseYear": 2016},
    },
    {
        "name": "have / продажа дороже новой, нулевой доход, ставка 0",
        "mode": "have",
        "toggles": {"paymentMode": "cash", "tradeInMode": "on"},
        "values": {"tradeInValue": 4_000_000, "monthlyIncome": 0, "savingsRate": 0,
                   "newCarRate": 0, "commuteTimeNew": 60},
    },
    {
        "name": "have / кредит покрыт взносом, покупка в этом году",
        "mode": "have",
        "toggles": {"creditMode": "on"},
        "values": {"newCarDownPayment": 3_000_000, "purchaseYear": 2026,
                   "monthsAlreadyPaid": 60},
    },
    {"name": "none / дефолты", "mode": "none"},
    {
        "name": "none / топливо от цены (км/л), наличные",
        "mode": "none",
        "toggles": {"ncFuelMode": "price", "ncPaymentMode": "cash",
                    "ncConsumptionUnit": "kmPer"},
        "values": {"ncConsumptionValue": 14, "ncCurrentSavings": 100_000},
    },
    {
        "name": "none / нулевой доход и ставка",
        "mode": "none",
        "values": {"ncMonthlyIncome": 0, "ncSavingsRate": 0, "ncRate": 0,
                   "ncCommuteTimeNow": 0},
    },
]


def close(a, b, tol=1.0) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= max(tol, abs(b) * 1e-6)


def main() -> int:
    failures = 0
    for case in CASES:
        js = run_js(case)
        s = py_state(case)
        py = py_values(s)
        problems: list[str] = []

        for key, expected in py.items():
            got = as_number(js["text"].get(key, ""))
            if not close(got, expected):
                problems.append(f"  {key}: JS={js['text'].get(key)!r} PY={expected!r}")

        pc = py_curves(s)
        cap = js.get("cap", {})
        if "cost" in cap:
            for label, js_series, py_series in (
                ("cost_a", cap["cost"]["a"], pc["cost_a"]),
                ("cost_b", cap["cost"]["b"], pc["cost_b"]),
            ):
                if len(js_series) != len(py_series):
                    problems.append(f"  {label}: длина JS={len(js_series)} PY={len(py_series)}")
                    continue
                for i, (jp, pp) in enumerate(zip(js_series, py_series)):
                    if not close(jp["perKm"], pp, tol=0.01):
                        problems.append(f"  {label}[{i}]: JS={jp['perKm']} PY={pp}")
        if "sav" in cap:
            for si, (js_pts, py_pts) in enumerate(zip(cap["sav"], pc["sav"])):
                for i, (jp, pp) in enumerate(zip(js_pts, py_pts)):
                    if not close(jp["value"], pp, tol=0.5):
                        problems.append(f"  sav[{si}][{i}]: JS={jp['value']} PY={pp}")
        if "hap" in cap and "hap" in pc:
            for i, (jp, pp) in enumerate(zip(cap["hap"], pc["hap"])):
                if not close(jp["value"], pp, tol=1e-6):
                    problems.append(f"  hap[{i}]: JS={jp['value']} PY={pp}")

        if not close(as_number(str(js["residual"])), round(calc.have_residual(s)), tol=1.0):
            problems.append(f"  residual: JS={js['residual']} PY={calc.have_residual(s)}")

        # Инсайты сравниваем как текст без разметки.
        if s.mode == "have":
            py_ins = {
                "loanComparison": report.loan_comparison(s, calc.have_new_car_loan(s)),
                "happinessInsight": report.happiness_insight(calc.happiness(s)),
                "savingsInsight": report.have_savings_insight(calc.have_savings(s)),
            }
        else:
            py_ins = {"savingsInsight": report.none_savings_insight(calc.none_savings(s))}
        for key, py_text in py_ins.items():
            a = strip_tags(js["insight"].get(key, ""))
            b = strip_tags(py_text).replace("⚠️ ", "").replace("💸 ", "")
            a_clean = a.replace("⚠️ ", "").replace("💸 ", "")
            if a_clean != b:
                problems.append(f"  insight {key}:\n    JS: {a_clean}\n    PY: {b}")

        status = "OK " if not problems else "FAIL"
        print(f"[{status}] {case['name']}")
        for p in problems:
            print(p)
        failures += bool(problems)
    print()
    print("Всё сошлось" if not failures else f"Расхождений в кейсах: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
