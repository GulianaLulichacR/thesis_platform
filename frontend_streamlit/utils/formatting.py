from datetime import datetime


def as_percent(value: float) -> str:
    return f"{value:.1f}%"


def now_label() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
