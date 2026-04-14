"""AI智能分析报告服务 — DeepSeek API"""

import logging
from typing import Any

import httpx
from config import settings
from services.report_figures import build_figure_reference_rules

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT_TEMPLATE = """你是一位专业的农业生态分析师，服务于海南省三亚市天涯区农业农村局智慧监测平台。请根据以下监测数据摘要，生成一份完整的农业生态环境监测分析报告。

【报告要求】
- 总字数：要求极其详尽，务必达到 5000 字 到 8000 字之间（各章节字数参考括号内说明，但必须做详尽扩展和深挖）
- 结构完整，逐章节详细展开，论述必须充分、不可简略
- 语言专业、严谨，数据有据可查，量化描述为主
- 适合农业技术人员和管理部门阅读
- 涉及具体防治措施时，给出可操作的方案（时间、方法、药剂或生物手段）

【报告结构与撰写指令】
你必须严格按照以下7个章节输出。
- 每一章使用"## 一、章节名"格式
- 每章内部小节使用"**1.1 小节名**"格式（加粗，不用###），小节序号与章序号对应，如第二章用2.1、2.2，第三章用3.1、3.2，以此类推
- 每章至少2个小节
- 绝对不允许将括号内的"(约xxx字)"等指令提示语打印到正文中

## 一、监测期综合概况
（核心要求：约400字。**1.1 监测周期与数据完整性评估**：综述监测时段、主要监测项目、各模块数据记录条数与完整率；**1.2 监测结果总体态势与区域背景影响**：简述各项监测结果总体态势，说明三亚市天涯区气候背景和当前农事背景对本期数据的宏观影响。）

## 二、气象条件深度分析
（核心要求：约700字。**2.1 温湿度变化特征分析**：详细分析温度变化规律及波动特征，温湿度耦合关系；**2.2 降雨分布与影响评估**：降雨时间分布、强度分级；**2.3 气象条件对农业生产的综合影响**：与三亚市同期气候正常值对比，分析对热带作物有利和不利影响。）

## 三、土壤墒情综合评估
（核心要求：约600字。**3.1 各层次墒情状态分析**：分析10、20、40cm三层土壤含水量绝对值及变化趋势，判断与作物根系层匹配情况；**3.2 土壤水分平衡与灌溉建议**：结合降雨和蒸散发分析水分平衡，提出具体灌溉或排水制度建议。）

## 四、病虫害监测与风险评估
（核心要求：约900字。**4.1 虫情种类组成与发生规律**：详细分析各类昆虫种类组成比例，各优势虫种生活史特点及对主要作物危害；**4.2 孢子捕捉与真菌病害风险评估**：孢子数量分析，真菌性病害发生风险等级评定；**4.3 综合风险等级与纵向比对**：综合评定本期风险等级，与往期数据纵向比对。）

## 五、农业生产影响综合评价
（核心要求：约600字。**5.1 对主要作物的综合影响**：综合气象、土壤墒情、病虫害三维数据，系统评价对水稻、热带经济作物（橡胶、槟榔）、蔬菜瓜果的影响；**5.2 主要风险因子识别**：指出本期最突出的风险因子及其危害路径。）

## 六、防治措施与技术建议
（核心要求：约1500字。**6.1 分虫种化学防治方案**：针对优势虫种提出防治窗口期、具体农药名称、配比浓度；**6.2 生物与物理防治措施**：生物防治手段、灯光诱杀、色板等物理措施；**6.3 无人机作业建议**：作业时间、飞行高度、喷液量；**6.4 气象灾害防范预案**：针对极端天气的防范措施。）

## 七、下一监测周期预测与预警
（核心要求：约400字。**7.1 主要风险走向预测**：预测下一周期气象趋势和病虫害扩散态势；**7.2 预警级别与农事建议**：发布预警级别（绿色/黄色/橙色/红色），提出对应预防性农事准备。）

监测数据摘要：
{data_summary}

【极其重要的格式要求】
1. 直接从"## 一、监测期综合概况"开头输出，绝对不要有任何引导语。
2. 绝对不可以把"（核心要求：...）"这些我写给你的规则文字原样输出到报告里！！
3. 每个"## "章节必须包含"### "小节细分（至少2个小节）。
4. 切记不要在最终报告里带任何类似"综述监测时段："这类生硬的前缀提示。

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

    w = summary.get("weather", {})
    if w.get("records_count", 0) > 0:
        lines.append(
            f"气象数据（{w['records_count']}条记录）：\n"
            f"  - 平均温度 {w.get('avg_temp', '—')}°C，最高 {w.get('max_temp', '—')}°C，最低 {w.get('min_temp', '—')}°C\n"
            f"  - 平均湿度 {w.get('avg_humidity', '—')}%\n"
            f"  - 累计降雨量 {w.get('total_rainfall', 0)} mm"
        )
    else:
        lines.append("气象数据：暂无记录")

    s = summary.get("soil", {})
    if s.get("records_count", 0) > 0:
        lines.append(
            f"土壤墒情（{s['records_count']}条记录）：\n"
            f"  - 10cm 平均墒情 {s.get('avg_moisture_10cm', '—')}%\n"
            f"  - 20cm 平均墒情 {s.get('avg_moisture_20cm', '—')}%\n"
            f"  - 40cm 平均墒情 {s.get('avg_moisture_40cm', '—')}%"
        )
    else:
        lines.append("墒情数据：暂无记录")

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
