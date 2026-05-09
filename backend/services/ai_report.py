"""AI智能分析报告服务 — DeepSeek API"""

import logging
import re
from typing import Any

import httpx
from config import settings
from services.report_figures import build_figure_reference_rules

logger = logging.getLogger(__name__)
_MIN_ANALYSIS_CHARS = 4500
_FORBIDDEN_STANDALONE_HEADINGS = (
    "《指南》指标适配摘要",
    "本期已确认业务口径",
)
_REQUIRED_CHAPTER_HEADINGS = (
    "## 一、监测期综合概况与评估背景",
    "## 二、森林生物多样性与生态健康指标分析",
    "## 三、水文调节功能与水土流失监测分析",
    "## 四、区域水环境质量与生态容量评价",
    "## 五、近自然化改造生态效益综合判析",
    "## 六、森林抚育与生态系统精准修复建议",
    "## 七、长期生态趋势监测预测与展望",
)

ANALYSIS_PROMPT_TEMPLATE = """你是一位顶尖的生态修复与效益评估专家，服务于“三亚市天涯区橡胶林近自然化改造和农田提升监测平台”。请根据以下监测数据摘要，撰写一份详尽的《橡胶林近自然化改造生态效益评估报告》。

【报告要求】
- 总字数：要求极其详尽，务必达到 5000 字 到 8000 字之间（各章节必须做深度扩展，结合生态学理论进行专业判析）
- 报告性质：生态效益评估，侧重于近自然化改造对生物多样性、水资源调节、环境质量的提升作用
- 语言专业、严谨，论述必须充分，杜绝空洞的套话，应以量化数据支撑定性结论
- 行文口吻必须面向项目汇报和管理决策场景，表达自然、正式、克制，优先给出判断和结论，再说明数据依据
- 适合林业专家、生态资源管理部门及技术人员阅读
- 监测数据只要在摘要中出现，就必须纳入分析，禁止只分析其中一部分；孢子数据仅作为图片附录保留，不进入正文分析
- 必须开展“多源联合分析”，把虫情、降雨、径流、水质放在同一生态过程链条中综合讨论
- 必须开展“历史对比分析”，默认将本期与上一等长周期进行同口径比较，明确说明上升、下降、持平及其管理含义
- 对于数值为 0 的指标，要视为“有监测且监测值为 0”，禁止误写为“无数据”
- 对于监测记录数大于 0 的模块，必须至少给出 2 个以上明确的数据结论或判断
- 必须加入“监测体系科学性说明”，明确监测点布设、监测对象和数据完整性基础
- 必须加入“《指南》指标适配结果”与“适应性管理闭环说明”，但这些内容必须直接融合进七章正文对应位置，不能单独另起摘要块或附录块
- 严禁在正文中出现任何原始数据库字段名、程序变量名或接口键名，必须全部改写为中文业务表述
- 避免写成数据库导出说明、公式注释或括号堆砌的技术表达，不要机械重复“约为”“以某某为基准”等生硬口径说明，应改写为自然、完整的报告语言

【报告结构与撰写指令】
你必须严格按照以下7个章节输出。
- 每一章使用"## 一、章节名"格式
- 每章内部小节使用"**1.1 小节名**"格式（加粗，不用###），小节序号与章序号对应
- 每章至少2个小节
- 七章标题必须与下列标题完全一致，不得增删改，不得在七章之前插入任何额外总标题、摘要标题或说明标题
- 严禁输出“《指南》指标适配摘要”“监测体系科学性说明”“本期已确认业务口径”等独立一级或二级标题
- “监测体系科学性说明”和“基准期口径”并入第一章；“水土流失监测型估算”和“气象支撑信息”并入第三章；“农业面源污染削减率”和相关口径说明并入第四章；“虫情风险链条”并入第二章、第六章和第七章
- 绝对不允许将括号内的指令提示语打印到正文中

## 一、监测期综合概况与评估背景
（**1.1 监测周期与数据完整性评估**：说明统计周期、各类设备运行状态、数据采集完整率；**1.2 近自然化改造项目背景与监测意义**：阐述天涯区橡胶林近自然化改造的目标，说明本期监测对评估森林结构优化、生态功能恢复的关键意义。）

## 二、森林生物多样性与生态健康指标分析
（**2.1 虫情监测与昆虫种群群落稳定性评估**：从核心虫情数据分析昆虫多样性，评估生态位占用情况及其作为森林健康指示器的意义；**2.2 生物多样性恢复与生态链稳定性评估**：结合虫种结构、优势虫种与捕获趋势，研判林分结构调整对生境异质性和生态稳定性的影响。）

## 三、水文调节功能与水土流失监测分析
（**3.1 降雨分布与林冠层截留作用评价**：结合降雨监测，分析橡胶林对降水的缓冲作用；**3.2 地表径流监测与水源涵养能力分析**：通过径流量、流速及产沙情况（地表径流数据），评估近自然化改造后橡胶林在拦截雨水、减少水土流失方面的效益。）

## 四、区域水环境质量与生态容量评价
（**4.1 汇水区域水质指标演变分析**：详细分析氨氮、总磷、高猛酸盐、总氮等指标，评估林地改善对水环境的净化贡献；**4.2 农田提升区面源污染拦截效益**：研判林地改造对下游农田提升区生态缓冲带的作用。）

## 五、近自然化改造生态效益综合判析
（**5.1 生态系统稳定性提升评价**：综合分析多源数据，判断橡胶林从人工单一林向近自然复层林转变过程中的生态稳定性；**5.2 生效服务功能价值化初判**：从固碳、涵养水源、生物多样性保护等维度给予定性及初步定量评价。）

## 六、森林抚育与生态系统精准修复建议
（**6.1 林分结构优化与植植补植策略**：针对监测出的生态薄弱环节提出技术优化建议；**6.2 生物防治与天敌恢复技术方案**：基于虫情数据，提出利用本土生物多样性进行病虫害生态调控的方案。）

## 七、长期生态趋势监测预测与展望
（**7.1 演替趋势与未来风险预警**：预测生态系统演替方向；**7.2 评估结论与后期监测重点建议**。）

监测数据摘要：
{data_summary}

【全量分析强制要求】
1. 你必须逐项检查并使用以下模块的全部可用数据：虫情、降雨、地表径流、水质。孢子数据不得写入正文分析，只能由系统在报告最后作为图片附录展示。
2. 只要某模块监测记录数大于 0，就必须在正文中明确分析该模块，不能省略。
3. 必须把不同模块之间的关系说清楚，例如：降雨与径流、水文与水质、虫情与生物多样性。
4. 对地表径流必须结合各监测点分别分析，不能只写总体平均值。
5. 如果某模块监测值较低或为 0，应解释其生态含义、监测背景和可能原因，而不是直接跳过。
6. 结论必须来自摘要中的真实数据，严禁编造不存在的设备、指标、峰值或趋势。
7. 如果摘要中提供了 guideline_metrics 或 weather_support，必须纳入正文，重点说明水土流失监测型估算、面源污染削减率、虫情风险链条和气象支撑信息。
8. 如果摘要中提供了历史对比分析，必须在各相关章节明确引用上一等长周期的对比结果，至少交代“本期值、上一周期值、变化方向、变化幅度和管理判断”。

【极其重要的数据对齐与格式要求】
1. 直接从"## 一、监测期综合概况与评估背景"开头输出，禁止任何前言、总结性套话或额外摘要块。
2. 内部的小节标题必须使用 **1.1 小节名** 这种加粗格式，禁止使用###。
3. 文中引用的图号（见图N）必须严格按照监测数据摘要后的规则嵌入，不可随意捏造图号。
4. 严格控制空行：章节标题、小节标题与正文之间禁止出现多余的空行，确保报告排版紧凑专业。

{figure_reference_rules}"""


async def generate_ai_analysis(
    summary_dict: dict,
    figure_manifest: list[dict[str, Any]] | None = None,
) -> str:
    """Call LLM API to generate intelligent agricultural analysis."""
    if not settings.LLM_API_KEY:
        return (
            "【AI智能分析 — 未配置API Key】\n\n"
            "请在 backend/.env 中配置 LLM_API_KEY 以启用智能分析功能。"
        )

    data_summary = format_summary_for_prompt(summary_dict)
    figure_reference_rules = build_figure_reference_rules(figure_manifest or [])
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        data_summary=data_summary,
        figure_reference_rules=figure_reference_rules,
    )

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            content = await _request_analysis(
                client,
                [{"role": "user", "content": prompt}],
            )
            if _analysis_char_count(content) < _MIN_ANALYSIS_CHARS:
                expanded = await _request_analysis(
                    client,
                    [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": content},
                        {
                            "role": "user",
                            "content": (
                                "请在不改变现有七章结构、图号引用规则和数据口径的前提下，"
                                "继续扩写并补足正文细节，使全文达到 5000-8000 字。"
                                "不要省略已有内容，也不要改写成摘要，更不要另起《指南》指标适配摘要之类的独立板块。"
                            ),
                        },
                    ],
                )
                if _analysis_char_count(expanded) > _analysis_char_count(content):
                    content = expanded
            if _needs_structure_rewrite(content):
                rewritten = await _request_analysis(
                    client,
                    [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": content},
                        {
                            "role": "user",
                            "content": (
                                "请严格重写为七章正文结构。不要输出《指南》指标适配摘要、监测体系科学性说明、"
                                "本期已确认业务口径等独立标题；必须把这些信息分别并入第一、第三、第四、"
                                "第六和第七章对应段落，并保留 **1.1 小节名** 这种二级小节格式。"
                            ),
                        },
                    ],
                )
                if rewritten:
                    content = rewritten
            return content
    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP error: {e.response.status_code} {e.response.text}")
        return f"【AI分析服务暂时不可用】HTTP {e.response.status_code}，请稍后重试。"
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return f"【AI分析服务异常】{str(e)}"


def _analysis_char_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def _needs_structure_rewrite(text: str) -> bool:
    if not text:
        return True
    if any(token in text for token in _FORBIDDEN_STANDALONE_HEADINGS):
        return True
    return any(title not in text for title in _REQUIRED_CHAPTER_HEADINGS)


async def _request_analysis(client: httpx.AsyncClient, messages: list[dict[str, str]]) -> str:
    resp = await client.post(
        f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.LLM_MODEL,
            "messages": messages,
            "max_tokens": 8192,
            "temperature": 0.7,
        },
    )
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]


def _prompt_value(value: Any, unit: str = "") -> str:
    if value is None or value == "":
        return "—"
    return f"{value}{unit}"


def _append_fact(lines: list[str], label: str, value: Any, unit: str = "") -> None:
    lines.append(f"  - {label}：{_prompt_value(value, unit)}")


def format_summary_for_prompt(summary: dict) -> str:
    """Format summary dict into reader-facing Chinese facts for the prompt."""
    lines: list[str] = []
    p = summary.get("period", {})
    lines.append(f"统计周期：{p.get('start', '—')} 至 {p.get('end', '—')}")

    ins = summary.get("insect", {})
    top = ins.get("top_species", [])
    top_str = "、".join(f"{n}（{c}只）" for n, c in top[:10]) if top else "无"
    lines.append("虫情测报：")
    _append_fact(lines, "监测记录数", ins.get("records_count", 0), " 条")
    _append_fact(lines, "周期内有效捕获昆虫", ins.get("total_count", 0), " 只")
    _append_fact(lines, "主要虫种", top_str)
    _append_fact(lines, "实拍图片数量", len(ins.get("capture_images") or []), " 张")
    if ins.get("daily"):
        lines.append("  - 虫情日尺度序列：")
        for item in ins["daily"]:
            lines.append(f"    * {item.get('date', '—')}：捕获 {item.get('count', 0)} 只")

    wq = summary.get("water_quality", {})
    lines.append("水质监测：")
    _append_fact(lines, "监测记录数", wq.get("records_count", 0), " 条")
    _append_fact(lines, "平均氨氮", wq.get("avg_nh3_n"), " mg/L")
    _append_fact(lines, "平均总磷", wq.get("avg_tp"), " mg/L")
    _append_fact(lines, "平均高锰酸盐指数", wq.get("avg_permanganate"), " mg/L")
    _append_fact(lines, "平均总氮", wq.get("avg_tn"), " mg/L")

    ro = summary.get("runoff", {})
    lines.append("地表径流监测：")
    _append_fact(lines, "监测记录数", ro.get("records_count", 0), " 条")
    _append_fact(lines, "监测点数量", ro.get("device_count", 0), " 个")
    _append_fact(lines, "总体平均流量", ro.get("avg_flow_rate"))
    _append_fact(lines, "总体最大流量", ro.get("max_flow_rate"))
    _append_fact(lines, "总体平均水位", ro.get("avg_water_level"))
    if ro.get("by_device"):
        lines.append("  - 各径流监测点明细：")
        for code, item in ro["by_device"].items():
            lines.append(
                f"    * {code} / {item.get('name', code)}："
                f"监测记录数 {_prompt_value(item.get('records_count', 0), ' 条')}，"
                f"平均流速 {_prompt_value(item.get('avg_flow_speed'))}，"
                f"最大流速 {_prompt_value(item.get('max_flow_speed'))}，"
                f"平均流量 {_prompt_value(item.get('avg_flow_rate'))}，"
                f"最大流量 {_prompt_value(item.get('max_flow_rate'))}，"
                f"最新累计流量 {_prompt_value(item.get('total_flow_latest'))}，"
                f"平均水位 {_prompt_value(item.get('avg_water_level'))}，"
                f"最高水位 {_prompt_value(item.get('max_water_level'))}，"
                f"平均含沙量 {_prompt_value(item.get('avg_sand_content'))}，"
                f"平均液位压力 {_prompt_value(item.get('avg_liquid_pressure'))}，"
                f"累计径流量 {_prompt_value(item.get('total_runoff'))}，"
                f"累计降雨量 {_prompt_value(item.get('total_rainfall'))}"
            )

    rn = summary.get("rain", {})
    lines.append("雨量监测：")
    _append_fact(lines, "监测记录数", rn.get("records_count", 0), " 条")
    _append_fact(lines, "累计降雨量（雨量计口径）", rn.get("total_rainfall", 0), " mm")

    weather = summary.get("weather_support", {}) or {}
    if weather.get("enabled") and weather.get("status") == "ok":
        current = weather.get("current", {}) or {}
        history_summary = weather.get("history_summary", {}) or {}
        history_range = weather.get("history_range", {}) or {}
        lines.append("气象补充数据：")
        _append_fact(lines, "数据来源", weather.get("source", "QWeather"))
        _append_fact(lines, "当前天气", current.get("text"))
        _append_fact(lines, "当前温度", current.get("temp"), " ℃")
        _append_fact(lines, "当前湿度", current.get("humidity"), " %")
        _append_fact(lines, "当前风速", current.get("wind_speed"), " km/h")
        _append_fact(lines, "历史区间", f"{history_range.get('start', '—')} 至 {history_range.get('end', '—')}")
        _append_fact(lines, "最近7天累计降水", history_summary.get("total_precip"), " mm")
        _append_fact(lines, "最近7天平均气温", history_summary.get("avg_temp_mean"), " ℃")
        _append_fact(lines, "最近7天平均湿度", history_summary.get("avg_humidity"), " %")
        _append_fact(lines, "最近7天平均风速", history_summary.get("avg_wind_speed"), " km/h")

    guideline = summary.get("guideline_metrics", {}) or {}
    runoff_guideline = guideline.get("runoff_erosion", {}) or {}
    water_guideline = guideline.get("water_quality", {}) or {}
    pest_guideline = guideline.get("pest_management", {}) or {}
    methodology = guideline.get("methodology", {}) or {}
    water_source_support = guideline.get("water_source_support", {}) or {}
    implementation_matrix = guideline.get("implementation_matrix", {}) or {}
    warning_analysis = guideline.get("warning_analysis", {}) or {}

    if methodology:
        lines.append("需融入第一章的监测体系与基准期口径：")
        _append_fact(lines, "监测体系说明", methodology.get("monitoring_statement"))
        _append_fact(lines, "基准期说明", methodology.get("baseline_statement"))

    if runoff_guideline.get("available"):
        reference_station = runoff_guideline.get("reference_station") or {}
        lines.append("需融入第三章的水土流失监测型估算：")
        _append_fact(lines, "参照监测点", f"{reference_station.get('name', '—')} ({reference_station.get('device_code', '—')})")
        _append_fact(lines, "参照侵蚀代理指标", reference_station.get("erosion_proxy"))
        _append_fact(lines, "其他监测点平均侵蚀代理指标", runoff_guideline.get("plantation_avg_proxy"))
        _append_fact(lines, "估算减蚀率", runoff_guideline.get("estimated_reduction_rate"), " %")
        _append_fact(lines, "说明", runoff_guideline.get("note"))

    if water_guideline.get("available"):
        lines.append("需融入第四章的农业面源污染削减率：")
        _append_fact(
            lines,
            "基准期",
            f"{water_guideline.get('baseline_period', {}).get('start', '—')} 至 "
            f"{water_guideline.get('baseline_period', {}).get('end', '—')}",
        )
        _append_fact(lines, "基准期记录数", water_guideline.get("baseline_period", {}).get("records_count", 0), " 条")
        _append_fact(lines, "近30天综合削减率", water_guideline.get("composite_reduction_rate"), " %")
        for metric in water_guideline.get("metrics", []):
            unit = metric.get("unit", "")
            lines.append(
                f"    * {metric.get('label', '—')}："
                f"基准期均值 {_prompt_value(metric.get('baseline_avg'), f' {unit}' if unit else '')}，"
                f"近30天均值 {_prompt_value(metric.get('recent_avg'), f' {unit}' if unit else '')}，"
                f"近30天相对削减率 {_prompt_value(metric.get('recent_reduction_rate'), ' %')}"
            )

    if pest_guideline.get("available"):
        lines.append("需融入第二章、第六章和第七章的虫情风险链条：")
        _append_fact(lines, "风险等级", pest_guideline.get("risk_level"))
        _append_fact(
            lines,
            "虫情峰值",
            f"{pest_guideline.get('insect_peak', {}).get('date', '—')} / "
            f"{pest_guideline.get('insect_peak', {}).get('count', 0)} 只",
        )
        _append_fact(lines, "建议动作", pest_guideline.get("suggestion"))
        _append_fact(lines, "闭环说明", pest_guideline.get("chain_text"))

    if warning_analysis:
        lines.append("需融入第二章和第三章的分级预警判定：")
        _append_fact(lines, "历史对比状态", warning_analysis.get("comparison", {}).get("message"))
        for item in warning_analysis.get("indicator_warnings", []):
            if item.get("key") == "spore_peak":
                continue
            lines.append(
                f"    * {item.get('title', '—')}："
                f"预警等级 {_prompt_value(item.get('level'))}，"
                f"监测值 {_prompt_value(item.get('display_value'))}，"
                f"判定区间 {_prompt_value(item.get('band'))}，"
                f"分级规则 {_prompt_value(item.get('rule_text'))}，"
                f"建议动作 {_prompt_value(item.get('action'))}"
            )

    confirmed_rules = implementation_matrix.get("confirmed_rules") or []
    if confirmed_rules:
        lines.append("需融入第四章和第五章的数据口径约束：")
        for item in confirmed_rules:
            lines.append(f"  - {item}")

    if water_source_support and water_source_support.get("message"):
        lines.append("需融入第三章的气象补充与水源涵养支撑：")
        _append_fact(lines, "支撑状态", water_source_support.get("status"))
        _append_fact(lines, "说明", water_source_support.get("message"))

    history_comparison = summary.get("history_comparison", {}) or {}
    previous_period = history_comparison.get("previous_period", {}) or {}
    if history_comparison:
        lines.append("历史对比分析：")
        _append_fact(lines, "对比口径", history_comparison.get("comparison_basis", "本期与上一等长周期对比"))
        _append_fact(
            lines,
            "上一等长周期",
            f"{previous_period.get('start', '—')} 至 {previous_period.get('end', '—')}",
        )
        for item in (history_comparison.get("modules") or {}).values():
            lines.append(
                f"  - {item.get('label', '—')}："
                f"{item.get('metric_label', '—')}本期 {_prompt_value(item.get('current_value'), f' {item.get('unit', '')}' if item.get('unit') else '')}，"
                f"上一等长周期 {_prompt_value(item.get('previous_value'), f' {item.get('unit', '')}' if item.get('unit') else '')}，"
                f"变化值 {_prompt_value(item.get('change_value'), f' {item.get('unit', '')}' if item.get('unit') else '')}，"
                f"变化率 {_prompt_value(item.get('change_rate'), ' %')}，"
                f"趋势 {item.get('trend', '—')}"
            )
        water_history = history_comparison.get("water_quality", {}) or {}
        if water_history.get("metrics"):
            lines.append("  - 水质关键指标周期均值对比：")
            for metric in water_history.get("metrics", []):
                lines.append(
                    f"    * {metric.get('label', '—')}："
                    f"本期 {_prompt_value(metric.get('current_value'), f' {metric.get('unit', '')}' if metric.get('unit') else '')}，"
                    f"上一等长周期 {_prompt_value(metric.get('previous_value'), f' {metric.get('unit', '')}' if metric.get('unit') else '')}，"
                    f"变化值 {_prompt_value(metric.get('change_value'), f' {metric.get('unit', '')}' if metric.get('unit') else '')}，"
                    f"变化率 {_prompt_value(metric.get('change_rate'), ' %')}，"
                    f"趋势 {metric.get('trend', '—')}"
                )

    return "\n".join(lines)
