"""SquirtCar — телеграм-версия калькулятора владения авто.

Запуск:  BOT_TOKEN=... python -m squirtcar.bot
"""

import asyncio
import logging
import os
from html import escape
from io import BytesIO

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)

from . import calc, charts, report, sections, share
from .model import ALL_FIELDS, DISCLAIMER, THEMES, TOGGLES, State

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("squirtcar")

TG_LIMIT = 4000


# ============ СОСТОЯНИЕ ============


def get_state(context: ContextTypes.DEFAULT_TYPE) -> State:
    s = context.user_data.get("state")
    if not isinstance(s, State):
        s = State()
        context.user_data["state"] = s
    return s


def fmt_value(s: State, key: str) -> str:
    f = ALL_FIELDS[key]
    raw = s.values.get(key, f.default)
    if f.kind == "text":
        return str(raw)
    try:
        v = float(raw)
    except (TypeError, ValueError):
        v = 0.0
    if f.kind == "int" or v == int(v):
        body = f"{int(v):,}".replace(",", " ")
    else:
        body = f"{v:g}"
    return f"{body} {f.unit}".strip()


# ============ КЛАВИАТУРЫ ============


def kb_modes() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚗 У меня уже есть машина", callback_data="mode:have")],
            [InlineKeyboardButton("🅿️ У меня нет машины", callback_data="mode:none")],
        ]
    )


def kb_menu(s: State) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(title, callback_data=f"sec:{key}")]
        for key, title in sections.MENU[s.mode]
    ]
    rows.append([InlineKeyboardButton("📊 Показать результат", callback_data="result")])
    rows.append(
        [
            InlineKeyboardButton("🔗 Скачать HTML", callback_data="share"),
            InlineKeyboardButton("🎨 Тема", callback_data="theme"),
        ]
    )
    if s.mode == "none":
        rows.append([InlineKeyboardButton("⚠️ Что входит в владение", callback_data="disclaimer")])
    rows.append(
        [
            InlineKeyboardButton("🔄 Сбросить", callback_data="reset"),
            InlineKeyboardButton("← Другой сценарий", callback_data="pick"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def kb_section(section: str, s: State) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pending: list[InlineKeyboardButton] = []

    def flush() -> None:
        nonlocal pending
        if pending:
            rows.append(pending)
            pending = []

    for kind, key in sections.items(section, s):
        if kind == "head":
            flush()
        elif kind == "field":
            pending.append(
                InlineKeyboardButton(ALL_FIELDS[key].label, callback_data=f"edit:{section}:{key}")
            )
            if len(pending) == 2:
                flush()
        elif kind == "toggle":
            flush()
            options = TOGGLES[key][1]
            rows.append(
                [
                    InlineKeyboardButton(
                        ("● " if s.toggles[key] == value else "○ ") + caption,
                        callback_data=f"tog:{section}:{key}:{value}",
                    )
                    for value, caption in options
                ]
            )
        elif kind == "action" and key == "residual":
            flush()
            rows.append(
                [
                    InlineKeyboardButton(
                        "= подставить остаточную стоимость",
                        callback_data=f"act:{section}:residual",
                    )
                ]
            )
    flush()
    rows.append(
        [
            InlineKeyboardButton("📊 Результат", callback_data="result"),
            InlineKeyboardButton("← В меню", callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def kb_theme(s: State) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                ("● " if s.theme == key else "○ ") + caption, callback_data=f"th:{key}"
            )
        ]
        for key, caption in THEMES
    ]
    rows.append([InlineKeyboardButton("← В меню", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def kb_share(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    personal = context.user_data.get("sharePersonal", True)
    savings = context.user_data.get("shareSavings", True)
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    ("☑️" if personal else "☐") + " Личные расходы", callback_data="shtog:personal"
                )
            ],
            [
                InlineKeyboardButton(
                    ("☑️" if savings else "☐") + " Накопления", callback_data="shtog:savings"
                )
            ],
            [InlineKeyboardButton("⬇️ Скачать HTML", callback_data="shgo")],
            [InlineKeyboardButton("← В меню", callback_data="menu")],
        ]
    )


def kb_happy(section: str, key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(str(v), callback_data=f"set:{section}:{key}:{v}")
                for v in range(1, 6)
            ],
            [
                InlineKeyboardButton(str(v), callback_data=f"set:{section}:{key}:{v}")
                for v in range(6, 11)
            ],
            [InlineKeyboardButton("← Назад", callback_data=f"sec:{section}")],
        ]
    )


# ============ ТЕКСТЫ ЭКРАНОВ ============

WELCOME = (
    "🚗 <b>SquirtCar</b> — дружелюбный калькулятор владения авто.\n\n"
    "Выберите сценарий — от него зависит, какие поля появятся. "
    "Вернуться назад можно в любой момент."
)


def menu_text(s: State) -> str:
    if s.mode == "have":
        head = "Сценарий: <b>у меня уже есть машина</b>"
        sub = "Считаю, сколько стоит текущая, и стоит ли менять её на новую."
        summary = (
            f"Текущая: <b>{report.fmt(calc.have_current_monthly(s))} ₽/мес</b>\n"
            f"Новая: <b>{report.fmt(calc.have_new_monthly(s))} ₽/мес</b>"
        )
    else:
        head = "Сценарий: <b>у меня нет машины</b>"
        sub = "Прикидываю, во что обойдётся покупка, и как это повлияет на накопления."
        summary = f"Машина: <b>{report.fmt(calc.nc_monthly(s))} ₽/мес</b>"
    return f"{head}\n{sub}\n\n{summary}\n\nЧто поправим?"


def section_text(section: str, s: State) -> str:
    lines = [f"<b>{sections.SECTION_TITLES[section]}</b>", ""]
    for kind, key in sections.items(section, s):
        if kind == "head":
            lines += ["", f"<b>{escape(key)}</b>"]
        elif kind == "field":
            lines.append(f"• {ALL_FIELDS[key].label}: <b>{escape(fmt_value(s, key))}</b>")
        elif kind == "toggle":
            caption = dict(TOGGLES[key][1])[s.toggles[key]]
            lines.append(f"↳ <i>{escape(caption)}</i>")
    if section == "cur" and s.toggles["depreciationMode"] == "auto":
        lines.append(
            f"\n📉 Потери в год: <b>{report.fmt(calc.have_auto_depreciation(s))} ₽</b>"
        )
    if section == "cur" and s.toggles["fuelMode"] == "price":
        lines.append(
            f"\n⛽ Расчётная стоимость топлива: <b>{report.fmt(calc.have_fuel_annual(s))} ₽/год</b>"
        )
    if section == "car" and s.toggles["ncFuelMode"] == "price":
        lines.append(
            f"\n⛽ Расчётная стоимость топлива: <b>{report.fmt(calc.nc_fuel_annual(s))} ₽/год</b>"
        )
    if section == "cur" and s.toggles["creditMode"] == "on":
        lines.append(
            f"\n💳 Выплаты: <b>{report.fmt(calc.have_credit_yearly(s))} ₽/год</b> · "
            f"переплата <b>{report.fmt(calc.have_credit_overpay(s))} ₽</b>"
        )
    if section == "new":
        lines.append(
            f"\nБаза роста расходов = расходы текущей: "
            f"<b>{report.fmt(calc.have_operating(s))} ₽/год</b>"
        )
    lines.append("\nНажмите на поле, чтобы изменить значение.")
    return "\n".join(lines)


# ============ ОТРИСОВКА ============


async def render(update: Update, text: str, markup: InlineKeyboardMarkup) -> None:
    """Экраны меню всегда живут в одном сообщении — правим его на месте."""
    query = update.callback_query
    if query is not None:
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except BadRequest as err:
            if "not modified" in str(err).lower():
                return  # экран уже такой — второе сообщение было бы мусором
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        return
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


def split_message(text: str, limit: int = TG_LIMIT) -> list[str]:
    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current)
    return chunks


async def build_charts(s: State) -> list[bytes]:
    """matplotlib блокирует — уводим в поток, чтобы не вешать апдейты."""

    def work() -> list[bytes]:
        images: list[bytes] = []
        if s.mode == "have":
            existing, new = calc.have_curves(s)
            cost = charts.cost_chart(
                s.theme,
                existing,
                new,
                calc.current_year(),
                "Текущая машина (₽/км)",
                "Новая машина (₽/км)",
            )
            if cost:
                images.append(cost)
            images.append(charts.happiness_chart(s.theme, calc.happiness(s)))
            images.append(charts.have_savings_chart(s.theme, calc.have_savings(s)))
        else:
            cost = charts.cost_chart(
                s.theme,
                [],
                calc.none_curve(s),
                calc.current_year(),
                "Без машины (0 ₽/км)",
                "Рассматриваемая (₽/км)",
            )
            if cost:
                images.append(cost)
            images.append(charts.none_savings_chart(s.theme, calc.none_savings(s)))
        return images

    return await asyncio.to_thread(work)


async def send_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_state(context)
    chat = update.effective_chat
    await chat.send_action("typing")
    for chunk in split_message(report.report(s)):
        await chat.send_message(chunk, parse_mode=ParseMode.HTML)
    images = await build_charts(s)
    if len(images) == 1:
        await chat.send_photo(BytesIO(images[0]))
    elif images:
        await chat.send_media_group([InputMediaPhoto(BytesIO(img)) for img in images])
    await chat.send_message(
        "Что дальше?",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("← В меню", callback_data="menu")],
                [InlineKeyboardButton("🔗 Скачать HTML", callback_data="share")],
            ]
        ),
    )


# ============ ХЭНДЛЕРЫ ============


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_state(context)
    s.mode = None
    context.user_data.pop("awaiting", None)
    await render(update, WELCOME, kb_modes())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "/start — выбрать сценарий\n"
        "/menu — меню расчёта\n"
        "/result — показать результат и графики\n"
        "/share — скачать расчёт одним HTML-файлом\n"
        "/theme — тема графиков\n"
        "/reset — вернуть значения по умолчанию\n\n"
        "Все поля уже заполнены разумными значениями — можно сразу смотреть результат "
        "и править только то, что важно."
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_state(context)
    context.user_data.pop("awaiting", None)
    if not s.mode:
        await render(update, WELCOME, kb_modes())
        return
    await render(update, menu_text(s), kb_menu(s))


async def cmd_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_state(context)
    if not s.mode:
        await render(update, WELCOME, kb_modes())
        return
    await send_result(update, context)


async def cmd_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_state(context)
    if not s.mode:
        await render(update, WELCOME, kb_modes())
        return
    await render(update, "Что включить в файл?", kb_share(context))


async def cmd_theme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render(update, "Тема графиков:", kb_theme(get_state(context)))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_state(context)
    s.reset()
    context.user_data.pop("awaiting", None)
    if s.mode:
        await render(update, "Значения сброшены.\n\n" + menu_text(s), kb_menu(s))
    else:
        await render(update, WELCOME, kb_modes())


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    s = get_state(context)
    data = query.data or ""
    parts = data.split(":")
    action = parts[0]

    if action == "mode":
        s.mode = parts[1]
        context.user_data.pop("awaiting", None)
        await render(update, menu_text(s), kb_menu(s))

    elif action == "pick":
        s.mode = None
        await render(update, WELCOME, kb_modes())

    elif action == "menu":
        context.user_data.pop("awaiting", None)
        await render(update, menu_text(s), kb_menu(s))

    elif action == "sec":
        context.user_data.pop("awaiting", None)
        section = parts[1]
        await render(update, section_text(section, s), kb_section(section, s))

    elif action == "tog":
        _, section, key, value = parts
        s.toggles[key] = value
        await render(update, section_text(section, s), kb_section(section, s))

    elif action == "act" and parts[2] == "residual":
        section = parts[1]
        s.values["tradeInValue"] = round(calc.have_residual(s))
        await render(update, section_text(section, s), kb_section(section, s))

    elif action == "edit":
        _, section, key = parts
        f = ALL_FIELDS[key]
        if key in ("happyAtPurchase", "happyNow"):
            await render(
                update,
                f"<b>{f.label}</b>\nСейчас: <b>{fmt_value(s, key)}</b>\n\nОцените от 1 до 10:",
                kb_happy(section, key),
            )
            return
        context.user_data["awaiting"] = (section, key)
        limits = []
        if f.minimum is not None:
            limits.append(f"от {f.minimum:g}")
        if f.maximum is not None:
            limits.append(f"до {f.maximum:g}")
        hint = f"\nДопустимо: {', '.join(limits)}" if f.kind != "text" and limits else ""
        await render(
            update,
            f"<b>{f.label}</b>\nСейчас: <b>{escape(fmt_value(s, key))}</b>{hint}\n\n"
            "Пришлите новое значение сообщением.",
            InlineKeyboardMarkup(
                [[InlineKeyboardButton("← Отмена", callback_data=f"sec:{section}")]]
            ),
        )

    elif action == "set":
        _, section, key, value = parts
        s.values[key] = int(value)
        await render(update, section_text(section, s), kb_section(section, s))

    elif action == "result":
        await send_result(update, context)

    elif action == "theme":
        await render(update, "Тема графиков:", kb_theme(s))

    elif action == "th":
        s.theme = parts[1]
        await render(update, "Тема графиков:", kb_theme(s))

    elif action == "share":
        await render(update, "Что включить в файл?", kb_share(context))

    elif action == "shtog":
        flag = "sharePersonal" if parts[1] == "personal" else "shareSavings"
        context.user_data[flag] = not context.user_data.get(flag, True)
        await render(update, "Что включить в файл?", kb_share(context))

    elif action == "shgo":
        html = share.build_shared_html(
            s,
            context.user_data.get("sharePersonal", True),
            context.user_data.get("shareSavings", True),
        )
        document = BytesIO(html.encode("utf-8"))
        document.name = "squirtcar-raschet.html"
        await query.message.reply_document(document, filename="squirtcar-raschet.html")
        await query.message.reply_text(
            "Готово.", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("← В меню", callback_data="menu")]]
            )
        )

    elif action == "disclaimer":
        await render(
            update,
            DISCLAIMER,
            InlineKeyboardMarkup([[InlineKeyboardButton("← В меню", callback_data="menu")]]),
        )

    elif action == "reset":
        s.reset()
        await render(update, "Значения сброшены.\n\n" + menu_text(s), kb_menu(s))


def parse_number(raw: str) -> float | None:
    cleaned = (
        raw.replace(" ", "")
        .replace(" ", "")
        .replace("₽", "")
        .replace("%", "")
        .replace(",", ".")
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    awaiting = context.user_data.get("awaiting")
    s = get_state(context)
    if not awaiting:
        if s.mode:
            await update.effective_message.reply_text(menu_text(s), parse_mode=ParseMode.HTML,
                                                      reply_markup=kb_menu(s))
        else:
            await update.effective_message.reply_text(WELCOME, parse_mode=ParseMode.HTML,
                                                      reply_markup=kb_modes())
        return

    section, key = awaiting
    f = ALL_FIELDS[key]
    raw = (update.effective_message.text or "").strip()

    if f.kind == "text":
        s.values[key] = raw[:60]
    else:
        value = parse_number(raw)
        if value is None:
            await update.effective_message.reply_text(
                "Не разобрал число. Пришлите, например: 1500000 или 8.5"
            )
            return
        if f.minimum is not None and value < f.minimum:
            value = f.minimum
        if f.maximum is not None and value > f.maximum:
            value = f.maximum
        s.values[key] = int(round(value)) if f.kind == "int" else value

    context.user_data.pop("awaiting", None)
    await update.effective_message.reply_text(
        section_text(section, s), parse_mode=ParseMode.HTML, reply_markup=kb_section(section, s)
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Ошибка при обработке апдейта", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Что-то пошло не так при расчёте. Попробуйте /menu или /reset."
        )


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("Не задан BOT_TOKEN — положите токен в переменную окружения.")

    persistence = PicklePersistence(filepath=os.environ.get("STATE_FILE", "squirtcar_state.pickle"))
    app = Application.builder().token(token).persistence(persistence).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("result", cmd_result))
    app.add_handler(CommandHandler("share", cmd_share))
    app.add_handler(CommandHandler("theme", cmd_theme))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    log.info("SquirtCar bot запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
