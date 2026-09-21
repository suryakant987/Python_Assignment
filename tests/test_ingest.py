from pathlib import Path

from asset_registry.ingest.pipeline import MissingColumnsError, StrictIngestAborted, ingest_csv_file
from tests.conftest import SAMPLE_CSV


def test_supplied_file_rejects_bad_rows_and_continues(db_session):
    result = ingest_csv_file(db_session, SAMPLE_CSV)
    assert result.rows_read == 62
    assert result.rows_accepted == 51
    assert result.rows_rejected == 11
    assert len(result.rejects) == 11
    reasons = " | ".join(item["reason"] for item in result.rejects)
    assert "already in use" in reasons
    assert "missing" in reasons
    assert "valid JSON" in reasons


def test_missing_column_stops_the_run(db_session, tmp_path: Path):
    broken = tmp_path / "broken.csv"
    broken.write_text("asset_id,name\nPL-0001,x\n", encoding="utf-8")
    try:
        ingest_csv_file(db_session, broken)
        assert False, "expected MissingColumnsError"
    except MissingColumnsError as exc:
        assert "latitude" in exc.missing


def test_strict_mode_aborts_and_stores_nothing(db_session, tmp_path: Path):
    sample = tmp_path / "one_bad.csv"
    sample.write_text(
        "asset_id,name,asset_type,latitude,longitude,elevation_m,surveyed_on,surveyor,status,condition_score,attribute_json\n"
        "PL-5001,Good pole,pole,20.29,85.82,40,2026-09-10,Anita Das,active,8,"
        '{"height_m": 9}\n'
        "BAD,Bad pole,pole,20.29,85.82,40,2026-09-10,Anita Das,active,8,"
        '{"height_m": 9}\n',
        encoding="utf-8",
    )
    try:
        ingest_csv_file(db_session, sample, strict=True)
        assert False, "expected StrictIngestAborted"
    except StrictIngestAborted:
        pass
    from asset_registry.db.models import Asset

    assert db_session.query(Asset).count() == 0
