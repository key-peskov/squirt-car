"""Графики — порт трёх canvas-функций из HTML на matplotlib.

Палитры повторяют getColors(): light / dark / cyber, включая «свечение»
киберпанк-темы (широкая полупрозрачная линия под основной).
"""

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

from .calc import CurvePoint, Happiness, HaveSavings, NoneSavings  # noqa: E402

PALETTES = {
    "light": {
        "surface": "#ffffff",
        "grid": "#e3e7ed",
        "text": "#8a929e",
        "title": "#1a1d23",
        "accent": "#2b5fd9",
        "warning": "#b45309",
        "savings": "#14804a",
        "savings_new": "#b45309",
        "savings_no_car": "#8a929e",
        "positive": "#14804a",
        "zero_line": "#c8ced6",
        "glow": False,
    },
    "dark": {
        "surface": "#1c1f24",
        "grid": "#333941",
        "text": "#707885",
        "title": "#e8eaed",
        "accent": "#5b8bf0",
        "warning": "#fbbf24",
        "savings": "#4ade80",
        "savings_new": "#fbbf24",
        "savings_no_car": "#707885",
        "positive": "#4ade80",
        "zero_line": "#4a5260",
        "glow": False,
    },
    "cyber": {
        "surface": "#120a22",
        "grid": "#3d1a5c",
        "text": "#9b7fc4",
        "title": "#e8f5ff",
        "accent": "#ff2a9d",
        "warning": "#00e5ff",
        "savings": "#00ff9d",
        "savings_new": "#00e5ff",
        "savings_no_car": "#9b7fc4",
        "positive": "#00ff9d",
        "zero_line": "#5a3a7a",
        "glow": True,
    },
}


def _fmt_thousands(v: float, _pos: int = 0) -> str:
    return f"{round(v):,}".replace(",", " ")


def _new_axes(theme: str, title: str, subtitle: str = ""):
    c = PALETTES.get(theme, PALETTES["light"])
    fig, ax = plt.subplots(figsize=(9.5, 4.4), dpi=130)
    fig.patch.set_facecolor(c["surface"])
    ax.set_facecolor(c["surface"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=c["text"], labelsize=9, length=0)
    ax.grid(True, axis="y", color=c["grid"], linewidth=0.9)
    ax.set_axisbelow(True)
    ax.set_title(title, color=c["title"], fontsize=13, fontweight="bold", loc="left", pad=16)
    if subtitle:
        ax.text(
            0, 1.02, subtitle, transform=ax.transAxes, color=c["text"], fontsize=9, va="bottom"
        )
    return fig, ax, c


def _plot_line(ax, xs, ys, color, *, dashed=False, glow=False, label=None):
    if len(xs) < 2:
        return
    style = (0, (5, 3)) if dashed else "solid"
    if glow:
        # Гало всегда сплошное: пунктирное распадается на отдельные пятна.
        ax.plot(xs, ys, color=color, linewidth=7, alpha=0.3, solid_capstyle="round")
    ax.plot(xs, ys, color=color, linewidth=2.4, linestyle=style, label=label)


def _today_marker(ax, c, x: float, text: str = "сегодня"):
    ax.axvline(x, color=c["positive"], linewidth=1.3, linestyle=(0, (2, 2)))
    ax.text(
        x,
        0.97,
        text,
        transform=ax.get_xaxis_transform(),
        color=c["positive"],
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="top",
    )


def _render(fig) -> bytes:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _legend(ax, c, loc: str = "upper left"):
    leg = ax.legend(loc=loc, frameon=False, fontsize=9)
    for txt in leg.get_texts():
        txt.set_color(c["text"])


def cost_chart(
    theme: str,
    existing: list[CurvePoint],
    new: list[CurvePoint],
    today_year: int,
    legend_existing: str,
    legend_new: str,
) -> bytes | None:
    """📈 Стоимость владения по годам — ₽ за километр."""
    all_pts = [p for p in list(existing) + list(new) if p.per_km > 0]
    if len(all_pts) < 2:
        return None
    fig, ax, c = _new_axes(
        theme,
        "Стоимость владения по годам",
        "Сколько стоит километр с учётом амортизации, эксплуатации и кредита",
    )
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_thousands))
    _plot_line(
        ax,
        [p.calendar_year for p in existing],
        [p.per_km for p in existing],
        c["accent"],
        glow=c["glow"],
        label=legend_existing,
    )
    _plot_line(
        ax,
        [p.calendar_year for p in new],
        [p.per_km for p in new],
        c["warning"],
        dashed=True,
        glow=c["glow"],
        label=legend_new,
    )
    years = [p.calendar_year for p in all_pts]
    ax.set_xlim(min(years), max(years))
    ax.set_ylim(0, max(p.per_km for p in all_pts) * 1.1)
    ax.set_ylabel("₽ / км", color=c["text"], fontsize=9)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    if min(years) <= today_year <= max(years):
        _today_marker(ax, c, today_year)
    # Слева кривые стартуют высоко — легенда уезжает вправо, чтобы их не перекрывать.
    _legend(ax, c, loc="upper right")
    return _render(fig)


def happiness_chart(theme: str, h: Happiness) -> bytes:
    """😊 Счастье от машины — линия «тогда → сейчас», продолженная в будущее."""
    fig, ax, c = _new_axes(
        theme,
        "Счастье от машины",
        "Линия между «тогда» и «сейчас» продолжена в будущее",
    )
    xs = [p[0] for p in h.series]
    ys = [p[1] for p in h.series]
    _plot_line(ax, xs, ys, c["accent"], glow=c["glow"], label="Текущая машина")
    ax.set_ylim(0, 10)
    ax.set_xlim(h.purchase_year, max(h.purchase_year + 10, h.now + 10))
    ax.set_ylabel("оценка из 10", color=c["text"], fontsize=9)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    _today_marker(ax, c, h.now)
    _legend(ax, c)
    return _render(fig)


def _savings_axes(theme: str):
    fig, ax, c = _new_axes(
        theme, "Накопления за 10 лет", "Как изменятся накопления при разных сценариях"
    )
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: _fmt_thousands(v) + " ₽"))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    ax.set_xlabel("лет", color=c["text"], fontsize=9)
    return fig, ax, c


def _finish_savings(fig, ax, c, series: list[list[tuple[int, float]]], years: int) -> bytes:
    lo = min(min(v for _, v in s) for s in series)
    hi = max(max(v for _, v in s) for s in series)
    if lo < 0 < hi:
        ax.axhline(0, color=c["zero_line"], linewidth=1, linestyle=(0, (3, 3)))
    ax.set_xlim(0, years)
    _legend(ax, c)
    return _render(fig)


def have_savings_chart(theme: str, sav: HaveSavings, years: int = 10) -> bytes:
    fig, ax, c = _savings_axes(theme)
    for pts, color, dashed, label in (
        (sav.keep, c["savings"], False, "Оставить текущую"),
        (sav.new, c["savings_new"], False, "Купить новую"),
        (sav.no_car, c["savings_no_car"], True, "Без машины вообще"),
    ):
        _plot_line(
            ax,
            [p[0] for p in pts],
            [p[1] for p in pts],
            color,
            dashed=dashed,
            glow=c["glow"],
            label=label,
        )
    return _finish_savings(fig, ax, c, [sav.keep, sav.new, sav.no_car], years)


def none_savings_chart(theme: str, sav: NoneSavings, years: int = 10) -> bytes:
    fig, ax, c = _savings_axes(theme)
    for pts, color, dashed, label in (
        (sav.car, c["savings_new"], False, "Купить машину"),
        (sav.no_car, c["savings_no_car"], True, "Без машины"),
    ):
        _plot_line(
            ax,
            [p[0] for p in pts],
            [p[1] for p in pts],
            color,
            dashed=dashed,
            glow=c["glow"],
            label=label,
        )
    return _finish_savings(fig, ax, c, [sav.car, sav.no_car], years)
