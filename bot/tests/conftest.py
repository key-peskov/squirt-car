import pytest
from squirtcar.model import State


@pytest.fixture
def have() -> State:
    """Состояние сценария «есть машина» со значениями по умолчанию из HTML."""
    s = State()
    s.mode = "have"
    return s


@pytest.fixture
def none() -> State:
    s = State()
    s.mode = "none"
    return s


@pytest.fixture
def frozen_year(monkeypatch) -> int:
    """Фиксируем «сегодня»: иначе тесты про амортизацию поедут в следующем году."""
    monkeypatch.setattr("squirtcar.calc.current_year", lambda: 2026)
    return 2026
