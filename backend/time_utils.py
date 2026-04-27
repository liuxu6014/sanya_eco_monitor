from datetime import datetime
from zoneinfo import ZoneInfo


CHINA_TZ = ZoneInfo("Asia/Shanghai")


def cn_now() -> datetime:
    return datetime.now(CHINA_TZ)


def cn_now_naive() -> datetime:
    return cn_now().replace(tzinfo=None)


def cn_now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return cn_now().strftime(fmt)
