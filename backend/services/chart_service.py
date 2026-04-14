"""Chart generation service — produces base64-encoded PNG charts for HTML reports.

Each public function accepts the summary dict (as built by ReportService) and returns
a base64-encoded PNG string suitable for embedding in an <img> tag, or None when there
is insufficient data to draw a meaningful chart.
"""

from __future__ import annotations

import base64
import io
from typing import Any

# Configure matplotlib before any pyplot import so it uses a non-interactive backend
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
})

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ---------------------------------------------------------------------------
# Colour palette (consistent across all charts)
# ---------------------------------------------------------------------------

_BLUE   = "#2E86C1"
_GREEN  = "#28B463"
_ORANGE = "#E67E22"
_RED    = "#C0392B"
_PURPLE = "#8E44AD"
_TEAL   = "#17A589"
_GRAY   = "#7F8C8D"

_PALETTE = [_BLUE, _GREEN, _ORANGE, _RED, _PURPLE, _TEAL, _GRAY,
            "#F1C40F", "#1ABC9C", "#D35400"]

_BG      = "#FAFAFA"
_GRID    = "#DDDDDD"
_TEXT    = "#2C3E50"
_SUBTEXT = "#7F8C8D"


def _fig_to_b64(fig: plt.Figure) -> str:
    """Render *fig* to PNG bytes and return as base64 string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
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


# ---------------------------------------------------------------------------
# Chart 1: Temperature trend (line chart)
# ---------------------------------------------------------------------------

def chart_temp_trend(summary: dict[str, Any]) -> str | None:
    daily = summary.get("weather", {}).get("daily", [])
    if len(daily) < 2:
        return None

    dates = [d["date"][5:] for d in daily]   # MM-DD
    temps = [d["avg_temp"] for d in daily]

    # Fill None with linear interpolation
    valid = [(i, t) for i, t in enumerate(temps) if t is not None]
    if len(valid) < 2:
        return None

    fig, ax = _base_fig(9, 3.8)

    x = np.arange(len(dates))
    y = np.array([t if t is not None else float("nan") for t in temps])

    ax.plot(x, y, color=_ORANGE, linewidth=2.2, marker="o", markersize=5,
            markerfacecolor="white", markeredgecolor=_ORANGE, markeredgewidth=1.5,
            zorder=3, label="日均气温")
    ax.fill_between(x, y, alpha=0.12, color=_ORANGE)

    # Annotate max/min
    valid_y = [(i, v) for i, v in enumerate(y) if not np.isnan(v)]
    if valid_y:
        max_i, max_v = max(valid_y, key=lambda t: t[1])
        min_i, min_v = min(valid_y, key=lambda t: t[1])
        ax.annotate(f"{max_v:.1f}°C", (max_i, max_v),
                    textcoords="offset points", xytext=(0, 8),
                    fontsize=8, color=_RED, fontweight="bold", ha="center")
        ax.annotate(f"{min_v:.1f}°C", (min_i, min_v),
                    textcoords="offset points", xytext=(0, -14),
                    fontsize=8, color=_BLUE, fontweight="bold", ha="center")

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("气温 (°C)", fontsize=9, color=_TEXT)
    ax.set_title("日均气温变化趋势", fontsize=12, fontweight="bold", color=_TEXT, pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Chart 2: Daily rainfall (bar chart)
# ---------------------------------------------------------------------------

def chart_rainfall(summary: dict[str, Any]) -> str | None:
    daily = summary.get("weather", {}).get("daily", [])
    if not daily:
        return None

    dates = [d["date"][5:] for d in daily]
    rain = [d.get("total_rainfall") or 0 for d in daily]

    if all(r == 0 for r in rain):
        return None

    fig, ax = _base_fig(9, 3.6)
    x = np.arange(len(dates))
    bars = ax.bar(x, rain, color=_BLUE, width=0.6, alpha=0.85, zorder=3)

    # Colour heavy-rain bars differently
    for bar, r in zip(bars, rain):
        if r >= 25:
            bar.set_color(_RED)
        elif r >= 10:
            bar.set_color(_ORANGE)

    # Value labels on bars > 0
    for bar, r in zip(bars, rain):
        if r > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                    f"{r:.1f}", ha="center", va="bottom", fontsize=7.5, color=_TEXT)

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("降雨量 (mm)", fontsize=9, color=_TEXT)
    ax.set_title("每日降雨量", fontsize=12, fontweight="bold", color=_TEXT, pad=10)

    # Legend patches
    patches = [
        mpatches.Patch(color=_BLUE, label="小雨 (<10 mm)"),
        mpatches.Patch(color=_ORANGE, label="中雨 (10-25 mm)"),
        mpatches.Patch(color=_RED, label="大雨 (≥25 mm)"),
    ]
    ax.legend(handles=patches, fontsize=8, framealpha=0.7)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Chart 3: Soil moisture multi-depth line chart
# ---------------------------------------------------------------------------

def chart_soil_moisture(summary: dict[str, Any]) -> str | None:
    daily = summary.get("soil", {}).get("daily", [])
    if len(daily) < 2:
        return None

    dates = [d["date"][5:] for d in daily]
    m10 = [d.get("avg_moisture_10cm") for d in daily]
    m20 = [d.get("avg_moisture_20cm") for d in daily]
    m40 = [d.get("avg_moisture_40cm") for d in daily]

    has_data = any(v is not None for series in (m10, m20, m40) for v in series)
    if not has_data:
        return None

    fig, ax = _base_fig(9, 3.8)
    x = np.arange(len(dates))

    def _plot(series, color, label):
        y = np.array([v if v is not None else float("nan") for v in series])
        ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=4,
                markerfacecolor="white", markeredgecolor=color,
                label=label, zorder=3)

    _plot(m10, _BLUE,   "10 cm")
    _plot(m20, _GREEN,  "20 cm")
    _plot(m40, _ORANGE, "40 cm")

    # Optimal moisture reference band
    ax.axhspan(55, 75, alpha=0.08, color=_GREEN, label="适宜墒情区间 (55–75%)")

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("土壤含水量 (%)", fontsize=9, color=_TEXT)
    ax.set_title("各层次土壤墒情变化", fontsize=12, fontweight="bold", color=_TEXT, pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Chart 4: Insect daily capture bar chart
# ---------------------------------------------------------------------------

def chart_insect_daily(summary: dict[str, Any]) -> str | None:
    daily = summary.get("insect", {}).get("daily", [])
    if not daily:
        return None

    dates = [d["date"][5:] for d in daily]
    counts = [d["count"] for d in daily]

    if all(c == 0 for c in counts):
        return None

    fig, ax = _base_fig(9, 3.6)
    x = np.arange(len(dates))

    # Gradient colour based on capture level
    max_c = max(counts) if counts else 1
    colors = [plt.cm.YlOrRd(0.25 + 0.65 * (c / max_c)) for c in counts]

    bars = ax.bar(x, counts, color=colors, width=0.6, zorder=3, edgecolor="white",
                  linewidth=0.5)

    for bar, c in zip(bars, counts):
        if c > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_c * 0.01,
                    str(c), ha="center", va="bottom", fontsize=7.5, color=_TEXT)

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("捕获数量 (只)", fontsize=9, color=_TEXT)
    ax.set_title("每日虫情捕获量", fontsize=12, fontweight="bold", color=_TEXT, pad=10)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Chart 5: Insect species horizontal bar chart (top 10)
# ---------------------------------------------------------------------------

def chart_insect_species(summary: dict[str, Any]) -> str | None:
    top = summary.get("insect", {}).get("top_species", [])
    if not top:
        return None

    # Trim to top 10
    top = top[:10]
    names = [item[0] for item in top]
    counts = [item[1] for item in top]
    total = sum(counts) or 1

    fig, ax = _base_fig(9, max(3.5, 0.5 * len(names) + 1.5))
    y = np.arange(len(names))

    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(names))]
    bars = ax.barh(y, counts, color=colors, height=0.6, alpha=0.88,
                   edgecolor="white", linewidth=0.5, zorder=3)

    for bar, c in zip(bars, counts):
        pct = c / total * 100
        ax.text(bar.get_width() + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{c} 只 ({pct:.1f}%)", va="center", fontsize=8, color=_TEXT)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("捕获数量 (只)", fontsize=9, color=_TEXT)
    ax.set_title("主要虫种捕获统计（Top 10）", fontsize=12, fontweight="bold", color=_TEXT, pad=10)
    ax.xaxis.grid(True, color=_GRID, linestyle="--", linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    # Remove y-grid (horizontal bars already separated)
    ax.yaxis.grid(False)
    max_x = max(counts) if counts else 1
    ax.set_xlim(0, max_x * 1.25)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Chart 6: Spore daily line chart
# ---------------------------------------------------------------------------

def chart_spore_daily(summary: dict[str, Any]) -> str | None:
    daily = summary.get("spore", {}).get("daily", [])
    if len(daily) < 2:
        return None

    dates = [d["date"][5:] for d in daily]
    counts = [d["count"] for d in daily]

    if all(c == 0 for c in counts):
        return None

    fig, ax = _base_fig(9, 3.6)
    x = np.arange(len(dates))
    y = np.array(counts, dtype=float)

    ax.plot(x, y, color=_PURPLE, linewidth=2.2, marker="D", markersize=5,
            markerfacecolor="white", markeredgecolor=_PURPLE, markeredgewidth=1.5,
            label="每日孢子数", zorder=3)
    ax.fill_between(x, y, alpha=0.10, color=_PURPLE)

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("孢子数量 (个)", fontsize=9, color=_TEXT)
    ax.set_title("每日孢子捕获量趋势", fontsize=12, fontweight="bold", color=_TEXT, pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Convenience: generate all charts at once
# ---------------------------------------------------------------------------

def generate_all_charts(summary: dict[str, Any]) -> dict[str, str | None]:
    """Generate all report charts and return a dict keyed by chart name."""
    return {
        "气温趋势":   chart_temp_trend(summary),
        "降雨量":     chart_rainfall(summary),
        "土壤墒情":   chart_soil_moisture(summary),
        "虫情日捕获": chart_insect_daily(summary),
        "虫种统计":   chart_insect_species(summary),
        "孢子趋势":   chart_spore_daily(summary),
    }
