from asset_registry.domain.cleaning import parse_coordinate, tidy_description, tidy_surveyor
from asset_registry.domain.constants import condition_band
from asset_registry.domain.geo import haversine_km
from asset_registry.domain.validation import validate_record


def test_description_trim_collapse_and_capitalise():
    cleaned = tidy_description("  old  TEAK   pole  ")
    assert cleaned == "Old Teak Pole"


def test_surveyor_variants_collapse_to_one_name():
    assert tidy_surveyor("ramesh  patel") == "Ramesh Patel"
    assert tidy_surveyor("RAMESH PATEL") == "Ramesh Patel"
    assert tidy_surveyor("Ramesh Patel") == "Ramesh Patel"


def test_compass_coordinates_become_signed_decimals():
    assert parse_coordinate("28.6148 N") == 28.6148
    assert parse_coordinate("20.2961 S") == -20.2961
    assert parse_coordinate("85.8245 E") == 85.8245
    assert parse_coordinate("85.8245 W") == -85.8245
    assert parse_coordinate("20.2961") == 20.2961


def test_condition_bands_at_boundaries():
    assert condition_band(10) == "GOOD"
    assert condition_band(8) == "GOOD"
    assert condition_band(7) == "FAIR"
    assert condition_band(5) == "FAIR"
    assert condition_band(4) == "POOR"
    assert condition_band(3) == "POOR"
    assert condition_band(2) == "CRITICAL"
    assert condition_band(0) == "CRITICAL"


def test_haversine_known_short_distance():
    distance = haversine_km(20.2961, 85.8245, 20.2971, 85.8245)
    assert 0.1 < distance < 0.15


def _valid(**overrides):
    row = {
        "asset_id": "PL-0142",
        "name": "Feeder pole",
        "asset_type": "pole",
        "latitude": "20.2961",
        "longitude": "85.8245",
        "elevation_m": "40",
        "surveyed_on": "2026-09-10",
        "surveyor": "Anita Das",
        "status": "active",
        "condition_score": "7",
        "attribute_json": '{"height_m": 9}',
    }
    row.update(overrides)
    return row


def test_valid_row_is_accepted_and_standardised():
    result = validate_record(_valid(asset_type="PoLe", name="  feeder   pole "))
    assert result.ok
    assert result.asset is not None
    assert result.asset.asset_type == "pole"
    assert result.asset.name == "Feeder Pole"
    assert result.asset.condition_band == "FAIR"


def test_name_length_boundaries():
    assert validate_record(_valid(name="abc")).ok
    assert validate_record(_valid(name="a" * 120)).ok
    assert not validate_record(_valid(name="ab")).ok
    assert not validate_record(_valid(name="a" * 121)).ok


def test_latitude_boundaries():
    assert validate_record(_valid(latitude="-90")).ok
    assert validate_record(_valid(latitude="90")).ok
    assert not validate_record(_valid(latitude="90.1")).ok
    assert not validate_record(_valid(latitude="-90.1")).ok


def test_longitude_must_be_numeric():
    result = validate_record(_valid(longitude="east of temple"))
    assert not result.ok
    assert any(issue.field == "longitude" for issue in result.issues)


def test_condition_14_is_rejected():
    result = validate_record(_valid(condition_score="14"))
    assert not result.ok
    assert any(issue.field == "condition_score" for issue in result.issues)


def test_blank_condition_is_rejected():
    result = validate_record(_valid(condition_score=""))
    assert not result.ok


def test_future_date_is_rejected():
    result = validate_record(_valid(surveyed_on="2099-03-01"))
    assert not result.ok
    assert any(issue.field == "surveyed_on" for issue in result.issues)


def test_invalid_json_is_rejected():
    result = validate_record(_valid(attribute_json="{height: 9}"))
    assert not result.ok


def test_unknown_type_is_rejected():
    result = validate_record(_valid(asset_type="cable"))
    assert not result.ok


def test_bad_asset_code_is_rejected():
    result = validate_record(_valid(asset_id="POLE-12"))
    assert not result.ok


def test_missing_asset_code_is_rejected():
    result = validate_record(_valid(asset_id=""))
    assert not result.ok


def test_decommissioned_cannot_be_above_2():
    result = validate_record(_valid(status="decommissioned", condition_score="8"))
    assert not result.ok


def test_duplicate_id_in_batch_is_rejected():
    result = validate_record(_valid(), existing_ids={"PL-0142"}, require_unique=True)
    assert not result.ok
    assert any("already in use" in issue.reason for issue in result.issues)


def test_blank_elevation_is_stored_as_not_recorded():
    result = validate_record(_valid(elevation_m=""))
    assert result.ok
    assert result.asset is not None
    assert result.asset.elevation_m is None
