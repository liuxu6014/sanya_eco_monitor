"""设备掉线（异常）统计服务。

两路数据互补：
1. **数据空档反推**（历史）：每台设备按固定节律上报数据，`collection_time` 序列里
   超过阈值的"空档"即视为一次掉线。基于已有数据，部署前的历史也能立刻统计。
2. **状态事件**（增量）：调度器每轮采样把"在线→离线"翻转写入 device_status_events，
   补"探测失败但本就不该有数据"等空档反推覆盖不到的场景。

两路区间取并集后再统计次数与总时长，供平台展示与供应商反馈。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import (
    DeviceStatusEvent,
    InsectRecord,
    RainfallRecord,
    RunoffRecord,
    SporeRecord,
    WaterQualityRecord,
)
from time_utils import cn_now_naive

# 设备编码 → 中文名（与 routers/summary.py 的设备元数据保持一致）。
RUNOFF_NAMES = {
    "16132920": "橡胶林1监测点",
    "16132921": "次生林监测点",
    "16132922": "芒果林1监测点",
    "16132923": "槟榔林监测点",
    "16132924": "橡胶林2监测点",
    "16132925": "芒果林2监测点",
}
RAIN_NAMES = {
    "16132920": "橡胶林雨量站",
    "16132921": "次生林雨量站",
    "16132922": "芒果林雨量站",
}


# 各设备类型的"期望上报间隔"与"判定掉线的空档阈值"，按线上接口实测节律校准
# （2026-06 实测 collection_time 间隔分布）：
#   水质 / 雨量 / 径流：中位 5 分钟、p99 ≤ 8 分钟，极规律 → 阈值 30 分钟（≈6 条缺失，远超噪声）。
#   虫情：夜间成簇上报，白天正常空档最大 ~24 小时 → 阈值 30 小时（留 6 小时余量）。
#   孢子：每天早上采一次，正常最大间隔 ~26 小时 → 阈值 36 小时（≈连续漏报 >1 天）。
def _type_expected_interval(device_type: str) -> timedelta:
    if device_type in ("rain", "runoff", "water"):
        return timedelta(minutes=5)
    if device_type == "insect":
        return timedelta(hours=1)
    # spore
    return timedelta(hours=6)


def _type_gap_threshold(device_type: str) -> timedelta:
    if device_type in ("rain", "runoff", "water"):
        return timedelta(minutes=30)
    if device_type == "insect":
        return timedelta(hours=30)
    # spore：每天一报，连续漏报超过 ~1.5 天才算掉线
    return timedelta(hours=36)


@dataclass(frozen=True)
class DataSource:
    model: type
    code: str | None  # 数据表按 device_code 过滤；None 表示整表（单设备表）


@dataclass(frozen=True)
class MonitoredDevice:
    key: str
    name: str
    type: str
    # 一台物理设备可能同时上报多路数据（如径流站内置雨量计，同编码上报径流+降雨）。
    # 判活/反推时取所有数据源时间戳的并集——任一路有数据即视为在线。
    sources: tuple[DataSource, ...]

    @property
    def expected_interval(self) -> timedelta:
        return _type_expected_interval(self.type)

    @property
    def gap_threshold(self) -> timedelta:
        return _type_gap_threshold(self.type)


def build_device_registry() -> list[MonitoredDevice]:
    """构建被监控的物理设备清单。

    径流站（含内置雨量计）按物理设备合并为一条：同编码的径流+降雨两路数据归入同一台设备，
    避免同一次掉电被拆成"径流断"和"雨量断"两条重复统计。
    """
    devices: list[MonitoredDevice] = [
        MonitoredDevice("insect", "智能虫情测报灯", "insect", (DataSource(InsectRecord, None),)),
        MonitoredDevice("spore", "孢子捕捉仪", "spore", (DataSource(SporeRecord, None),)),
        MonitoredDevice("water", "面源污染监测站", "water", (DataSource(WaterQualityRecord, None),)),
    ]
    runoff_codes = [c.strip() for c in settings.RUNOFF_CODES.split(",") if c.strip()]
    runoff_set = set(runoff_codes)
    rain_codes = [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()] or list(RAIN_NAMES)
    rain_set = set(rain_codes)

    for code in runoff_codes:
        sources = [DataSource(RunoffRecord, code)]
        if code in rain_set:
            # 该径流站内置雨量计，同编码同时上报降雨，合并为同一台物理设备。
            sources.append(DataSource(RainfallRecord, code))
        devices.append(
            MonitoredDevice(
                key=f"runoff_{code}",
                name=RUNOFF_NAMES.get(code, f"径流监测点{code}"),
                type="runoff",
                sources=tuple(sources),
            )
        )
    # 仅当雨量计编码不属于任何径流站时，才作为独立雨量设备单列。
    for code in rain_codes:
        if code in runoff_set:
            continue
        devices.append(
            MonitoredDevice(
                key=f"rain_{code}",
                name=RAIN_NAMES.get(code, f"雨量站{code}"),
                type="rain",
                sources=(DataSource(RainfallRecord, code),),
            )
        )
    return devices


def get_device_by_key(key: str) -> MonitoredDevice | None:
    for device in build_device_registry():
        if device.key == key:
            return device
    return None


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    ordered = sorted((s, e) for s, e in intervals if e > s)
    merged: list[tuple[datetime, datetime]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _clip(interval: tuple[datetime, datetime], lo: datetime, hi: datetime) -> tuple[datetime, datetime] | None:
    start = max(interval[0], lo)
    end = min(interval[1], hi)
    if end <= start:
        return None
    return (start, end)


def reconstruct_gaps(
    timestamps: list[datetime],
    *,
    range_start: datetime,
    range_end: datetime,
    expected: timedelta,
    threshold: timedelta,
    now: datetime,
) -> list[tuple[datetime, datetime]]:
    """从一台设备的上报时间序列里反推掉线区间（未裁剪到范围）。"""
    intervals: list[tuple[datetime, datetime]] = []
    ordered = sorted(timestamps)
    prev: datetime | None = None
    for ts in ordered:
        if prev is not None:
            gap = ts - prev
            if gap > threshold:
                intervals.append((prev + expected, ts))
        prev = ts
    # 末尾空档：最后一条数据之后一直没有上报，直到当前时间（或范围末端）。
    tail_end = min(now, range_end)
    if prev is not None and tail_end - prev > threshold:
        intervals.append((prev + expected, tail_end))
    return intervals


async def _device_timestamps(
    db: AsyncSession,
    device: MonitoredDevice,
    *,
    query_start: datetime,
    query_end: datetime,
) -> list[datetime]:
    timestamps: list[datetime] = []
    for src in device.sources:
        stmt = select(src.model.collection_time).where(
            src.model.collection_time >= query_start,
            src.model.collection_time <= query_end,
        )
        if src.code is not None:
            stmt = stmt.where(src.model.device_code == src.code)
        result = await db.execute(stmt)
        timestamps.extend(row[0] for row in result.all() if row[0] is not None)
    timestamps.sort()
    return timestamps


async def _last_timestamp_before(
    db: AsyncSession,
    device: MonitoredDevice,
    before: datetime,
) -> datetime | None:
    """窗口之前最近一条上报时间，用作反推的锚点。

    无此锚点时，整窗口无数据的设备会被当作"从未上线"而不计入掉线，
    避免把"接入中、尚无数据"的设备误报为掉线。多数据源时取各源最近时间的最大值。
    """
    best: datetime | None = None
    for src in device.sources:
        stmt = select(src.model.collection_time).where(src.model.collection_time < before)
        if src.code is not None:
            stmt = stmt.where(src.model.device_code == src.code)
        stmt = stmt.order_by(src.model.collection_time.desc()).limit(1)
        row = (await db.execute(stmt)).first()
        if row and row[0] is not None and (best is None or row[0] > best):
            best = row[0]
    return best


async def _event_intervals(
    db: AsyncSession,
    device: MonitoredDevice,
    *,
    range_start: datetime,
    range_end: datetime,
    now: datetime,
) -> list[tuple[datetime, datetime]]:
    stmt = (
        select(DeviceStatusEvent.started_at, DeviceStatusEvent.ended_at)
        .where(
            DeviceStatusEvent.device_key == device.key,
            DeviceStatusEvent.started_at <= range_end,
        )
        .order_by(DeviceStatusEvent.started_at)
    )
    result = await db.execute(stmt)
    intervals: list[tuple[datetime, datetime]] = []
    for started_at, ended_at in result.all():
        if started_at is None:
            continue
        end = ended_at or min(now, range_end)
        intervals.append((started_at, end))
    return intervals


def _duration_seconds(intervals: list[tuple[datetime, datetime]]) -> int:
    return int(sum((end - start).total_seconds() for start, end in intervals))


async def _device_outages(
    db: AsyncSession,
    device: MonitoredDevice,
    *,
    range_start: datetime,
    range_end: datetime,
    now: datetime,
) -> list[tuple[datetime, datetime]]:
    # 多取一个阈值的余量，便于检测跨范围左边界的空档。
    query_start = range_start - device.gap_threshold - device.expected_interval
    timestamps = await _device_timestamps(db, device, query_start=query_start, query_end=range_end)
    # 预置窗口前最近一条记录作为锚点：既能检测跨左边界的掉线，也能识别"整窗口无数据但此前曾在线"。
    anchor = await _last_timestamp_before(db, device, query_start)
    if anchor is not None:
        timestamps = [anchor, *timestamps]
    gap_intervals = reconstruct_gaps(
        timestamps,
        range_start=query_start,
        range_end=range_end,
        expected=device.expected_interval,
        threshold=device.gap_threshold,
        now=now,
    )
    event_intervals = await _event_intervals(
        db, device, range_start=range_start, range_end=range_end, now=now
    )
    merged = _merge_intervals(gap_intervals + event_intervals)
    clipped = [c for c in (_clip(i, range_start, range_end) for i in merged) if c is not None]
    return clipped


async def compute_outage_report(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    device_key: str | None = None,
    now: datetime | None = None,
) -> dict:
    """生成掉线运维报表：明细清单 + 当前范围统计 + 近7天/近30天统计。"""
    now = now or cn_now_naive()
    registry = build_device_registry()
    if device_key:
        registry = [d for d in registry if d.key == device_key]

    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    rows: list[dict] = []
    per_device: list[dict] = []
    for device in registry:
        range_outages = await _device_outages(
            db, device, range_start=start, range_end=end, now=now
        )
        for outage_start, outage_end in range_outages:
            ongoing = outage_end >= min(now, end) and outage_end >= now - device.expected_interval
            rows.append(
                {
                    "device_key": device.key,
                    "device_name": device.name,
                    "device_type": device.type,
                    "start": outage_start.isoformat(),
                    "end": outage_end.isoformat(),
                    "duration_seconds": int((outage_end - outage_start).total_seconds()),
                    "ongoing": ongoing,
                }
            )

        # 固定窗口（近7天/近30天）独立统计，不受筛选范围影响。
        week_outages = await _device_outages(
            db, device, range_start=week_start, range_end=now, now=now
        )
        month_outages = await _device_outages(
            db, device, range_start=month_start, range_end=now, now=now
        )
        per_device.append(
            {
                "device_key": device.key,
                "device_name": device.name,
                "device_type": device.type,
                "range_count": len(range_outages),
                "range_duration_seconds": _duration_seconds(range_outages),
                "week_count": len(week_outages),
                "week_duration_seconds": _duration_seconds(week_outages),
                "month_count": len(month_outages),
                "month_duration_seconds": _duration_seconds(month_outages),
            }
        )

    rows.sort(key=lambda r: r["start"], reverse=True)

    totals = {
        "range_count": sum(d["range_count"] for d in per_device),
        "range_duration_seconds": sum(d["range_duration_seconds"] for d in per_device),
        "week_count": sum(d["week_count"] for d in per_device),
        "week_duration_seconds": sum(d["week_duration_seconds"] for d in per_device),
        "month_count": sum(d["month_count"] for d in per_device),
        "month_duration_seconds": sum(d["month_duration_seconds"] for d in per_device),
    }

    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": now.isoformat(),
        "rows": rows,
        "per_device": per_device,
        "totals": totals,
    }


async def compute_current_statuses(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> dict[str, str]:
    """按"最后一条数据时间戳是否陈旧"判断每台设备当前在线/离线。

    平台 /data-n 接口即使设备停报通常仍返回 200 + 旧值，故不能用 HTTP 状态码判活；
    以数据时间戳的新鲜度为准，与空档反推同源。从未上报过的设备（接入中）不纳入。
    """
    now = now or cn_now_naive()
    statuses: dict[str, str] = {}
    for device in build_device_registry():
        last = await _last_timestamp_before(db, device, now + timedelta(seconds=1))
        if last is None:
            continue
        statuses[device.key] = "online" if (now - last) <= device.gap_threshold else "offline"
    return statuses


async def record_status_snapshot(
    db: AsyncSession,
    statuses: dict[str, str],
    *,
    now: datetime | None = None,
) -> None:
    """根据本轮探测到的设备状态，维护 device_status_events 的开/合。

    statuses: {device_key: "online"|"offline"|"timeout"}。
    在线→离线：开一条 ended_at 为空的事件；离线→在线：补全最近一条未结束事件。
    """
    now = now or cn_now_naive()
    for device in build_device_registry():
        status = statuses.get(device.key)
        if status is None:
            continue
        is_down = status != "online"
        open_event = (
            await db.execute(
                select(DeviceStatusEvent)
                .where(
                    DeviceStatusEvent.device_key == device.key,
                    DeviceStatusEvent.ended_at.is_(None),
                )
                .order_by(DeviceStatusEvent.started_at.desc())
                .limit(1)
            )
        ).scalars().first()

        if is_down and open_event is None:
            db.add(
                DeviceStatusEvent(
                    device_key=device.key,
                    device_name=device.name,
                    device_type=device.type,
                    status=status,
                    started_at=now,
                    ended_at=None,
                    source="probe",
                )
            )
        elif not is_down and open_event is not None:
            open_event.ended_at = now
    await db.commit()
