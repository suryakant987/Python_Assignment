from __future__ import annotations

import csv
from pathlib import Path

COLUMNS = [
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
]


def row(**kwargs) -> dict:
    base = {column: "" for column in COLUMNS}
    base.update(kwargs)
    return base


def build_rows() -> list[dict]:
    rows: list[dict] = []

    # --- 51 accepted rows (some deliberately untidy, all recoverable) ---
    poles = [
        row(
            asset_id="pl-0101",
            name="  old  teak  pole  near  market  ",
            asset_type="Pole",
            latitude="20.2961 N",
            longitude="85.8245 E",
            elevation_m="42.0",
            surveyed_on="2026-09-10",
            surveyor="ramesh  patel",
            status="active",
            condition_score="6",
            attribute_json='{"height_m": 9.5, "material": "concrete"}',
        ),
        row(
            asset_id="PL-0102",
            name="feeder pole at jaydev vihar",
            asset_type="POLE",
            latitude="20.3012",
            longitude="85.8190",
            elevation_m="",
            surveyed_on="2026-09-10",
            surveyor="RAMESH PATEL",
            status="Active",
            condition_score="8",
            attribute_json='{"height_m": 11.0, "material": "steel"}',
        ),
        row(
            asset_id="PL-0103",
            name="pole beside school wall",
            asset_type="pole",
            latitude="20.2888 N",
            longitude="85.8311 E",
            elevation_m="39.4",
            surveyed_on="2026-09-11",
            surveyor="Ramesh Patel",
            status="active",
            condition_score="4",
            attribute_json='{"height_m": 8.0, "material": "wood"}',
        ),
    ]
    rows.extend(poles)

    for index in range(4, 21):
        score = (index % 9) + 1
        rows.append(
            row(
                asset_id=f"PL-01{index:02d}",
                name=f"distribution pole {index} nandankanan road",
                asset_type="pole" if index % 2 else "Pole",
                latitude=f"{20.2700 + index * 0.001:.4f}",
                longitude=f"{85.8100 + index * 0.001:.4f}",
                elevation_m="" if index % 5 == 0 else f"{40 + index * 0.1:.1f}",
                surveyed_on="2026-09-11" if index % 2 else "2026-09-12",
                surveyor="anita das" if index % 3 else "Anita Das",
                status="active" if score > 2 else "proposed",
                condition_score=str(score),
                attribute_json='{"height_m": 9.0, "material": "concrete"}',
            )
        )

    for index in range(1, 13):
        score = ((index + 3) % 10)
        rows.append(
            row(
                asset_id=f"VL-02{index:02d}",
                name=f"  isolation  valve  chamber  {index} ",
                asset_type="VALVE" if index % 2 else "valve",
                latitude=f"{20.2500 + index * 0.0015:.4f}",
                longitude=f"{85.8000 + index * 0.0012:.4f}",
                elevation_m=f"{35 + index:.1f}",
                surveyed_on="2026-09-12",
                surveyor="s. mohanty" if index % 2 else "S. Mohanty",
                status="active" if index != 4 else "decommissioned",
                condition_score="1" if index == 4 else str(max(score, 3)),
                attribute_json='{"bore_mm": 150, "turn_direction": "clockwise"}',
            )
        )

    for index in range(1, 11):
        score = 3 + (index % 7)
        rows.append(
            row(
                asset_id=f"MH-03{index:02d}",
                name=f"ug cable chamber {index} saheed nagar",
                asset_type="Manhole",
                latitude=f"{20.3100 + index * 0.0008:.4f}",
                longitude=f"{85.8400 + index * 0.0009:.4f}",
                elevation_m="41.2",
                surveyed_on="2026-09-13",
                surveyor="Bijay Sahu",
                status="active",
                condition_score=str(score),
                attribute_json='{"depth_m": 2.1, "cover_type": "cast_iron"}',
            )
        )

    for index in range(1, 10):
        score = 5 + (index % 6)
        rows.append(
            row(
                asset_id=f"TR-04{index:02d}",
                name=f"distribution transformer {index} patia",
                asset_type="transformer",
                latitude=f"{20.3400 + index * 0.0011:.4f}",
                longitude=f"{85.7900 + index * 0.0013:.4f}",
                elevation_m="48.0",
                surveyed_on="2026-09-14",
                surveyor="Anita Das",
                status="active",
                condition_score=str(min(score, 10)),
                attribute_json='{"kva": 250, "phase": 3}',
            )
        )

    assert len(rows) == 51

    # --- 11 rejected rows covering every known handheld fault ---
    rows.extend(
        [
            row(
                asset_id="PL-0991",
                name="pole with impossible latitude",
                asset_type="pole",
                latitude="120.5000",
                longitude="85.8245",
                elevation_m="40",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="5",
                attribute_json='{"height_m": 9}',
            ),
            row(
                asset_id="PL-0992",
                name="pole with unreadable longitude",
                asset_type="pole",
                latitude="20.2961",
                longitude="east of temple",
                elevation_m="40",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="5",
                attribute_json='{"height_m": 9}',
            ),
            row(
                asset_id="PL-0101",
                name="duplicate of the first pole",
                asset_type="pole",
                latitude="20.2962",
                longitude="85.8246",
                elevation_m="42",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="6",
                attribute_json='{"height_m": 9.5}',
            ),
            row(
                asset_id="",
                name="broken stencil pole with no code",
                asset_type="pole",
                latitude="20.2970",
                longitude="85.8250",
                elevation_m="41",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="5",
                attribute_json='{"height_m": 8}',
            ),
            row(
                asset_id="POLE-12",
                name="asset code not in utility format",
                asset_type="pole",
                latitude="20.2971",
                longitude="85.8251",
                elevation_m="41",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="5",
                attribute_json='{"height_m": 8}',
            ),
            row(
                asset_id="PL-0993",
                name="condition rating off the scale",
                asset_type="pole",
                latitude="20.2972",
                longitude="85.8252",
                elevation_m="41",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="14",
                attribute_json='{"height_m": 8}',
            ),
            row(
                asset_id="PL-0994",
                name="condition rating left blank",
                asset_type="pole",
                latitude="20.2973",
                longitude="85.8253",
                elevation_m="41",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="",
                attribute_json='{"height_m": 8}',
            ),
            row(
                asset_id="PL-0995",
                name="survey recorded in the future",
                asset_type="pole",
                latitude="20.2974",
                longitude="85.8254",
                elevation_m="41",
                surveyed_on="2099-03-01",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="5",
                attribute_json='{"height_m": 8}',
            ),
            row(
                asset_id="PL-0996",
                name="attribute snippet is not json",
                asset_type="pole",
                latitude="20.2975",
                longitude="85.8255",
                elevation_m="41",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="5",
                attribute_json="{height: 9}",
            ),
            row(
                asset_id="PL-0997",
                name="unrecognised kind of asset",
                asset_type="cable",
                latitude="20.2976",
                longitude="85.8256",
                elevation_m="41",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="active",
                condition_score="5",
                attribute_json='{"length_m": 40}',
            ),
            row(
                asset_id="PL-0998",
                name="decommissioned but rated as new",
                asset_type="pole",
                latitude="20.2977",
                longitude="85.8257",
                elevation_m="41",
                surveyed_on="2026-09-10",
                surveyor="Ramesh Patel",
                status="decommissioned",
                condition_score="8",
                attribute_json='{"height_m": 8}',
            ),
        ]
    )
    assert len(rows) == 62
    return rows


def main() -> None:
    target = Path(__file__).resolve().parent / "survey_export.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(build_rows())
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
