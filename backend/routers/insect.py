from datetime import datetime, time, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models import InsectRecord, SporeRecord

router = APIRouter(prefix="/api/insect", tags=["虫情"])

SPECIES_KNOWLEDGE = {
    "甜菜夜蛾": {
        "intro": "甜菜夜蛾属于夜蛾类害虫，寄主范围广，幼虫取食能力强，常在蔬菜、玉米、豆类以及周边杂草上辗转发生。低龄幼虫多群集取食叶肉，高龄后分散危害，取食量明显增大，容易造成叶片孔洞、缺刻和嫩梢受损。",
        "harm_score": 90,
        "warning_threshold": 70,
        "harm_analysis": "危害性评分较高，主要原因是该虫繁殖快、世代重叠明显、幼虫进入高龄后防治难度上升。诱捕量持续升高通常提示田间卵块或低龄幼虫可能正在增加，应重点判断是否存在连续多日上升、峰值后维持高位以及周边杂草寄主向作物迁移的情况。",
        "strategy": "防治上应把握低龄幼虫期，优先清除田边杂草和残株，结合灯诱、性诱、田间卵块调查开展早期压低虫口；达到阈值时采用针对鳞翅目幼虫的高效低毒药剂轮换使用，避免长期单一用药导致抗性上升。",
        "strategy_steps": [
            "重点巡查叶背、嫩叶和田边杂草，发现卵块或低龄幼虫时优先点片处理。",
            "诱捕量连续上升时提高巡查频次，并同步记录幼虫龄期，避免错过低龄防治窗口。",
            "药剂防治应轮换作用机制，优先选择对天敌影响较小的方案，并避开高温强光时段施药。",
        ],
    },
    "稻飞虱": {
        "intro": "稻飞虱以刺吸式口器吸食水稻汁液，具有迁飞性强、繁殖速度快、田间扩散快的特点，是水稻中后期需要持续监测的重点害虫。",
        "harm_score": 92,
        "warning_threshold": 80,
        "harm_analysis": "危害评分高，原因在于其能够造成稻株失水、黄化、倒伏，严重时形成“冒穿”风险。诱捕量升高时，需要结合田间虫口密度、若虫比例和水稻生育期综合判断，不能只看单次捕获数量。",
        "strategy": "加强田间巡查，控制氮肥偏施；达到阈值时优先选用高效低毒药剂并轮换用药。",
        "strategy_steps": [
            "重点查看田块中下部稻丛和密植、偏施氮肥区域，确认若虫密度。",
            "保护蜘蛛、寄生蜂等天敌，避免早期盲目广谱用药破坏自然控制能力。",
            "达到防治阈值后选用内吸性较好的药剂，并注意轮换用药和足量喷施到稻株基部。",
        ],
    },
    "二化螟": {
        "intro": "二化螟以幼虫钻蛀水稻茎秆为主，隐蔽性强，初期不易被发现，常造成枯心苗、枯孕穗和白穗，是水稻生产中典型的钻蛀性害虫。",
        "harm_score": 88,
        "warning_threshold": 60,
        "harm_analysis": "危害评分较高，主要因为幼虫钻入茎秆后药剂难以触达，错过卵孵化和低龄幼虫期后防治成本明显增加。诱捕峰值通常可作为成虫发生和产卵风险的参考，应与卵块调查联动。",
        "strategy": "结合诱捕量与田间卵块调查，抓住低龄幼虫期防治，保护天敌并减少重复用药。",
        "strategy_steps": [
            "诱捕峰后重点开展卵块调查，关注稻叶背面和近水面叶鞘部位。",
            "低龄幼虫孵化盛期是关键防治窗口，钻蛀后应转为查漏补防和田间损失评估。",
            "收割后清理稻桩和残茬，降低越冬虫源基数。",
        ],
    },
    "稻纵卷叶螟": {
        "intro": "稻纵卷叶螟幼虫吐丝卷叶并在卷叶内取食叶肉，影响水稻叶片光合作用。迁入峰明显时，田间卷叶率可能短期升高。",
        "harm_score": 82,
        "warning_threshold": 70,
        "harm_analysis": "危害评分较高，主要体现在暴发期扩散速度快、叶面积损失明显。应重点关注迁入峰后低龄幼虫数量，而不是仅依据成虫灯诱量作出结论。",
        "strategy": "重点关注迁入峰和低龄幼虫盛期，优先采用性诱、灯诱和精准药剂防治。",
        "strategy_steps": [
            "迁入峰后 3 至 7 天加强田间卷叶率和幼虫龄期调查。",
            "低龄幼虫期优先精准防治，高龄后应评估实际叶面积损失再决定处置强度。",
            "避免在天敌活跃期过度用药，保留自然控制能力。",
        ],
    },
    "粘虫": {
        "intro": "粘虫具有迁飞性和群集暴食特征，幼虫取食叶片速度快，适宜条件下短时间内可造成明显缺刻甚至叶片残缺。",
        "harm_score": 78,
        "warning_threshold": 50,
        "harm_analysis": "危害评分偏高，原因是幼虫集中发生时取食量大、扩散快。灯诱量升高后应重点确认田间是否出现低龄幼虫集中带，避免由点片发生扩展为面状危害。",
        "strategy": "夜间和清晨巡查重点地块，发现集中发生及时点片挑治，避免扩散。",
        "strategy_steps": [
            "清晨或傍晚巡查叶片缺刻、新鲜虫粪和幼虫聚集区。",
            "点片发生时优先局部处理，阻断扩散路线。",
            "加强田边草丛和相邻作物巡查，减少迁移虫源。",
        ],
    },
    "草地贪夜蛾": {
        "intro": "草地贪夜蛾是迁飞性强、寄主范围广的重大害虫，幼虫偏好取食玉米等禾本科作物，常在心叶、嫩叶和生长点附近造成孔洞、缺刻和虫粪堆积。",
        "harm_score": 96,
        "warning_threshold": 40,
        "harm_analysis": "危害评分极高，原因是迁飞扩散快、繁殖潜力强、幼虫隐蔽在心叶内后防治难度上升。监测到该虫后应按重点预警对象处理，即使数量不高，也需要快速开展田间复核。",
        "strategy": "坚持早发现、早处置，重点抓住低龄幼虫尚未钻入心叶深处的阶段；结合性诱、灯诱、田间踏查和应急防控，防止虫口快速扩散。",
        "strategy_steps": [
            "发现成虫诱捕后，立即检查玉米心叶、嫩叶孔洞和虫粪。",
            "低龄幼虫期优先精准喷施，确保药液进入心叶和幼虫活动部位。",
            "对连续诱捕区域建立重点台账，跟踪 3 至 7 天内虫口变化。",
        ],
    },
    "斜纹夜蛾": {
        "intro": "斜纹夜蛾为多食性夜蛾类害虫，幼虫取食叶片、嫩茎和果实表面，低龄群集、高龄分散，暴发时危害面积扩大较快。",
        "harm_score": 86,
        "warning_threshold": 60,
        "harm_analysis": "危害评分较高，原因是寄主广、夜间取食活跃、低龄到高龄转换后取食量快速增加。若诱捕量连续增加，应重点关注叶背卵块和低龄幼虫群集点。",
        "strategy": "以卵块清除和低龄幼虫防治为主，结合田边杂草管理、诱杀和轮换用药，降低后期高龄幼虫造成的防治压力。",
        "strategy_steps": [
            "优先巡查叶背卵块、嫩叶缺刻和幼虫群集取食点。",
            "低龄幼虫集中期点片处理，避免高龄后扩散。",
            "田边杂草和残株及时处理，减少隐蔽虫源。",
        ],
    },
    "金龟子": {
        "intro": "金龟子成虫可取食叶片、花器和嫩梢，幼虫蛴螬多在土壤中取食根系。不同虫态危害部位不同，监测时需要区分成虫诱捕与地下幼虫风险。",
        "harm_score": 72,
        "warning_threshold": 80,
        "harm_analysis": "危害评分中高，单次诱捕量高不一定立即代表田间严重危害，但若成虫持续偏多，可能提示周边土壤虫源基数较高。需要结合叶片缺刻、根系受害和植株长势判断。",
        "strategy": "成虫期可结合灯诱、人工震落和局部防治；地下幼虫风险则需要通过土壤调查、翻耕暴露和生物防治进行控制。",
        "strategy_steps": [
            "成虫发生期重点观察叶片缺刻和嫩梢取食情况。",
            "苗期长势异常时检查根系和土壤蛴螬密度。",
            "减少未腐熟有机肥使用，必要时结合土壤处理降低地下虫口。",
        ],
    },
    "棉铃虫": {
        "intro": "棉铃虫为多食性蛾类害虫，幼虫可蛀食花蕾、果实和嫩部组织，隐蔽取食特征明显，常导致落花落果或果实受损。",
        "harm_score": 84,
        "warning_threshold": 55,
        "harm_analysis": "危害评分较高，原因是幼虫蛀入花蕾或果实后防治难度明显增加。诱捕量上升时应关注产卵和初孵幼虫阶段，避免等到钻蛀后再处理。",
        "strategy": "以成虫诱测、卵量调查和低龄幼虫期防治为核心，结合清除受害蕾果和轮换用药降低虫源积累。",
        "strategy_steps": [
            "诱捕峰后重点检查花蕾、嫩果和叶背卵粒。",
            "低龄幼虫期及时防治，钻蛀后以摘除受害组织和压低虫源为主。",
            "避免长期单一药剂，降低抗药性风险。",
        ],
    },
    "玉米螟": {
        "intro": "玉米螟幼虫钻蛀玉米茎秆、穗轴和雄穗，造成折秆、穗部受损和产量下降，是玉米生产中典型钻蛀性害虫。",
        "harm_score": 82,
        "warning_threshold": 50,
        "harm_analysis": "危害评分较高，钻蛀后药剂触达困难，防治窗口主要集中在卵孵化和低龄幼虫尚未钻蛀前。诱捕量升高应与卵块密度和心叶受害状况结合判断。",
        "strategy": "抓住低龄幼虫期开展心叶定向防治，收获后处理秸秆和残茬，降低越冬虫源。",
        "strategy_steps": [
            "重点检查玉米心叶排孔、虫粪和茎秆蛀孔。",
            "低龄幼虫期定向处理心叶和穗部周边。",
            "收获后粉碎秸秆或深翻处理，减少越冬基数。",
        ],
    },
}

SPORE_KNOWLEDGE = {
    "炭疽病孢子": {
        "intro": "炭疽病孢子在高湿、温暖条件下更易扩散，常与叶片病斑、果实病斑风险相关。",
        "harm_score": 86,
        "warning_threshold": 60,
        "strategy": "加强通风降湿，雨后及时巡查叶片和嫩梢；连续上升时可结合保护性药剂和清除病残体处理。",
    },
    "白粉病孢子": {
        "intro": "白粉病孢子易在郁闭、湿度波动大的环境中传播，影响叶片光合作用。",
        "harm_score": 74,
        "warning_threshold": 50,
        "strategy": "降低田间郁闭度，控制过量氮肥；发现初发点后优先局部处理，避免扩展。",
    },
    "霜霉病孢子": {
        "intro": "霜霉病孢子与低温高湿、叶面长时间结露密切相关，适合开展连续预警。",
        "harm_score": 80,
        "warning_threshold": 55,
        "strategy": "重点关注夜间湿度和雨后时段，提前清理病叶并采用预防性防治措施。",
    },
}


def _species_profile(name: str) -> dict:
    defaults = {
        "intro": f"{name}为当前监测记录中的虫种。由于不同地区寄主作物、发生世代和田间生态条件存在差异，系统将其作为专项关注对象进行研判，需要把诱捕数量、连续出现天数、田间危害症状和近期气象条件结合起来判断。",
        "harm_score": 60,
        "warning_threshold": 40,
        "harm_analysis": f"{name}当前按中等危害等级进行默认评分。若该虫种在短时间内连续出现，或在诱捕结果中占比升高，应视为潜在风险上升信号；若仅零星出现，则更适合作为背景虫情记录，需继续观察其是否形成持续趋势。",
        "strategy": "保持连续监测，若数量连续上升，应开展田间复核并采用物理诱控、生物防治与低毒药剂相结合的策略。",
        "strategy_steps": [
            "先核对诱捕数据是否连续出现，再到对应地块复核叶片、嫩梢、果实或根系危害症状。",
            "若数量连续上升，应提高巡查频次，并记录发生点位、虫态、危害部位和处置结果。",
            "防治上优先采用诱捕、清除虫源、生物防治和低毒精准药剂组合，避免没有田间依据的泛化用药。",
        ],
    }
    profile = {**defaults, **SPECIES_KNOWLEDGE.get(name, {})}
    profile["risk_level_text"] = (
        "高危害"
        if profile["harm_score"] >= 85
        else "中高危害"
        if profile["harm_score"] >= 70
        else "持续关注"
    )
    return profile


def _spore_profile(name: str) -> dict:
    defaults = {
        "intro": f"{name}为当前空气孢子监测记录中的类型，需结合湿度、降雨、作物长势和田间病斑进行综合判断。",
        "harm_score": 58,
        "warning_threshold": 35,
        "strategy": "保持连续监测；若捕获量连续升高，应加强通风降湿、清理病残体，并对重点区域开展田间复核。",
    }
    return {**defaults, **SPORE_KNOWLEDGE.get(name, {})}


def _insect_analysis_text(
    *,
    species: str | None,
    days: int,
    total_count: int,
    avg_daily: float,
    peak: dict,
    active_days: int,
    focus: list[dict],
    profile: dict | None = None,
) -> str:
    peak_date = peak.get("date") or "暂无峰值日期"
    peak_count = peak.get("total") or 0
    if species and profile:
        threshold = profile.get("warning_threshold") or 0
        harm_score = profile.get("harm_score") or 0
        pressure = "高压发生" if total_count >= threshold else "持续关注" if total_count >= threshold * 0.6 else "低位波动"
        return (
            f"近{days}天{species}累计捕获{total_count}只，日均{avg_daily}只，"
            f"活跃记录覆盖{active_days}天，峰值出现在{peak_date}，单日达到{peak_count}只。"
            f"该虫种危害评分为{harm_score}分，预警参考阈值为{threshold}只，当前处于{pressure}状态。"
            "研判上应重点看三点：一是诱捕量是否连续上升，二是峰值后是否仍维持高位，三是田间叶片、嫩梢或果实是否出现对应危害症状。"
            "建议把灯诱数据作为预警信号，结合样方调查确认虫龄和发生范围，再决定是否开展点片防治或区域联防。"
        )

    top = focus[0] if focus else None
    top_text = (
        f"当前综合关注度最高的虫种为{top['name']}，累计{top['count']}只，危害评分{top['harm_score']}分。"
        if top
        else "当前暂未形成明确优势虫种。"
    )
    return (
        f"近{days}天虫情累计捕获{total_count}只，日均{avg_daily}只，"
        f"活跃记录覆盖{active_days}天，峰值出现在{peak_date}，单日达到{peak_count}只。"
        f"{top_text}"
        "整体研判需同时考虑数量规模、虫种危害性和连续出现天数：数量高但危害低的虫种以观察为主，危害评分高且数量持续增长的虫种应优先进入田间复核清单。"
        "建议后续按重点虫种建立巡查台账，记录诱捕量变化、田间危害点位和处置结果，便于形成可追踪的防控闭环。"
    )


def _spore_analysis_text(
    *,
    name: str | None,
    days: int,
    total_count: int,
    avg_daily: float,
    peak: dict,
    active_days: int,
    focus: list[dict],
    profile: dict | None = None,
) -> str:
    peak_date = peak.get("date") or "暂无峰值日期"
    peak_count = peak.get("total") or 0
    if name and profile:
        threshold = profile.get("warning_threshold") or 0
        return (
            f"近{days}天{name}累计捕获{total_count}个，日均{avg_daily}个，"
            f"活跃记录覆盖{active_days}天，峰值出现在{peak_date}，单日达到{peak_count}个。"
            f"该类型预警参考阈值为{threshold}个，应结合雨后湿度、夜间结露和田间病斑同步判断。"
            "若捕获量连续升高，说明病原传播条件可能正在形成，应优先核查通风差、湿度高和植株郁闭区域。"
        )
    top = focus[0] if focus else None
    top_text = f"当前需优先关注{top['name']}，累计{top['count']}个。" if top else "当前暂无明显优势孢子类型。"
    return (
        f"近{days}天空气孢子累计捕获{total_count}个，日均{avg_daily}个，"
        f"活跃记录覆盖{active_days}天，峰值出现在{peak_date}，单日达到{peak_count}个。{top_text}"
        "孢子数据更适合作为病害发生的前置信号，建议与降雨、湿度、田间病斑和作物长势联动研判。"
    )


def _recent_day_labels(days: int, fmt: str) -> list[str]:
    today = datetime.now().date()
    start_day = today - timedelta(days=days - 1)
    return [(start_day + timedelta(days=i)).strftime(fmt) for i in range(days)]


def _is_synthetic_record(record) -> bool:
    return bool((record.raw_data or {}).get("synthetic"))


async def _latest_non_empty_image(db: AsyncSession, model) -> tuple[str, datetime] | None:
    result = await db.execute(
        select(model.image_url, model.collection_time)
        .where(model.image_url.is_not(None), model.image_url != "")
        .order_by(desc(model.collection_time))
        .limit(1)
    )
    row = result.one_or_none()
    if not row:
        return None
    return row[0], row[1]


@router.get("/latest")
async def get_latest_insect(db: AsyncSession = Depends(get_db)):
    """最新一条虫情记录"""
    result = await db.execute(
        select(InsectRecord).order_by(desc(InsectRecord.collection_time)).limit(20)
    )
    records = result.scalars().all()
    record = next((item for item in records if not _is_synthetic_record(item)), None)
    if not record:
        return {"data": None}
    fallback_image = None if record.image_url else await _latest_non_empty_image(db, InsectRecord)
    image_url = record.image_url or (fallback_image[0] if fallback_image else None)
    image_time = record.collection_time if record.image_url else (fallback_image[1] if fallback_image else None)
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "total_count": record.total_count,
            "species_data": record.species_data,
            "image_url": image_url,
            "image_collection_time": image_time.isoformat() if image_time else None,
        }
    }


@router.get("/trend")
async def get_insect_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """近N天虫情趋势 (每日汇总)"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since)
        .order_by(InsectRecord.collection_time)
    )
    records = result.scalars().all()

    # Group by day
    daily: dict = {}
    for r in records:
        day = r.collection_time.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "total": 0, "species": {}}
        daily[day]["total"] += r.total_count
        for name, cnt in (r.species_data or {}).items():
            daily[day]["species"][name] = daily[day]["species"].get(name, 0) + cnt

    return {"data": list(daily.values())}


@router.get("/species-stats")
async def get_species_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """各虫种统计汇总"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(InsectRecord).where(InsectRecord.collection_time >= since)
    )
    records = result.scalars().all()

    totals: dict = {}
    for r in records:
        for name, cnt in (r.species_data or {}).items():
            totals[name] = totals.get(name, 0) + cnt

    sorted_species = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return {
        "data": [{"name": name, "value": cnt} for name, cnt in sorted_species]
    }


@router.get("/spore/latest")
async def get_latest_spore(db: AsyncSession = Depends(get_db)):
    """最新孢子捕捉数据"""
    result = await db.execute(
        select(SporeRecord).order_by(desc(SporeRecord.collection_time)).limit(20)
    )
    records = result.scalars().all()
    record = next((item for item in records if not _is_synthetic_record(item)), None)
    if not record:
        return {"data": None}
    fallback_image = None if record.image_url else await _latest_non_empty_image(db, SporeRecord)
    image_url = record.image_url or (fallback_image[0] if fallback_image else None)
    image_time = record.collection_time if record.image_url else (fallback_image[1] if fallback_image else None)
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "total_count": record.total_count,
            "spore_data": record.spore_data,
            "image_url": image_url,
            "image_collection_time": image_time.isoformat() if image_time else None,
        }
    }


@router.get("/spore/trend")
async def get_spore_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """近N天孢子趋势"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= since)
        .order_by(SporeRecord.collection_time)
    )
    records = result.scalars().all()

    daily: dict = {}
    for r in records:
        day = r.collection_time.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "total": 0}
        daily[day]["total"] += r.total_count

    return {"data": list(daily.values())}


@router.get("/combined-trend")
async def get_combined_trend(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """虫情+孢子 联合趋势（逐日，用于相关性分析图）"""
    since = datetime.now() - timedelta(days=days)

    insect_res = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since)
        .order_by(InsectRecord.collection_time)
    )
    spore_res = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= since)
        .order_by(SporeRecord.collection_time)
    )
    insects = insect_res.scalars().all()
    spores = spore_res.scalars().all()

    insect_daily: dict = {}
    for r in insects:
        day = r.collection_time.strftime("%Y-%m-%d")
        insect_daily[day] = insect_daily.get(day, 0) + r.total_count

    spore_daily: dict = {}
    for r in spores:
        day = r.collection_time.strftime("%Y-%m-%d")
        spore_daily[day] = spore_daily.get(day, 0) + r.total_count

    all_days = sorted(set(list(insect_daily.keys()) + list(spore_daily.keys())))
    data = [
        {
            "date": d,
            "insect": insect_daily.get(d, 0),
            "spore": spore_daily.get(d, 0),
        }
        for d in all_days
    ]
    return {"data": data}


@router.get("/species-heatmap")
async def get_species_heatmap(
    days: int = Query(14, ge=7, le=30),
    db: AsyncSession = Depends(get_db),
):
    """虫种-日期热力图数据（二维矩阵）"""
    today = datetime.now().date()
    since = datetime.combine(today - timedelta(days=days - 1), time.min)
    result = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since)
        .order_by(InsectRecord.collection_time)
    )
    records = result.scalars().all()

    # Collect all dates and species
    from collections import defaultdict
    matrix: dict = defaultdict(lambda: defaultdict(int))
    all_species: set = set()
    for r in records:
        day = r.collection_time.strftime("%m-%d")
        for sp, cnt in (r.species_data or {}).items():
            matrix[day][sp] += cnt
            all_species.add(sp)

    dates = _recent_day_labels(days, "%m-%d")
    species = sorted(all_species)
    # Build flat list: [date_index, species_index, value]
    flat = []
    for di, date in enumerate(dates):
        for si, sp in enumerate(species):
            flat.append([di, si, matrix[date].get(sp, 0)])

    return {"data": {"dates": dates, "species": species, "values": flat}}


@router.get("/images")
async def get_insect_images(
    days: int = Query(30, ge=1, le=180),
    species: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.combine(datetime.now().date() - timedelta(days=days - 1), time.min)
    result = await db.execute(
        select(InsectRecord)
        .where(
            InsectRecord.collection_time >= since,
            InsectRecord.image_url.is_not(None),
            InsectRecord.image_url != "",
        )
        .order_by(desc(InsectRecord.collection_time))
        .limit(240)
    )
    records = result.scalars().all()
    items = []
    for record in records:
        species_data = record.species_data or {}
        if species and species not in species_data:
            continue
        items.append(
            {
                "id": record.id,
                "image_url": record.image_url,
                "collection_time": record.collection_time.isoformat(),
                "total_count": record.total_count,
                "species_data": species_data,
                "species_count": species_data.get(species) if species else None,
            }
        )
    return {"data": items}


@router.get("/analysis-detail")
async def get_insect_analysis_detail(
    species: str | None = Query(default=None),
    days: int = Query(30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.combine(datetime.now().date() - timedelta(days=days - 1), time.min)
    result = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since)
        .order_by(InsectRecord.collection_time)
    )
    records = result.scalars().all()

    daily: dict[str, int] = {label: 0 for label in _recent_day_labels(days, "%Y-%m-%d")}
    totals: dict[str, int] = {}
    latest_image = None
    images = []
    for record in records:
        day = record.collection_time.strftime("%Y-%m-%d")
        species_data = record.species_data or {}
        count = species_data.get(species, 0) if species else record.total_count
        daily[day] = daily.get(day, 0) + count
        for name, value in species_data.items():
            totals[name] = totals.get(name, 0) + value
        if record.image_url and (not species or species in species_data):
            image_item = {
                "id": record.id,
                "image_url": record.image_url,
                "collection_time": record.collection_time.isoformat(),
                "total_count": record.total_count,
                "species_count": species_data.get(species) if species else None,
            }
            images.append(image_item)
            latest_image = image_item

    focus = []
    for name, count in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:8]:
        profile = _species_profile(name)
        focus.append(
            {
                "name": name,
                "count": count,
                "harm_score": profile["harm_score"],
                "attention_score": min(100, round(profile["harm_score"] * 0.65 + min(count, 120) * 0.35)),
                "warning_threshold": profile["warning_threshold"],
            }
        )
    focus.sort(key=lambda item: item["attention_score"], reverse=True)

    trend = [{"date": key, "total": value} for key, value in sorted(daily.items())]
    total_count = sum(item["total"] for item in trend)
    peak = max(trend, key=lambda item: item["total"], default={"date": None, "total": 0})
    avg_daily = round(total_count / max(days, 1), 1)

    active_days = len([item for item in trend if item["total"] > 0])
    profile = _species_profile(species) if species else None
    analysis = _insect_analysis_text(
        species=species,
        days=days,
        total_count=total_count,
        avg_daily=avg_daily,
        peak=peak,
        active_days=active_days,
        focus=focus,
        profile=profile,
    )

    payload = {
        "mode": "species" if species else "overall",
        "species": species,
        "period_days": days,
        "trend": trend,
        "species_stats": [{"name": name, "value": value} for name, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)],
        "latest_image": latest_image,
        "images": list(reversed(images[-60:])),
        "focus_species": focus,
        "summary": {
            "total_count": total_count,
            "current_period_total": total_count,
            "avg_daily": avg_daily,
            "peak_date": peak["date"],
            "peak_count": peak["total"],
            "active_days": active_days,
            "analysis": analysis,
        },
    }
    if species:
        payload["profile"] = profile
        payload["warning"] = {
            "threshold": profile["warning_threshold"],
            "current_month_total": total_count,
            "level": "高" if total_count >= profile["warning_threshold"] else "关注" if total_count >= profile["warning_threshold"] * 0.6 else "低",
        }
    return {"data": payload}


@router.get("/spore/images")
async def get_spore_images(
    days: int = Query(30, ge=1, le=180),
    name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.combine(datetime.now().date() - timedelta(days=days - 1), time.min)
    result = await db.execute(
        select(SporeRecord)
        .where(
            SporeRecord.collection_time >= since,
            SporeRecord.image_url.is_not(None),
            SporeRecord.image_url != "",
        )
        .order_by(desc(SporeRecord.collection_time))
        .limit(240)
    )
    records = result.scalars().all()
    items = []
    for record in records:
        spore_data = record.spore_data or {}
        if name and name not in spore_data:
            continue
        items.append(
            {
                "id": record.id,
                "image_url": record.image_url,
                "collection_time": record.collection_time.isoformat(),
                "total_count": record.total_count,
                "spore_data": spore_data,
                "spore_count": spore_data.get(name) if name else None,
            }
        )
    return {"data": items}


@router.get("/spore/analysis-detail")
async def get_spore_analysis_detail(
    name: str | None = Query(default=None),
    days: int = Query(30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.combine(datetime.now().date() - timedelta(days=days - 1), time.min)
    result = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= since)
        .order_by(SporeRecord.collection_time)
    )
    records = result.scalars().all()
    real_records = [record for record in records if not _is_synthetic_record(record)]
    latest_record_time = real_records[-1].collection_time if real_records else None

    daily: dict[str, int] = {label: 0 for label in _recent_day_labels(days, "%Y-%m-%d")}
    totals: dict[str, int] = {}
    latest_image = None
    images = []
    for record in records:
        day = record.collection_time.strftime("%Y-%m-%d")
        spore_data = record.spore_data or {}
        count = spore_data.get(name, 0) if name else record.total_count
        daily[day] = daily.get(day, 0) + count
        for spore_name, value in spore_data.items():
            totals[spore_name] = totals.get(spore_name, 0) + value
        if record.image_url and (not name or name in spore_data):
            image_item = {
                "id": record.id,
                "image_url": record.image_url,
                "collection_time": record.collection_time.isoformat(),
                "total_count": record.total_count,
                "spore_count": spore_data.get(name) if name else None,
            }
            images.append(image_item)
            latest_image = image_item

    focus = []
    for spore_name, count in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:8]:
        profile = _spore_profile(spore_name)
        focus.append(
            {
                "name": spore_name,
                "count": count,
                "harm_score": profile["harm_score"],
                "attention_score": min(100, round(profile["harm_score"] * 0.62 + min(count, 120) * 0.38)),
                "warning_threshold": profile["warning_threshold"],
            }
        )
    focus.sort(key=lambda item: item["attention_score"], reverse=True)

    trend = [{"date": key, "total": value} for key, value in sorted(daily.items())]
    total_count = sum(item["total"] for item in trend)
    peak = max(trend, key=lambda item: item["total"], default={"date": None, "total": 0})
    active_days = len([item for item in trend if item["total"] > 0])
    avg_daily = round(total_count / max(days, 1), 1)

    profile = _spore_profile(name) if name else None
    analysis = _spore_analysis_text(
        name=name,
        days=days,
        total_count=total_count,
        avg_daily=avg_daily,
        peak=peak,
        active_days=active_days,
        focus=focus,
        profile=profile,
    )

    payload = {
        "mode": "spore" if name else "overall",
        "name": name,
        "period_days": days,
        "trend": trend,
        "spore_stats": [{"name": key, "value": value} for key, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)],
        "latest_image": latest_image,
        "latest_record_time": latest_record_time.isoformat() if latest_record_time else None,
        "latest_image_time": latest_image["collection_time"] if latest_image else None,
        "images": list(reversed(images[-60:])),
        "focus_spores": focus,
        "summary": {
            "total_count": total_count,
            "current_period_total": total_count,
            "avg_daily": avg_daily,
            "peak_date": peak["date"],
            "peak_count": peak["total"],
            "active_days": active_days,
            "analysis": analysis,
        },
    }
    if name:
        payload["profile"] = profile
        payload["warning"] = {
            "threshold": profile["warning_threshold"],
            "current_month_total": total_count,
            "level": "高" if total_count >= profile["warning_threshold"] else "关注" if total_count >= profile["warning_threshold"] * 0.6 else "低",
        }
    return {"data": payload}
