"""Report generation service for the Sanya monitoring platform.

Provides aggregated summaries of weather, soil, insect, and spore data
over configurable date ranges, and can render those summaries as Excel
workbooks or standalone HTML documents.
"""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from jinja2 import Environment, BaseLoader
from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Font,
    PatternFill,
    Border,
    Side,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    InsectRecord, SporeRecord, WeatherRecord, SoilRecord,
    WaterQualityRecord, RainfallRecord, RunoffRecord
)
from services.report_figures import build_figure_manifest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_avg(values: list[float]) -> float | None:
    """Return the arithmetic mean of *values*, or None when the list is empty."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 2)


def _round_or_none(value: float | None, ndigits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, ndigits)


def _date_range_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Convert date objects to datetime range covering full days (inclusive)."""
    start_dt = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
    return start_dt, end_dt


# ---------------------------------------------------------------------------
# ReportService
# ---------------------------------------------------------------------------

class ReportService:
    """Aggregate monitoring data and produce reports."""

    # ------------------------------------------------------------------
    # Public summary entry points
    # ------------------------------------------------------------------

    async def get_week_summary(
        self,
        db: AsyncSession,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Return an aggregated summary for the 7 days ending on *end_date*."""
        if end_date is None:
            end_date = date.today()
        start_date = end_date - timedelta(days=6)
        return await self._build_summary(db, start_date, end_date)

    async def get_month_summary(
        self,
        db: AsyncSession,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Return an aggregated summary for the 30 days ending on *end_date*."""
        if end_date is None:
            end_date = date.today()
        start_date = end_date - timedelta(days=29)
        return await self._build_summary(db, start_date, end_date)

    async def get_custom_summary(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Return an aggregated summary for the given date range (inclusive)."""
        return await self._build_summary(db, start_date, end_date)

    # ------------------------------------------------------------------
    # Core aggregation
    # ------------------------------------------------------------------

    async def _build_summary(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        start_dt, end_dt = _date_range_bounds(start_date, end_date)

        weather = await self._aggregate_weather(db, start_dt, end_dt)
        soil = await self._aggregate_soil(db, start_dt, end_dt)
        insect = await self._aggregate_insect(db, start_dt, end_dt)
        spore = await self._aggregate_spore(db, start_dt, end_dt)
        water_quality = await self._aggregate_water_quality(db, start_dt, end_dt)
        rain = await self._aggregate_rainfall(db, start_dt, end_dt)
        runoff = await self._aggregate_runoff(db, start_dt, end_dt)

        return {
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
            },
            "weather": weather,
            "soil": soil,
            "insect": insect,
            "spore": spore,
            "water_quality": water_quality,
            "rain": rain,
            "runoff": runoff,
        }

    # ------------------------------------------------------------------
    # Per-model aggregators
    # ------------------------------------------------------------------

    async def _aggregate_weather(
        self,
        db: AsyncSession,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(WeatherRecord).where(
                WeatherRecord.collection_time >= start_dt,
                WeatherRecord.collection_time <= end_dt,
            )
        )
        records = result.scalars().all()

        temps = [r.temperature for r in records if r.temperature is not None]
        humidities = [r.humidity for r in records if r.humidity is not None]
        rainfalls = [r.rainfall for r in records if r.rainfall is not None]

        # Daily aggregation for charts
        daily_buckets: dict[str, dict] = defaultdict(
            lambda: {"temps": [], "humidity": [], "rainfall": []}
        )
        for r in records:
            day = r.collection_time.strftime("%Y-%m-%d")
            if r.temperature is not None:
                daily_buckets[day]["temps"].append(r.temperature)
            if r.humidity is not None:
                daily_buckets[day]["humidity"].append(r.humidity)
            if r.rainfall is not None:
                daily_buckets[day]["rainfall"].append(r.rainfall)

        daily_list = [
            {
                "date": d,
                "avg_temp": _safe_avg(v["temps"]),
                "avg_humidity": _safe_avg(v["humidity"]),
                "total_rainfall": round(sum(v["rainfall"]), 2) if v["rainfall"] else 0.0,
            }
            for d, v in sorted(daily_buckets.items())
        ]

        return {
            "avg_temp": _safe_avg(temps),
            "max_temp": _round_or_none(max(temps)) if temps else None,
            "min_temp": _round_or_none(min(temps)) if temps else None,
            "avg_humidity": _safe_avg(humidities),
            "total_rainfall": _round_or_none(sum(rainfalls)) if rainfalls else 0.0,
            "records_count": len(records),
            "daily": daily_list,
        }

    async def _aggregate_soil(
        self,
        db: AsyncSession,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(SoilRecord).where(
                SoilRecord.collection_time >= start_dt,
                SoilRecord.collection_time <= end_dt,
            )
        )
        records = result.scalars().all()

        m10 = [r.moisture_10cm for r in records if r.moisture_10cm is not None]
        m20 = [r.moisture_20cm for r in records if r.moisture_20cm is not None]
        m40 = [r.moisture_40cm for r in records if r.moisture_40cm is not None]

        # Daily aggregation for charts
        soil_buckets: dict[str, dict] = defaultdict(
            lambda: {"m10": [], "m20": [], "m40": []}
        )
        for r in records:
            day = r.collection_time.strftime("%Y-%m-%d")
            if r.moisture_10cm is not None:
                soil_buckets[day]["m10"].append(r.moisture_10cm)
            if r.moisture_20cm is not None:
                soil_buckets[day]["m20"].append(r.moisture_20cm)
            if r.moisture_40cm is not None:
                soil_buckets[day]["m40"].append(r.moisture_40cm)

        soil_daily = [
            {
                "date": d,
                "avg_moisture_10cm": _safe_avg(v["m10"]),
                "avg_moisture_20cm": _safe_avg(v["m20"]),
                "avg_moisture_40cm": _safe_avg(v["m40"]),
            }
            for d, v in sorted(soil_buckets.items())
        ]

        return {
            "avg_moisture_10cm": _safe_avg(m10),
            "avg_moisture_20cm": _safe_avg(m20),
            "avg_moisture_40cm": _safe_avg(m40),
            "records_count": len(records),
            "daily": soil_daily,
        }

    async def _aggregate_insect(
        self,
        db: AsyncSession,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(InsectRecord).where(
                InsectRecord.collection_time >= start_dt,
                InsectRecord.collection_time <= end_dt,
            ).order_by(InsectRecord.collection_time)
        )
        records = result.scalars().all()

        total_count = sum(r.total_count for r in records)

        # Aggregate species counts across all records
        species_totals: dict[str, int] = defaultdict(int)
        for r in records:
            if r.species_data:
                for name, cnt in r.species_data.items():
                    species_totals[name] += int(cnt)

        top_species = sorted(
            species_totals.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Daily aggregation
        daily: dict[str, int] = defaultdict(int)
        for r in records:
            day_key = r.collection_time.strftime("%Y-%m-%d")
            daily[day_key] += r.total_count

        daily_list = [
            {"date": d, "count": c}
            for d, c in sorted(daily.items())
        ]

        return {
            "total_count": total_count,
            "records_count": len(records),
            "top_species": [list(item) for item in top_species],
            "daily": daily_list,
        }

    async def _aggregate_spore(
        self,
        db: AsyncSession,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(SporeRecord).where(
                SporeRecord.collection_time >= start_dt,
                SporeRecord.collection_time <= end_dt,
            ).order_by(SporeRecord.collection_time)
        )
        records = result.scalars().all()

        total_count = sum(r.total_count for r in records)

        daily: dict[str, int] = defaultdict(int)
        for r in records:
            day_key = r.collection_time.strftime("%Y-%m-%d")
            daily[day_key] += r.total_count

        daily_list = [
            {"date": d, "count": c}
            for d, c in sorted(daily.items())
        ]

        return {
            "total_count": total_count,
            "records_count": len(records),
            "daily": daily_list,
        }

    async def _aggregate_water_quality(
        self,
        db: AsyncSession,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(WaterQualityRecord).where(
                WaterQualityRecord.collection_time >= start_dt,
                WaterQualityRecord.collection_time <= end_dt,
            )
        )
        records = result.scalars().all()
        if not records:
            return {"records_count": 0}

        phs = [r.ph for r in records if r.ph is not None]
        dos = [r.dissolved_oxygen for r in records if r.dissolved_oxygen is not None]
        turbs = [r.turbidity for r in records if r.turbidity is not None]
        nh3s = [r.ammonia_nitrogen for r in records if r.ammonia_nitrogen is not None]
        tps = [r.total_phosphorus for r in records if r.total_phosphorus is not None]
        tns = [r.total_nitrogen for r in records if r.total_nitrogen is not None]
        cods = [r.cod for r in records if r.cod is not None]

        return {
            "records_count": len(records),
            "avg_ph": _safe_avg(phs),
            "avg_do": _safe_avg(dos),
            "avg_turbidity": _safe_avg(turbs),
            "avg_nh3_n": _safe_avg(nh3s),
            "avg_tp": _safe_avg(tps),
            "avg_tn": _safe_avg(tns),
            "avg_cod": _safe_avg(cods),
        }

    async def _aggregate_rainfall(
        self,
        db: AsyncSession,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(RainfallRecord).where(
                RainfallRecord.collection_time >= start_dt,
                RainfallRecord.collection_time <= end_dt,
            )
        )
        records = result.scalars().all()
        if not records:
            return {"records_count": 0, "total_rainfall": 0.0}

        # Daily max of daily_rainfall per device per day is a good enough guess if data is periodic
        # But let's just use hourly_rainfall sum if available
        hourly = [r.hourly_rainfall for r in records if r.hourly_rainfall is not None]

        return {
            "records_count": len(records),
            "total_rainfall": round(sum(hourly), 2) if hourly else 0.0,
        }

    async def _aggregate_runoff(
        self,
        db: AsyncSession,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(RunoffRecord).where(
                RunoffRecord.collection_time >= start_dt,
                RunoffRecord.collection_time <= end_dt,
            )
        )
        records = result.scalars().all()
        if not records:
            return {"records_count": 0}

        flows = [r.flow_rate for r in records if r.flow_rate is not None]
        levels = [r.water_level for r in records if r.water_level is not None]

        return {
            "records_count": len(records),
            "avg_flow_rate": _safe_avg(flows),
            "avg_water_level": _safe_avg(levels),
            "max_flow_rate": _round_or_none(max(flows)) if flows else None,
        }

    # ------------------------------------------------------------------
    # Excel export
    # ------------------------------------------------------------------

    async def generate_excel(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
    ) -> bytes:
        """Create a multi-sheet Excel workbook and return the raw bytes."""
        summary = await self._build_summary(db, start_date, end_date)
        start_dt, end_dt = _date_range_bounds(start_date, end_date)

        # Fetch raw records for detail sheets
        weather_res = await db.execute(
            select(WeatherRecord).where(
                WeatherRecord.collection_time >= start_dt,
                WeatherRecord.collection_time <= end_dt,
            ).order_by(WeatherRecord.collection_time)
        )
        weather_records = weather_res.scalars().all()

        insect_res = await db.execute(
            select(InsectRecord).where(
                InsectRecord.collection_time >= start_dt,
                InsectRecord.collection_time <= end_dt,
            ).order_by(InsectRecord.collection_time)
        )
        insect_records = insect_res.scalars().all()

        soil_res = await db.execute(
            select(SoilRecord).where(
                SoilRecord.collection_time >= start_dt,
                SoilRecord.collection_time <= end_dt,
            ).order_by(SoilRecord.collection_time)
        )
        soil_records = soil_res.scalars().all()

        wb = Workbook()

        # Remove default sheet
        default_sheet = wb.active
        wb.remove(default_sheet)

        self._write_summary_sheet(wb, summary)
        self._write_insect_sheet(wb, insect_records)
        self._write_weather_sheet(wb, weather_records)
        self._write_soil_sheet(wb, soil_records)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Excel sheet writers
    # ------------------------------------------------------------------

    @staticmethod
    def _header_fill() -> PatternFill:
        return PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")

    @staticmethod
    def _sub_header_fill() -> PatternFill:
        return PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")

    @staticmethod
    def _header_font() -> Font:
        return Font(name="微软雅黑", bold=True, color="FFFFFF", size=11)

    @staticmethod
    def _title_font() -> Font:
        return Font(name="微软雅黑", bold=True, color="FFFFFF", size=13)

    @staticmethod
    def _label_font() -> Font:
        return Font(name="微软雅黑", bold=True, color="1F4E79", size=10)

    @staticmethod
    def _value_font() -> Font:
        return Font(name="微软雅黑", size=10)

    @staticmethod
    def _thin_border() -> Border:
        side = Side(style="thin", color="BFBFBF")
        return Border(left=side, right=side, top=side, bottom=side)

    @staticmethod
    def _center_align() -> Alignment:
        return Alignment(horizontal="center", vertical="center", wrap_text=True)

    def _write_title_row(
        self,
        ws,
        title: str,
        col_span: int,
        row: int = 1,
    ) -> None:
        ws.cell(row=row, column=1, value=title).font = self._title_font()
        ws.cell(row=row, column=1).fill = PatternFill(
            start_color="1F4E79", end_color="1F4E79", fill_type="solid"
        )
        ws.cell(row=row, column=1).alignment = self._center_align()
        ws.merge_cells(
            start_row=row, start_column=1, end_row=row, end_column=col_span
        )

    def _apply_header_row(self, ws, headers: list[str], row: int) -> None:
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = self._header_font()
            cell.fill = self._sub_header_fill()
            cell.alignment = self._center_align()
            cell.border = self._thin_border()

    def _write_summary_sheet(self, wb: Workbook, summary: dict) -> None:
        ws = wb.create_sheet("综合汇总")
        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 18

        period = summary["period"]
        title = (
            f"三亚市天涯区橡胶林近自然化改造和农田提升监测平台  "
            f"监测报告 {period['start']} 至 {period['end']}"
        )
        self._write_title_row(ws, title, 4, row=1)
        ws.row_dimensions[1].height = 28

        # ---- Weather section ----
        row = 3
        ws.cell(row=row, column=1, value="【气象概况】").font = self._label_font()
        ws.cell(row=row, column=1).fill = PatternFill(
            start_color="DEEAF1", end_color="DEEAF1", fill_type="solid"
        )
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1

        w = summary["weather"]
        weather_rows = [
            ("平均温度 (°C)", w["avg_temp"], "最高温度 (°C)", w["max_temp"]),
            ("最低温度 (°C)", w["min_temp"], "平均湿度 (%)", w["avg_humidity"]),
            ("累计降雨量 (mm)", w["total_rainfall"], "气象记录条数", w["records_count"]),
        ]
        for label_a, val_a, label_b, val_b in weather_rows:
            ws.cell(row=row, column=1, value=label_a).font = self._label_font()
            ws.cell(row=row, column=2, value=val_a if val_a is not None else "—").font = self._value_font()
            ws.cell(row=row, column=3, value=label_b).font = self._label_font()
            ws.cell(row=row, column=4, value=val_b if val_b is not None else "—").font = self._value_font()
            for col in range(1, 5):
                ws.cell(row=row, column=col).border = self._thin_border()
                ws.cell(row=row, column=col).alignment = self._center_align()
            row += 1

        # ---- Soil section ----
        row += 1
        ws.cell(row=row, column=1, value="【土壤墒情】").font = self._label_font()
        ws.cell(row=row, column=1).fill = PatternFill(
            start_color="DEEAF1", end_color="DEEAF1", fill_type="solid"
        )
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1

        s = summary["soil"]
        soil_rows = [
            ("10cm 平均墒情 (%)", s["avg_moisture_10cm"], "20cm 平均墒情 (%)", s["avg_moisture_20cm"]),
            ("40cm 平均墒情 (%)", s["avg_moisture_40cm"], "墒情记录条数", s["records_count"]),
        ]
        for label_a, val_a, label_b, val_b in soil_rows:
            ws.cell(row=row, column=1, value=label_a).font = self._label_font()
            ws.cell(row=row, column=2, value=val_a if val_a is not None else "—").font = self._value_font()
            ws.cell(row=row, column=3, value=label_b).font = self._label_font()
            ws.cell(row=row, column=4, value=val_b if val_b is not None else "—").font = self._value_font()
            for col in range(1, 5):
                ws.cell(row=row, column=col).border = self._thin_border()
                ws.cell(row=row, column=col).alignment = self._center_align()
            row += 1

        # ---- Insect section ----
        row += 1
        ws.cell(row=row, column=1, value="【虫情测报】").font = self._label_font()
        ws.cell(row=row, column=1).fill = PatternFill(
            start_color="DEEAF1", end_color="DEEAF1", fill_type="solid"
        )
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1

        ins = summary["insect"]
        ws.cell(row=row, column=1, value="捕获总数 (只)").font = self._label_font()
        ws.cell(row=row, column=2, value=ins["total_count"]).font = self._value_font()
        ws.cell(row=row, column=3, value="记录条数").font = self._label_font()
        ws.cell(row=row, column=4, value=ins["records_count"]).font = self._value_font()
        for col in range(1, 5):
            ws.cell(row=row, column=col).border = self._thin_border()
            ws.cell(row=row, column=col).alignment = self._center_align()
        row += 1

        if ins["top_species"]:
            ws.cell(row=row, column=1, value="主要虫种统计").font = self._label_font()
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
            ws.cell(row=row, column=1).alignment = self._center_align()
            row += 1
            for name, count in ins["top_species"]:
                ws.cell(row=row, column=1, value=name).font = self._value_font()
                ws.cell(row=row, column=2, value=count).font = self._value_font()
                ws.cell(row=row, column=1).border = self._thin_border()
                ws.cell(row=row, column=2).border = self._thin_border()
                ws.cell(row=row, column=1).alignment = self._center_align()
                ws.cell(row=row, column=2).alignment = self._center_align()
                row += 1

        # ---- Spore section ----
        row += 1
        ws.cell(row=row, column=1, value="【孢子捕捉】").font = self._label_font()
        ws.cell(row=row, column=1).fill = PatternFill(
            start_color="DEEAF1", end_color="DEEAF1", fill_type="solid"
        )
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1

        sp = summary["spore"]
        ws.cell(row=row, column=1, value="孢子总数 (个)").font = self._label_font()
        ws.cell(row=row, column=2, value=sp["total_count"]).font = self._value_font()
        ws.cell(row=row, column=3, value="记录条数").font = self._label_font()
        ws.cell(row=row, column=4, value=sp["records_count"]).font = self._value_font()
        for col in range(1, 5):
            ws.cell(row=row, column=col).border = self._thin_border()
            ws.cell(row=row, column=col).alignment = self._center_align()

    def _write_insect_sheet(self, wb: Workbook, records: list[InsectRecord]) -> None:
        ws = wb.create_sheet("虫情数据")
        headers = ["采集时间", "设备编号", "捕获数量 (只)", "主要虫种"]
        for col_idx, w in enumerate([22, 24, 16, 40], start=1):
            ws.column_dimensions[
                ws.cell(row=1, column=col_idx).column_letter
            ].width = w

        self._write_title_row(ws, "虫情测报详细数据", len(headers), row=1)
        ws.row_dimensions[1].height = 24
        self._apply_header_row(ws, headers, row=2)

        for row_idx, r in enumerate(records, start=3):
            top = sorted(
                (r.species_data or {}).items(), key=lambda x: x[1], reverse=True
            )[:3]
            species_str = "  ".join(f"{n}:{c}" for n, c in top) if top else "—"
            row_data = [
                r.collection_time.strftime("%Y-%m-%d %H:%M"),
                r.device_code,
                r.total_count,
                species_str,
            ]
            for col_idx, val in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = self._value_font()
                cell.border = self._thin_border()
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if row_idx % 2 == 0:
                for col_idx in range(1, len(headers) + 1):
                    ws.cell(row=row_idx, column=col_idx).fill = PatternFill(
                        start_color="EBF3FB", end_color="EBF3FB", fill_type="solid"
                    )

    def _write_weather_sheet(
        self, wb: Workbook, records: list[WeatherRecord]
    ) -> None:
        ws = wb.create_sheet("气象数据")
        headers = [
            "采集时间", "设备编号", "温度 (°C)", "湿度 (%)",
            "风速 (m/s)", "风向", "降雨量 (mm)", "气压 (hPa)", "光照 (lux)",
        ]
        col_widths = [22, 14, 12, 12, 12, 10, 14, 12, 14]
        for col_idx, w in enumerate(col_widths, start=1):
            ws.column_dimensions[
                ws.cell(row=1, column=col_idx).column_letter
            ].width = w

        self._write_title_row(ws, "气象数据详细记录", len(headers), row=1)
        ws.row_dimensions[1].height = 24
        self._apply_header_row(ws, headers, row=2)

        for row_idx, r in enumerate(records, start=3):
            row_data = [
                r.collection_time.strftime("%Y-%m-%d %H:%M"),
                r.device_code,
                r.temperature,
                r.humidity,
                r.wind_speed,
                r.wind_direction or "—",
                r.rainfall,
                r.pressure,
                r.light,
            ]
            for col_idx, val in enumerate(row_data, start=1):
                cell = ws.cell(
                    row=row_idx,
                    column=col_idx,
                    value=val if val is not None else "—",
                )
                cell.font = self._value_font()
                cell.border = self._thin_border()
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if row_idx % 2 == 0:
                for col_idx in range(1, len(headers) + 1):
                    ws.cell(row=row_idx, column=col_idx).fill = PatternFill(
                        start_color="EBF3FB", end_color="EBF3FB", fill_type="solid"
                    )

    def _write_soil_sheet(self, wb: Workbook, records: list[SoilRecord]) -> None:
        ws = wb.create_sheet("墒情数据")
        headers = [
            "采集时间", "设备编号",
            "10cm 墒情 (%)", "20cm 墒情 (%)", "40cm 墒情 (%)",
            "10cm 地温 (°C)",
        ]
        col_widths = [22, 14, 16, 16, 16, 16]
        for col_idx, w in enumerate(col_widths, start=1):
            ws.column_dimensions[
                ws.cell(row=1, column=col_idx).column_letter
            ].width = w

        self._write_title_row(ws, "土壤墒情详细数据", len(headers), row=1)
        ws.row_dimensions[1].height = 24
        self._apply_header_row(ws, headers, row=2)

        for row_idx, r in enumerate(records, start=3):
            row_data = [
                r.collection_time.strftime("%Y-%m-%d %H:%M"),
                r.device_code,
                r.moisture_10cm,
                r.moisture_20cm,
                r.moisture_40cm,
                r.temperature_10cm,
            ]
            for col_idx, val in enumerate(row_data, start=1):
                cell = ws.cell(
                    row=row_idx,
                    column=col_idx,
                    value=val if val is not None else "—",
                )
                cell.font = self._value_font()
                cell.border = self._thin_border()
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if row_idx % 2 == 0:
                for col_idx in range(1, len(headers) + 1):
                    ws.cell(row=row_idx, column=col_idx).fill = PatternFill(
                        start_color="EBF3FB", end_color="EBF3FB", fill_type="solid"
                    )

    # ------------------------------------------------------------------
    # HTML report
    # ------------------------------------------------------------------

    @staticmethod
    def _render_ai_html(text: str) -> str:
        """Convert AI markdown output (## / ### / **1.1 bold** / **bold**) to HTML."""
        import re
        # Pattern: line is ONLY **x.x 小节名** (subsection heading style)
        _subsection_re = re.compile(r"^\*\*(\d+\.\d+\s+[^*]+)\*\*$")
        lines = text.split("\n")
        html_lines: list[str] = []
        in_para = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_para:
                    html_lines.append("</p>")
                    in_para = False
                continue
            # Chapter heading  ## 一、xxx
            if stripped.startswith("## "):
                if in_para:
                    html_lines.append("</p>")
                    in_para = False
                content = stripped[3:].strip()
                content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
                html_lines.append(f'<h2 class="ai-h2">{content}</h2>')
            # Sub-section  ### xxx
            elif stripped.startswith("### "):
                if in_para:
                    html_lines.append("</p>")
                    in_para = False
                content = stripped[4:].strip()
                content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
                html_lines.append(f'<h3 class="ai-h3">{content}</h3>')
            # Sub-section heading style: **1.1 小节名**  (entire line is bold subsection)
            elif _subsection_re.match(stripped):
                if in_para:
                    html_lines.append("</p>")
                    in_para = False
                content = _subsection_re.match(stripped).group(1).strip()
                html_lines.append(f'<h3 class="ai-h3">{content}</h3>')
            # Bullet
            elif stripped.startswith(("- ", "• ", "* ")):
                if in_para:
                    html_lines.append("</p>")
                    in_para = False
                content = stripped[2:].strip()
                content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
                html_lines.append(f'<li>{content}</li>')
            else:
                content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                if not in_para:
                    html_lines.append("<p>")
                    in_para = True
                else:
                    html_lines.append(" ")
                html_lines.append(content)
        if in_para:
            html_lines.append("</p>")
        return "\n".join(html_lines)

    @staticmethod
    def generate_html_report(
        summary_dict: dict,
        ai_analysis: str | None = None,
        charts: dict | None = None,
        ai_images: dict | None = None,
        figure_manifest: list[dict[str, Any]] | None = None,
    ) -> str:
        """Render *summary_dict* as a professional self-contained HTML report.

        Args:
            summary_dict: Aggregated data from ReportService.
            ai_analysis:  Pre-generated AI analysis text (markdown).
            charts:       Dict of chart_name → base64 PNG string (from chart_service).
            ai_images:    Dict from gemini_image_service.generate_report_images().
        """
        charts = charts or {}
        ai_images = ai_images or {}
        figure_manifest = figure_manifest or build_figure_manifest(summary_dict, charts, ai_images)

        period = summary_dict.get("period", {})
        start_str = period.get("start", "")
        end_str = period.get("end", "")

        try:
            s = datetime.strptime(start_str, "%Y-%m-%d").date()
            e = datetime.strptime(end_str, "%Y-%m-%d").date()
            span = (e - s).days + 1
            report_type = "周报" if span <= 7 else ("月报" if span <= 31 else "自定义报告")
        except (ValueError, TypeError):
            report_type = "自定义报告"

        ai_html = ReportService._render_ai_html(ai_analysis) if ai_analysis else ""

        # Gemini AI images
        cover_img_src = ai_images.get("cover")

        def _v(val, unit: str = "", fallback: str = "—") -> str:
            if val is None:
                return fallback
            return f"{val}{unit}"

        w = summary_dict.get("weather", {})
        s = summary_dict.get("soil", {})
        ins = summary_dict.get("insect", {})
        sp = summary_dict.get("spore", {})

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Cover background style (Gemini-generated image)
        cover_style = (
            f'style="background-image:linear-gradient(160deg,rgba(13,33,55,0.82) 0%,'
            f'rgba(10,61,98,0.72) 55%,rgba(16,78,139,0.80) 100%),'
            f'url(\'{cover_img_src}\');background-size:cover;background-position:center;"'
            if cover_img_src else ""
        )

        def _is_pest_figure(item: dict[str, Any]) -> bool:
            return item["html_id"].startswith("fig-pest-")

        def _render_standard_figure(item: dict[str, Any]) -> str:
            tag_html = (
                f'&nbsp;<span class="gemini-tag">{item["tag"]}</span>'
                if item.get("tag")
                else ""
            )
            class_name = "chart-figure ai-img-figure" if item["source"] == "ai" else "chart-figure"
            return (
                f'<figure class="{class_name}" id="{item["html_id"]}">'
                f'<img src="{item["src"]}" alt="{item["caption"]}" />'
                f'<figcaption>图{item["number"]}&nbsp;&nbsp;{item["caption"]}{tag_html}</figcaption>'
                f'</figure>'
            )

        def _render_section_figures(section: str) -> str:
            return "".join(
                _render_standard_figure(item)
                for item in figure_manifest
                if item["section"] == section and not _is_pest_figure(item)
            )

        def _render_pest_gallery() -> str:
            cards = []
            for item in figure_manifest:
                if item["section"] != "insect" or not _is_pest_figure(item):
                    continue
                tag_html = (
                    f'&nbsp;<span class="gemini-tag">{item["tag"]}</span>'
                    if item.get("tag")
                    else ""
                )
                cards.append(
                    f'<figure class="pest-card" id="{item["html_id"]}">'
                    f'<img src="{item["src"]}" alt="{item["caption"]}" />'
                    f'<figcaption>图{item["number"]}&nbsp;&nbsp;{item["caption"]}{tag_html}</figcaption>'
                    f'</figure>'
                )
            if not cards:
                return ""
            return f'<div class="pest-gallery">{"".join(cards)}</div>'

        pest_gallery = _render_pest_gallery()

        # ----------------------------------------------------------------
        # Build HTML sections
        # ----------------------------------------------------------------

        # Section 2: Weather
        sec_weather = f"""
<section class="report-section" id="sec-weather">
  <h2 class="sec-title"><span class="sec-num">二</span>气象数据监测</h2>
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">监测记录</div>
      <div class="kpi-value">{_v(w.get('records_count'))}<span class="kpi-unit">条</span></div>
    </div>
    <div class="kpi-card kpi-warm">
      <div class="kpi-label">平均气温</div>
      <div class="kpi-value">{_v(w.get('avg_temp'), '°C')}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">最高气温</div>
      <div class="kpi-value">{_v(w.get('max_temp'), '°C')}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">最低气温</div>
      <div class="kpi-value">{_v(w.get('min_temp'), '°C')}</div>
    </div>
    <div class="kpi-card kpi-blue">
      <div class="kpi-label">平均湿度</div>
      <div class="kpi-value">{_v(w.get('avg_humidity'), '%')}</div>
    </div>
    <div class="kpi-card kpi-blue">
      <div class="kpi-label">累计降雨量</div>
      <div class="kpi-value">{_v(w.get('total_rainfall'), 'mm', '0mm')}</div>
    </div>
  </div>
  {_render_section_figures('weather')}
</section>"""

        # Section 3: Soil
        sec_soil = f"""
<section class="report-section" id="sec-soil">
  <h2 class="sec-title"><span class="sec-num">三</span>土壤墒情监测</h2>
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">监测记录</div>
      <div class="kpi-value">{_v(s.get('records_count'))}<span class="kpi-unit">条</span></div>
    </div>
    <div class="kpi-card kpi-green">
      <div class="kpi-label">10 cm 平均墒情</div>
      <div class="kpi-value">{_v(s.get('avg_moisture_10cm'), '%')}</div>
    </div>
    <div class="kpi-card kpi-green">
      <div class="kpi-label">20 cm 平均墒情</div>
      <div class="kpi-value">{_v(s.get('avg_moisture_20cm'), '%')}</div>
    </div>
    <div class="kpi-card kpi-green">
      <div class="kpi-label">40 cm 平均墒情</div>
      <div class="kpi-value">{_v(s.get('avg_moisture_40cm'), '%')}</div>
    </div>
  </div>
  {_render_section_figures('soil')}
</section>"""

        # Section 4: Insect
        species_rows = "".join(
            f"<tr><td>{item[0]}</td><td class='num'>{item[1]}</td>"
            f"<td class='num'>{item[1] / max(ins.get('total_count', 1), 1) * 100:.1f}%</td></tr>"
            for item in (ins.get("top_species") or [])
        )
        species_table = f"""
<div class="table-wrap">
  <table class="data-table">
    <caption>主要虫种捕获统计</caption>
    <thead><tr><th>虫种名称</th><th>捕获数量（只）</th><th>占比</th></tr></thead>
    <tbody>{species_rows}</tbody>
  </table>
</div>""" if species_rows else ""

        sec_insect = f"""
<section class="report-section" id="sec-insect">
  <h2 class="sec-title"><span class="sec-num">四</span>虫情测报监测</h2>
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">监测记录</div>
      <div class="kpi-value">{_v(ins.get('records_count'))}<span class="kpi-unit">条</span></div>
    </div>
    <div class="kpi-card kpi-warn">
      <div class="kpi-label">期间捕获总数</div>
      <div class="kpi-value">{_v(ins.get('total_count', 0))}<span class="kpi-unit">只</span></div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">记录虫种数</div>
      <div class="kpi-value">{len(ins.get('top_species') or [])}<span class="kpi-unit">种</span></div>
    </div>
  </div>
  {_render_section_figures('insect')}
  {species_table}
  {pest_gallery}
</section>"""

        # Section 5: Spore
        sec_spore = f"""
<section class="report-section" id="sec-spore">
  <h2 class="sec-title"><span class="sec-num">五</span>孢子捕捉监测</h2>
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">监测记录</div>
      <div class="kpi-value">{_v(sp.get('records_count'))}<span class="kpi-unit">条</span></div>
    </div>
    <div class="kpi-card kpi-purple">
      <div class="kpi-label">期间捕获总数</div>
      <div class="kpi-value">{_v(sp.get('total_count', 0))}<span class="kpi-unit">个</span></div>
    </div>
  </div>
  {_render_section_figures('spore')}
</section>"""

        # Section 6: AI
        if ai_html:
            ai_body = f'<div class="ai-body">{ai_html}</div>'
        else:
            ai_body = '<div class="ai-placeholder"><strong>AI 智能分析</strong>（配置 DEEPSEEK_API_KEY 后自动生成完整分析报告）</div>'

        sec_ai = f"""
<section class="report-section ai-section" id="sec-ai">
  <h2 class="sec-title"><span class="sec-num">六</span>AI 智能综合分析报告
    <span class="ai-badge">DeepSeek</span>
  </h2>
  {ai_body}
</section>"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>三亚市天涯区橡胶林近自然化改造和农田提升监测平台 — {report_type}</title>
  <style>
/* ============================================================
   全局重置与基础
   ============================================================ */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Helvetica Neue", sans-serif;
  font-size: 14px;
  line-height: 1.8;
  background: #F4F6F9;
  color: #2C3E50;
  min-height: 100vh;
}}

/* ============================================================
   封面页
   ============================================================ */
.cover {{
  background: linear-gradient(160deg, #0d2137 0%, #0a3d62 55%, #104e8b 100%);
  color: #fff;
  min-height: 320px;
  padding: 60px 80px 50px;
  position: relative;
  overflow: hidden;
  page-break-after: always;
}}
.cover::before {{
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 15% 40%, rgba(255,255,255,0.04) 0%, transparent 50%),
    radial-gradient(circle at 85% 20%, rgba(88,166,255,0.08) 0%, transparent 40%);
  pointer-events: none;
}}
.cover-platform {{
  font-size: 13px;
  letter-spacing: 4px;
  color: #79c0ff;
  text-transform: uppercase;
  margin-bottom: 20px;
  position: relative;
}}
.cover-title {{
  font-size: 36px;
  font-weight: 900;
  letter-spacing: 2px;
  line-height: 1.25;
  color: #fff;
  position: relative;
  margin-bottom: 12px;
}}
.cover-subtitle {{
  font-size: 18px;
  font-weight: 400;
  color: #a5d6ff;
  letter-spacing: 2px;
  position: relative;
  margin-bottom: 36px;
}}
.cover-meta {{
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  position: relative;
}}
.cover-meta-item {{
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 8px;
  padding: 10px 20px;
}}
.cover-meta-label {{
  font-size: 11px;
  color: #79c0ff;
  letter-spacing: 2px;
  margin-bottom: 4px;
}}
.cover-meta-value {{
  font-size: 15px;
  font-weight: 700;
  color: #e6edf3;
  letter-spacing: 1px;
}}
.cover-divider {{
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #1f6aa5, #58a6ff, #1f6aa5);
}}

/* ============================================================
   目录
   ============================================================ */
.toc-section {{
  background: #fff;
  max-width: 900px;
  margin: 32px auto 0;
  border-radius: 12px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.07);
  padding: 32px 40px;
}}
.toc-title {{
  font-size: 16px;
  font-weight: 700;
  color: #1a5276;
  border-bottom: 2px solid #2E86C1;
  padding-bottom: 10px;
  margin-bottom: 18px;
  letter-spacing: 2px;
}}
.toc-list {{
  list-style: none;
}}
.toc-list li {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 6px 0;
  border-bottom: 1px dashed #DDDDDD;
  font-size: 14px;
}}
.toc-list li:last-child {{ border-bottom: none; }}
.toc-list a {{
  color: #2C3E50;
  text-decoration: none;
  font-weight: 500;
}}
.toc-list a:hover {{ color: #2E86C1; }}
.toc-num {{
  color: #2E86C1;
  font-weight: 700;
  margin-right: 8px;
  min-width: 24px;
  display: inline-block;
}}

/* ============================================================
   报告主体
   ============================================================ */
.report-body {{
  max-width: 900px;
  margin: 28px auto 60px;
  padding: 0 16px;
}}

/* ============================================================
   章节
   ============================================================ */
.report-section {{
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.07);
  margin-bottom: 28px;
  overflow: hidden;
}}

.sec-title {{
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(90deg, #1a5276, #2E86C1);
  padding: 16px 28px;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 10px;
}}
.sec-num {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255,255,255,0.25);
  font-size: 13px;
  font-weight: 900;
  flex-shrink: 0;
}}

/* ============================================================
   概述卡片（Section 1）
   ============================================================ */
.overview-section .sec-title {{
  background: linear-gradient(90deg, #1a5276, #2471a3);
}}
.overview-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1px;
  background: #eee;
  margin: 0;
}}
.overview-item {{
  background: #fff;
  padding: 20px 24px;
  text-align: center;
}}
.overview-label {{
  font-size: 11px;
  color: #7F8C8D;
  letter-spacing: 1px;
  margin-bottom: 8px;
  text-transform: uppercase;
}}
.overview-value {{
  font-size: 28px;
  font-weight: 900;
  color: #2C3E50;
}}
.overview-unit {{
  font-size: 13px;
  color: #7F8C8D;
  margin-left: 2px;
  font-weight: 400;
}}

/* ============================================================
   KPI 卡片行
   ============================================================ */
.kpi-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 20px 24px;
  background: #F8FAFC;
  border-bottom: 1px solid #EFEFEF;
}}
.kpi-card {{
  background: #fff;
  border: 1px solid #E8EDF2;
  border-radius: 10px;
  padding: 14px 20px;
  min-width: 120px;
  flex: 1;
  border-top: 3px solid #2E86C1;
}}
.kpi-card.kpi-warm  {{ border-top-color: #E67E22; }}
.kpi-card.kpi-green {{ border-top-color: #28B463; }}
.kpi-card.kpi-blue  {{ border-top-color: #2980B9; }}
.kpi-card.kpi-warn  {{ border-top-color: #C0392B; }}
.kpi-card.kpi-purple {{ border-top-color: #8E44AD; }}

.kpi-label {{
  font-size: 11px;
  color: #7F8C8D;
  letter-spacing: 1px;
  margin-bottom: 6px;
}}
.kpi-value {{
  font-size: 22px;
  font-weight: 800;
  color: #2C3E50;
  line-height: 1;
}}
.kpi-unit {{
  font-size: 12px;
  color: #7F8C8D;
  font-weight: 400;
  margin-left: 2px;
}}

/* ============================================================
   图表
   ============================================================ */
.chart-figure {{
  margin: 0 auto;
  padding: 24px 24px 16px;
  border-bottom: 1px solid #F0F0F0;
  display: flex;
  flex-direction: column;
  align-items: center;
}}
.chart-figure img {{
  width: 100%;
  max-width: 860px;
  height: auto;
  display: block;
  border-radius: 8px;
  border: 1px solid #E8EDF2;
}}
.chart-figure figcaption {{
  margin-top: 10px;
  font-size: 13px;
  color: #555;
  text-align: center;
  letter-spacing: 0.5px;
  font-weight: 500;
  width: 100%;
}}
.ai-img-figure img {{
  max-width: 720px;
  border: 1px solid #D5E8F3;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}}

/* ============================================================
   数据表格
   ============================================================ */
.table-wrap {{
  padding: 0 24px 20px;
  overflow-x: auto;
}}
.data-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 12px;
}}
.data-table caption {{
  font-weight: 700;
  color: #1a5276;
  text-align: left;
  padding: 8px 0 6px;
  font-size: 13px;
  letter-spacing: 0.5px;
}}
.data-table th {{
  background: #1a5276;
  color: #fff;
  font-weight: 700;
  padding: 10px 14px;
  text-align: left;
  font-size: 12px;
  letter-spacing: 0.5px;
}}
.data-table td {{
  padding: 8px 14px;
  border-bottom: 1px solid #EFEFEF;
  color: #2C3E50;
  vertical-align: middle;
}}
.data-table td.num {{
  text-align: right;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}}
.data-table tr:nth-child(even) td {{ background: #F8FAFC; }}
.data-table tr:hover td {{ background: #EBF5FB; }}

/* ============================================================
   AI 分析区
   ============================================================ */
.ai-section .sec-title {{
  background: linear-gradient(90deg, #1a3a4a, #1f6aa5);
}}
.ai-badge {{
  margin-left: auto;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 20px;
  padding: 3px 12px;
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 1px;
}}
.ai-body {{
  padding: 28px 36px;
  color: #2C3E50;
  font-size: 14.5px;
  line-height: 2;
}}
.ai-body h2.ai-h2 {{
  font-size: 17px;
  font-weight: 800;
  color: #1a5276;
  margin: 28px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #D6EAF8;
  letter-spacing: 1px;
}}
.ai-body h2.ai-h2:first-child {{ margin-top: 0; }}
.ai-body h3.ai-h3 {{
  font-size: 15px;
  font-weight: 700;
  color: #2E86C1;
  margin: 20px 0 8px;
  padding-left: 10px;
  border-left: 4px solid #2E86C1;
  letter-spacing: 0.5px;
}}
.ai-body p {{
  margin-bottom: 12px;
  text-align: justify;
  text-indent: 2em;
}}
.ai-body li {{
  margin: 6px 0 6px 24px;
  list-style-type: disc;
}}
.ai-body strong {{
  font-weight: 700;
  color: #1a5276;
}}
.ai-placeholder {{
  padding: 40px;
  text-align: center;
  color: #7F8C8D;
  font-size: 14px;
}}
.ai-placeholder strong {{
  display: block;
  font-size: 16px;
  color: #2C3E50;
  margin-bottom: 8px;
}}

/* ============================================================
   页脚
   ============================================================ */
.page-footer {{
  background: #1a5276;
  color: rgba(255,255,255,0.6);
  text-align: center;
  padding: 20px 40px;
  font-size: 12px;
  letter-spacing: 1px;
  margin-top: 40px;
}}
.page-footer strong {{
  color: rgba(255,255,255,0.9);
  font-weight: 600;
}}

/* ============================================================
   Gemini AI 图片样式
   ============================================================ */
.ai-img-figure img {{
  max-width: 720px;
  width: 100%;
  max-height: none;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border: 1px solid #D5E8F3;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}}
.gemini-tag {{
  display: inline-block;
  background: linear-gradient(90deg, #4285F4, #EA4335, #FBBC04, #34A853);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 700;
  font-size: 11px;
}}

/* 虫种图鉴 Gallery */
.pest-gallery {{
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 20px 24px;
  background: #F8FAFC;
  border-top: 1px solid #EFEFEF;
}}
.pest-card {{
  flex: 1;
  min-width: 220px;
  max-width: 320px;
  background: #fff;
  border: 1px solid #E8EDF2;
  border-radius: 10px;
  overflow: hidden;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  align-items: center;
}}
.pest-card img {{
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block;
}}
.pest-card figcaption {{
  font-size: 12px;
  color: #555;
  text-align: center;
  padding: 8px 8px 10px;
  font-weight: 500;
  line-height: 1.4;
}}
.pest-card .pest-name {{
  font-size: 13px;
  font-weight: 700;
  color: #2C3E50;
  padding: 8px 8px 2px;
}}
.pest-card .pest-label {{
  font-size: 10px;
  color: #7F8C8D;
  padding-bottom: 8px;
  letter-spacing: 0.5px;
}}

/* ============================================================
   打印优化
   ============================================================ */
@media print {{
  body {{ background: #fff; }}
  .report-section, .toc-section {{ box-shadow: none; border: 1px solid #ddd; }}
  .sec-title {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .kpi-card {{ border-top-width: 3px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
  </style>
</head>
<body>

<!-- ============================================================
     封面
     ============================================================ -->
<div class="cover" {cover_style}>
  <div class="cover-platform">三亚市天涯区农业农村局 · 智慧农业生态监测平台</div>
  <div class="cover-title">农业生态环境监测报告</div>
  <div class="cover-subtitle">{report_type}</div>
  <div class="cover-meta">
    <div class="cover-meta-item">
      <div class="cover-meta-label">监测起始</div>
      <div class="cover-meta-value">{start_str}</div>
    </div>
    <div class="cover-meta-item">
      <div class="cover-meta-label">监测截止</div>
      <div class="cover-meta-value">{end_str}</div>
    </div>
    <div class="cover-meta-item">
      <div class="cover-meta-label">报告生成时间</div>
      <div class="cover-meta-value">{generated_at}</div>
    </div>
    <div class="cover-meta-item">
      <div class="cover-meta-label">智能分析</div>
      <div class="cover-meta-value">DeepSeek · Gemini</div>
    </div>
  </div>
  <div class="cover-divider"></div>
</div>

<!-- ============================================================
     目录
     ============================================================ -->
<div class="toc-section">
  <div class="toc-title">目 &nbsp; 录</div>
  <ul class="toc-list">
    <li><a href="#sec-overview"><span class="toc-num">一、</span>监测期数据概览</a></li>
    <li><a href="#sec-weather"><span class="toc-num">二、</span>气象数据监测</a></li>
    <li><a href="#sec-soil"><span class="toc-num">三、</span>土壤墒情监测</a></li>
    <li><a href="#sec-insect"><span class="toc-num">四、</span>虫情测报监测</a></li>
    <li><a href="#sec-spore"><span class="toc-num">五、</span>孢子捕捉监测</a></li>
    <li><a href="#sec-ai"><span class="toc-num">六、</span>AI 智能综合分析报告</a></li>
  </ul>
</div>

<!-- ============================================================
     正文
     ============================================================ -->
<div class="report-body">

  <!-- 一、数据概览 -->
  <section class="report-section overview-section" id="sec-overview">
    <h2 class="sec-title"><span class="sec-num">一</span>监测期数据概览</h2>
    <div class="overview-grid">
      <div class="overview-item">
        <div class="overview-label">气象记录</div>
        <div class="overview-value">{_v(w.get('records_count'), '', '0')}<span class="overview-unit">条</span></div>
      </div>
      <div class="overview-item">
        <div class="overview-label">墒情记录</div>
        <div class="overview-value">{_v(s.get('records_count'), '', '0')}<span class="overview-unit">条</span></div>
      </div>
      <div class="overview-item">
        <div class="overview-label">虫情捕获</div>
        <div class="overview-value">{_v(ins.get('total_count', 0))}<span class="overview-unit">只</span></div>
      </div>
      <div class="overview-item">
        <div class="overview-label">孢子捕获</div>
        <div class="overview-value">{_v(sp.get('total_count', 0))}<span class="overview-unit">个</span></div>
      </div>
      <div class="overview-item">
        <div class="overview-label">记录虫种</div>
        <div class="overview-value">{len(ins.get('top_species') or [])}<span class="overview-unit">种</span></div>
      </div>
      <div class="overview-item">
        <div class="overview-label">累计降雨</div>
        <div class="overview-value">{_v(w.get('total_rainfall'), '', '0')}<span class="overview-unit">mm</span></div>
      </div>
    </div>
  </section>

  {sec_weather}
  {sec_soil}
  {sec_insect}
  {sec_spore}
  {sec_ai}

</div><!-- /report-body -->

<footer class="page-footer">
  <strong>三亚市天涯区农业农村局智慧农业生态监测平台</strong>&nbsp;·&nbsp;
  数据来源：天涯区在线监测设备网络&nbsp;·&nbsp;
  报告生成时间：{generated_at}&nbsp;·&nbsp;
  AI 分析由 DeepSeek 提供支持
</footer>

</body>
</html>"""
        return html
