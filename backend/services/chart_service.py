"""Chart generation service for report figures."""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
import subprocess
from typing import Any

import matplotlib

matplotlib.use("Agg")

from matplotlib import font_manager
from matplotlib.font_manager import FontProperties


logger = logging.getLogger(__name__)


_PREFERRED_FONT_FAMILIES = [
    "Microsoft YaHei",
    "WenQuanYi Zen Hei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "SimHei",
    "SimSun",
    "Noto Sans CJK JP",
    "Noto Serif CJK SC",
    "AR PL UKai CN",
    "AR PL UMing CN",
    "DejaVu Sans",
]

_PREFERRED_FONT_PATHS = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    Path("/usr/share/fonts/truetype/arphic/ukai.ttc"),
    Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
]

_REGULAR_FONT_HINTS = ("regular", "normal")
_BOLD_FONT_HINTS = ("bold", "demi", "medium", "semibold")


def _register_font(path: Path, registered: list[str]) -> None:
    if not path.exists():
        return
    try:
        font_manager.fontManager.addfont(str(path))
        registered.append(font_manager.FontProperties(fname=str(path)).get_name())
    except Exception:
        logger.debug("Failed to register font: %s", path, exc_info=True)


def _fontconfig_match_paths(patterns: list[str]) -> list[Path]:
    matched: list[Path] = []
    for pattern in patterns:
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{file}\n", pattern],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            continue

        for line in result.stdout.splitlines():
            path = Path(line.strip())
            if path.exists():
                matched.append(path)
    return matched


def _ordered_font_families(registered: list[str]) -> list[str]:
    # Keep Simplified Chinese families ahead of TTC-derived aliases such as
    # "Noto Sans CJK JP" so single titles do not mix glyphs across locales.
    ordered: list[str] = []
    for family in _PREFERRED_FONT_FAMILIES + registered:
        if family and family not in ordered:
            ordered.append(family)
    return ordered


def _find_font_for_family(family: str, *, weight: str | None = None) -> str | None:
    try:
        return font_manager.findfont(
            FontProperties(family=[family], weight=weight),
            fallback_to_default=False,
        )
    except Exception:
        return None


def _get_chart_font_family(*, weight: str | None = None) -> str | None:
    for family in _PREFERRED_FONT_FAMILIES:
        if _find_font_for_family(family, weight=weight):
            return family
    return None


def _resolve_preferred_font_paths() -> list[Path]:
    paths = list(_PREFERRED_FONT_PATHS)
    paths.extend(
        _fontconfig_match_paths(
            [
                "Microsoft YaHei",
                "WenQuanYi Zen Hei",
                "SimHei",
                "Noto Sans CJK SC",
                "Source Han Sans SC",
                "Noto Sans CJK JP",
                "Noto Serif CJK SC",
            ]
        )
    )
    ordered: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve(strict=False)
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        ordered.append(path)
    return ordered


def _select_font_path(paths: list[Path], *, weight: str | None = None) -> Path | None:
    if not paths:
        return None
    if not weight:
        return paths[0]

    weight_lower = weight.lower()
    hints = _BOLD_FONT_HINTS if weight_lower == "bold" else _REGULAR_FONT_HINTS
    fallback = paths[0]
    for path in paths:
        name = path.name.lower()
        if any(hint in name for hint in hints):
            return path
    return fallback


def _get_chart_font_path(*, weight: str | None = None) -> Path | None:
    paths = _resolve_preferred_font_paths()
    return _select_font_path(paths, weight=weight)


def _build_chart_font(*, size: float | None = None, weight: str | None = None) -> FontProperties | None:
    family = _get_chart_font_family(weight=weight)
    if family:
        return FontProperties(family=[family], size=size, weight=weight)
    path = _get_chart_font_path(weight=weight)
    if path is not None:
        return FontProperties(fname=str(path), size=size)
    return None


def _get_chart_font(*, size: float | None = None, weight: str | None = None) -> FontProperties:
    font = _build_chart_font(size=size, weight=weight)
    if font is not None:
        return font
    return FontProperties(family=_FONT_FAMILIES, size=size, weight=weight)


def _configure_fonts() -> list[str]:
    font_paths = _resolve_preferred_font_paths()
    registered: list[str] = []
    seen_paths: set[Path] = set()
    for path in font_paths:
        resolved = path.resolve(strict=False)
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        _register_font(path, registered)

    families = _ordered_font_families(registered)
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": families,
            "axes.unicode_minus": False,
        }
    )
    logger.info("Configured matplotlib font families: %s", families)
    return families


_FONT_FAMILIES = _configure_fonts()


def _apply_tick_font(labels: list[Any], *, size: float, weight: str | None = None) -> None:
    font = _get_chart_font(size=size, weight=weight)
    for label in labels:
        label.set_fontproperties(font)
        label.set_color(_TEXT)


def _apply_axis_title(text_obj: Any, *, size: float, weight: str | None = None) -> None:
    text_obj.set_fontproperties(_get_chart_font(size=size, weight=weight))
    text_obj.set_color(_TEXT)


def _text_kwargs(*, size: float, weight: str | None = None) -> dict[str, Any]:
    return {
        "fontsize": size,
        "fontproperties": _get_chart_font(size=size, weight=weight),
        "color": _TEXT,
    }

import matplotlib.pyplot as plt
import numpy as np


_BLUE = "#2E86C1"
_GREEN = "#28B463"
_ORANGE = "#E67E22"
_RED = "#C0392B"
_PURPLE = "#8E44AD"
_TEAL = "#17A589"
_GRAY = "#7F8C8D"

_PALETTE = [
    _BLUE,
    _GREEN,
    _ORANGE,
    _RED,
    _PURPLE,
    _TEAL,
    _GRAY,
    "#F1C40F",
    "#1ABC9C",
    "#D35400",
]

_BG = "#FAFAFA"
_GRID = "#DDDDDD"
_TEXT = "#2C3E50"

_LABEL_CAPTURE = "\u6355\u83b7\u6570\u91cf\uff08\u53ea\uff09"
_LABEL_RAINFALL = "\u964d\u96e8\u91cf\uff08mm\uff09"
_TITLE_INSECT_DAILY = "\u6bcf\u65e5\u866b\u60c5\u6355\u83b7\u91cf"
_TITLE_INSECT_SPECIES = "\u4e3b\u8981\u866b\u79cd\u6355\u83b7\u7edf\u8ba1\uff08Top 10\uff09"
_LABEL_SPORE = "\u5b62\u5b50\u6570\u91cf\uff08\u4e2a\uff09"
_TITLE_SPORE_DAILY = "\u6bcf\u65e5\u5b62\u5b50\u6355\u83b7\u91cf\u8d8b\u52bf"
_LEGEND_SPORE = "\u6bcf\u65e5\u5b62\u5b50\u6570\u91cf"
_TITLE_RAIN_DAILY = "\u76d1\u6d4b\u671f\u6bcf\u65e5\u964d\u96e8\u91cf"
_TITLE_RUNOFF_DEVICE = "\u5404\u76d1\u6d4b\u70b9\u7d2f\u8ba1\u5f84\u6d41\u91cf\u5bf9\u6bd4"
_TITLE_WATER_QUALITY = "\u6c34\u8d28\u5173\u952e\u6307\u6807\u5e73\u5747\u503c"
_TITLE_HISTORY_CORE = "\u672c\u671f\u4e0e\u4e0a\u4e00\u7b49\u957f\u5468\u671f\u6838\u5fc3\u76d1\u6d4b\u6307\u6807\u53d8\u5316\u7387"
_TITLE_HISTORY_WATER = "\u6c34\u8d28\u5173\u952e\u6307\u6807\u672c\u671f\u4e0e\u4e0a\u4e00\u5468\u671f\u5747\u503c\u5bf9\u6bd4"
_KEY_INSECT_DAILY = "\u866b\u60c5\u65e5\u6355\u83b7"
_KEY_INSECT_SPECIES = "\u866b\u79cd\u7edf\u8ba1"
_KEY_SPORE_DAILY = "\u5b62\u5b50\u8d8b\u52bf"
_KEY_RAIN_DAILY = "\u96e8\u91cf\u65e5\u7edf\u8ba1"
_KEY_RUNOFF_DEVICE = "\u5f84\u6d41\u7ad9\u70b9\u5bf9\u6bd4"
_KEY_WATER_QUALITY = "\u6c34\u8d28\u6307\u6807\u5747\u503c"
_KEY_HISTORY_CORE = "\u6838\u5fc3\u6307\u6807\u5386\u53f2\u5bf9\u6bd4"
_KEY_HISTORY_WATER = "\u6c34\u8d28\u5386\u53f2\u5bf9\u6bd4"
_UNIT_ONLY = "\u53ea"


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _base_fig(width: float = 9, height: float = 4) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_GRID)
    ax.spines["bottom"].set_color(_GRID)
    ax.tick_params(colors=_TEXT, labelsize=9)
    ax.yaxis.grid(True, color=_GRID, linestyle="--", linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def chart_insect_daily(summary: dict[str, Any]) -> str | None:
    daily = summary.get("insect", {}).get("daily", [])
    if not daily:
        return None

    dates = [d["date"][5:] for d in daily]
    counts = [d["count"] for d in daily]
    if all(count == 0 for count in counts):
        return None

    fig, ax = _base_fig(9, 3.6)
    x = np.arange(len(dates))
    max_count = max(counts) if counts else 1
    colors = [plt.cm.YlOrRd(0.25 + 0.65 * (count / max_count)) for count in counts]

    bars = ax.bar(x, counts, color=colors, width=0.6, zorder=3, edgecolor="white", linewidth=0.5)
    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_count * 0.01,
                str(count),
                ha="center",
                va="bottom",
                **_text_kwargs(size=7.5),
            )

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    _apply_tick_font(list(ax.get_xticklabels()), size=8)
    ylabel = ax.set_ylabel(_LABEL_CAPTURE)
    _apply_axis_title(ylabel, size=9)
    title = ax.set_title(_TITLE_INSECT_DAILY, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_rainfall_daily(summary: dict[str, Any]) -> str | None:
    daily = summary.get("rain", {}).get("daily", [])
    if not daily:
        return None

    dates = [item["date"][5:] for item in daily]
    rainfalls = [float(item.get("rainfall") or 0) for item in daily]
    if not any(value > 0 for value in rainfalls):
        return None

    fig, ax = _base_fig(9, 3.6)
    x = np.arange(len(dates))
    bars = ax.bar(x, rainfalls, color=_BLUE, width=0.58, alpha=0.88, zorder=3)

    for bar, value in zip(bars, rainfalls):
        if value > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(rainfalls) * 0.02,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                **_text_kwargs(size=7.5),
            )

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    _apply_tick_font(list(ax.get_xticklabels()), size=8)
    ylabel = ax.set_ylabel(_LABEL_RAINFALL)
    _apply_axis_title(ylabel, size=9)
    title = ax.set_title(_TITLE_RAIN_DAILY, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_runoff_device(summary: dict[str, Any]) -> str | None:
    by_device = (summary.get("runoff") or {}).get("by_device") or {}
    if not by_device:
        return None

    ordered = sorted(
        by_device.items(),
        key=lambda item: ((item[1].get("total_runoff") or 0), item[1].get("name", item[0])),
        reverse=True,
    )
    names = [item[1].get("name", item[0]) for item in ordered]
    values = [float(item[1].get("total_runoff") or 0) for item in ordered]

    fig, ax = _base_fig(9, max(3.8, 0.6 * len(names) + 1.5))
    y = np.arange(len(names))
    bars = ax.barh(y, values, color=_TEAL, height=0.58, alpha=0.9, zorder=3)

    max_value = max(values) if values else 0
    axis_max = max(max_value * 1.18, 1.0)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_width() + axis_max * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f} m3",
            va="center",
            **_text_kwargs(size=8),
        )

    ax.set_yticks(y)
    ax.set_yticklabels(names)
    _apply_tick_font(list(ax.get_yticklabels()), size=9)
    ax.invert_yaxis()
    xlabel = ax.set_xlabel("\u7d2f\u8ba1\u5f84\u6d41\u91cf\uff08m3\uff09")
    _apply_axis_title(xlabel, size=9)
    title = ax.set_title(_TITLE_RUNOFF_DEVICE, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    ax.xaxis.grid(True, color=_GRID, linestyle="--", linewidth=0.6, alpha=0.8)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    ax.set_xlim(0, axis_max)
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_water_quality_metrics(summary: dict[str, Any]) -> str | None:
    water = summary.get("water_quality", {})
    metric_pairs = [
        ("\u6c28\u6c2e", water.get("avg_nh3_n")),
        ("\u603b\u78f7", water.get("avg_tp")),
        ("\u9ad8\u731b\u9178\u76d0", water.get("avg_permanganate")),
        ("\u603b\u6c2e", water.get("avg_tn")),
    ]
    metrics = [(name, float(value)) for name, value in metric_pairs if value is not None]
    if len(metrics) < 2:
        return None

    names = [item[0] for item in metrics]
    values = [item[1] for item in metrics]

    fig, ax = _base_fig(9, 4)
    x = np.arange(len(names))
    bars = ax.bar(x, values, color=_PALETTE[: len(names)], width=0.62, alpha=0.9, zorder=3)
    max_value = max(values) if values else 1

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_value * 0.03,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            **_text_kwargs(size=8),
        )

    ax.set_xticks(x)
    ax.set_xticklabels(names)
    _apply_tick_font(list(ax.get_xticklabels()), size=9)
    ylabel = ax.set_ylabel("\u5e73\u5747\u503c\uff08\u6309\u5404\u81ea\u6307\u6807\u5355\u4f4d\uff09")
    _apply_axis_title(ylabel, size=9)
    title = ax.set_title(_TITLE_WATER_QUALITY, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    ax.set_xlim(-0.5, len(names) - 0.5)
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_insect_species(summary: dict[str, Any]) -> str | None:
    top = summary.get("insect", {}).get("top_species", [])
    if not top:
        return None

    top = top[:10]
    names = [item[0] for item in top]
    counts = [item[1] for item in top]
    total = sum(counts) or 1

    fig, ax = _base_fig(9, max(3.5, 0.5 * len(names) + 1.5))
    y = np.arange(len(names))
    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(names))]
    bars = ax.barh(y, counts, color=colors, height=0.6, alpha=0.88, edgecolor="white", linewidth=0.5, zorder=3)

    max_count = max(counts) if counts else 1
    for bar, count in zip(bars, counts):
        pct = count / total * 100
        ax.text(
            bar.get_width() + max_count * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{count} {_UNIT_ONLY} ({pct:.1f}%)",
            va="center",
            **_text_kwargs(size=8),
        )

    ax.set_yticks(y)
    ax.set_yticklabels(names)
    _apply_tick_font(list(ax.get_yticklabels()), size=9)
    ax.invert_yaxis()
    xlabel = ax.set_xlabel(_LABEL_CAPTURE)
    _apply_axis_title(xlabel, size=9)
    title = ax.set_title(_TITLE_INSECT_SPECIES, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    ax.xaxis.grid(True, color=_GRID, linestyle="--", linewidth=0.6, alpha=0.8)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max_count * 1.25)
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_spore_daily(summary: dict[str, Any]) -> str | None:
    daily = summary.get("spore", {}).get("daily", [])
    if len(daily) < 2:
        return None

    dates = [d["date"][5:] for d in daily]
    counts = [d["count"] for d in daily]
    if all(count == 0 for count in counts):
        return None

    fig, ax = _base_fig(9, 3.6)
    x = np.arange(len(dates))
    y = np.array(counts, dtype=float)

    ax.plot(
        x,
        y,
        color=_PURPLE,
        linewidth=2.2,
        marker="D",
        markersize=5,
        markerfacecolor="white",
        markeredgecolor=_PURPLE,
        markeredgewidth=1.5,
        label=_LEGEND_SPORE,
        zorder=3,
    )
    ax.fill_between(x, y, alpha=0.10, color=_PURPLE)

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    _apply_tick_font(list(ax.get_xticklabels()), size=8)
    ylabel = ax.set_ylabel(_LABEL_SPORE)
    _apply_axis_title(ylabel, size=9)
    title = ax.set_title(_TITLE_SPORE_DAILY, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    legend = ax.legend(prop=_get_chart_font(size=8), framealpha=0.7)
    for text in legend.get_texts():
        text.set_color(_TEXT)
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_history_core(summary: dict[str, Any]) -> str | None:
    history = summary.get("history_comparison", {}) or {}
    modules = history.get("modules", {}) or {}
    ordered_keys = ("insect", "spore", "rain", "runoff")

    labels: list[str] = []
    values: list[float] = []
    for key in ordered_keys:
        item = modules.get(key) or {}
        rate = item.get("change_rate")
        if rate is None:
            continue
        labels.append(item.get("label", key))
        values.append(float(rate))

    if not values:
        return None

    fig, ax = _base_fig(9, max(3.8, 0.6 * len(labels) + 1.2))
    y = np.arange(len(labels))
    colors = [_GREEN if value <= 0 else _ORANGE for value in values]
    bars = ax.barh(y, values, color=colors, height=0.58, alpha=0.92, zorder=3)

    max_abs = max(abs(value) for value in values) if values else 1.0
    axis_limit = max(max_abs * 1.25, 10.0)
    ax.axvline(0, color=_GRAY, linewidth=1.0, alpha=0.8)

    for bar, value in zip(bars, values):
        ax.text(
            value + (axis_limit * 0.03 if value >= 0 else -axis_limit * 0.03),
            bar.get_y() + bar.get_height() / 2,
            f"{value:+.1f}%",
            va="center",
            ha="left" if value >= 0 else "right",
            **_text_kwargs(size=8),
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    _apply_tick_font(list(ax.get_yticklabels()), size=9)
    ax.invert_yaxis()
    xlabel = ax.set_xlabel("较上一等长周期变化率（%）")
    _apply_axis_title(xlabel, size=9)
    title = ax.set_title(_TITLE_HISTORY_CORE, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    ax.xaxis.grid(True, color=_GRID, linestyle="--", linewidth=0.6, alpha=0.8)
    ax.yaxis.grid(False)
    ax.set_xlim(-axis_limit, axis_limit)
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_history_water_quality(summary: dict[str, Any]) -> str | None:
    history = summary.get("history_comparison", {}) or {}
    water = history.get("water_quality", {}) or {}
    metrics = water.get("metrics") or []
    if len(metrics) < 2:
        return None

    names = [item.get("label", "—") for item in metrics]
    current_values = [float(item.get("current_value")) for item in metrics if item.get("current_value") is not None and item.get("previous_value") is not None]
    previous_values = [float(item.get("previous_value")) for item in metrics if item.get("current_value") is not None and item.get("previous_value") is not None]
    filtered_names = [item.get("label", "—") for item in metrics if item.get("current_value") is not None and item.get("previous_value") is not None]
    if len(filtered_names) < 2:
        return None

    fig, ax = _base_fig(9, 4)
    x = np.arange(len(filtered_names))
    width = 0.34
    prev_bars = ax.bar(x - width / 2, previous_values, width=width, color=_GRAY, alpha=0.85, label="上一周期", zorder=3)
    curr_bars = ax.bar(x + width / 2, current_values, width=width, color=_BLUE, alpha=0.9, label="本期", zorder=3)

    max_value = max(current_values + previous_values) if current_values or previous_values else 1.0
    for bars in (prev_bars, curr_bars):
        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_value * 0.03,
                f"{bar.get_height():.2f}",
                ha="center",
                va="bottom",
                **_text_kwargs(size=8),
            )

    ax.set_xticks(x)
    ax.set_xticklabels(filtered_names)
    _apply_tick_font(list(ax.get_xticklabels()), size=9)
    ylabel = ax.set_ylabel("指标均值（mg/L）")
    _apply_axis_title(ylabel, size=9)
    title = ax.set_title(_TITLE_HISTORY_WATER, pad=10)
    _apply_axis_title(title, size=12, weight="bold")
    legend = ax.legend(prop=_get_chart_font(size=8), framealpha=0.75)
    for text in legend.get_texts():
        text.set_color(_TEXT)
    fig.tight_layout()
    return _fig_to_b64(fig)


def generate_all_charts(summary: dict[str, Any]) -> dict[str, str | None]:
    return {
        _KEY_RAIN_DAILY: chart_rainfall_daily(summary),
        _KEY_RUNOFF_DEVICE: chart_runoff_device(summary),
        _KEY_HISTORY_CORE: chart_history_core(summary),
        _KEY_WATER_QUALITY: chart_water_quality_metrics(summary),
        _KEY_HISTORY_WATER: chart_history_water_quality(summary),
        _KEY_INSECT_DAILY: chart_insect_daily(summary),
        _KEY_INSECT_SPECIES: chart_insect_species(summary),
        _KEY_SPORE_DAILY: chart_spore_daily(summary),
    }
