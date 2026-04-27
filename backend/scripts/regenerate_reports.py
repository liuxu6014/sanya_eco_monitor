from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from database import AsyncSessionLocal
from models import GeneratedReport
from routers.report import generate_managed_report


@dataclass(frozen=True)
class ReportSpec:
    report_type: str
    period_start: str
    period_end: str


def _candidate_local_paths(stored_path: str | None) -> list[Path]:
    if not stored_path:
        return []

    candidates: list[Path] = []
    raw = Path(stored_path)
    candidates.append(raw)

    basename = raw.name
    if basename:
        candidates.append(BACKEND_DIR / "data" / "reports" / basename)

    deduped: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        key = str(item.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _remove_report_files(report: GeneratedReport) -> list[str]:
    removed: list[str] = []
    for stored_path in (report.html_path, report.docx_path):
        for candidate in _candidate_local_paths(stored_path):
            try:
                resolved = candidate.resolve(strict=False)
            except OSError:
                continue

            reports_dir = (BACKEND_DIR / "data" / "reports").resolve(strict=False)
            try:
                resolved.relative_to(reports_dir)
            except ValueError:
                continue

            if not resolved.exists():
                continue
            resolved.unlink()
            removed.append(str(resolved))
            break
    return removed


async def _load_existing_reports() -> list[GeneratedReport]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GeneratedReport).order_by(
                GeneratedReport.created_at.desc(),
                GeneratedReport.id.desc(),
            )
        )
        return list(result.scalars().all())


async def _generate_specs(specs: list[ReportSpec]) -> list[GeneratedReport]:
    created_ids: list[int] = []
    async with AsyncSessionLocal() as session:
        for spec in specs:
            print(
                f"Generating {spec.report_type} report for "
                f"{spec.period_start}..{spec.period_end}"
            )
            await generate_managed_report(
                report_type=spec.report_type,
                end=spec.period_end,
                db=session,
            )

        result = await session.execute(
            select(GeneratedReport).order_by(
                GeneratedReport.created_at.desc(),
                GeneratedReport.id.desc(),
            )
        )
        rows = list(result.scalars().all())
        for row in rows:
            if row.id not in created_ids:
                created_ids.append(row.id)
            if len(created_ids) == len(specs):
                break

        created = [row for row in rows if row.id in created_ids]
        created.sort(key=lambda item: item.id)
        return created


async def _cleanup_old_reports(old_reports: list[GeneratedReport]) -> tuple[list[int], list[str]]:
    removed_ids: list[int] = []
    removed_files: list[str] = []
    async with AsyncSessionLocal() as session:
        for report in old_reports:
            persistent = await session.get(GeneratedReport, report.id)
            if persistent is None:
                continue
            removed_files.extend(_remove_report_files(persistent))
            await session.delete(persistent)
            removed_ids.append(report.id)
        await session.commit()
    return removed_ids, removed_files


async def main(keep_old: bool) -> int:
    old_reports = await _load_existing_reports()
    if not old_reports:
        print("No existing generated reports found.")
        return 0

    specs = [
        ReportSpec(r.report_type, r.period_start, r.period_end)
        for r in old_reports
    ]
    unique_specs = list(dict.fromkeys(specs))

    print("Existing reports:")
    for report in old_reports:
        print(
            f"  old id={report.id} type={report.report_type} "
            f"period={report.period_start}..{report.period_end}"
        )

    created = await _generate_specs(unique_specs)

    print("Created reports:")
    for report in created:
        print(
            f"  new id={report.id} type={report.report_type} "
            f"period={report.period_start}..{report.period_end}"
        )
        print(f"    html={report.html_path}")
        print(f"    docx={report.docx_path}")

    if keep_old:
        print("Keeping old report rows and files.")
        return 0

    removed_ids, removed_files = await _cleanup_old_reports(old_reports)
    print(f"Removed old rows: {removed_ids}")
    for path in removed_files:
        print(f"  removed file: {path}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate existing managed reports.")
    parser.add_argument(
        "--keep-old",
        action="store_true",
        help="Generate fresh reports without deleting the previous rows/files.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(keep_old=args.keep_old)))
