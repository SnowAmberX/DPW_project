from datetime import datetime
import random

from app.constants.country_codes import ISO3_CODES


def generate_mock_snapshot() -> dict:
    """构造测试用快照，后续可以替换为真实业务数据。"""
    infections = {code: random.randint(0, 300000) for code in ISO3_CODES}
    return {
        "time": datetime.now().strftime("%Y:%m:%d"),
        "infections_by_country": infections,
    }
