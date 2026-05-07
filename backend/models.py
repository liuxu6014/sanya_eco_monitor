from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from time_utils import cn_now_naive


class InsectRecord(Base):
    __tablename__ = "insect_records"
    __table_args__ = (
        Index(
            "ux_insect_records_device_code_collection_time",
            "device_code",
            "collection_time",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str] = mapped_column(String(64), index=True)
    collection_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    species_data: Mapped[dict] = mapped_column(JSON, default=dict)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class SporeRecord(Base):
    __tablename__ = "spore_records"
    __table_args__ = (
        Index(
            "ux_spore_records_device_code_collection_time",
            "device_code",
            "collection_time",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str] = mapped_column(String(64), index=True)
    collection_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    spore_data: Mapped[dict] = mapped_column(JSON, default=dict)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class WaterQualityRecord(Base):
    __tablename__ = "water_quality_records"
    __table_args__ = (
        Index(
            "ux_water_quality_records_device_code_collection_time",
            "device_code",
            "collection_time",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str] = mapped_column(String(64), index=True)
    collection_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    ammonia_nitrogen: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_phosphorus: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_nitrogen: Mapped[float | None] = mapped_column(Float, nullable=True)
    permanganate_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class RainfallRecord(Base):
    __tablename__ = "rainfall_records"
    __table_args__ = (
        Index(
            "ux_rainfall_records_device_code_collection_time",
            "device_code",
            "collection_time",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str] = mapped_column(String(64), index=True)
    collection_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    hourly_rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class RunoffRecord(Base):
    __tablename__ = "runoff_records"
    __table_args__ = (
        Index(
            "ux_runoff_records_device_code_collection_time",
            "device_code",
            "collection_time",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str] = mapped_column(String(64), index=True)
    collection_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    flow_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    flow_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    runoff: Mapped[float | None] = mapped_column(Float, nullable=True)
    sand_content: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquid_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class WaterLevelRecord(Base):
    __tablename__ = "water_level_records"
    __table_args__ = (
        Index(
            "ux_water_level_records_device_code_collection_time",
            "device_code",
            "collection_time",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str] = mapped_column(String(64), index=True)
    collection_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    water_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class CollectLog(Base):
    __tablename__ = "collect_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    records_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(32), index=True)
    period_start: Mapped[str] = mapped_column(String(16), index=True)
    period_end: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(128))
    html_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    docx_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=cn_now_naive, index=True)
    status: Mapped[str] = mapped_column(String(24), default="completed", index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    visible_to_leader: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
