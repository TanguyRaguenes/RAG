from app.components.dashboard import _as_float, _average, _clamp, _format_score


def test_as_float_accepts_numbers_and_preserves_missing_values() -> None:
    assert _as_float("1.5") == 1.5
    assert _as_float(None) is None
    assert _as_float(float("nan")) is None


def test_average_ignores_negative_values_and_preserves_absence() -> None:
    assert _average([1.0, -1.0, 0.5]) == 0.75
    assert _average([-1.0, None]) is None


def test_clamp_bounds_score_between_zero_and_one() -> None:
    assert _clamp(-0.5) == 0.0
    assert _clamp(0.4) == 0.4
    assert _clamp(1.5) == 1.0


def test_format_score_uses_percent_or_absolute_scale() -> None:
    assert _format_score(0.876, 1.0) == "88%"
    assert _format_score(4.2, 5.0) == "4.2/5"
    assert _format_score(None, 5.0) == "N/A"
