from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
import sys

from PIL import Image
from matplotlib import font_manager

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.chart_service import (
    _FONT_FAMILIES,
    _TITLE_HISTORY_CORE,
    _TITLE_HISTORY_WATER,
    _TITLE_RUNOFF_DEVICE,
    _TITLE_WATER_QUALITY,
    _get_chart_font,
    _get_chart_font_family,
    _get_chart_font_path,
    generate_all_charts,
)


def main() -> None:
    summary = {
        "insect": {
            "daily": [
                {"date": "2026-05-01", "count": 12},
                {"date": "2026-05-02", "count": 18},
                {"date": "2026-05-03", "count": 9},
                {"date": "2026-05-04", "count": 22},
            ],
            "top_species": [
                ["甜菜夜蛾", 48],
                ["斜纹夜蛾", 19],
                ["稻纵卷叶螟", 11],
            ],
        },
        "spore": {
            "daily": [
                {"date": "2026-05-01", "count": 4},
                {"date": "2026-05-02", "count": 7},
                {"date": "2026-05-03", "count": 3},
                {"date": "2026-05-04", "count": 6},
            ]
        },
        "rain": {
            "daily": [
                {"date": "2026-05-01", "rainfall": 12.4},
                {"date": "2026-05-02", "rainfall": 39.4},
                {"date": "2026-05-03", "rainfall": 21.4},
                {"date": "2026-05-04", "rainfall": 30.8},
            ],
            "total_rainfall": 104.0,
        },
        "runoff": {
            "by_device": {
                "16132920": {"name": "橡胶林径流点1", "total_runoff": 24.6},
                "16132921": {"name": "次生林径流点", "total_runoff": 18.2},
                "16132922": {"name": "芒果林径流点1", "total_runoff": 13.7},
                "16132923": {"name": "槟榔林径流点", "total_runoff": 11.9},
                "16132924": {"name": "橡胶林径流点2", "total_runoff": 9.1},
                "16132925": {"name": "芒果林径流点2", "total_runoff": 7.5},
            }
        },
        "water_quality": {
            "avg_nh3_n": 0.13,
            "avg_tp": 0.02,
            "avg_permanganate": 1.80,
            "avg_tn": 0.57,
        },
        "history_comparison": {
            "modules": {
                "insect": {"label": "虫情监测", "change_rate": 25.9},
                "spore": {"label": "孢子监测", "change_rate": 29.4},
                "rain": {"label": "雨量监测", "change_rate": 42.8},
                "runoff": {"label": "地表径流监测", "change_rate": 33.7},
            },
            "water_quality": {
                "metrics": [
                    {"label": "氨氮", "current_value": 0.13, "previous_value": 0.21},
                    {"label": "总磷", "current_value": 0.02, "previous_value": 0.03},
                    {"label": "高锰酸盐", "current_value": 1.80, "previous_value": 2.10},
                    {"label": "总氮", "current_value": 0.57, "previous_value": 0.63},
                ]
            },
        },
    }

    font_path = _get_chart_font_path()
    bold_font_path = _get_chart_font_path(weight="bold")
    chart_font = _get_chart_font(size=12, weight="bold")
    chart_font_family = _get_chart_font_family()
    chart_bold_family = _get_chart_font_family(weight="bold")
    print("python_default_font=", font_manager.findfont(font_manager.FontProperties(), fallback_to_default=True))
    print("python_sans_font=", font_manager.findfont(font_manager.FontProperties(family=["sans-serif"]), fallback_to_default=True))
    print("font_families=", _FONT_FAMILIES)
    print("chart_font_family=", chart_font_family)
    print("chart_bold_font_family=", chart_bold_family)
    print("chart_font_path=", font_path)
    print("chart_bold_font_path=", bold_font_path)
    print("chart_font_file=", chart_font.get_file())
    print("title_runoff=", _TITLE_RUNOFF_DEVICE)
    print("title_water=", _TITLE_WATER_QUALITY)
    print("title_history_core=", _TITLE_HISTORY_CORE)
    print("title_history_water=", _TITLE_HISTORY_WATER)
    print("runoff_names=", [item["name"] for item in summary["runoff"]["by_device"].values()])
    print("water_names=", ["氨氮", "总磷", "高锰酸盐", "总氮"])
    print("history_core_labels=", [summary["history_comparison"]["modules"][key]["label"] for key in ("insect", "spore", "rain", "runoff")])
    print("history_water_labels=", [item["label"] for item in summary["history_comparison"]["water_quality"]["metrics"]])

    charts = generate_all_charts(summary)
    out_dir = Path(__file__).resolve().parents[1] / "tmp" / "debug_chart_fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, b64 in charts.items():
        if not b64:
            continue
        data = base64.b64decode(b64)
        path = out_dir / f"{key}.png"
        path.write_bytes(data)
        im = Image.open(BytesIO(data))
        print(f"saved={path.name} size={im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
