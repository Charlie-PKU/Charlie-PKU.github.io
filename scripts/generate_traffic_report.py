from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "traffic-input"
OUTPUT_DIR = ROOT / "traffic-report"
OUTPUT_CHART = OUTPUT_DIR / "weekly-traffic-trend.svg"
OUTPUT_SUMMARY = OUTPUT_DIR / "weekly-traffic-summary.md"


DATE_KEYS = ("date", "day", "time", "timestamp")
VISITOR_KEYS = ("visitors", "visitor", "unique_visitors", "unique visitors")
VIEW_KEYS = ("pageviews", "page_views", "views", "page views")


@dataclass
class DailyStat:
    day: datetime
    visitors: int
    views: int


def normalize(name: str) -> str:
    return name.strip().lower().replace("-", "_")


def pick_key(fieldnames: Iterable[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {normalize(name): name for name in fieldnames}
    for candidate in candidates:
      key = normalized.get(normalize(candidate))
      if key:
          return key
    return None


def parse_date(value: str) -> datetime:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise ValueError(f"Unsupported date format: {value}") from exc


def parse_int(value: str) -> int:
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return 0
    return int(float(cleaned))


def newest_csv() -> Path:
    csv_files = sorted(INPUT_DIR.glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not csv_files:
        raise FileNotFoundError(
            "No CSV found in traffic-input. Export daily stats from Counter.dev and put the file there."
        )
    return csv_files[0]


def load_daily_stats(path: Path) -> list[DailyStat]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")

        date_key = pick_key(reader.fieldnames, DATE_KEYS)
        visitor_key = pick_key(reader.fieldnames, VISITOR_KEYS)
        view_key = pick_key(reader.fieldnames, VIEW_KEYS)

        if not date_key or not visitor_key or not view_key:
            raise ValueError(
                "CSV header must include date/day plus visitors and pageviews/views columns."
            )

        rows: list[DailyStat] = []
        for row in reader:
            if not row.get(date_key):
                continue
            rows.append(
                DailyStat(
                    day=parse_date(row[date_key]),
                    visitors=parse_int(row.get(visitor_key, "0")),
                    views=parse_int(row.get(view_key, "0")),
                )
            )

    if not rows:
        raise ValueError("CSV contained no usable rows.")
    rows.sort(key=lambda item: item.day)
    return rows


def aggregate_by_week(rows: list[DailyStat]) -> list[DailyStat]:
    weekly: dict[datetime, dict[str, int]] = defaultdict(lambda: {"visitors": 0, "views": 0})
    for row in rows:
        week_start = row.day - timedelta(days=row.day.weekday())
        week_start = datetime(week_start.year, week_start.month, week_start.day)
        weekly[week_start]["visitors"] += row.visitors
        weekly[week_start]["views"] += row.views

    result = [
        DailyStat(day=week, visitors=stats["visitors"], views=stats["views"])
        for week, stats in sorted(weekly.items())
    ]
    return result


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_label(day: datetime) -> str:
    return day.strftime("%Y-%m-%d")


def build_chart(weekly_rows: list[DailyStat]) -> str:
    width = 1120
    height = 620
    margin_left = 92
    margin_right = 42
    margin_top = 92
    margin_bottom = 92
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    max_value = max(max(item.visitors, item.views) for item in weekly_rows)
    if max_value <= 0:
        max_value = 1

    max_value = int(math.ceil(max_value / 10.0) * 10)
    points = max(len(weekly_rows) - 1, 1)

    def x_pos(index: int) -> float:
        return margin_left + (chart_width * index / points)

    def y_pos(value: int) -> float:
        return margin_top + chart_height - (chart_height * value / max_value)

    visitor_points = " ".join(
        f"{x_pos(i):.2f},{y_pos(item.visitors):.2f}" for i, item in enumerate(weekly_rows)
    )
    view_points = " ".join(
        f"{x_pos(i):.2f},{y_pos(item.views):.2f}" for i, item in enumerate(weekly_rows)
    )

    y_ticks = 5
    x_label_step = max(1, math.ceil(len(weekly_rows) / 6))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Weekly traffic trend</title>',
        '<desc id="desc">Line chart of weekly visitors and page views.</desc>',
        '<rect width="100%" height="100%" fill="#f7f2e8" rx="28" ry="28"/>',
        f'<text x="{margin_left}" y="54" font-family="PT Sans Narrow, Arial, sans-serif" font-size="32" font-weight="700" fill="#201d1a">Weekly Traffic Trend</text>',
        f'<text x="{margin_left}" y="82" font-family="PT Serif, Georgia, serif" font-size="18" fill="#6c6257">Visitors and page views aggregated by week</text>',
    ]

    for tick in range(y_ticks + 1):
        value = int(max_value * tick / y_ticks)
        y = y_pos(value)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="#d9d0c4" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 14}" y="{y + 6:.2f}" text-anchor="end" font-family="PT Sans Narrow, Arial, sans-serif" font-size="16" fill="#7b6f62">{value}</text>'
        )

    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{width - margin_right}" y2="{margin_top + chart_height}" stroke="#8b7e70" stroke-width="2"/>'
    )
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" stroke="#8b7e70" stroke-width="2"/>'
    )

    for index, row in enumerate(weekly_rows):
        if index % x_label_step != 0 and index != len(weekly_rows) - 1:
            continue
        x = x_pos(index)
        parts.append(
            f'<text x="{x:.2f}" y="{height - 34}" text-anchor="middle" font-family="PT Sans Narrow, Arial, sans-serif" font-size="15" fill="#7b6f62">{svg_escape(format_label(row.day))}</text>'
        )

    parts.append(
        f'<polyline fill="none" stroke="#c4682d" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{visitor_points}"/>'
    )
    parts.append(
        f'<polyline fill="none" stroke="#2d6a8c" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{view_points}"/>'
    )

    for index, row in enumerate(weekly_rows):
        x = x_pos(index)
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y_pos(row.visitors):.2f}" r="4.5" fill="#c4682d" />'
        )
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y_pos(row.views):.2f}" r="4.5" fill="#2d6a8c" />'
        )

    legend_y = height - 64
    parts.extend(
        [
            f'<circle cx="{margin_left}" cy="{legend_y}" r="7" fill="#c4682d"/>',
            f'<text x="{margin_left + 16}" y="{legend_y + 6}" font-family="PT Sans Narrow, Arial, sans-serif" font-size="18" fill="#201d1a">Visitors</text>',
            f'<circle cx="{margin_left + 136}" cy="{legend_y}" r="7" fill="#2d6a8c"/>',
            f'<text x="{margin_left + 152}" y="{legend_y + 6}" font-family="PT Sans Narrow, Arial, sans-serif" font-size="18" fill="#201d1a">Page views</text>',
        ]
    )

    parts.append("</svg>")
    return "\n".join(parts)


def change_text(current: int, previous: int) -> str:
    delta = current - previous
    if previous == 0:
        return f"{current} (new baseline)"
    percentage = delta / previous * 100
    direction = "up" if delta >= 0 else "down"
    return f"{current} ({direction} {abs(delta)}, {abs(percentage):.1f}%)"


def build_summary(source: Path, weekly_rows: list[DailyStat]) -> str:
    latest = weekly_rows[-1]
    previous = weekly_rows[-2] if len(weekly_rows) > 1 else None

    lines = [
        "# Weekly Traffic Summary",
        "",
        f"- Source file: `{source.name}`",
        f"- Weekly periods covered: {len(weekly_rows)}",
        f"- Latest week: `{format_label(latest.day)}`",
        f"- Latest visitors: `{latest.visitors}`",
        f"- Latest page views: `{latest.views}`",
    ]

    if previous:
        lines.extend(
            [
                f"- Visitor trend vs previous week: `{change_text(latest.visitors, previous.visitors)}`",
                f"- Page-view trend vs previous week: `{change_text(latest.views, previous.views)}`",
            ]
        )

    peak_visitors = max(weekly_rows, key=lambda row: row.visitors)
    peak_views = max(weekly_rows, key=lambda row: row.views)
    lines.extend(
        [
            f"- Peak visitors week: `{format_label(peak_visitors.day)}` with `{peak_visitors.visitors}` visitors",
            f"- Peak views week: `{format_label(peak_views.day)}` with `{peak_views.views}` page views",
            "",
            "## Files",
            "",
            f"- Chart: `{OUTPUT_CHART.name}`",
            f"- Summary: `{OUTPUT_SUMMARY.name}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    source = newest_csv()
    daily_rows = load_daily_stats(source)
    weekly_rows = aggregate_by_week(daily_rows)

    OUTPUT_CHART.write_text(build_chart(weekly_rows), encoding="utf-8")
    OUTPUT_SUMMARY.write_text(build_summary(source, weekly_rows), encoding="utf-8")

    print(f"Wrote {OUTPUT_CHART}")
    print(f"Wrote {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
