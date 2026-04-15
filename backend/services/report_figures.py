"""Shared figure ordering for report HTML, DOCX, and AI analysis prompts."""

from __future__ import annotations

from typing import Any

FigureManifestItem = dict[str, Any]

_FIGURE_PLAN: tuple[dict[str, str], ...] = (
    {
        "type": "chart",
        "section": "insect",
        "key": "虫情日捕获",
        "caption": "每日虫情捕获量",
        "html_id": "fig-insect-daily",
    },
    {
        "type": "chart",
        "section": "insect",
        "key": "虫种统计",
        "caption": "主要虫种捕获量对比（Top 10）",
        "html_id": "fig-insect-species",
    },
    {
        "type": "pests",
        "section": "insect",
    },
    {
        "type": "chart",
        "section": "spore",
        "key": "孢子趋势",
        "caption": "每日孢子捕获量趋势",
        "html_id": "fig-spore",
    },
    {
        "type": "disease",
        "section": "spore",
        "caption": "病害孢子扩散风险示意（AI生成配图）",
        "html_id": "fig-disease",
    },
)

_SCENE_PRIORITY: tuple[str, ...] = (
    "smart_devices",
    "forest_ecology",
    "weather",
    "rainfall",
    "soil",
    "runoff",
    "pollution",
)


def _ordered_pest_names(summary: dict[str, Any], pests: dict[str, str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    top_species = (summary.get("insect") or {}).get("top_species") or []
    for item in top_species:
        if not item:
            continue
        name = item[0]
        if name in pests and name not in seen:
            ordered.append(name)
            seen.add(name)
    for name in sorted(pests):
        if name not in seen:
            ordered.append(name)
    return ordered


def _append_figure(
    manifest: list[FigureManifestItem],
    *,
    section: str,
    caption: str,
    html_id: str,
    src: str,
    source: str,
) -> None:
    number = len(manifest) + 1
    manifest.append(
        {
            "number": number,
            "section": section,
            "caption": caption,
            "html_id": html_id,
            "src": src,
            "source": source,
            "tag": "Gemini" if source == "ai" else None,
        }
    )


def build_figure_manifest(
    summary: dict[str, Any],
    charts: dict[str, str] | None,
    ai_images: dict[str, Any] | None,
) -> list[FigureManifestItem]:
    """Build the exact top-to-bottom figure order used by all report outputs."""

    charts = charts or {}
    ai_images = ai_images or {}
    manifest: list[FigureManifestItem] = []
    pests: dict[str, str] = ai_images.get("pests") or {}

    for item in _FIGURE_PLAN:
        item_type = item["type"]
        if item_type == "chart":
            chart_b64 = charts.get(item["key"])
            if not chart_b64:
                continue
            _append_figure(
                manifest,
                section=item["section"],
                caption=item["caption"],
                html_id=item["html_id"],
                src=f"data:image/png;base64,{chart_b64}",
                source="chart",
            )
            continue

        if item_type == "scene":
            for key in _SCENE_PRIORITY:
                src = ai_images.get(key)
                if not src:
                    continue
                _append_figure(
                    manifest,
                    section=item["section"],
                    caption=item["caption"],
                    html_id=item["html_id"],
                    src=src,
                    source="ai",
                )
                break
            continue

        if item_type == "pests":
            for name in _ordered_pest_names(summary, pests):
                src = pests.get(name)
                if not src:
                    continue
                _append_figure(
                    manifest,
                    section=item["section"],
                    caption=f"{name}生态图鉴（AI生成配图）",
                    html_id=f"fig-pest-{len(manifest) + 1}",
                    src=src,
                    source="ai",
                )
            continue

        if item_type == "disease":
            src = ai_images.get("disease")
            if not src:
                continue
            _append_figure(
                manifest,
                section=item["section"],
                caption=item["caption"],
                html_id=item["html_id"],
                src=src,
                source="ai",
            )

    return manifest


def build_figure_reference_rules(manifest: list[FigureManifestItem]) -> str:
    """Return prompt instructions that exactly match the current figure manifest."""

    if not manifest:
        return (
            "【图表引用规范】\n"
            "本次报告未生成任何图表或配图。不要编造图号，也不要输出“见图X”“如图X所示”之类的引用。"
        )

    lines = [
        "【图表引用规范】",
        "报告配图已按以下顺序排列，请在正文对应位置将图号自然嵌入句子，不要单独成行：",
    ]
    for item in manifest:
        lines.append(f"  图{item['number']} — {item['caption']}")
    lines.extend(
        [
            "注意：",
            "1. 只能引用上面真实存在的图号。",
            "2. 图号必须严格按从小到大的顺序出现，绝对禁止跳号、回跳或先写图8再写图2。",
            "3. 每张图最多引用一次，不要重复引用。",
            "4. 引用方式写在句子里，例如“……（见图3）……”或“……如图3所示……”。",
        ]
    )
    return "\n".join(lines)


def build_figure_map(
    manifest: list[FigureManifestItem],
) -> dict[int, tuple[str, str]]:
    """Return DOCX insertion lookup keyed by figure number."""

    return {
        item["number"]: (item["src"], f"图{item['number']}  {item['caption']}")
        for item in manifest
    }
