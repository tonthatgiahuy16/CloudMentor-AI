from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core import config


def get_current_business_date() -> date:
    """Return today's date in the configured business timezone."""
    try:
        return datetime.now(ZoneInfo(config.APP_TIMEZONE)).date()
    except Exception:
        return datetime.now().astimezone().date()
