"""State: разбор значений полей ровно как num()/intInRange() в HTML."""

import pytest
from squirtcar.model import ALL_FIELDS, DEFAULTS, TOGGLES, State


def test_state_starts_from_html_defaults():
    s = State()
    assert s.values == DEFAULTS
    assert s.values is not DEFAULTS  # копия, а не общая ссылка
    assert s.toggles == {k: v[0] for k, v in TOGGLES.items()}


def test_two_states_do_not_share_values():
    a, b = State(), State()
    a.values["purchasePrice"] = 1
    a.toggles["creditMode"] = "on"
    assert b.values["purchasePrice"] == DEFAULTS["purchasePrice"]
    assert b.toggles["creditMode"] == "off"


@pytest.mark.parametrize(
    "raw,expected",
    [("1000", 1000.0), (1000, 1000.0), ("12.5", 12.5), (-5, 0.0), ("-5", 0.0), (0, 0.0)],
)
def test_num_zeroes_out_non_positive(raw, expected):
    s = State()
    s.values["purchasePrice"] = raw
    assert s.num("purchasePrice") == expected


@pytest.mark.parametrize("raw", ["", "абв", None, "1 000"])
def test_num_zeroes_out_garbage(raw):
    s = State()
    s.values["purchasePrice"] = raw
    assert s.num("purchasePrice") == 0.0


def test_num_of_unknown_key_is_zero():
    assert State().num("нет такого поля") == 0.0


@pytest.mark.parametrize("raw,expected", [(5, 5), (0, 1), (99, 10), ("7", 7), ("абв", 5), (7.9, 7)])
def test_intval_clamps_into_range(raw, expected):
    s = State()
    s.values["happyNow"] = raw
    assert s.intval("happyNow", 1, 10, 5) == expected


def test_reset_returns_everything_to_defaults():
    s = State()
    s.values["purchasePrice"] = 42
    s.toggles["paymentMode"] = "cash"
    s.reset()
    assert s.values == DEFAULTS
    assert s.toggles["paymentMode"] == "credit"


def test_every_field_key_is_unique_and_has_a_default():
    assert set(ALL_FIELDS) == set(DEFAULTS)
    assert all(f.key == key for key, f in ALL_FIELDS.items())


def test_toggle_defaults_are_listed_among_their_options():
    for key, (default, options) in TOGGLES.items():
        assert default in [value for value, _ in options], key
