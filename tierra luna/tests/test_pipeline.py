import os
import sys

import numpy as np
import pytest
import rasterio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GridConfig, HARMONIZED_BANDS, DATA_SOURCES_URLS
from lunar_extractor import extract_lunar_data, extract_lunar_from_files, compute_slope_and_roughness
from earth_extractor import extract_earth_data
from harmonizer_cleaner import clean_planetary_dataset, export_to_geotiff, dataset_to_dataframe
from pds_reader import parse_pds3_label, CACHE_DIR
from analog_finder import compute_analog_ranking, export_web_bundle


@pytest.fixture(scope="module")
def cfg():
    return GridConfig(grid_shape=(60, 60))


@pytest.fixture(scope="module")
def raw(cfg):
    return extract_lunar_data(cfg), extract_earth_data(cfg)


@pytest.fixture(scope="module")
def clean(cfg, raw):
    moon, am = clean_planetary_dataset(raw[0], "moon", cfg)
    earth, ae = clean_planetary_dataset(raw[1], "earth", cfg)
    return moon, earth, am, ae


def test_slope_flat_and_ramp():
    flat = np.zeros((10, 10), dtype=np.float32)
    s, r = compute_slope_and_roughness(flat, 500.0)
    assert np.allclose(s, 0) and np.allclose(r, 0)
    ramp = np.tile(np.arange(10, dtype=np.float32) * 500.0, (10, 1))
    s, _ = compute_slope_and_roughness(ramp, 500.0)
    assert np.allclose(s, 45.0, atol=0.1)


def test_raw_has_all_bands_same_shape(raw, cfg):
    for data in raw:
        assert list(data.keys()) == HARMONIZED_BANDS
        for b in HARMONIZED_BANDS:
            assert data[b].shape == cfg.grid_shape


def test_raw_contains_injected_artifacts(raw):
    assert (raw[0]["elevation_m"] == -32768).any()
    assert np.nanmax(raw[1]["temp_k"]) > 10000


@pytest.mark.parametrize("idx,rng", [(0, "valid_ranges_moon"), (1, "valid_ranges_earth")])
def test_clean_in_range_and_finite(clean, cfg, idx, rng):
    ranges = getattr(cfg, rng)
    for b in HARMONIZED_BANDS:
        a = clean[idx][b]
        assert np.isfinite(a).all(), b
        assert a.min() >= ranges[b][0] and a.max() <= ranges[b][1], b


def test_scale_fix_modis_dn(clean):
    audit = clean[3]
    row = audit[audit.variable == "temp_k"].iloc[0]
    assert row.scale_corrected_px > 0
    assert clean[1]["temp_k"].min() > 180


def test_audit_counts_sentinels(clean):
    row = clean[2][clean[2].variable == "elevation_m"].iloc[0]
    assert row.nodata_sentinel_px >= 12


def test_geotiff_7_bands_same_grid(clean, cfg, tmp_path):
    paths = []
    for name, data in (("moon", clean[0]), ("earth", clean[1])):
        p = str(tmp_path / f"{name}.tif")
        export_to_geotiff(data, p, name, cfg)
        paths.append(p)
    meta = []
    for p in paths:
        with rasterio.open(p) as src:
            assert src.count == 7
            assert src.res == (cfg.target_resolution_m, cfg.target_resolution_m)
            assert "Kelvin" in src.descriptions[HARMONIZED_BANDS.index("temp_k")]
            meta.append((src.width, src.height, src.res, src.crs))
    assert meta[0] == meta[1]


def test_csv_dataframe_columns_match(clean, cfg):
    dm = dataset_to_dataframe(clean[0], "moon", cfg)
    de = dataset_to_dataframe(clean[1], "earth", cfg)
    assert list(dm.columns) == list(de.columns)
    assert len(dm) == len(de) == 60 * 60
    assert not dm.isna().any().any() and not de.isna().any().any()


def test_pds3_labels_parsed_correctly():
    lbl_lola = os.path.join(CACHE_DIR, "ldem_64.lbl")
    lbl_ra = os.path.join(CACHE_DIR, "dgdr_ra_avg_cyl_032_img.lbl")
    lbl_st = os.path.join(CACHE_DIR, "dgdr_st_clc_cyl_0030_032_img.lbl")
    assert os.path.exists(lbl_lola) and os.path.exists(lbl_ra) and os.path.exists(lbl_st)

    info_lola = parse_pds3_label(open(lbl_lola).read(), "ldem_64.lbl")
    assert info_lola["lines"] == 11520 and info_lola["samples"] == 23040
    assert info_lola["scale"] == 0.5 and info_lola["ppd"] == 64.0

    info_ra = parse_pds3_label(open(lbl_ra).read(), "ra.lbl")
    assert info_ra["scale"] == 0.001 and info_ra["ppd"] == 32.0

    info_st = parse_pds3_label(open(lbl_st).read(), "st.lbl")
    assert info_st["scale"] == 0.02 and info_st["ppd"] == 32.0


def test_real_pds_tycho_window_and_cleaning(tmp_path):
    cfg_real = GridConfig(
        grid_shape=(120, 120),
        global_mode=False,
        moon_center_lat=-43.3,
        moon_center_lon=-11.4,
    )
    raw_pds = extract_lunar_from_files(
        cfg_real,
        lola_dem_path=DATA_SOURCES_URLS["lola_dem_pds_url"],
        diviner_temp_path=DATA_SOURCES_URLS["diviner_temp_pds_url"],
        diviner_rock_path=DATA_SOURCES_URLS["diviner_rock_pds_url"],
    )
    assert np.isfinite(raw_pds["elevation_m"]).all()
    assert -4000.0 < raw_pds["elevation_m"].min() < -3000.0
    assert 1000.0 < raw_pds["elevation_m"].max() < 2000.0

    clean_pds, audit_pds = clean_planetary_dataset(raw_pds, "moon", cfg_real)

    assert np.isfinite(clean_pds["rock_or_bare_frac"]).all()
    assert 0.0 <= clean_pds["rock_or_bare_frac"].min() <= clean_pds["rock_or_bare_frac"].max() <= 1.0

    assert np.isfinite(clean_pds["temp_k"]).all()
    assert 46.0 < clean_pds["temp_k"].min() and clean_pds["temp_k"].max() < 160.0

    assert np.isnan(clean_pds["sar_sigma0_db"]).all()
    tif_path = str(tmp_path / "moon_real.tif")
    export_to_geotiff(clean_pds, tif_path, "moon", cfg_real)
    with rasterio.open(tif_path) as src:
        assert src.count == 7
        sar_band = src.read(7)
        assert np.all(sar_band == cfg_real.nodata_value)


def test_analog_finder_ranking_and_weights(clean, cfg, tmp_path):
    dm = dataset_to_dataframe(clean[0], "moon", cfg)
    de = dataset_to_dataframe(clean[1], "earth", cfg)

    top_bal, _, meta_bal = compute_analog_ranking(dm, de, top_k=20)
    assert len(top_bal) == 20
    assert top_bal["similarity_pct"].iloc[0] >= top_bal["similarity_pct"].iloc[-1]
    assert 0.0 <= top_bal["similarity_pct"].min() <= top_bal["similarity_pct"].max() <= 100.0
    assert "matched_lunar_zone" in top_bal.columns

    top_therm, _, _ = compute_analog_ranking(
        dm,
        de,
        weights={"temp_k": 1.0, "slope_deg": 0.0, "roughness_m": 0.0, "elevation_rel_m": 0.0, "rock_or_bare_frac": 0.0, "sar_sigma0_db": 0.0},
        top_k=20,
    )
    assert not np.allclose(top_bal["similarity_pct"].to_numpy(), top_therm["similarity_pct"].to_numpy())

    paths = export_web_bundle(dm, de, out_dir=str(tmp_path), web_dir=str(tmp_path))
    assert os.path.exists(paths["ranking_csv"])
    assert os.path.exists(paths["web_js"])


def test_global_moon_and_earth_coverage():
    cfg_glob = GridConfig(grid_shape=(90, 180), global_mode=True)
    raw_moon = extract_lunar_data(
        cfg_glob, lola_dem_path=DATA_SOURCES_URLS["lola_dem_global_pds_url"]
    )
    raw_earth = extract_earth_data(cfg_glob)
    clean_m, _ = clean_planetary_dataset(raw_moon, "moon", cfg_glob)
    clean_e, _ = clean_planetary_dataset(raw_earth, "earth", cfg_glob)

    dm = dataset_to_dataframe(clean_m, "moon", cfg_glob, source="real_PDS")
    de = dataset_to_dataframe(clean_e, "earth", cfg_glob, source="global_model")

    assert dm["lat_deg"].min() < -85.0 and dm["lat_deg"].max() > 85.0
    assert dm["lon_deg"].min() < -175.0 and dm["lon_deg"].max() > 175.0
    assert de["lat_deg"].min() < -85.0 and de["lat_deg"].max() > 85.0
    assert de["lon_deg"].min() < -175.0 and de["lon_deg"].max() > 175.0
    assert dm["elevation_m"].min() < -5000.0 and dm["elevation_m"].max() > 5000.0


def test_verified_real_landmarks_moon_and_earth():
    cfg_glob = GridConfig(grid_shape=(90, 180), global_mode=True)
    raw_moon = extract_lunar_data(
        cfg_glob, lola_dem_path=DATA_SOURCES_URLS["lola_dem_global_pds_url"]
    )
    raw_earth = extract_earth_data(cfg_glob)
    clean_m, _ = clean_planetary_dataset(raw_moon, "moon", cfg_glob)
    clean_e, _ = clean_planetary_dataset(raw_earth, "earth", cfg_glob)

    def rc(lat, lon):
        return int(np.clip((90.0 - lat) / 2.0, 0, 89)), int(np.clip((lon + 180.0) / 2.0, 0, 179))

    r_spa, c_spa = rc(-53.0, -169.0)
    assert clean_m["elevation_m"][r_spa, c_spa] < -5000.0

    r_tycho, c_tycho = rc(-43.3, -11.4)
    assert clean_m["rock_or_bare_frac"][r_tycho, c_tycho] > 0.03
    assert clean_m["temp_k"][r_tycho, c_tycho] > 100.0

    r_imb, c_imb = rc(33.0, -16.0)
    assert clean_m["elevation_m"][r_imb, c_imb] < -1500.0
    assert clean_m["roughness_m"][r_imb, c_imb] < 100.0

    r_kor, c_kor = rc(-4.0, -157.4)
    assert clean_m["elevation_m"][r_kor, c_kor] > 2000.0

    r_sp, c_sp = rc(-88.0, 0.0)
    assert clean_m["temp_k"][r_sp, c_sp] < 75.0

    r_tib, c_tib = rc(33.0, 88.0)
    assert clean_e["elevation_m"][r_tib, c_tib] > 4500.0
    assert clean_e["temp_k"][r_tib, c_tib] < 282.0

    r_ata, c_ata = rc(-23.5, -68.0)
    assert clean_e["elevation_m"][r_ata, c_ata] > 3500.0
    assert clean_e["rock_or_bare_frac"][r_ata, c_ata] > 0.85

    r_ant, c_ant = rc(-80.0, 75.0)
    assert clean_e["elevation_m"][r_ant, c_ant] > 3500.0
    assert clean_e["temp_k"][r_ant, c_ant] < 230.0

    r_sah, c_sah = rc(21.0, 18.0)
    assert clean_e["rock_or_bare_frac"][r_sah, c_sah] > 0.85
    assert clean_e["temp_k"][r_sah, c_sah] > 300.0

    r_amz, c_amz = rc(-3.0, -62.0)
    assert 0.0 < clean_e["elevation_m"][r_amz, c_amz] < 200.0
    assert clean_e["rock_or_bare_frac"][r_amz, c_amz] < 0.10

    r_atl, c_atl = rc(0.0, -30.0)
    r_pac, c_pac = rc(0.0, -140.0)
    assert clean_e["elevation_m"][r_atl, c_atl] < 0.0
    assert clean_e["elevation_m"][r_pac, c_pac] < 0.0

    dm = dataset_to_dataframe(clean_m, "moon", cfg_glob, source="real_PDS")
    de = dataset_to_dataframe(clean_e, "earth", cfg_glob, source="real_NOAA")
    top_ranking, earth_scored, meta = compute_analog_ranking(dm, de, top_k=50)
    assert (earth_scored["elevation_m"] > 0.0).all()
    assert (top_ranking["elevation_m"] > 0.0).all()
    assert "mission_filters" in meta and "mission_stats" in meta
    assert "optimal_mission_zones" in meta
    for m_key in ("rover", "solar", "thermal", "ice", "all"):
        assert m_key in meta["optimal_mission_zones"]
        assert len(meta["optimal_mission_zones"][m_key]) >= 3
    for m_col in ("pass_rover", "pass_solar", "pass_thermal", "pass_ice", "pass_all"):
        assert m_col in top_ranking.columns


def test_mission_filters_json_and_cli_integration():
    from mission_filters import load_cfg, validate, selftest
    from rover_preset import selftest as rover_selftest

    selftest()
    assert rover_selftest() == 0
    cfg_m = load_cfg(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mission_filters.json"))
    problems = validate(cfg_m, strict=True)
    assert problems == []




