from app.dal.repositories.usage_repository import _to_decimal_or_none


def test_to_decimal_or_none_preserves_decimal_precision() -> None:
    assert _to_decimal_or_none(None) is None
    assert str(_to_decimal_or_none(0.123456)) == "0.123456"
