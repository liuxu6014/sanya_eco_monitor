"""Shared figure ordering for report HTML, DOCX, and AI analysis prompts."""

from __future__ import annotations

import re
from typing import Any

FigureManifestItem = dict[str, Any]

_FIGURE_PLAN: tuple[dict[str, str], ...] = (
    {
        "type": "chart",
        "section": "hydrology",
        "key": "雨量日统计",
        "caption": "监测期每日降雨量",
        "html_id": "fig-rain-daily",
    },
    {
        "type": "chart",
        "section": "hydrology",
        "key": "径流站点对比",
        "caption": "各监测点累计径流量对比",
        "html_id": "fig-runoff-device",
    },
    {
        "type": "chart",
        "section": "hydrology",
        "key": "核心指标历史对比",
        "caption": "本期与上一等长周期核心监测指标变化率",
        "html_id": "fig-history-core",
    },
    {
        "type": "chart",
        "section": "water_quality",
        "key": "水质指标均值",
        "caption": "水质关键指标平均值",
        "html_id": "fig-water-quality",
    },
    {
        "type": "chart",
        "section": "water_quality",
        "key": "水质历史对比",
        "caption": "水质关键指标本期与上一周期均值对比",
        "html_id": "fig-history-water",
    },
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
        "type": "capture",
        "section": "insect",
        "key": "insect",
        "caption": "虫情监测设备最近实拍图",
        "html_id": "fig-insect-capture",
    },
    {
        "type": "pests",
        "section": "insect",
    },
)

_SCENE_PRIORITY: tuple[str, ...] = (
    "smart_devices",
    "forest_ecology",
    "rainfall",
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


def _latest_capture_image(summary: dict[str, Any], section: str) -> str | None:
    capture_images = (summary.get(section) or {}).get("capture_images") or []
    if not capture_images:
        return None
    return capture_images[-1].get("url")


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

        if item_type == "capture":
            src = _latest_capture_image(summary, item["key"])
            if not src:
                continue
            _append_figure(
                manifest,
                section=item["section"],
                caption=item["caption"],
                html_id=item["html_id"],
                src=src,
                source="capture",
            )
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


_FIGURE_REF_RE = re.compile(r"图(\d+)")
_FIGURE_REFERENCE_PHRASE_RE = re.compile(
    r"[（(]\s*(?:见|参见|如)?图\d+(?:\s*[、,，和及至~\-—–]\s*图?\d+)*\s*(?:所示)?\s*[）)]"
    r"|(?:见|参见|如)?图\d+(?:\s*[、,，和及至~\-—–]\s*图?\d+)*\s*(?:所示)?"
)

_SECTION_REFERENCE_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "insect",
        (
            "森林生物多样性",
            "生态健康",
            "虫情",
            "病虫",
            "害虫",
        ),
    ),
    (
        "hydrology",
        (
            "水文调节",
            "水土流失",
            "水文",
            "径流",
            "降雨",
            "雨量",
        ),
    ),
    (
        "water_quality",
        (
            "水环境质量",
            "生态容量",
            "水质",
            "面源",
            "污染负荷",
        ),
    ),
)


def _format_figure_reference_sentence(numbers: list[int]) -> str:
    refs = "、".join(f"图{number}" for number in numbers)
    return f"本章相关图表见{refs}。"


def strip_figure_references(text: str) -> str:
    """Remove AI-supplied figure numbers before deterministic renumbering."""

    if not text:
        return text

    cleaned = _FIGURE_REFERENCE_PHRASE_RE.sub("", text)
    cleaned = re.sub(r"[（(]\s*[）)]", "", cleaned)
    cleaned = re.sub(r"([。；;，,、])\1+", r"\1", cleaned)
    cleaned = re.sub(r"^[，,、；;]\s*", "", cleaned, flags=re.MULTILINE)
    return cleaned


def finalize_figure_references(
    text: str,
    manifest: list[FigureManifestItem],
) -> tuple[str, list[FigureManifestItem]]:
    """Return AI text and manifest with one authoritative figure order."""

    cleaned_text = strip_figure_references(text or "")
    ordered_manifest = order_manifest_for_text(manifest, cleaned_text)
    return augment_text_with_figure_references(cleaned_text, ordered_manifest), ordered_manifest


def _is_heading_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("#") or stripped.startswith("**")


def _section_order_for_text(text: str) -> list[str]:
    ordered_sections: list[str] = []
    for line in (text or "").splitlines():
        if not _is_heading_line(line):
            continue
        for section, keywords in _SECTION_REFERENCE_TARGETS:
            if section in ordered_sections:
                continue
            if any(keyword in line for keyword in keywords):
                ordered_sections.append(section)
                break
    for section, _keywords in _SECTION_REFERENCE_TARGETS:
        if section not in ordered_sections:
            ordered_sections.append(section)
    return ordered_sections


def order_manifest_for_text(
    manifest: list[FigureManifestItem],
    text: str = "",
) -> list[FigureManifestItem]:
    """Return a copy renumbered in the order figures should appear in body text."""

    if not manifest:
        return []

    section_order = _section_order_for_text(text)
    section_rank = {section: index for index, section in enumerate(section_order)}
    original_index = {id(item): index for index, item in enumerate(manifest)}
    ordered = sorted(
        manifest,
        key=lambda item: (
            section_rank.get(str(item.get("section")), len(section_rank)),
            original_index[id(item)],
        ),
    )
    renumbered: list[FigureManifestItem] = []
    for number, item in enumerate(ordered, 1):
        copied = dict(item)
        copied["number"] = number
        if str(copied.get("html_id", "")).startswith("fig-pest-"):
            copied["html_id"] = f"fig-pest-{number}"
        renumbered.append(copied)
    return renumbered


def augment_text_with_figure_references(
    text: str,
    manifest: list[FigureManifestItem],
) -> str:
    """Add missing in-body 图N references so report figures have deterministic anchors.

    AI output sometimes omits requested figure references. HTML can then show charts
    disconnected from the article, and DOCX has no reliable inline insertion point.
    This helper adds one concise reference sentence after the matching chapter
    heading, without duplicating figure numbers that already exist in the body.
    """

    if not text or not text.strip() or not manifest:
        return text

    referenced_numbers = {
        int(match.group(1))
        for match in _FIGURE_REF_RE.finditer(text)
        if match.group(1).isdigit()
    }
    section_numbers: dict[str, list[int]] = {}
    for item in manifest:
        number = item.get("number")
        section = item.get("section")
        if not isinstance(number, int) or not section or number in referenced_numbers:
            continue
        section_numbers.setdefault(str(section), []).append(number)

    if not section_numbers:
        return text

    lines = text.splitlines()
    inserted_sections: set[str] = set()
    output: list[str] = []
    active_section: str | None = None

    for line in lines:
        if _is_heading_line(line):
            active_section = None
            for section, keywords in _SECTION_REFERENCE_TARGETS:
                numbers = section_numbers.get(section)
                if not numbers or section in inserted_sections:
                    continue
                if any(keyword in line for keyword in keywords):
                    active_section = section
                    break
            output.append(line)
            continue

        if active_section and line.strip():
            numbers = section_numbers.get(active_section)
            if numbers and active_section not in inserted_sections:
                line = f"{line.rstrip()}（{_format_figure_reference_sentence(numbers)}）"
                inserted_sections.add(active_section)
                active_section = None
        output.append(line)

    for line_index, line in enumerate(output):
        for section, keywords in _SECTION_REFERENCE_TARGETS:
            numbers = section_numbers.get(section)
            if not numbers or section in inserted_sections:
                continue
            if any(keyword in line for keyword in keywords):
                output.insert(line_index + 1, _format_figure_reference_sentence(numbers))
                inserted_sections.add(section)
                break

    for section, _keywords in _SECTION_REFERENCE_TARGETS:
        numbers = section_numbers.get(section)
        if numbers and section not in inserted_sections:
            output.append(_format_figure_reference_sentence(numbers))
            inserted_sections.add(section)

    return "\n".join(output)


def build_figure_map(
    manifest: list[FigureManifestItem],
) -> dict[int, tuple[str, str]]:
    """Return DOCX insertion lookup keyed by figure number."""

    return {
        item["number"]: (item["src"], f"图{item['number']}  {item['caption']}")
        for item in manifest
    }
