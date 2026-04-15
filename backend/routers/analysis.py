"""
综合生态分析接口 - 跨数据集交叉计算衍生指标
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models import WeatherRecord, SoilRecord, InsectRecord, SporeRecord, RunoffRecord, WaterQualityRecord

router = APIRouter(prefix="/api/analysis", tags=["综合分析"])


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


@router.get("/eco-index")
async def get_eco_index(db: AsyncSession = Depends(get_db)):
    """
    综合生态健康指数，基于最近24h气象/土壤/虫情/孢子多源数据交叉运算。
    返回:
      - pest_risk      病虫害风险指数 0-100
      - growth_suitability  作物生长适宜度 0-100
      - irrigation_urgency  灌溉需求紧迫度 0-100
      - eco_health     综合生态健康指数 0-100
      - alerts         预警列表
    """
    now = datetime.now()
    since_24h = now - timedelta(hours=24)
    since_7d  = now - timedelta(days=7)

    # ── 气象最新 (取最近一个小时的平均值) ──
    res = await db.execute(
        select(WeatherRecord)
        .where(WeatherRecord.collection_time >= now - timedelta(hours=1))
    )
    ws = res.scalars().all()
    w_temp = sum(r.temperature for r in ws if r.temperature is not None) / len(ws) if ws else 25
    w_hum  = sum(r.humidity for r in ws if r.humidity is not None) / len(ws) if ws else 70
    w_rain = sum(r.rainfall for r in ws if r.rainfall is not None) / len(ws) if ws else 0
    w_light = sum(r.light for r in ws if r.light is not None) / len(ws) if ws else 30000

    # ── 土壤最新 (取最近一小时所有站点的平均) ──
    res = await db.execute(
        select(SoilRecord)
        .where(SoilRecord.collection_time >= now - timedelta(hours=1))
    )
    ss = res.scalars().all()
    sm10 = sum(r.moisture_10cm for r in ss if r.moisture_10cm is not None) / len(ss) if ss else 30
    sm20 = sum(r.moisture_20cm for r in ss if r.moisture_20cm is not None) / len(ss) if ss else 35
    sm40 = sum(r.moisture_40cm for r in ss if r.moisture_40cm is not None) / len(ss) if ss else 38

    # ── 近7日虫情合计 ──
    res = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since_7d)
        .order_by(desc(InsectRecord.collection_time))
    )
    insects = res.scalars().all()
    total_insects = sum(r.total_count for r in insects)
    avg_insects = total_insects / len(insects) if insects else 0

    # ── 近7日孢子合计 ──
    res = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= since_7d)
        .order_by(desc(SporeRecord.collection_time))
    )
    spores = res.scalars().all()
    total_spores = sum(r.total_count for r in spores)
    avg_spores = total_spores / len(spores) if spores else 0

    # ── 径流/降雨 (水土流失分析 - 取最近1小时平均) ──
    res = await db.execute(
        select(RunoffRecord)
        .where(RunoffRecord.collection_time >= now - timedelta(hours=1))
    )
    ros = res.scalars().all()
    avg_flow = sum(r.flow_rate for r in ros if r.flow_rate is not None) / len(ros) if ros else 0
    avg_sand = sum(r.sand_content for r in ros if r.sand_content is not None) / len(ros) if ros else 0
    avg_runoff_rain = sum(r.rainfall for r in ros if r.rainfall is not None) / len(ros) if ros else 0

    # ── 水质 (面源污染分析 - 取最近一条记录) ──
    res = await db.execute(select(WaterQualityRecord).order_by(desc(WaterQualityRecord.collection_time)).limit(1))
    wq = res.scalar_one_or_none()

    # ══════════════════════════════════════════════════
    # 1. 病虫害风险指数 (0-100, 越高越危险)
    # 逻辑：虫情基数 + 孢子密度 + 气象促发条件(高温高湿)
    # ══════════════════════════════════════════════════
    insect_score = _clamp(avg_insects / 1.5, 0, 40)       # 每批次150只满分，占40分
    spore_score  = _clamp(avg_spores  / 1.5, 0, 30)       # 每批次150个满分，占30分
    weather_factor = 0
    temp = w_temp
    hum  = w_hum
    # 高温高湿是病虫害爆发温床：25-32°C, 湿度>70%
    if 22 <= temp <= 35:
        weather_factor += (temp - 22) / 13 * 15
    if hum > 70:
        weather_factor += (hum - 70) / 30 * 15
    weather_factor = _clamp(weather_factor, 0, 30)
    pest_risk = round(insect_score + spore_score + weather_factor)

    # ══════════════════════════════════════════════════
    # 2. 作物生长适宜度 (0-100, 越高越适合)
    # 综合：温度、湿度、光照、土壤湿度
    # ══════════════════════════════════════════════════
    # 温度适宜区间 22-30°C
    temp_score = 0
    if 22 <= temp <= 30:
        temp_score = 35 - abs(temp - 26) / 4 * 10   # 26°C最佳
    elif temp < 22:
        temp_score = max(0, 20 - (22 - temp) * 3)
    else:
        temp_score = max(0, 20 - (temp - 30) * 5)
    temp_score = _clamp(temp_score, 0, 35)

    # 湿度适宜区间 60-80%
    hum_score = 0
    if 60 <= hum <= 80:
        hum_score = 25
    elif hum < 60:
        hum_score = max(0, 20 - (60 - hum))
    else:
        hum_score = max(0, 20 - (hum - 80) * 0.5)
    hum_score = _clamp(hum_score, 0, 25)

    # 土壤湿度综合 (10+20+40cm 各占权重)
    m10 = sm10
    m20 = sm20
    m40 = sm40
    avg_moisture = m10 * 0.4 + m20 * 0.35 + m40 * 0.25
    # 最优土壤湿度 30-45%
    if 30 <= avg_moisture <= 45:
        moist_score = 25
    elif avg_moisture < 30:
        moist_score = max(0, 25 - (30 - avg_moisture) * 1.5)
    else:
        moist_score = max(0, 25 - (avg_moisture - 45) * 1.5)
    moist_score = _clamp(moist_score, 0, 25)

    # 光照 (20000-60000 lux 为最佳)
    light = w_light
    if 20000 <= light <= 60000:
        light_score = 15
    elif light < 20000:
        light_score = max(0, 15 - (20000 - light) / 2000)
    else:
        light_score = max(0, 15 - (light - 60000) / 5000)
    light_score = _clamp(light_score, 0, 15)

    growth_suitability = round(temp_score + hum_score + moist_score + light_score)

    # ══════════════════════════════════════════════════
    # 3. 灌溉需求紧迫度 (0-100, 越高越需要灌溉)
    # 逻辑：土壤偏干 + 气温偏高 + 近期少雨
    # ══════════════════════════════════════════════════
    # 土壤偏干程度
    dry_score = 0
    if avg_moisture < 25:
        dry_score = 60
    elif avg_moisture < 35:
        dry_score = (35 - avg_moisture) / 10 * 60
    moisture_urgency = _clamp(dry_score, 0, 60)

    # 高温蒸发加剧
    heat_urgency = _clamp((temp - 20) / 15 * 25, 0, 25)

    # 近期降雨量 (取气象站和径流站降雨的极大值)
    rain = max(w_rain, avg_runoff_rain)
    rain_urgency = _clamp((5 - rain) / 5 * 15, 0, 15)

    irrigation_urgency = round(moisture_urgency + heat_urgency + rain_urgency)

    # ══════════════════════════════════════════════════
    # 5. 水土流失风险指数 (Erosion Index)
    # 逻辑: 降雨强度 * 径流流速 * 含沙量
    # ══════════════════════════════════════════════════
    rain_rate = rain
    flow_speed = avg_flow
    sand_val = avg_sand
    # 归一化计算: 假设 10mm降雨 * 1.0m/s流速 * 0.5kg/L含沙量 为极高(100)
    erosion_val = (rain_rate * 5 + flow_speed * 30 + sand_val * 100)
    erosion_index = _clamp(round(erosion_val), 0, 100)

    # ══════════════════════════════════════════════════
    # 6. 面源污染负荷指数 (Pollution Load)
    # 逻辑: COD, 氨氮, 总磷, 总氮的加权超标倍数
    # ══════════════════════════════════════════════════
    if wq:
        # 简单权重: COD(0.3), NH4(0.3), TP(0.2), TN(0.2)
        # 假设基准: COD 20, NH4 1.0, TP 0.2, TN 1.0
        p_cod = _clamp(wq.cod / 40 * 100, 0, 100)
        p_nh4 = _clamp(wq.ammonia_nitrogen / 2.0 * 100, 0, 100)
        p_tp  = _clamp(wq.total_phosphorus / 0.4 * 100, 0, 100)
        p_tn  = _clamp(wq.total_nitrogen / 2.0 * 100, 0, 100)
        pollution_index = round(p_cod * 0.3 + p_nh4 * 0.3 + p_tp * 0.2 + p_tn * 0.2)
    else:
        pollution_index = 0

    eco_health = round(
        growth_suitability * 0.4 +
        (100 - pest_risk) * 0.2 +
        (100 - irrigation_urgency) * 0.15 +
        (100 - erosion_index) * 0.15 +
        (100 - pollution_index) * 0.1
    )

    # ══════════════════════════════════════════════════
    # 5. 智能预警
    # ══════════════════════════════════════════════════
    alerts = []
    if pest_risk >= 70:
        alerts.append({"level": "danger", "msg": "病虫害风险极高，建议立即田间核查"})
    elif pest_risk >= 45:
        alerts.append({"level": "warning", "msg": "病虫害风险偏高，建议加强监测频率"})

    if irrigation_urgency >= 65:
        alerts.append({"level": "danger", "msg": "土壤干旱严重，建议立即启动灌溉"})
    elif irrigation_urgency >= 40:
        alerts.append({"level": "warning", "msg": "土壤湿度偏低，近期需适量灌溉"})

    if growth_suitability >= 80:
        alerts.append({"level": "info", "msg": "当前气候土壤条件优良，适宜作物生长"})
    elif growth_suitability <= 40:
        alerts.append({"level": "warning", "msg": "生长条件较差，建议检查气候与土壤因素"})

    if not alerts:
        alerts.append({"level": "info", "msg": "各项指标正常，生态系统运行良好"})

    return {
        "data": {
            "pest_risk": pest_risk,
            "growth_suitability": growth_suitability,
            "irrigation_urgency": irrigation_urgency,
            "erosion_risk": erosion_index,
            "pollution_load": pollution_index,
            "eco_health": eco_health,
            "alerts": alerts,
            "computed_at": now.isoformat(),
            "meta": {
                "avg_insects_7d": round(avg_insects, 1),
                "avg_spores_7d":  round(avg_spores, 1),
                "avg_moisture_pct": round(avg_moisture, 1),
                "temperature": round(temp, 1),
                "humidity": round(hum, 1),
                "rainfall": round(rain, 1),
            }
        }
    }
