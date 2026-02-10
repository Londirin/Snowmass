from pathlib import Path

from app.aspen_raw import parse_latest_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "snowmass_summary_sample.htm"


def test_parse_latest_row_and_types() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    snapshot = parse_latest_snapshot(html)

    assert snapshot is not None
    assert snapshot.timestamp is not None
    assert snapshot.temp_mid_alt_f == 29.0
    assert snapshot.wind_speed_alpine_mph == 24.0
    assert snapshot.max_gust_alpine_mph == 38.0
    assert isinstance(snapshot.swe_24hr_inches, float)


def test_parse_nan_to_none() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    snapshot = parse_latest_snapshot(html)

    assert snapshot is not None
    assert snapshot.new_snow_inches is None
    assert snapshot.snowfall_1hr_inches is None
