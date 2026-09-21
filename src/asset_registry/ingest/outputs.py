from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from asset_registry.domain.constants import ASSET_TYPES
from asset_registry.domain.validation import ValidAsset
from asset_registry.ingest.pipeline import IngestResult


def write_rejects(path: Path, rejects: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "asset_id",
        "name",
        "asset_type",
        "latitude",
        "longitude",
        "elevation_m",
        "surveyed_on",
        "surveyor",
        "status",
        "condition_score",
        "attribute_json",
        "reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rejects:
            writer.writerow(row)


def write_geojson(path: Path, assets: list[ValidAsset]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for asset in assets:
        properties = asset.as_dict()
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [asset.longitude, asset.latitude],
                },
                "properties": properties,
            }
        )
    document = {
        "type": "FeatureCollection",
        "features": features,
    }
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


def write_summary_report(path: Path, result: IngestResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = _summary_lines(result)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary_lines(result: IngestResult) -> list[str]:
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    assets = result.accepted
    lines = [
        "UTILITY ASSET SURVEY SUMMARY",
        f"Run at: {run_at}",
        f"Source: {result.source}",
        "",
        f"{'Type':<14}{'Surveyed':>10}{'Avg condition':>16}{'Worst asset':>14}",
        "-" * 54,
    ]
    for asset_type in sorted(ASSET_TYPES):
        group = [item for item in assets if item.asset_type == asset_type]
        if not group:
            lines.append(f"{asset_type:<14}{0:>10}{'—':>16}{'—':>14}")
            continue
        average = sum(item.condition_score for item in group) / len(group)
        worst = min(group, key=lambda item: (item.condition_score, item.asset_id))
        lines.append(
            f"{asset_type:<14}{len(group):>10}{average:>16.2f}{worst.asset_id:>14}"
        )

    lats = [item.latitude for item in assets]
    lons = [item.longitude for item in assets]
    lines.extend(["", "Survey extent"])
    if lats:
        lines.extend(
            [
                f"  North: {max(lats):.6f}",
                f"  South: {min(lats):.6f}",
                f"  East:  {max(lons):.6f}",
                f"  West:  {min(lons):.6f}",
            ]
        )
    else:
        lines.append("  No accepted assets.")

    lines.extend(
        [
            "",
            f"Rows read:      {result.rows_read}",
            f"Rows accepted:  {result.rows_accepted}",
            f"Rows rejected:  {result.rows_rejected}",
        ]
    )
    return lines
