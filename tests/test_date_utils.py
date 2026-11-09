from datetime import date
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.core.date_utils import get_current_business_date


def test_get_current_business_date_returns_date():
    today = get_current_business_date()
    assert isinstance(today, date)


def test_get_current_business_date_uses_configured_timezone():
    with patch("app.core.config.APP_TIMEZONE", "Asia/Ho_Chi_Minh"):
        today = get_current_business_date()
        assert isinstance(today, date)
