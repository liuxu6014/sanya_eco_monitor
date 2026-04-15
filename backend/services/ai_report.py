"""AI智能分析报告服务 — DeepSeek API"""

import logging
from typing import Any

import httpx
from config import settings
from services.report_figures import build_figure_reference_rules

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT_TEMPLATE = """你是一位顶尖的生态修复与效益评估专家，服务于“三亚市天涯区橡胶林近自然化改造和农田提升监测平台”。请根据以下监测数据摘要，撰写一份详尽的《橡胶林近自然化改造生态效益评估报告》。

【报告要求】
- 总字数：要求极其详尽，务必达到 5000 字 到 8000 字之间（各章节必须做深度扩展，结合生态学理论进行专业判析）
- 报告性质：生态效益评估，侧重于近自然化改造对生物多样性、水资源调节、环境质量的提升作用
- 语言专业、严谨，论述必须充分，杜绝空洞的套话，应以量化数据支撑定性结论
- 适合林业专家、生态资源管理部门及技术人员阅读

【报告结构与撰写指令】
你必须严格按照以下7个章节输出。
- 每一章使用"## 一、章节名"格式
- 每章内部小节使用"**1.1 小节名**"格式（加粗，不用###），小节序号与章序号对应
- 每章至少2个小节
- 绝对不允许将括号内的指令提示语打印到正文中

## 一、监测期综合概况与评估背景
（**1.1 监测周期与数据完整性评估**：说明统计周期、各类设备运行状态、数据采集完整率；**1.2 近自然化改造项目背景与监测意义**：阐述天涯区橡胶林近自然化改造的目标，说明本期监测对评估森林结构优化、生态功能恢复的关键意义。）

## 二、森林生物多样性与生态健康指标分析
（**2.1 虫情监测与昆虫种群群落稳定性评估**：从核心虫情数据分析昆虫多样性，评估生态位占用情况及其作为森林健康指示器的意义；**2.2 孢子监测与林间微生态环境调控**：分析孢子捕获数据，研判林下湿度、透光率改变对真菌病害及微生态平衡的影响；**2.3 生态链恢复状况定性评估**。）

## 三、水文调节功能与水土流失监测分析
（**3.1 降雨分布与林冠层截留作用评价**：结合降雨监测，分析橡胶林对降水的缓冲作用；**3.2 地表径流监测与水源涵养能力分析**：通过径流量、流速及产沙情况（地表径流数据），评估近自然化改造后橡胶林在拦截雨水、减少水土流失方面的效益。）

## 四、区域水环境质量与生态容量评价
（**4.1 汇水区域水质指标演变分析**：详细分析pH、溶氧、氨氮、COD等指标，评估林地改善对水环境的净化贡献；**4.2 农田提升区面源污染拦截效益**：研判林地改造对下游农田提升区生态缓冲带的作用。）

## 五、近自然化改造生态效益综合判析
（**5.1 生态系统稳定性提升评价**：综合分析多源数据，判断橡胶林从人工单一林向近自然复层林转变过程中的生态稳定性；**5.2 生效服务功能价值化初判**：从固碳、涵养水源、生物多样性保护等维度给予定性及初步定量评价。）

## 六、森林抚育与生态系统精准修复建议
（**6.1 林分结构优化与植植补植策略**：针对监测出的生态薄弱环节提出技术优化建议；**6.2 生物防治与天敌恢复技术方案**：基于虫情数据，提出利用本土生物多样性进行病虫害生态调控的方案。）

## 七、长期生态趋势监测预测与展望
（**7.1 演替趋势与未来风险预警**：预测生态系统演替方向；**7.2 评估结论与后期监测重点建议**。）

监测数据摘要：
{data_summary}

【极其重要的数据对齐与格式要求】
1. 直接从"## 一、监测期综合概况"开头输出，禁止任何前言或总结性套话。
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
            resp = await client.post(
                f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8192,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP error: {e.response.status_code} {e.response.text}")
        return f"【AI分析服务暂时不可用】HTTP {e.response.status_code}，请稍后重试。"
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return f"【AI分析服务异常】{str(e)}"


def format_summary_for_prompt(summary: dict) -> str:
    """Format summary dict into readable Chinese text for the prompt."""
    lines = []
    p = summary.get("period", {})
    lines.append(f"统计周期：{p.get('start', '—')} 至 {p.get('end', '—')}")

    ins = summary.get("insect", {})
    if ins.get("total_count", 0) > 0:
        top = ins.get("top_species", [])
        top_str = "、".join(f"{n}({c}只)" for n, c in top[:5]) if top else "无"
        lines.append(
            f"虫情测报（{ins['records_count']}条记录）：\n"
            f"  - 周期内捕获昆虫 {ins['total_count']} 只\n"
            f"  - 主要虫种：{top_str}"
        )
    else:
        lines.append("虫情数据：周期内未捕获或暂无记录")

    sp = summary.get("spore", {})
    if sp.get("total_count", 0) > 0:
        lines.append(
            f"孢子捕捉（{sp['records_count']}条记录）：周期内捕获孢子 {sp['total_count']} 个"
        )
    else:
        lines.append("孢子数据：周期内未捕获或暂无记录")

    wq = summary.get("water_quality", {})
    if wq.get("records_count", 0) > 0:
        lines.append(
            f"水质监测（{wq['records_count']}条记录）：\n"
            f"  - 平均 pH {wq.get('avg_ph', '—')}，溶解氧 {wq.get('avg_do', '—')}mg/L\n"
            f"  - 氨氮 {wq.get('avg_nh3_n', '—')}mg/L，总磷 {wq.get('avg_tp', '—')}mg/L，总氮 {wq.get('avg_tn', '—')}mg/L\n"
            f"  - COD {wq.get('avg_cod', '—')}mg/L"
        )

    ro = summary.get("runoff", {})
    if ro.get("records_count", 0) > 0:
        lines.append(
            f"地表径流（{ro['records_count']}条记录）：\n"
            f"  - 平均流量 {ro.get('avg_flow_rate', '—')} m³/h，最高流量 {ro.get('max_flow_rate', '—')} m³/h\n"
            f"  - 平均液位 {ro.get('avg_water_level', '—')} mm"
        )

    rn = summary.get("rain", {})
    if rn.get("records_count", 0) > 0:
        lines.append(
            f"降雨监测（{rn['records_count']}条记录）：累计降雨量 {rn.get('total_rainfall', 0)} mm"
        )

    return "\n".join(lines)
